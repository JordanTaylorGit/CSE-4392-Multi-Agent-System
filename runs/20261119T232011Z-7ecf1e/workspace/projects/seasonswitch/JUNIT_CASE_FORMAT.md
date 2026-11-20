# SeasonSwitch JUnit case vocabulary (generate and adapt modes)

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

The materializer checks the existing G1 decision **against the original case-set bytes**.
In `--mode adapt`, it copies the approved cases, changes only the `target` label
in memory, and renders a test class that runs against Maven's `refactored` profile.
The expected values, preconditions, case IDs, and units are unchanged. Its output
is Java source only; it does not modify `testcases_final.json` or write a second
case-set JSON. A separate LangGraph G3 approval is still required before executing
tests against the refactored source in the full workflow. The `adapt` CLI itself
does not implement G3 or run Maven.

Example (from the repository root, after a real G1 acceptance):

```bash
python3 .agents/testgen/materialize_junit.py \
  --mode adapt \
  --profile projects/seasonswitch/profile.json \
  --cases runs/<run>/testcases_final.json \
  --report runs/<run>/dedupe-report.md \
  --log runs/<run>/hitl_decisions.json \
  --out java/src/test/java/cse4392/SeasonSwitchAdaptedTest.java
```

If the original generated class is already present, this adds a second JUnit
class rather than replacing it. Loc's harness instead reuses the original Java
tests and swaps Maven profiles, which is sufficient while the public interface
remains compatible. This adapter is project-specific; the main testgen CLI
contains no SeasonSwitch behavior.
