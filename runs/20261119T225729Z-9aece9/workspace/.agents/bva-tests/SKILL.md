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

# Methodology
Read `.agents/_methodology/boundary-value-analysis.md` and apply it in full — its point selection,
robust-vs-normal rule, and decision-embedded-threshold rule are authoritative for how cases are
derived.

# Contract
- Reads: `projects/<project>/profile.json`, the source at `profile.source`, and the methodology
  file above.
- Writes: `testcases_bva.json` matching `schemas/testcase-set.schema.json`.
- Runs as a subagent alongside `ep-tests`; the parent `testgen` launches both concurrently and
  neither may read the other's output.
- For every boundary emit the value below, on, and above. No interior representatives.

# Procedure
1. Read `boundaries` from the profile. Each entry gives a `value`, the `applies_to` unit, and the
   `condition` that decides the branch.
2. For each boundary emit three cases: `value - 1`, `value`, `value + 1` (methodology §Method 1;
   add the just-invalid side only when validation is specified — §Method 2).
3. Derive the expected outcome from `on_true` / `on_false` and the condition, not from guessing.
4. **Check the operator.** A `>` boundary and a `<` boundary put the "on" outcome on opposite
   sides, and at the value itself both conditions are false. Assuming all thresholds behave the
   same way produces wrong tests and leaves a branch uncovered.
5. Boundaries that apply to different units or different state dimensions produce different
   classes — do not merge them. When the unit reads `state_variables`, each (state x boundary
   side) combination is its own case.
6. `rationale` names the boundary and which side the value sits on: `below`, `at`, `above`.
   `partition` is `<boundary>-<side>`.
7. Honour every entry in `constraints` when constructing `setup`.

# Output shape
`{"generated_by": "bva-tests", "target": <target>, "cases": [...]}` — each case has `id`
(`BVA-NN`), `method` `"BVA"`, `target`, `unit`, `setup`, `inputs`, `expected`, `partition`,
`rationale`. Assert every `observable` key the case can reach — printed text and device state can
disagree if the implementation is wrong.

# Self-check before finishing
Run the methodology file's checklist, plus:
- [ ] >=3 cases per `boundaries` entry (below, at, above — smallest domain step)
- [ ] both sides of every cut tested, correct side keyed to the operator
- [ ] no two cases share all `dedupe_key` fields
- [ ] every `constraints` entry honoured
- [ ] file validates against `schemas/testcase-set.schema.json`
