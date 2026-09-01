import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rl_engine import RLEngine  # noqa: E402
from rl_engine.storage import digest  # noqa: E402


def main() -> None:
    fixture_path = ROOT / "tests" / "fixtures" / "final_solution_report.json"
    report = json.loads(fixture_path.read_text(encoding="utf-8"))
    runtime = ROOT / "runtime" / "laptop1_only_acceptance"
    laptop2_simulation = RLEngine(runtime / "simulated_laptop2")
    receipt = laptop2_simulation.ingest_final_report(report)
    decision = {
        "schema_version": "rl.user-save-decision.v1",
        "run_id": report["run_id"],
        "report_sha256": digest(report),
        "decision": "SAVE",
        "actor": "laptop1-acceptance-fixture",
        "decided_at": "2026-09-01T12:01:00Z"
    }
    result = laptop2_simulation.record_user_decision(decision)
    if receipt["state"] != "AWAITING_USER_DECISION" or result["state"] != "SAVED_AND_QUEUED_FOR_SYNC":
        raise SystemExit("Laptop 1-only acceptance failed")
    event_path = runtime / "simulated_laptop2" / "sync" / "outbox" / f"{result['event_id']}.json"
    envelope = json.loads(event_path.read_text(encoding="utf-8"))
    acknowledgement = RLEngine(runtime / "laptop1").receive_sync_event(envelope)
    if acknowledgement["state"] != "APPLIED":
        raise SystemExit("Laptop 1 replica acceptance failed")
    print(json.dumps({
        "mode": "SYNTHETIC_LAPTOP1_ONLY",
        "receipt": receipt,
        "result": result,
        "laptop1_acknowledgement": acknowledgement,
        "runtime": str(runtime)
    }, indent=2))


if __name__ == "__main__":
    main()
