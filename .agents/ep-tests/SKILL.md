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

# Contract
- Reads: `projects/<project>/profile.json` and the source at `profile.source`.
- Writes: `testcases_ep.json` matching `schemas/testcase-set.schema.json`.
- Runs as a subagent alongside `bva-tests`; the parent `testgen` launches both concurrently and
  neither may read the other's output.
- One representative per class. Threshold values belong to `bva-tests`, not here.

# Procedure
1. Read the profile. It gives you `units`, `state_variables`, `observable`, and `boundaries`.
2. Build the class table before writing any case. One row per unit x each distinct behaviour. Split a
   row whenever a `boundaries` entry says the unit behaves differently on each side of a value.
3. Choose one representative per class from the **interior** of that class. Never pick a value equal
   to a boundary — that is `bva-tests`' job, and duplicating it here makes dedupe throw work away.
4. Emit a case per row. `partition` names the class; `rationale` says why the representative
   exercises that class and no other.
5. `setup` carries preconditions (initial state, field values); `inputs` carries arguments. Leave
   either empty when the unit needs neither — a stateless function has no `setup`.
6. `expected` must include every key in `observable` that this case can assert on: `return`,
   `exception`, `stdout`, or state variables.

# Prompt
TODO(P1): write the equivalence-partition prompt.
Requirements:
- Build the class table first and show it before emitting cases.
- Classes come from the profile, not from reading the implementation and inventing a domain.
- A missing class is a hole the coverage stage finds later, at higher cost.
- If `constraints` in the profile is non-empty, every generated case must honour it.
