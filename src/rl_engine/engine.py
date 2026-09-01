from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import validate
from .errors import ContractError, NotEligibleError
from .fingerprint import build_fingerprint
from .storage import AtomicStore, digest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class RLEngine:
    """Consumes completed Phase 3+4 reports; it never participates before Phase 4."""

    def __init__(self, runtime_root: str | Path = "runtime"):
        self.store = AtomicStore(runtime_root)

    def ingest_final_report(self, report: dict[str, Any]) -> dict[str, Any]:
        validate(report, "phase4_solution_report_v1.schema.json")
        if report["report_status"] != "FINAL":
            raise ContractError("RL accepts reports only after Phase 4 has produced report_status=FINAL")

        run_id = report["run_id"]
        report_sha = digest(report)
        self.store.write(report, "audit", "reports", f"{run_id}.json", immutable=True)
        existing_receipt = self.store.read("audit", "receipts", f"{run_id}.json")
        if existing_receipt is not None:
            return existing_receipt
        receipt = {
            "schema_version": "rl.ingest-receipt.v1",
            "run_id": run_id,
            "report_sha256": report_sha,
            "state": "AWAITING_USER_DECISION",
            "received_at": _now(),
        }
        self.store.write(receipt, "audit", "receipts", f"{run_id}.json", immutable=True)
        self._write_status(run_id, "AWAITING_USER_DECISION", report_sha)
        return receipt

    def record_user_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        validate(decision, "user_save_decision_v1.schema.json")
        run_id = decision["run_id"]
        report = self.store.read("audit", "reports", f"{run_id}.json")
        if report is None:
            raise ContractError(f"no completed Phase 4 report is stored for run_id={run_id}")
        if decision["report_sha256"] != digest(report):
            raise ContractError("user decision does not reference the stored report SHA-256")

        decision_sha = digest(decision)
        existing_result = self.store.read("audit", "results", f"{run_id}.json")
        if existing_result is not None:
            return existing_result
        self.store.write(decision, "audit", "decisions", run_id, f"{decision_sha}.json", immutable=True)
        choice = decision["decision"]
        if choice == "SAVE":
            result = self._save_approach(report, decision)
        elif choice == "DO_NOT_SAVE":
            result = self._finalize_without_registry(report, "NOT_SAVED_BY_USER")
        else:
            result = self._finalize_without_registry(report, "REVIEW_LATER")
        if choice != "REVIEW_LATER":
            self.store.write(result, "audit", "results", f"{run_id}.json", immutable=True)
        self._write_status(run_id, result["state"], digest(report))
        return result

    def receive_sync_event(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Apply a Laptop 2 outbox event to a Laptop 1 read-only replica."""
        validate(envelope, "sync_envelope_v1.schema.json")
        if envelope["payload_sha256"] != digest(envelope["payload"]):
            raise ContractError("sync envelope payload SHA-256 does not match its payload")

        event_id = envelope["event_id"]
        existing_ack = self.store.read("sync", "acknowledgements", f"{event_id}.json")
        self.store.write(envelope, "sync", "inbox", f"{event_id}.json", immutable=True)
        if existing_ack is not None:
            return existing_ack

        if envelope["event_type"] == "APPROACH_SAVED":
            approach = envelope["payload"]
            validate(approach, "saved_approach_v1.schema.json")
            self.store.write(
                approach,
                "registry", "replica", f"{approach['approach_id']}.json",
                immutable=True,
            )

        acknowledgement = {
            "schema_version": "rl.sync-acknowledgement.v1",
            "event_id": event_id,
            "run_id": envelope["run_id"],
            "payload_sha256": envelope["payload_sha256"],
            "state": "APPLIED",
            "applied_at": _now(),
        }
        self.store.write(
            acknowledgement,
            "sync", "acknowledgements", f"{event_id}.json",
            immutable=True,
        )
        return acknowledgement

    def _save_approach(self, report: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        outcome = report["phase4_outcome"]
        if (
            outcome["gate_decision"] != "EXECUTED"
            or outcome["fault_cleared"] is not True
            or outcome["human_intervention_required"] is not False
        ):
            raise NotEligibleError("only executed, verified, fault-cleared outcomes can be reusable")

        fingerprint, normalized_context = build_fingerprint(report["matching_context"])
        report_sha = digest(report)
        approach_id = f"appr_{fingerprint[:16]}_{report_sha[:12]}"
        approach = {
            "schema_version": "rl.saved-approach.v1",
            "approach_id": approach_id,
            "run_id": report["run_id"],
            "incident_id": report["incident_id"],
            "fingerprint_sha256": fingerprint,
            "matching_context": normalized_context,
            "phase3_solution": report["phase3_analysis"]["technical_solution"],
            "phase4_verification": outcome,
            "source_report_sha256": report_sha,
            "saved_by": decision["actor"],
            "saved_at": _now(),
            "status": "VALIDATED",
        }
        validate(approach, "saved_approach_v1.schema.json")
        self.store.write(approach, "registry", "validated", f"{approach_id}.json", immutable=True)
        envelope = self._emit_sync_event("APPROACH_SAVED", report["run_id"], approach)
        return {"run_id": report["run_id"], "state": "SAVED_AND_QUEUED_FOR_SYNC", "approach_id": approach_id, "event_id": envelope["event_id"]}

    def _finalize_without_registry(self, report: dict[str, Any], state: str) -> dict[str, Any]:
        envelope = self._emit_sync_event("USER_DECISION_RECORDED", report["run_id"], {"state": state})
        return {"run_id": report["run_id"], "state": state, "event_id": envelope["event_id"]}

    def _emit_sync_event(self, event_type: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = {
            "schema_version": "rl.sync-envelope.v1",
            "event_id": f"evt_{uuid4().hex}",
            "event_type": event_type,
            "run_id": run_id,
            "created_at": _now(),
            "payload_sha256": digest(payload),
            "payload": payload,
        }
        validate(envelope, "sync_envelope_v1.schema.json")
        self.store.write(envelope, "sync", "outbox", f"{envelope['event_id']}.json", immutable=True)
        return envelope

    def _write_status(self, run_id: str, state: str, report_sha: str) -> None:
        self.store.write(
            {
                "schema_version": "ui.rl-status.v1",
                "component": "rl",
                "placement": "POST_PHASE4_ONLY",
                "run_id": run_id,
                "state": state,
                "source_report_sha256": report_sha,
                "updated_at": _now(),
            },
            "status_bar", "rl", "current.json",
        )
