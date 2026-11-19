# Run 20261116T193013Z: original baseline (manual, not a pipeline run)

P3 ran the existing JUnit suite against the original `SeasonSwitch` by hand, before the
orchestrator exists. It records the starting coverage number; it is not evidence that the agent
pipeline ran (no `testcases_*.json`, `hitl_decisions.json`, `transcripts/` or `STATE.md` yet).

| | |
|---|---|
| Command | `scripts/coverage.sh original` |
| Code | `talha/p3-build-ops` 9d54b83 + `jordan/p5-refactor` e7afdc8 (SeasonSwitchTest.java) + `miguel/p4-testgen-skill` 6e67e81, merged locally |
| Tools | JDK 17.0.14, Maven 3.10.0, JUnit 5.10.2, JaCoCo 0.8.12, macOS |
| Tests | 21 run, 0 failures, 0 errors, 0 skipped (`surefire/TEST-cse4392.SeasonSwitchTest.xml`) |
| Branch coverage | **28 / 28 = 100%** (`coverage.txt`; `main()` excluded, see `docs/original-behavior.md`) |

Per method (from `jacoco.xml`): `cool` 4/4, `heat` 4/4, `off` 4/4, `timerOff` 8/8,
`Room.actionPerformed` 8/8. `main` 0/8 is left out of the number.

Files: `coverage.txt` (the coverage.sh line), `jacoco.xml`, `surefire/*.xml`, `log.txt` (full
console output, including the program's own "Cooling/Heating started" lines).
