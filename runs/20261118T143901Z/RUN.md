# Run 20261118T143901Z: refactored baseline (manual, not a pipeline run)

P3 ran the same JUnit suite against Jordan's State-pattern `SeasonSwitch` by hand. Like
`runs/20261116T193013Z/` (the original), it records a coverage number; it is not evidence that the
agent pipeline ran.

| | |
|---|---|
| Command | `scripts/coverage.sh refactored` |
| Code | `talha/p3-build-ops` 2aa2112 + `jordan/p5-refactor` 01ac6bc + `miguel/p4-testgen-skill` 113976c + `loc/p2-langgraph` b79cd8a, merged locally with no conflicts |
| Tools | JDK 17.0.14, Maven 3.10.0, JUnit 5.10.2, JaCoCo 0.8.12, macOS |
| Tests | 21 run, 0 failures, 0 errors, 0 skipped: the same `SeasonSwitchTest.java` as the original run, unchanged |
| Branch coverage | **8 / 8 = 100%** (`coverage.txt`; `main()` excluded) |

Per method (from `jacoco.xml`): `CoolState.timerOff` 2/2, `CoolState.roomActionPerformed` 2/2,
`HeatState.timerOff` 2/2, `HeatState.roomActionPerformed` 2/2. Every line outside `main()` is
covered, in every class (`SeasonSwitch`, `OffState`, `CoolState`, `HeatState`, `NoOpState`, `AC`,
`Heater`, `Room`).

Why 8 branches instead of 28: the original decides by `switch (state)` in five methods. The
refactor sends each call to the current state object instead, so those decisions become method
dispatch. JaCoCo doesn't count dispatch as a branch. What's left are the temperature checks
(68 and 77) and the device on/off checks in the room tick.
