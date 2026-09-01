# Laptop 2 integration

Install this repository beside, not inside, the Phase 3/4 source tree. Phase 4 remains the
owner of the combined report.

```python
from rl_engine import RLEngine

engine = RLEngine("runtime/rl")

# Call only after Phase 4 has atomically finalized the combined report.
receipt = engine.ingest_final_report(final_combined_report)

# Call after the UI posts SAVE, DO_NOT_SAVE, or REVIEW_LATER.
result = engine.record_user_decision(user_decision)
```

The Phase 4 orchestrator should treat ingestion failure as a delivery failure, not as a Phase
4 execution failure. Keep the final report, retry with backoff, and reuse the same `run_id`.
Identical retries are idempotent; changed content under the same `run_id` is rejected.

Production checklist:

- Write the combined report atomically before calling RL.
- Include actual Phase 3 and Phase 4 artifact SHA-256 values.
- Redact credentials before report finalization.
- Display the feedback prompt only after the ingestion receipt says
  `AWAITING_USER_DECISION`.
- Send `SAVE` only after explicit user selection.
- Synchronize outbox events by event ID and acknowledge them durably.
