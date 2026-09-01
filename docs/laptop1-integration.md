# Laptop 1 integration

Laptop 1 currently performs boundary verification only. Do not insert RL into the Phase 1 or
Phase 2 pipeline and do not change their contracts.

Run:

```powershell
.\VERIFY_LAPTOP1_ONLY.bat
```

The acceptance script:

1. Creates an isolated RL virtual environment.
2. Runs the complete RL test suite.
3. Ingests a synthetic, explicitly labeled final Phase 3+4 fixture.
4. Records `SAVE` feedback.
5. Verifies the registry, outbox and UI projection.

Later, Laptop 1 may receive validated approach events. That receiver must remain read-only
with respect to Laptop 2's authoritative registry and must not affect Phase 1/2 until a
separate, explicitly approved milestone.

To exercise or apply one received event:

```powershell
.\RL_ENGINE.bat --runtime runtime receive path\to\event.json
```

The receiver verifies the envelope contract and payload SHA-256, stores it idempotently,
updates only `registry/replica/`, and writes an acknowledgement.
