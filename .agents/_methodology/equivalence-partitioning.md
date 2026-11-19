# Equivalence Partitioning (EP)

Divide each input's domain into classes where the program is specified
to behave identically. One representative per class; a test per class.

## Method
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

## Budget
valid test ≈ fewest inputs covering all valid classes; invalid tests =
exactly one per invalid class.

## Checklist
- [ ] every parameter has >=1 valid and (if any validation exists)
      >=1 invalid class
- [ ] no invalid-invalid combinations in one test
- [ ] each class's expected behavior is written down before writing the
      test
