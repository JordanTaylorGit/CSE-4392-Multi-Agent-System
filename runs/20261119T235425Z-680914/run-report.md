# Pipeline run report

Status: **blocked**.

| Target | Tests | Passed | Covered | Missed | Branch % | Excluded main branches |
| --- | ---: | --- | ---: | ---: | ---: | ---: |

Coverage counts method-level JaCoCo branches once and excludes main(), following P3's scope.
The 100% gate requires zero missed branches and a nonempty passing suite; rounded percentages do not decide it.
EP and BVA are separate parallel graph nodes and join before review.
An Ollama server may queue concurrent requests depending on its configuration.
Approved Java tests are reused unchanged against the refactored Maven profile.
Human approvals, model transcripts, source diffs, and build reports are stored in this run directory.

Blocked: merge: merge_cases: 
ERROR: Conflicting expected results: EP-12 and BVA-01 have the same dedupe key ['unit', 'setup', 'inputs']

