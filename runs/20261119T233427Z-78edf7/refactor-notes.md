# Refactor Notes: SeasonSwitch State Pattern

| Original switch case | State class | Method |
|---|---|---|
| `cool() -> case OFF` | OffState | cool |
| `cool() -> case COOL` (no-op) | CoolState | cool |
| `cool() -> case HEAT` | CoolState | cool |
| `heat() -> case OFF` | HeatState | heat |
| `heat() -> case HEAT` (no-op) | HeatState | heat |
| `heat() -> case COOL` | HeatState | heat |
| `off() -> case OFF` (no-op) | OffState | off |
| `off() -> case HEAT` | HeatState | off |
| `off() -> case COOL` | CoolState | off |
| `timerOff() -> case OFF` (no-op) | OffState | timerOff |
| `timerOff() -> case COOL` | CoolState | timerOff |
| `timerOff() -> case HEAT` | HeatState | timerOff |
| `Room.actionPerformed -> case OFF` | OffState | roomActionPerformed |
| `Room.actionPerformed -> case COOL` | CoolState | roomActionPerformed |
| `Room.actionPerformed -> case HEAT` | HeatState | roomActionPerformed |
| Invalid state (e.g. 3) | NoOpState | all methods |
