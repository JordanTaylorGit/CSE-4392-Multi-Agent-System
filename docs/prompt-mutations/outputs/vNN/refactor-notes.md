# Refactor notes: SeasonSwitch to State pattern

Source of the refactored code: prompt `v05`, run in ChatGPT (free) on 2026-11-16.
The case-to-class table in `docs/prompt-mutations/outputs/v05/` is the LLM's raw mapping.
This file extends it with transitions, guards, effects and covering tests, so the transition
matrix for testing can be read directly. The extension was written after the run and checked
against the refactored source.

## Structure

| Role | Class |
|------|-------|
| Context | `SeasonSwitch` (delegates via `getCurrentState()`) |
| State interface | `SeasonState` |
| Concrete states | `OffState`, `CoolState`, `HeatState` |
| Unrecognized-value state | `NoOpState` |

`SeasonSwitch.state` stays an `int` and is the source of truth. `getCurrentState()` maps it to a state
object with `STATES.getOrDefault(state, NO_OP_STATE)`, which adds no branch.

## Transition matrix

| Event | From | Guard | To | Effects (in order) | Implemented in | Covering test |
|-------|------|-------|----|--------------------|----------------|---------------|
| `cool()` | OFF | | COOL | ac on, timer start, print "Cooling started" | `OffState.cool` | `cool_fromOff_turnsAcOnAndGoesToCool` |
| `cool()` | COOL | | COOL | none | `CoolState.cool` | `cool_fromCool_doesNothing` |
| `cool()` | HEAT | | COOL | heater off, ac on, timer start, print "Cooling started" | `HeatState.cool` | `cool_fromHeat_switchesHeaterOffAcOn` |
| `heat()` | OFF | | HEAT | heater on, timer start, print "Heating started" | `OffState.heat` | `heat_fromOff_turnsHeaterOnAndGoesToHeat` |
| `heat()` | HEAT | | HEAT | none | `HeatState.heat` | `heat_fromHeat_doesNothing` |
| `heat()` | COOL | | HEAT | ac off, heater on, timer start, print "Heating started" | `CoolState.heat` | `heat_fromCool_switchesAcOffHeaterOn` |
| `off()` | OFF | | OFF | none | `OffState.off` | `off_fromOff_doesNothing` |
| `off()` | HEAT | | OFF | heater off, timer stop, print "Heating stopped" | `HeatState.off` | `off_fromHeat_turnsHeaterOffAndGoesToOff` |
| `off()` | COOL | | OFF | ac off, timer stop, print "Cooling stopped" | `CoolState.off` | `off_fromCool_turnsAcOffAndGoesToOff` |
| `timerOff()` | OFF | | OFF | none | `OffState.timerOff` | `timerOff_inOff_doesNothing` |
| `timerOff()` | COOL | temp > coolTemp (68) | COOL | ac on, print "Cooling started" | `CoolState.timerOff` (if) | `timerOff_inCool_tempAboveThreshold_acOn` |
| `timerOff()` | COOL | temp <= 68 | COOL | ac off, print "Cooling stopped" | `CoolState.timerOff` (else) | `timerOff_inCool_tempAtThreshold_acOff` |
| `timerOff()` | HEAT | temp < heatTemp (77) | HEAT | heater on, print "Heating started" | `HeatState.timerOff` (if) | `timerOff_inHeat_tempBelowThreshold_heaterOn` |
| `timerOff()` | HEAT | temp >= 77 | HEAT | heater off, print "Heating stopped" | `HeatState.timerOff` (else) | `timerOff_inHeat_tempAtThreshold_heaterOff` |
| `Room.actionPerformed` | OFF | | OFF | temp unchanged | `OffState.roomActionPerformed` | `roomTick_inOff_tempUnchanged` |
| `Room.actionPerformed` | COOL | ac on | COOL | temp-- | `CoolState.roomActionPerformed` (if) | `roomTick_inCool_acOn_tempDrops` |
| `Room.actionPerformed` | COOL | ac off | COOL | temp++ | `CoolState.roomActionPerformed` (else) | `roomTick_inCool_acOff_tempRises` |
| `Room.actionPerformed` | HEAT | heater on | HEAT | temp++ | `HeatState.roomActionPerformed` (if) | `roomTick_inHeat_heaterOn_tempRises` |
| `Room.actionPerformed` | HEAT | heater off | HEAT | temp-- | `HeatState.roomActionPerformed` (else) | `roomTick_inHeat_heaterOff_tempDrops` |
| any | unrecognized (e.g. 3) | | unchanged | none | `NoOpState` (all methods) | `invalidState_isIgnoredByEveryMethod` |
| `actionPerformed` | any | | | delegates to `timerOff()` | `SeasonSwitch.actionPerformed` | `actionPerformed_delegatesToTimerOff` |

## Notes

- The unrecognized-value row has no counterpart in the original code, where no `switch` had a
  `default`. It makes the previously implicit "do nothing" behavior explicit (acceptance criterion 4).
- All conditional branches that remain in the refactored classes are the guards above (the four
  `if`/`else` pairs). The `switch` branches of the original no longer exist.
- Not removed: the "turn on, start timer, set state, print" sequence appears in both
  `OffState`/`HeatState` (cooling) and `OffState`/`CoolState` (heating). The original had the same
  duplication.
- `main()` is unchanged apart from indentation.
