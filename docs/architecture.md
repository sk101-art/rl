# Architecture

## Correct placement

RL is a terminal consumer of the completed Laptop 2 solution report:

1. Phase 3 performs multi-agent RCA and proposes a technical solution.
2. Phase 4 applies the proposal only inside its safety boundary and observes the result.
3. Phase 4 assembles one `phase4.solution-report.v1` containing both histories.
4. RL validates and archives the final report.
5. The UI offers `SAVE`, `DO_NOT_SAVE`, or `REVIEW_LATER`.
6. `SAVE` is accepted only for a verified, cleared outcome.
7. The saved approach and its evidence are placed in an atomic sync envelope.

RL cannot affect the incident currently being processed. Learning begins only after that
incident's Phase 4 report is complete.

## Two-laptop deployment

| Machine | Current responsibility | RL repository use |
|---|---|---|
| Laptop 1 | Phase 1, frozen Phase 2, Phase 3-ready handoff | Contract/fixture verification now; synchronized registry consumer later |
| Laptop 2 | Phase 3, Phase 4, combined report, feedback UI | Authoritative ingest, validated registry and outbox producer |

The Git repository is identical on both laptops. Runtime state is never synchronized through
Git. Initially, `runtime/sync/outbox` can be copied through the frozen file handoff. NATS can
replace that transport later without changing any schema.

Laptop 1 applies each received event to `registry/replica/` and writes a durable
acknowledgement. It never writes Laptop 2's authoritative `registry/validated/` directory.

## Truth model

- Immutable audit files answer what happened.
- The validated registry answers what the user allowed the system to reuse.
- The outbox answers what still needs synchronization.
- `status_bar/rl/current.json` is only an atomic UI projection.
