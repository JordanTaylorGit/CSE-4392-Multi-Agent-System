# Pipeline run report

Status: **complete**.

| Target | Tests | Passed | Covered | Missed | Branch % | Excluded main branches |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| original | 41 | True | 28 | 0 | 100.0000 | 8 |
| refactored | 41 | True | 8 | 0 | 100.0000 | 8 |

Coverage counts method-level JaCoCo branches once and excludes main(), following P3's scope.
The 100% gate requires zero missed branches and a nonempty passing suite; rounded percentages do not decide it.
EP and BVA are separate parallel graph nodes and join before review.
An Ollama server may queue concurrent requests depending on its configuration.
Approved Java tests are reused unchanged against the refactored Maven profile.
Human approvals, model transcripts, source diffs, and build reports are stored in this run directory.
