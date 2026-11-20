# Run state

- run_id: `20261119T232011Z-7ecf1e`
- status: `waiting_for_human`
- next_nodes: `review_testcases`

SQLite checkpoints are the resume source; this file is a readable projection.

## Stage attempts

| Stage | Attempts |
| --- | ---: |
| generation | 3 |

## Pending human review

```json
{
  "gate": "review_testcases",
  "artifact_sha256": "245868e3f993f65c91d16b79170f7b3fe6da122312add3fb640c1e32d2951945",
  "run_dir": "/home/kyle/Documents/CSE 4392/Assignments/Team Assignment 3/CSE-4392-Multi-Agent-System/runs/20261119T232011Z-7ecf1e",
  "cases": "/home/kyle/Documents/CSE 4392/Assignments/Team Assignment 3/CSE-4392-Multi-Agent-System/runs/20261119T232011Z-7ecf1e/testcases_final.json",
  "sources": "/home/kyle/Documents/CSE 4392/Assignments/Team Assignment 3/CSE-4392-Multi-Agent-System/runs/20261119T232011Z-7ecf1e/workspace/java/src",
  "notes": "/home/kyle/Documents/CSE 4392/Assignments/Team Assignment 3/CSE-4392-Multi-Agent-System/runs/20261119T232011Z-7ecf1e/dedupe-report.md",
  "proposed_tests": [],
  "instruction": "Review the artifacts, source diff, and any proposed tests. Supply reviewer, decision, requested_changes, and this artifact_sha256."
}
```
