# Run state

- run_id: `<RUN_ID>`
- status: `in_progress`        <!-- in_progress | complete | aborted -->
- current_step: `1`
- started_utc: `<ISO-8601>`
- reviewer: `<name>`

This file is the resume point. Update it after every step. If the session dies, the orchestrator
reads `current_step` and continues from there instead of restarting.

## Step log

| step | stage | status | started_utc | finished_utc | notes |
|------|-------|--------|-------------|--------------|-------|
| 1 | testgen (generate, original) | pending | | | |
| 2 | refactor-state | pending | | | |
| 3 | G3 HITL review | pending | | | |
| 4 | testgen (adapt, refactored) | pending | | | |
| 5 | halt | pending | | | |

## Gate iterations

| gate | attempts | last outcome |
|------|----------|--------------|
| G1 (inside testgen) | 0 | |
| G3 | 0 | |

## Open questions for the human

<!-- Anything the orchestrator stopped on. Empty means nothing is blocked. -->
