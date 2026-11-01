#!/usr/bin/env bash
# Branch coverage for one target.
#   usage: scripts/coverage.sh [original|refactored]
# Output (machine-readable, last line):
#   target branch_covered branch_missed branch_pct
set -euo pipefail

target="${1:-original}"
case "$target" in
  original|refactored) ;;
  *) echo "usage: $0 [original|refactored]" >&2; exit 2 ;;
esac

here="$(cd "$(dirname "$0")" && pwd)"
cd "$here/../java"

mvn -q -P "$target" clean test jacoco:report

python3 - "$target" <<'PY'
import sys, xml.etree.ElementTree as ET
from pathlib import Path

target = sys.argv[1]
report = Path("target/site/jacoco/jacoco.xml")
if not report.exists():
    sys.exit(f"no jacoco report at {report}")

covered = missed = 0
for counter in ET.parse(report).getroot().iter("counter"):
    if counter.get("type") == "BRANCH":
        covered += int(counter.get("covered", 0))
        missed += int(counter.get("missed", 0))

total = covered + missed
pct = 100.0 if total == 0 else round(100.0 * covered / total, 2)
print(f"{target} {covered} {missed} {pct}")
PY
