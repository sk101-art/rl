# Frozen v1 contracts

## `phase4.solution-report.v1`

Produced once by Laptop 2 after Phase 4. It contains:

- stable run, incident and correlation identifiers;
- normalized matching context;
- Phase 3 source artifact, observations and technical solution;
- Phase 4 source artifact, safety decision, before/after state, executed action and timings;
- an artifact manifest with SHA-256 values.

Blocked reports remain valid final audit reports, using `fault_cleared: null`. They cannot be
saved as reusable approaches.

## `rl.user-save-decision.v1`

The UI must reference both `run_id` and the exact final-report SHA-256. Choices are:

- `SAVE`: attempt to enter the validated registry;
- `DO_NOT_SAVE`: close the run without a reusable entry;
- `REVIEW_LATER`: keep the run pending and allow a later final decision.

## `rl.saved-approach.v1`

Created only after eligibility checks. It contains the normalized fingerprint, Phase 3
solution, Phase 4 proof and source-report digest.

## `rl.sync-envelope.v1`

An idempotent transport envelope containing an event ID, event type, run ID, timestamp,
payload and payload SHA-256. Receivers must acknowledge by event ID and dead-letter checksum
conflicts.
