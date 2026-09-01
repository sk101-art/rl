# Auto-SRE RL — post-Phase-4 learning boundary

This repository is the independent learning and synchronization component for Auto-SRE.
It **never runs before or during Phase 4**. Laptop 2 first completes one combined Phase 3+4
solution report. RL then archives that final report and waits for the user's decision.

```text
Laptop 1: Phase 1 -> Phase 2 -> Phase 3 input handoff
Laptop 2: Phase 3 -> Phase 4 -> FINAL combined solution report
                                      |
                                      v
                             RL ingest -> user choice
                                      |
                         SAVE -> registry + sync outbox
```

## Non-negotiable rules

- No RL routing, matching, or intervention before Phase 4.
- Phase 3 and Phase 4 are preserved together in `phase4.solution-report.v1`.
- Only `FINAL` reports are accepted.
- Only `EXECUTED` and `fault_cleared=true` reports can become reusable approaches.
- `DO_NOT_SAVE` retains audit evidence but creates no reusable approach.
- Reusing a `run_id` with different content fails closed.
- All writes are atomic and all synchronization payloads carry SHA-256 digests.
- This repository does not import or modify Phase 1, Phase 2, Phase 3, or Phase 4 code.

## Use immediately after cloning

```powershell
.\RL_ENGINE.bat --runtime runtime status
```

The Windows wrappers need only Python 3.10 or newer. Editable installation is optional.

## Laptop 1-only acceptance

This verifies the independent RL boundary with a synthetic completed report. It does not
pretend Phase 3 or Phase 4 ran on Laptop 1.

```powershell
.\VERIFY_LAPTOP1_ONLY.bat
```

## Production calls from Laptop 2

After Phase 4 atomically writes the combined report:

```powershell
.\RL_ENGINE.bat --runtime runtime ingest path\to\phase4_solution_report.json
```

After the UI writes the user's decision:

```powershell
.\RL_ENGINE.bat --runtime runtime feedback path\to\user_save_decision.json
```

See [Laptop 2 integration](docs/laptop2-integration.md) and [contracts](docs/contracts.md).

## Runtime boundary

```text
runtime/
├── audit/
│   ├── reports/<run_id>.json
│   ├── receipts/<run_id>.json
│   ├── decisions/<run_id>/<decision_sha>.json
│   └── results/<run_id>.json
├── registry/validated/<approach_id>.json
├── registry/replica/<approach_id>.json
├── sync/
│   ├── outbox/<event_id>.json
│   ├── inbox/<event_id>.json
│   └── acknowledgements/<event_id>.json
└── status_bar/rl/current.json
```

Runtime files are deliberately ignored by Git.

Laptop 1 applies an envelope copied from Laptop 2 with:

```powershell
.\RL_ENGINE.bat --runtime runtime receive path\to\sync_envelope.json
```
