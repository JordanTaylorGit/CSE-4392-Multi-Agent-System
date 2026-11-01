---
id: bva-tests
order: 11
executor: agent
inputs: [projects/<project>/profile.json]
outputs: [testcases_bva.json]
gate: none
schema: schemas/testcase-set.schema.json
---

# Purpose
Derive boundary-value-analysis test cases for any unit under test. Boundaries come from the profile,
not from this file.

# Contract
- Reads: `projects/<project>/profile.json` and the source at `profile.source`.
- Writes: `testcases_bva.json` matching `schemas/testcase-set.schema.json`.
- Runs as a subagent alongside `ep-tests`; the parent `testgen` launches both concurrently and
  neither may read the other's output.
- For every boundary emit the value below, on, and above. No interior representatives.

# Procedure
1. Read `boundaries` from the profile. Each entry gives a `value`, the `applies_to` unit, and the
   `condition` that decides the branch.
2. For each boundary emit three cases: `value - 1`, `value`, `value + 1`.
3. Derive the expected outcome from `on_true` / `on_false` and the condition, not from guessing.
4. **Check the operator.** A `>` boundary and a `<` boundary put the "on" outcome on opposite sides,
   and at the value itself both conditions are false. Assuming all thresholds behave the same way
   produces wrong tests and leaves a branch uncovered.
5. `rationale` names the boundary and which side the value sits on: `below`, `at`, `above`.

# Prompt
TODO(P1): write the boundary-value prompt.
Requirements:
- Three cases per boundary, minimum. No exceptions for "obvious" boundaries.
- `partition` is the boundary name from the profile plus side, e.g. `<boundary>-at`.
- Assert every observable key, not just the printed message — text and device state can disagree if
  the implementation is wrong.
- Boundaries that apply to different units produce different classes; do not merge them.
