# Boundary Value Analysis (BVA)

Bugs cluster at edges. Test the boundary itself and one step on each
side. This is the single highest-yield category for numeric/length
domains.

## Method
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

## Budget
k bounded parameters -> at least 2 points per bound (edge + outside),
4n+1 worst-case when every bound needs both sides and a nominal.

Use `scripts/boundaries.py` to generate the point list from the domain
spec. Feed its `valid`/`invalid` lists straight into parametrized tests.

## Checklist
- [ ] every bound from the domain spec appears in >=1 test at the edge
      and >=1 test just outside (if validation specified)
- [ ] both sides of every partition cut point are tested
- [ ] empty/zero/singleton covered for sized inputs

## Decision-embedded thresholds
Boundaries live in logic, not only in parameter domains. Every cut or
clamp inside the code/model — floors, caps, tier edges, comparison
constants — gets a both-sides test pair (just below / at / just above
in the smallest unit of the domain). Reconcile TEST_DESIGN's domain
table against the emitted tests: every listed boundary must name its
test.
