---
id: refactor-state
order: 60
executor: agent
inputs: [root:java/src/original/java/cse4392/SeasonSwitch.java]
outputs: [root:java/src/refactored/java/cse4392/, refactor-notes.md]
gate: none
---

# Purpose
Apply the State pattern to `SeasonSwitch`.

# Contract
- Writes the refactored sources under `src/refactored/java`.
- **Hard constraint (assignment hint):** the Subject class is named exactly `SeasonSwitch` and
  keeps the original public interface, so the existing tests are reusable via the
  `refactored` Maven profile.
- `refactor-notes.md` maps original branch -> state/transition, so the transition matrix for
  testing can be derived mechanically.

# Acceptance criteria (feeds the G3 gate)

The output is not "satisfactory" — the assignment's word — until ALL of these hold. These are what
the review gate checks:

1. A `SeasonState` interface exists and `SeasonSwitch` delegates to it.
2. No `if`/`switch` chain over state remains in the Subject.
3. Each concrete state handles its own transition.
4. Invalid transitions are handled explicitly, not by falling through.
5. No duplicated transition logic across states.
6. Public interface identical to the original — same class name `SeasonSwitch`, same methods.
7. Every original branch maps to a state or transition in `refactor-notes.md`.

# Prompt
This is version v1. Mutation history lives in `docs/prompt-mutations/`; the version that
produces acceptable code becomes the one referenced here.

TODO(P5): write the v1 prompt, then iterate:
- v2: add the exact public interface to the prompt.
- v3: forbid an if/switch chain inside the subject.
- v4: require explicit handling of invalid transitions.
- v5: require the transition matrix in `refactor-notes.md`.
Record what each mutation changed and why in `docs/prompt-mutations/README.md`.
