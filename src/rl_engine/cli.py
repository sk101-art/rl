import argparse
import json
from pathlib import Path

from .engine import RLEngine


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Post-Phase-4 RL evidence engine")
    parser.add_argument("--runtime", default="runtime")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="ingest one FINAL combined Phase 3+4 report")
    ingest.add_argument("report")
    feedback = sub.add_parser("feedback", help="record the user's save decision")
    feedback.add_argument("decision")
    receive = sub.add_parser("receive", help="apply one checksum-verified sync envelope")
    receive.add_argument("event")
    status = sub.add_parser("status", help="print current RL UI projection")

    args = parser.parse_args()
    engine = RLEngine(args.runtime)
    if args.command == "ingest":
        result = engine.ingest_final_report(_load(args.report))
    elif args.command == "feedback":
        result = engine.record_user_decision(_load(args.decision))
    elif args.command == "receive":
        result = engine.receive_sync_event(_load(args.event))
    else:
        result = engine.store.read("status_bar", "rl", "current.json") or {"state": "IDLE"}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
