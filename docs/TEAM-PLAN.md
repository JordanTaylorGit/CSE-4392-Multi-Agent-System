# Team Assignment 3 — Plan & Work Designation
**CSE 4392/5320 — Multi-Agent System for Software Testing and Refactoring**
Due: 11/8/2026 · Planned: 10/31/2026 · Team of 5
Repo: `JordanTaylorGit/CSE-4392-Multi-Agent-System`

---

## 0. Route: skills + existing agentic coding harness

Committed approach: **the agent system is a set of skill files executed by an agentic coding harness**
(Devin / Copilot / opencode). `.agents/orchestrator/SKILL.md` is the program; the harness is the runtime. There is
no runner in design 1 — invoking that one skill is the go button.

### The one rule that keeps the skills portable

Every skill file carries a frontmatter block that is, in effect, a graph specification:

```yaml
id: ep-tests
order: 10
executor: agent          # agent | llm
inputs:  [projects/<project>/profile.json]
outputs: [testcases_ep.json]
gate: none               # none | human
schema: schemas/testcase-set.schema.json
```

Consequences:

- The skills **are** the architecture. `docs/ARCH.md` describes them; `scripts/validate_skills.py`
  lints them in CI.
- If the teacher later requires a code-executed runner, the graph is already machine-readable, so that
  becomes writing an executor rather than redesigning the system. Nothing is built for it now.

### What the harness route must still deliver

The risk is that a skills-only submission has no runnable artifact, while §2.4 asks you to "review,
debug and test the agent system, and use it to perform the tasks." Two things close that gap without a
runner:

1. **`.agents/orchestrator/SKILL.md` is a state machine, not prose** — numbered steps, explicit exit conditions,
   four named gates, a refusal rule, and a 5-iteration cap on every loop.
2. **`runs/<timestamp>/STATE.md` is the durable progress record**, written after every step. It is what
   makes the run resumable and auditable, and it is the evidence that the pipeline actually ran.

Language split is unchanged: **prompts and JSON artifacts in Python-adjacent tooling, Java for the
tests and refactored code.** Test cases and refactored code are Java, per §2.3.

---

## 1. What is actually graded vs. what is hard

Pipeline plumbing is easy. Three things carry the grade:

1. **100% branch coverage on the refactored code.** The original is three `switch (state)` blocks in
   one class; the state-pattern version moves each transition into a state object, so the branch
   count *rises*. Derive tests from a `(state, action, temp-regime)` matrix, not from the code.
2. **The prompt-mutation study (§8/§9).** Explicitly required: variations of the refactor prompt until
   quality is satisfactory. Keep every version plus a table of what changed and why.
3. **HITL evidence (§4, §9).** Must be *recorded*: reviewer, timestamp, decision, requested changes,
   resulting diff. `runs/<ts>/hitl_decisions.json`.

Order is "preferably in the given order" — keep the 12 steps literally sequential in the graph.

---

## 2. Frozen contracts (freeze today)

### 2.0 Prerequisites — all five, before writing anything

- JDK 17
- Maven 3.9+ (`sudo apt install maven` on Debian/Ubuntu, `brew install maven` on macOS)
- Confirm it works: `cd java && mvn -P original test`

Everyone installs Maven, not just whoever owns the build. Each person has to run the suite locally to
check their own work, and 11/7 should not be spent fixing five different Java setups.

### 2.1 Test case schema — `schemas/testcase.schema.json`
```json
{
  "id": "EP-01",
  "method": "EP | BVA",
  "target": "original | refactored",
  "month": 3,
  "expected_season": "Spring",
  "expected_exception": null,
  "partition": "valid_spring",
  "rationale": "one line: which class or boundary this represents"
}
```

### 2.2 Node/stage contract
See §0. Skill files are the source of truth for the graph.

### 2.3 Run directory layout — `runs/<UTC timestamp>/`
```
testcases_ep.json  testcases_bva.json  testcases_final.json
surefire/*.xml     jacoco.xml          coverage.txt
changelog.md       hitl_decisions.json transcripts/  replay.json  log.txt
```
`transcripts/` holds the coding-agent session logs per stage — this is the "we ran the agent system"
evidence. `replay.json` caches stage outputs so a live demo cannot be derailed by a flaky model.

### 2.4 Repo layout
One directory per skill, each holding a `SKILL.md`:

Four working skills, one template:

```
.agents/
  orchestrator/SKILL.md         # the go button; dispatches the other three
  testgen/SKILL.md              # overarching test skill; runs twice (generate, adapt)
  ep-tests/SKILL.md             # subagent of testgen
  bva-tests/SKILL.md            # subagent of testgen
  refactor-state/SKILL.md       # State pattern + prompt mutation
  _template/SKILL.md

projects/
  README.md                     # the profile contract
  seasonswitch/profile.json     # this assignment
  grade-classifier/             # second project, proves the test skills generalise

schemas/  testcase.schema.json  hitl_decision.schema.json
java/     src/original src/refactored src/test pom.xml
scripts/  coverage.sh  validate_skills.py
docs/     ARCH.md CONTRACTS.md original-behavior.md test-design.md
          activity.drawio activity.png prompt-mutations/
slides/   team3.pptx
```

### 2.5 The graph (also the activity diagram content)
```
orchestrator
  ├─▶ testgen(mode=generate, target=original)
  │      ├─▶ ep-tests  ─┐  (concurrent subagents)
  │      └─▶ bva-tests ─┴─▶ join ─▶ dedupe ─▶ G1 human review
  │      ─▶ write JUnit ─▶ run ─▶ repair loop ─▶ coverage gate ─▶ exit
  ├─▶ refactor-state (prompt mutations until satisfactory)
  ├─▶ G3 human review of refactored code
  └─▶ testgen(mode=adapt, target=refactored)
         ─▶ re-target cases ─▶ run ─▶ repair loop ─▶ coverage gate ─▶ HALT
```

---

## 3. Work designation

Rule: **each person owns whole directories. Nobody edits another person's directory.** Cross-boundary
needs go through the frozen contracts above.

Team: **P1 = Kyle**. P2–P5 = teammates (names TBD at the 10/31 sync).

### P1 — Kyle (team lead): the two test-generation subagents
**Owns:** `.agents/ep-tests/SKILL.md`, `.agents/bva-tests/SKILL.md`, `docs/test-design.md`,
`schemas/testcase.schema.json`.
- These two skills are the focused subagent briefs `testgen` spawns. They stay project-agnostic —
  all domain knowledge comes from `projects/<project>/profile.json`, which is an input to your
  skills, not yours to maintain.
- Equivalence-class and boundary tables in `docs/test-design.md` — this is your graded evidence.
- Verify the initial branch coverage on the original code, using the reports from P3's run.
- Run your two skills once against `projects/grade-classifier` — no skill changes allowed — and
  hand the output to P3 for the deck. That is the generality evidence.
**Done when:** both skills emit schema-valid case sets that cover every class and boundary in the
profile, on `seasonswitch` and on `grade-classifier`; you have signed off on the original-code
coverage number.

### P2 — Overarching skill prompt + activity diagram
**Owns:** `.agents/orchestrator/SKILL.md`, `docs/activity.drawio` + `.png`, `docs/ARCH.md`, `docs/CONTRACTS.md`,
`templates/STATE.md`, `scripts/validate_skills.py`.
- Write the overarching prompt as an executable state machine: 12 steps, 4 gates, explicit exit
  condition per step, 5-iteration cap on every loop, refusal rules for the moves that would falsify
  the run.
- Draw the UML activity diagram of the same graph. The diagram and the prompt are one artifact in two
  notations, which is why they belong to one person — they have to be written together and stay in
  sync.
- Own the parallel/join claim and the resume protocol via `STATE.md`.
**Done when:** a full run completes from `orchestrator.md` alone, the diagram matches it step for step,
and both HITL gates stop and record.
**Depends on:** nothing but today's freeze — critical path on day 1.

### P3 — Java build, coverage tooling, deck assembly + pipeline operator
**Owns:** `java/pom.xml`, `scripts/coverage.sh`, `docs/original-behavior.md`, `slides/team3.pptx`,
the `runs/` evidence tree, `docs/changelog-format.md`.
- Own the pom (JUnit 5 + JaCoCo + surefire XML) and `scripts/coverage.sh`, which prints machine-readable
  branch % for either target. Maven itself is a prerequisite for everyone (§2.0), not your install.
- Compile and run `SeasonSwitch` per §2.2, write up the observed behavior.
- **You operate the pipeline.** Run it end to end, collect transcripts, `coverage.txt`, surefire XML,
  and `hitl_decisions.json` for the deck, and act as the human at G1 and G3 during dry runs.
- Assembles the deck, enforces the required section list, runs the dry run.
**Done when:** `./scripts/coverage.sh <target>` returns branch % for both targets; a complete run's
artifacts sit in `runs/`; the deck has all seven required sections and its coverage numbers come
from real files.

### P4 — The overarching test skill
**Owns:** `.agents/testgen/SKILL.md`, `projects/`.
- `testgen` is the heaviest single file: it spawns P1's two subagents concurrently, joins and
  dedupes, holds the G1 human gate, writes JUnit, runs and repairs the suite, and gates on 100%
  coverage — twice, once per target. Its `mode` parameter is what keeps step 10 honest: `adapt`
  re-targets the approved set rather than regenerating it.
- Writes `projects/seasonswitch/profile.json` — the units, boundaries, observable outputs, dedupe
  key, and constraints the test skills read. P1's skills depend on it, so the contract freezes on
  day 1.
**Done when:** `testgen(mode=generate)` and `testgen(mode=adapt)` both exit at 100% coverage in a
dry run; the profile is frozen and P1's skills consume it unchanged.

### P5 — State-pattern refactor + prompt mutation study
**Owns:** `.agents/refactor-state/SKILL.md`, `docs/prompt-mutations/` + mutation table,
`java/refactored/`.
- Run the prompt-mutation exercise against a web LLM until quality is satisfactory; keep every version.
- Refactored Java: `SeasonSwitch` subject + `SeasonState` interface + four concrete states.
- **Hard constraint from the assignment's hint:** keep the class name `SeasonSwitch` and its exact public
  interface, so existing tests are reusable. Put this in the skill as non-negotiable.
- Review checklist: open/closed respected, no if/switch chain, transitions centralized, no duplicated
  logic, invalid transitions handled.
**Done when:** refactored code compiles, original tests pass with only re-targeting, and 100% branch
coverage is achievable via the transition matrix.

### Presentation split
| Section | Owner |
|---|---|
| (a) overview & objectives | P3 |
| (b) activity diagram | P2 |
| (c) architecture, components, I/O | P2 |
| (d) code + explanation per component | P1 ep/bva subagents · P2 orchestrator · P4 testgen · P5 refactor |
| (e) test cases, results, coverage (both targets) | P1 (original + coverage sign-off) · P3 (runs + evidence) · P4 (testgen internals) · P5 (refactored) |
| (f) experience & lessons learned | P5 collates — everyone submits 2 bullets by 11/6 |
| (g) conclusion & future work | P5 |
| Assembly, coherence, dry run | P3 |

Everyone explains their own code — a deck where one person narrates another's component reads badly.

---

## 4. Timeline

| Date | Milestone |
|---|---|
| **Sat 10/31 (today)** | 60-min sync. Freeze §2 contracts. Everyone installs JDK 17 + Maven (§2.0). |
| Sun 11/1 – Fri 11/6 | Independent work. Each person owns their directory; no scheduled syncs. |
| **Sat 11/7** | First integration. Assemble, run end to end, fix what breaks, build the deck. |
| Sun 11/8 | Submit + buffer. |

The independence holds because §2 freezes the interfaces up front: the test case schema, the skill
frontmatter, the run directory layout, and the build commands. Each person can build and check their
own piece without waiting on anyone else's.

One risk, named once and not scheduled around: the pipeline is sequential, so the refactor cannot be
validated until the test runner works, which cannot be validated until dedupe works. The plan assumes
each piece lands correct. If 11/7 finds a break earlier in the chain, that day goes to it instead of
the deck.

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| Teacher requires a code-executed runner | The graph is already machine-readable; build the executor then, not now. |
| Skills-only submission looks like "no system" | `orchestrator.md` is an executable state machine, and `STATE.md` plus the run transcripts are the evidence it ran. |
| Refactored branch coverage stalls below 100% | Build the `(state, input)` transition matrix first; derive tests from it. |
| HITL looks fake to a grader | `hitl_decisions.json` with reviewer, timestamp, decision, changes, diff. Record one loop. |
| Model nondeterminism kills the live demo | Rehearse the full run on 11/7 and record it; demo from the recording if a model misbehaves. |
| Parallel work drifts from the schema | CI validates every skill output against `schemas/` on every push. |
| Java env differences between machines | Commit the Maven wrapper, pin JDK 17. |
| Orchestrator skill drifts into prose | Numbered steps, explicit exit conditions, named gates. `validate_skills.py` in CI. |

---

## 6. Questions for the professor (ask by Mon 11/2)

1. Is an agentic coding harness acceptable as the runtime, with the skills as the program and no
   runner? This is the one answer that changes the deliverable.
2. If not, does a code-executed runner have to be part of the submission?
3. Is the "effective prompt" a single prompt, or a set of per-role prompts?
4. What HITL evidence is expected — transcript, video, or a signed decisions log?
5. Does "adapt the existing test cases" allow re-targeting, or must test logic be untouched?

#1 decides the shape of the whole deliverable. #5 is the only one that could cost a day — ask it early.

---

## 7. Submission checklist

- [ ] PPT with all seven sections
- [ ] Agent system: orchestrator skill + stage skills + generated Java
- [ ] Test cases — original **and** refactored
- [ ] Test run results — original **and** refactored
- [ ] Coverage info — original **and** refactored
- [ ] Activity diagram (source + PNG)
- [ ] Prompt mutation log for the refactor
- [ ] HITL decision records
- [ ] Change log from the fix loops
