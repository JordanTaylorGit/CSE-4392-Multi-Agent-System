# SeasonSwitch JUnit case vocabulary (Phase C, original target)

The shared test-case schemas intentionally leave `setup`, `inputs`, and `expected` open.
For SeasonSwitch, the project adapter uses the following vocabulary. P1 should
emit cases using these keys; unfamiliar fields fail validation instead of being ignored.

| Field | Used in | Type | Meaning |
|---|---|---|---|
| `state` | `setup`, `expected` | `"OFF"`, `"COOL"`, `"HEAT"` | Current mode |
| `room.temp` | `setup` | integer | Room temperature before action |
| `ac.isOn` | `setup`, `expected` | boolean | Air-conditioner switch |
| `heater.isOn` | `setup`, `expected` | boolean | Heater switch |
| `stdout` | `expected` | string | Exact output from the invoked method, with `\n` newlines |

`inputs` must be `{}`: `cool`, `heat`, `off`, and `timerOff` take no arguments.
Missing `setup.state` means starting in OFF mode. At least one assertion is required.
State is reached using `cool()`, `heat()`, or `off()`, not by assigning `SeasonSwitch.state`.
The adapter stops Swing timers during testing, and captures only the output of
**the unit under test**, not setup transitions.

Example case (illustrative only; not a real EP agent output):

```json
{
  "id": "BVA-01",
  "method": "BVA",
  "target": "original",
  "unit": "timerOff",
  "setup": {"state": "COOL", "room.temp": 68},
  "inputs": {},
  "expected": {"state": "COOL", "ac.isOn": false, "stdout": "Cooling stopped. RmTemp=68\n"},
  "partition": "coolTemp-at",
  "rationale": "At 68, room.temp > coolTemp is false"
}
```

The generator checks the existing human G1 approval log. It generates only the
**original** target; refactored-source adapter and `mode=adapt` remain separate work.
This adapter is project-specific; the main testgen CLI contains no SeasonSwitch behavior.
