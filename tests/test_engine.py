import copy
import json
import tempfile
import unittest
from pathlib import Path

from rl_engine import ConflictError, ContractError, NotEligibleError, RLEngine
from rl_engine.storage import digest


FIXTURE = Path(__file__).parent / "fixtures" / "final_solution_report.json"


def report() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def decision(payload: dict, choice: str = "SAVE") -> dict:
    return {
        "schema_version": "rl.user-save-decision.v1",
        "run_id": payload["run_id"],
        "report_sha256": digest(payload),
        "decision": choice,
        "actor": "laptop1-test-user",
        "decided_at": "2026-09-01T12:01:00Z"
    }


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_rl_is_strictly_post_phase4(self):
        payload = report()
        payload["report_status"] = "IN_PROGRESS"
        with self.assertRaises(ContractError):
            RLEngine(self.root).ingest_final_report(payload)

    def test_save_creates_validated_approach_and_sync_event(self):
        payload = report()
        engine = RLEngine(self.root)
        receipt = engine.ingest_final_report(payload)
        result = engine.record_user_decision(decision(payload))
        self.assertEqual(receipt["state"], "AWAITING_USER_DECISION")
        self.assertEqual(result["state"], "SAVED_AND_QUEUED_FOR_SYNC")
        self.assertEqual(len(list((self.root / "registry" / "validated").glob("*.json"))), 1)
        self.assertEqual(len(list((self.root / "sync" / "outbox").glob("*.json"))), 1)
        status = json.loads((self.root / "status_bar" / "rl" / "current.json").read_text())
        self.assertEqual(status["placement"], "POST_PHASE4_ONLY")

    def test_do_not_save_keeps_audit_but_not_registry(self):
        payload = report()
        engine = RLEngine(self.root)
        engine.ingest_final_report(payload)
        result = engine.record_user_decision(decision(payload, "DO_NOT_SAVE"))
        self.assertEqual(result["state"], "NOT_SAVED_BY_USER")
        self.assertTrue((self.root / "audit" / "reports" / f"{payload['run_id']}.json").exists())
        self.assertFalse((self.root / "registry" / "validated").exists())

    def test_review_later_can_be_followed_by_save(self):
        payload = report()
        engine = RLEngine(self.root)
        engine.ingest_final_report(payload)
        self.assertEqual(engine.record_user_decision(decision(payload, "REVIEW_LATER"))["state"], "REVIEW_LATER")
        later = decision(payload, "SAVE")
        later["decided_at"] = "2026-09-01T13:00:00Z"
        self.assertEqual(engine.record_user_decision(later)["state"], "SAVED_AND_QUEUED_FOR_SYNC")

    def test_failed_solution_cannot_enter_registry(self):
        payload = report()
        payload["phase4_outcome"]["fault_cleared"] = False
        engine = RLEngine(self.root)
        engine.ingest_final_report(payload)
        with self.assertRaises(NotEligibleError):
            engine.record_user_decision(decision(payload))

    def test_blocked_report_is_auditable_but_not_saveable(self):
        payload = report()
        payload["phase4_outcome"].update({
            "gate_decision": "BLOCKED_GUARDRAIL",
            "agent_proposal": None,
            "guardrail_result": {"passed": False, "reason": "outside allowed surface"},
            "execution_result": None,
            "after_state": None,
            "fault_cleared": None,
            "human_intervention_required": True,
            "message": "Human review required."
        })
        engine = RLEngine(self.root)
        engine.ingest_final_report(payload)
        with self.assertRaises(NotEligibleError):
            engine.record_user_decision(decision(payload))

    def test_run_id_conflict_fails_closed(self):
        payload = report()
        engine = RLEngine(self.root)
        engine.ingest_final_report(payload)
        changed = copy.deepcopy(payload)
        changed["phase3_analysis"]["observations"].append("Conflicting late mutation")
        with self.assertRaises(ConflictError):
            engine.ingest_final_report(changed)

    def test_repeated_calls_are_idempotent(self):
        payload = report()
        engine = RLEngine(self.root)
        self.assertEqual(engine.ingest_final_report(payload), engine.ingest_final_report(payload))
        first = engine.record_user_decision(decision(payload))
        second = engine.record_user_decision(decision(payload))
        self.assertEqual(first, second)
        self.assertEqual(len(list((self.root / "sync" / "outbox").glob("*.json"))), 1)

    def test_feedback_must_bind_to_exact_report_digest(self):
        payload = report()
        engine = RLEngine(self.root)
        engine.ingest_final_report(payload)
        bad = decision(payload)
        bad["report_sha256"] = "0" * 64
        with self.assertRaises(ContractError):
            engine.record_user_decision(bad)

    def test_laptop2_to_laptop1_sync_round_trip(self):
        payload = report()
        laptop2 = RLEngine(self.root / "laptop2")
        laptop2.ingest_final_report(payload)
        result = laptop2.record_user_decision(decision(payload))
        event_path = self.root / "laptop2" / "sync" / "outbox" / f"{result['event_id']}.json"
        envelope = json.loads(event_path.read_text(encoding="utf-8"))

        laptop1 = RLEngine(self.root / "laptop1")
        first = laptop1.receive_sync_event(envelope)
        second = laptop1.receive_sync_event(envelope)
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "APPLIED")
        self.assertTrue((self.root / "laptop1" / "registry" / "replica" / f"{result['approach_id']}.json").exists())

    def test_corrupt_sync_payload_is_rejected(self):
        payload = report()
        laptop2 = RLEngine(self.root / "laptop2")
        laptop2.ingest_final_report(payload)
        result = laptop2.record_user_decision(decision(payload))
        event_path = self.root / "laptop2" / "sync" / "outbox" / f"{result['event_id']}.json"
        envelope = json.loads(event_path.read_text(encoding="utf-8"))
        envelope["payload"]["status"] = "CORRUPTED"
        with self.assertRaises(ContractError):
            RLEngine(self.root / "laptop1").receive_sync_event(envelope)


if __name__ == "__main__":
    unittest.main()
