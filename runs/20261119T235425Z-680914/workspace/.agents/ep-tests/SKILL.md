---
id: ep-tests
order: 10
executor: agent
inputs: [projects/<project>/profile.json]
outputs: [testcases_ep.json]
gate: none
schema: schemas/testcase-set.schema.json
---

# Purpose
Derive equivalence-partition test cases for any unit under test. Project-specific knowledge comes
from the profile; this file names no project, language, or domain.

# Methodology

## Equivalence partitioning
Divide each input's domain into classes where the program is specified
to behave identically. One representative per class; a test per class.

### Method
1. For each parameter (from the requirements model), list VALID classes
   and INVALID classes. Sources: type, range, length, format, enum
   membership, requiredness, semantic categories (e.g. "weekday" vs
   "weekend", "empty" vs "whitespace-only").
2. A parameter can have several valid classes (e.g. int in (-inf,0],
   (0,100], (100,inf) if behavior differs per interval — those intervals come from
   the REQUIREMENT, not the code).
3. Combine: one test covers as many valid classes simultaneously as
   possible (valid classes combine freely); INVALID classes get one test
   EACH (never combine two invalid classes — a single failure masks the
   other; you can't tell which check fired).
4. Expected output is defined per class, not per value.

### Budget
valid test ≈ fewest inputs covering all valid classes; invalid tests =
exactly one per invalid class.

### Checklist
- [ ] every parameter has >=1 valid and (if any validation exists)
      >=1 invalid class
- [ ] no invalid-invalid combinations in one test
- [ ] each class's expected behavior is written down before writing the
      test

## State machines: cover the grid, do not sample it
When the units act on a state variable, the state x operation grid is
the enumeration — every cell is a class.
1. Legal arcs: one case each, asserting resulting state AND transition
   side effects (fields changed, timers, printed output).
2. No-op and illegal cells count: for each (state, operation) pair that
   changes nothing or is specified-illegal, a case asserting the state
   is unchanged AND the attempted call produced no side effects.
   "Cannot happen" is not a reason to skip — if the API accepts the
   call, it is a class.
3. Operations conditioned on data (guards, e.g. a temperature
   threshold) get one class per regime: each side of the guard is a
   distinct class. Boundary points themselves belong to `bva-tests`;
   here use interior representatives.
4. A full n-state x m-operation table is n*m cells (times guard
   regimes); every cell is a case or is documented impossible.

# Contract
- Reads: `projects/<project>/profile.json`, the source at `profile.source`.
- Writes: `testcases_ep.json` matching `schemas/testcase-set.schema.json`.
- Runs as a subagent alongside `bva-tests`; the parent `testgen` launches both concurrently and
  neither may read the other's output.
- One representative per class. Threshold values belong to `bva-tests`, not here.

# Procedure
1. Read the profile. It gives you `units`, `state_variables`, `observable`, `boundaries`,
   `constraints`, and `dedupe_key`.
2. Build the class table before writing any case. One row per unit x each
   distinct behaviour; split a row whenever a `boundaries` entry says the unit behaves differently
   on each side of a value. If `state_variables` exist, the state x unit grid is the class table —
   enumerate every cell, including no-ops.
3. Choose one representative per class from the **interior** of that class — never a value
   `bva-tests` will cover (see Budget).
4. Emit a case per row. `partition` names the class; `rationale` says why the representative
   exercises that class and no other.
5. `setup` carries preconditions (initial state, field values); `inputs` carries arguments. Leave
   either empty when the unit needs neither — a stateless function has no `setup`.
6. `expected` must include every key in `observable` that this case can assert on: `return`,
   `exception`, `stdout`, or state variables. For no-op cells, assert BOTH the unchanged state
   AND the absence of side effects.
7. Honour every entry in `constraints` when constructing `setup` — e.g. drive state only through
   the public API, reset shared state between cases, use the declared observation channel.

# Output shape
`{"generated_by": "ep-tests", "target": <target>, "cases": [...]}` — each case has `id` (`EP-NN`),
`method` `"EP"`, `target`, `unit`, `setup`, `inputs`, `expected`, `partition`, `rationale`.
No two cases may agree on every `dedupe_key` field.

# Self-check before finishing
Run the methodology checklists, plus:
- [ ] state x operation grid fully accounted: every cell is a case or documented impossible
- [ ] no representative sits on any `boundaries` value
- [ ] no two cases share all `dedupe_key` fields
- [ ] every `constraints` entry honoured
- [ ] file validates against `schemas/testcase-set.schema.json`
