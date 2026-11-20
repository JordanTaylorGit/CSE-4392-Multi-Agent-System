# Refactor Notes: SeasonSwitch State Pattern

## Transition Matrix

| Original switch location | case | New state class | New method | Behavior |
|---|---|---|---|---|
| `SeasonSwitch.cool()` | `OFF` | `OffState` | `cool` | ac.on(), timer.start(), state=COOL, print "Cooling started..." |
| `SeasonSwitch.cool()` | `COOL` | `CoolState` | `cool` | no-op (already cooling) |
| `SeasonSwitch.cool()` | `HEAT` | `HeatState` | `cool` | heater.off(), ac.on(), timer.start(), state=COOL, print "Cooling started..." |
| `SeasonSwitch.heat()` | `OFF` | `OffState` | `heat` | heater.on(), timer.start(), state=HEAT, print "Heating started..." |
| `SeasonSwitch.heat()` | `HEAT` | `HeatState` | `heat` | no-op (already heating) |
| `SeasonSwitch.heat()` | `COOL` | `CoolState` | `heat` | ac.off(), heater.on(), timer.start(), state=HEAT, print "Heating started..." |
| `SeasonSwitch.off()` | `OFF` | `OffState` | `off` | no-op (already off) |
| `SeasonSwitch.off()` | `HEAT` | `HeatState` | `off` | heater.off(), timer.stop(), state=OFF, print "Heating stopped..." |
| `SeasonSwitch.off()` | `COOL` | `CoolState` | `off` | ac.off(), timer.stop(), state=OFF, print "Cooling stopped..." |
| `SeasonSwitch.timerOff()` | `OFF` | `OffState` | `timerOff` | no-op (no regulation while off) |
| `SeasonSwitch.timerOff()` | `COOL` | `CoolState` | `timerOff` | temp>coolTemp: ac.on()/print started; else ac.off()/print stopped |
| `SeasonSwitch.timerOff()` | `HEAT` | `HeatState` | `timerOff` | temp<heatTemp: heater.on()/print started; else heater.off()/print stopped |
| `Room.actionPerformed()` | `OFF` | `OffState` | `roomActionPerformed` | no-op (no drift while off) |
| `Room.actionPerformed()` | `COOL` | `CoolState` | `roomActionPerformed` | ac.isOn: temp-- else temp++ |
| `Room.actionPerformed()` | `HEAT` | `HeatState` | `roomActionPerformed` | heater.isOn: temp++ else temp-- |
| invalid state (e.g. `3`) | default | `NoOpState` | all methods | no-op, ignored silently via getOrDefault
