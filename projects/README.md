# Project profiles

The test-generation skills are project-agnostic. Everything they need to know about a specific
project comes from `projects/<project>/profile.json`. Swapping projects means writing a profile, not
editing a skill.

## Why this exists

The assignment targets `SeasonSwitch`, a stateful thermostat. A skill that hardcodes
"state / room_temp / action" only ever works on that class, and the claim "this workflow generalises"
stays untested. The profile is the seam that makes the claim checkable: the same `ep-tests` and
`bva-tests` skills run against `seasonswitch` (stateful, void-returning, console-observable) and
against `grade-classifier` (stateless, pure, return-valued) with no skill changes.

## Contract

| key | meaning |
|-----|---------|
| `project` | name, matches the directory |
| `subject` | class or module under test |
| `language` | `java`, `python`, … |
| `source` | path to the subject source |
| `test_root` | where generated tests are written |
| `units` | `[{name, kind, params}]` — the callable surface |
| `state_variables` | observable mutable state; empty for a pure unit |
| `observable` | everything a test may assert on: `return`, `exception`, `stdout`, state keys |
| `boundaries` | `[{name, value, applies_to, condition, on_true, on_false}]` — drives `bva-tests` |
| `dedupe_key` | fields that fully determine the outcome — drives `dedupe` |
| `coverage` | `{command, report, metric, threshold}` — drives `coverage` |
| `constraints` | project-specific testability rules the generated tests must honour |

`dedupe_key` is the one that most needs to be per-project: two cases are duplicates only if they agree
on every field that determines the outcome, and that set differs between a stateful object and a pure
function.

## Adding a project

1. `mkdir projects/<name>`
2. Write `profile.json` against the table above.
3. Point the orchestrator at it: `project: <name>`.
4. Nothing else changes. No skill edits.
