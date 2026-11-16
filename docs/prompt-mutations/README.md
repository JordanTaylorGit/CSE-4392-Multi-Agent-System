# Refactor prompt mutation study (owned by P5)

Assignment steps 8 and 9 require practising prompt engineering on the State-pattern refactor:
mutate the prompt against a web LLM until the output is satisfactory, then use the final prompt
in the agent system. This directory is that record.

One file per version (`v01.md` ... `v05.md`). Each version is cumulative: it contains everything
in the previous version plus one addition. Old versions are never edited. Every `{{ORIGINAL_SOURCE}}`
placeholder is replaced with the contents of `SeasonSwitch.java` before the prompt is sent.
The version that wins is copied into `.agents/refactor-state/SKILL.md` and referenced in the deck.

## Mutation table

Verdicts come only from real runs. Anything not yet run says `pending`.

| version | mutation | hypothesis | LLM / date | compiles | tests pass | verdict | notes |
|---------|----------|------------|------------|----------|------------|---------|-------|
| v01 | naive: "refactor using the State pattern" | baseline; shows what an unguided LLM does | pending | pending | pending | pending | |
| v02 | + exact public interface and `main` verbatim | the original tests can be reused unchanged | pending | pending | pending | pending | |
| v03 | + pattern requirements, forbid switch/if chain | forces real delegation to state objects | pending | pending | pending | pending | |
| v04 | + invalid-state handling (int stays source of truth) and no new branches | the invalid-state test passes and coverage stays reachable | pending | pending | pending | pending | |
| v05 | + role framing and an output format with an original-case to state mapping table | gives a mapping usable as `refactor-notes.md` and the transition matrix | ChatGPT free, 2026-11-16 | yes | 21 | Success with comments: main indentation differs, criterion 5 partial | Code was generated in 7s and followed all prompt criteria with no missing results |

## How to run a version

1. Replace `{{ORIGINAL_SOURCE}}` in `vNN.md` with the full `SeasonSwitch.java` and paste it into the LLM.
   Use a fresh chat for every version so earlier versions don't influence the result.
2. Save the raw LLM output under `docs/prompt-mutations/outputs/vNN/` (keep it even if it fails).
3. Copy the generated Java into `java/src/refactored/java/cse4392/` (replace any earlier attempt).
4. From `java/`, run `mvn -P refactored test`. Record whether it compiles and how many tests pass.
5. Open `target/site/jacoco/index.html`. Record branch coverage for `SeasonSwitch`. `main` is excluded
   from the coverage goal, so its 8 missed branches are expected.
6. Diff `main()` against the original. It must be identical.
7. Run `grep -rn "switch" java/src/refactored`. It should find nothing.
8. Review against the checklist below, then fill in the table row.

## Review checklist (G3 gate)

Acceptance criteria from `.agents/refactor-state/SKILL.md`:

- [ ] 1. A `SeasonState` interface exists and `SeasonSwitch` delegates to it
- [ ] 2. No `if`/`switch` chain over state remains in the Subject
- [ ] 3. Each concrete state handles its own transition
- [ ] 4. Invalid transitions are handled explicitly, not by falling through
- [ ] 5. No duplicated transition logic across states
- [ ] 6. Public interface identical to the original (same class name `SeasonSwitch`, same methods)
- [ ] 7. Every original branch maps to a state or transition in `refactor-notes.md`

Additional checks for this codebase:

- [ ] `main()` is identical to the original
- [ ] Console message text is unchanged
- [ ] No new conditional branches were added
- [ ] No `switch (state)` remains inside `Room` either
