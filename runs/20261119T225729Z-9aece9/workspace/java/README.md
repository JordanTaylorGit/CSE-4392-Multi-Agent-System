# Java artifacts

```
src/original/java/cse4392/    SeasonSwitch.java            <- Canvas original, do not reformat
src/refactored/java/cse4392/  SeasonSwitch.java + SeasonState + concrete states
src/test/java/cse4392/        SeasonSwitchTest.java, SeasonSwitchRefactoredTest.java
```

The original and refactored Subject share the class name `SeasonSwitch` on purpose (assignment
hint: reusing the tests is the point). They therefore live in separate source roots selected by
Maven profile:

```bash
mvn -P original   test     # original code
mvn -P refactored test     # state-pattern code, same tests
../scripts/coverage.sh original
```

## What the original actually is

Not a month-to-season mapper. It is a thermostat state machine:

- `static int state` in `{OFF, COOL, HEAT}`, plus constants `OFF=0, COOL=1, HEAT=2`.
- Entry points `cool()`, `heat()`, `off()`, `timerOff()`; `actionPerformed` delegates to `timerOff`.
- `coolTemp = 68`, `heatTemp = 77`; `Room.temp` starts at 70 and drifts on a 400 ms timer while
  `SeasonSwitch.timer` ticks every 1200 ms.
- `Room` is an inner class reading the outer `state`, `ac`, and `heater` directly.

That shape is why the assignment wants a State-pattern refactor: three `switch (state)` blocks in
the Subject are exactly the smell being removed. It is also why the tests are delicate — see the
testability constraints in `.agents/run-tests/SKILL.md`.

`main()` blocks forever (a `CountDownLatch` nobody counts down) and calls `System.exit`; it is not unit-testable and `scripts/coverage.sh` leaves it out. See `docs/original-behavior.md`.
