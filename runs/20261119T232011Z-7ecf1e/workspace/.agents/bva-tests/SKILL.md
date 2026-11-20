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

## Boundary value analysis
Bugs cluster at edges. Test the boundary itself and one step on each
side. This is the single highest-yield category for numeric/length
domains.

### Method
1. For every ordered bound (numeric range, string/collection length,
   date interval, index), emit points: at-boundary, one inside, one
   outside. For each bound of each parameter.
2. Robust BVA adds the just-invalid point (min-1, max+1); normal BVA
   stays in-domain. Do robust when validation is specified.
3. Multi-parameter: test each parameter's boundaries independently
   (hold others at nominal) unless the requirements couple them
   (e.g. a+b<=limit — then test the coupled boundary).
4. Zero/empty/one are boundaries too: empty string, empty list,
   single element, zero, negative-zero, MAXINT-ish extremes when the
   spec implies them.

### Budget
k bounded parameters -> at least 2 points per bound (edge + outside),
4n+1 worst-case when every bound needs both sides and a nominal.

### Checklist
- [ ] every bound from the domain spec appears in >=1 test at the edge
      and >=1 test just outside (if validation specified)
- [ ] both sides of every partition cut point are tested
- [ ] empty/zero/singleton covered for sized inputs

## Decision-embedded thresholds
Boundaries live in logic, not only in parameter domains. Every cut or
clamp inside the code/model — floors, caps, tier edges, comparison
constants — gets a both-sides test pair (just below / at / just above
in the smallest unit of the domain). Reconcile the declared boundary
list against the emitted cases: every listed boundary must name its
test.

# Contract
- Reads: `projects/<project>/profile.json`, the source at `profile.source`.
- Writes: `testcases_bva.json` matching `schemas/testcase-set.schema.json`.
- Runs as a subagent alongside `ep-tests`; the parent `testgen` launches both concurrently and
  neither may read the other's output.
- For every boundary emit the value below, on, and above. No interior representatives.

# Procedure
1. Read `boundaries` from the profile. Each entry gives a `value`, the `applies_to` unit, and the
   `condition` that decides the branch.
2. For each boundary emit three cases: `value - 1`, `value`, `value + 1` (Method 1;
   add the just-invalid side only when validation is specified — Method 2).
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
Run the methodology checklists, plus:
- [ ] >=3 cases per `boundaries` entry (below, at, above — smallest domain step)
- [ ] both sides of every cut tested, correct side keyed to the operator
- [ ] no two cases share all `dedupe_key` fields
- [ ] every `constraints` entry honoured
- [ ] file validates against `schemas/testcase-set.schema.json`
