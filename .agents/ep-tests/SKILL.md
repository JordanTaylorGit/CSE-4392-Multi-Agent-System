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
Read `.agents/_methodology/equivalence-partitioning.md` and apply it in full — its class-building
method, valid/invalid combination rules, and checklist are authoritative for how cases are derived.

# Contract
- Reads: `projects/<project>/profile.json`, the source at `profile.source`, and the methodology
  file above.
- Writes: `testcases_ep.json` matching `schemas/testcase-set.schema.json`.
- Runs as a subagent alongside `bva-tests`; the parent `testgen` launches both concurrently and
  neither may read the other's output.
- One representative per class. Threshold values belong to `bva-tests`, not here.

# Procedure
1. Read the profile. It gives you `units`, `state_variables`, `observable`, `boundaries`,
   `constraints`, and `dedupe_key`.
2. Build the class table before writing any case (methodology §Method). One row per unit x each
   distinct behaviour; split a row whenever a `boundaries` entry says the unit behaves differently
   on each side of a value.
3. Choose one representative per class from the **interior** of that class — never a value
   `bva-tests` will cover (see methodology §Budget).
4. Emit a case per row. `partition` names the class; `rationale` says why the representative
   exercises that class and no other.
5. `setup` carries preconditions (initial state, field values); `inputs` carries arguments. Leave
   either empty when the unit needs neither — a stateless function has no `setup`.
6. `expected` must include every key in `observable` that this case can assert on: `return`,
   `exception`, `stdout`, or state variables.
7. Honour every entry in `constraints` when constructing `setup` — e.g. drive state only through
   the public API, reset shared state between cases, use the declared observation channel.

# Output shape
`{"generated_by": "ep-tests", "target": <target>, "cases": [...]}` — each case has `id` (`EP-NN`),
`method` `"EP"`, `target`, `unit`, `setup`, `inputs`, `expected`, `partition`, `rationale`.
No two cases may agree on every `dedupe_key` field.

# Self-check before finishing
Run the methodology file's checklist, plus:
- [ ] no representative sits on any `boundaries` value
- [ ] no two cases share all `dedupe_key` fields
- [ ] every `constraints` entry honoured
- [ ] file validates against `schemas/testcase-set.schema.json`
