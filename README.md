# CSE 4392/5320 — Multi-Agent System for Software Testing and Refactoring

Team assignment 3. The system tests and refactors `SeasonSwitch` — a three-state thermostat
(`OFF`/`COOL`/`HEAT`) — with equivalence partitioning, boundary value analysis over the 68/77
temperature thresholds, a human-in-the-loop review gate, a repair loop, JaCoCo branch coverage
enforcement, and a State-pattern refactor driven by a versioned prompt.

## How it runs

The agentic coding harness is the runtime. `.agents/orchestrator/SKILL.md` is the program: it dispatches each
stage skill, enforces the four gates, and writes `STATE.md` so a run can resume.

```
point your harness at .agents/orchestrator/SKILL.md   <- the go button
```

Three skills: `.agents/orchestrator/` dispatches `.agents/testgen/` twice (generate, then adapt)
with `.agents/refactor-state/` between them. `testgen` spawns `.agents/ep-tests/` and
`.agents/bva-tests/` as concurrent subagents. They are plain prompts, so any harness that can read a
file and spawn subagents can run the pipeline. Nothing is compiled, nothing is installed, and there
is no runner.

```bash
python3 scripts/validate_skills.py      # lint the skill graph (not a runner)
cd java && mvn -P original test         # original code
../scripts/coverage.sh original         # branch coverage
```

## Where things live

| Path | Owner | What |
|------|-------|------|
| `.agents/orchestrator/` | P2 | orchestrator: the go button, the gates, `STATE.md` |
| `.agents/ep-tests, bva-tests` | P1 | the two test-generation subagents |
| `.agents/testgen` | P4 | the overarching test skill |
| `.agents/refactor-state` | P5 | State-pattern refactor + prompt mutations |
| `projects/` | P4 | project profiles — the seam that keeps the test skills generic |
| `java/`, `scripts/`, `runs/` evidence, `slides/` | P3 | build, coverage tooling, operator, deck |

Full plan and role definitions: `docs/TEAM-PLAN.md`.

## Ground rules

- Own your directory. Do not edit another stage's outputs.
- Skill frontmatter is a frozen contract (`docs/CONTRACTS.md`).
- Test cases and refactored code are Java; the skills are prompts.
- The refactored Subject class stays named `SeasonSwitch` with the original public interface.
- Never weaken an assertion to make the suite pass.
