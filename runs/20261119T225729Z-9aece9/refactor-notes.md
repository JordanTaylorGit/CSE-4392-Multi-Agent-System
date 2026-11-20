# SeasonSwitch State Pattern Refactor Notes

## Transition Matrix: original switch cases -> state class / method

| Original method | Original switch case | New state class | New method |
|---|---|---|---|
| `cool()` | `OFF` | `OffState` | `cool` |
| `cool()` | `COOL` (no-op) | `CoolState` | `cool` |
| `cool()` | `HEAT` | `HeatState` | `cool` |
| `heat()` | `OFF` | `OffState` | `heat` |
| `heat()` | `HEAT` (no-op) | `HeatState` | `heat` |
| `heat()` | `COOL` | `CoolState` | `heat` |
| `off()` | `OFF` (no-op) | `OffState` | `off` |
| `off()` | `HEAT` | `HeatState` | `off` |
| `off()` | `COOL` | `CoolState` | `off` |
| `timerOff()` | `OFF` (no-op) | `OffState` | `timerOff` |
| `timerOff()` | `COOL` | `CoolState` | `timerOff` |
| `timerOff()` | `HEAT` | `HeatState` | `timerOff` |
| `Room.actionPerformed()` | `OFF` (no-op) | `OffState` | `roomActionPerformed` |
| `Room.actionPerformed()` | `COOL` | `CoolState` | `roomActionPerformed` |
| `Room.actionPerformed()` | `HEAT` | `HeatState` | `roomActionPerformed` |
| invalid state (default) | — | `NoOpState` | all methods |
