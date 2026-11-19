# Run state

- run_id: `<RUN_ID>`
- status: `in_progress` <!-- in_progress | waiting_for_human | blocked | complete -->
- next_nodes: `<LANGGRAPH_NEXT_NODES>`

SQLite checkpoints are the resume source; this file is a readable projection.
The CLI rewrites this file from graph state after execution updates and on status inspection.
Do not edit it to skip a stage or approve a gate.

## Stage attempts

| Stage | Attempts |
| --- | ---: |
| generation | 0 |
| refactor | 0 |
| repair_original | 0 |
| repair_refactored | 0 |
| gap_original | 0 |
| gap_refactored | 0 |

## Pending human review

The CLI inserts the pending gate, reviewed artifact paths, and exact artifact hash here.
Supply a separate decision JSON after actual review; do not edit the evidence log.

## Blocked

The CLI records the stage and reason when validation or an attempt limit stops a run.
