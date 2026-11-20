"""Build the team 3 deck (owned by P3).

    python3 -m pip install python-pptx      # once; not a project dependency
    python3 slides/build_deck.py             # writes slides/team3.pptx

The seven sections (a)-(g) come from docs/TEAM-PLAN.md, "Presentation split". Numbers are read
from runs/ when a run exists, so the deck never quotes a coverage figure no file backs. Anything
still waiting on a teammate is an amber TODO box naming its owner; search the deck for "TODO"
before submitting.
"""

import argparse
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

REPO_ROOT = Path(__file__).resolve().parent.parent

# Same palette as the team 2 deck.
INK = RGBColor(0x1D, 0x1D, 0x1F)
MUTED = RGBColor(0x6E, 0x6E, 0x73)
BLUE = RGBColor(0x00, 0x71, 0xE3)
GREEN = RGBColor(0x1E, 0x7B, 0x34)
AMBER = RGBColor(0xB2, 0x50, 0x00)
SURFACE = RGBColor(0xF5, 0xF5, 0xF7)
LINE = RGBColor(0xD2, 0xD2, 0xD7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLUE_TINT = RGBColor(0xE8, 0xF1, 0xFC)
GREEN_TINT = RGBColor(0xE8, 0xF5, 0xEC)
AMBER_TINT = RGBColor(0xFD, 0xF0, 0xE4)

SANS = "Arial"      # present on every Windows/Mac PowerPoint
MONO = "Consolas"   # ships with Office on both

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.7)


# ------------------------------------------------------------------ helpers

def text(slide, x, y, w, h, runs, size=18, color=INK, bold=False, font=SANS,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.15):
    """A text box. `runs` is a string, or a list of paragraphs; a paragraph is a
    string or a list of (text, {bold, color, size}) pieces."""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        pieces = para if isinstance(para, list) else [(para, {})]
        for piece, style in pieces:
            r = p.add_run()
            r.text = piece
            r.font.name = style.get("font", font)
            r.font.size = Pt(style.get("size", size))
            r.font.bold = style.get("bold", bold)
            r.font.color.rgb = style.get("color", color)
    return box


def rect(slide, x, y, w, h, fill=SURFACE, line=None, radius=0.08, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, x, y, w, h)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.text_frame.text = ""
    return s


def label_box(slide, x, y, w, h, title, sub="", fill=WHITE, line=LINE, title_color=INK, size=14):
    rect(slide, x, y, w, h, fill=fill, line=line, radius=0.12)
    paras = [[(title, {"bold": True, "color": title_color, "size": size})]]
    if sub:
        paras.append([(sub, {"color": MUTED, "size": size - 3})])
    text(slide, x + Inches(0.12), y, w - Inches(0.24), h, paras, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, spacing=1.05)


def arrow(slide, x1, y1, x2, y2, color=MUTED):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = color
    c.line.width = Pt(1.5)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


def plain(slide, x1, y1, x2, y2, color=MUTED):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    c.line.color.rgb = color
    c.line.width = Pt(1.5)
    return c


def header(slide, title, takeaway=""):
    text(slide, MARGIN, Inches(0.55), W - 2 * MARGIN, Inches(0.7), title, size=32, bold=True)
    if takeaway:
        text(slide, MARGIN, Inches(1.25), W - 2 * MARGIN, Inches(0.5), takeaway, size=16, color=MUTED)


def footer(slide, n, section=""):
    label = f"{section}  ·  {n}" if section else str(n)
    text(slide, W - MARGIN - Inches(6), H - Inches(0.45), Inches(6), Inches(0.3),
         f"Multi-Agent Testing & Refactoring  ·  {label}", size=10, color=MUTED, align=PP_ALIGN.RIGHT)


def table(slide, x, y, w, rows, col_w, size=13, row_h=0.42, head_fill=SURFACE):
    """Simple ruled table built from text boxes (keeps full control of the look)."""
    cy = y
    for r, row in enumerate(rows):
        hgt = Inches(row_h)
        if r == 0:
            rect(slide, x, cy, w, hgt, fill=head_fill, radius=0.15)
        cx = x
        for c, cell in enumerate(row):
            cw = Inches(col_w[c])
            text(slide, cx + Inches(0.12), cy, cw - Inches(0.2), hgt, cell, size=size,
                 bold=(r == 0), color=INK if r else MUTED, anchor=MSO_ANCHOR.MIDDLE, spacing=1.0)
            cx += cw
        cy += hgt
        if r:
            ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, cy, x + w, cy)
            ln.line.color.rgb = LINE
            ln.line.width = Pt(0.75)
    return cy




def code(slide, x, y, w, h, source: str, size=12):
    rect(slide, x, y, w, h, fill=SURFACE, radius=0.04)
    text(slide, x + Inches(0.25), y + Inches(0.2), w - Inches(0.5), h - Inches(0.4),
         source.strip("\n").split("\n"), size=size, font=MONO, spacing=1.08)


def bullets(slide, x, y, w, h, items, size=16, gap=0.12):
    paras = []
    for item in items:
        if isinstance(item, tuple):  # (bold lead, rest)
            paras.append([(item[0], {"bold": True}), (item[1], {})])
        else:
            paras.append(item)
    box = text(slide, x, y, w, h, paras, size=size, spacing=1.2)
    for p in box.text_frame.paragraphs:
        p.space_after = Pt(size * gap * 4)
    return box




def todo(slide, x, y, w, h, owner, what, size=15):
    """An amber placeholder: names who fills it and what goes there."""
    rect(slide, x, y, w, h, fill=AMBER_TINT, line=AMBER, radius=0.06)
    text(slide, x + Inches(0.3), y, w - Inches(0.6), h,
         [[("TODO, " + owner, {"bold": True, "color": AMBER})], what],
         size=size, color=AMBER, anchor=MSO_ANCHOR.MIDDLE, spacing=1.2)


# ------------------------------------------------------------------ evidence

def latest_run(runs: Path, target: str) -> dict | None:
    """Newest runs/<ts>/ whose coverage.txt is for `target`, read into numbers."""
    for run in sorted(runs.glob("*/coverage.txt"), reverse=True):
        parts = run.read_text().split()
        if len(parts) == 4 and parts[0] == target:
            return {"dir": run.parent, "covered": int(parts[1]), "missed": int(parts[2]),
                    "pct": float(parts[3]), **surefire(run.parent / "surefire"),
                    "methods": methods(run.parent / "jacoco.xml")}
    return None


def surefire(folder: Path) -> dict:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for xml in folder.glob("*.xml"):
        head = re.search(r"<testsuite [^>]*>", xml.read_text())
        for key in totals:
            m = re.search(rf'\b{key}="(\d+)"', head.group(0)) if head else None
            totals[key] += int(m.group(1)) if m else 0
    return totals


def methods(jacoco: Path) -> list[tuple[str, int, int]]:
    """(method, covered, missed) branch counts, main() left out as in scripts/coverage.sh."""
    import xml.etree.ElementTree as ET
    if not jacoco.exists():
        return []
    out = []
    for cls in ET.parse(jacoco).getroot().iter("class"):
        # SeasonSwitch's own methods stay bare; inner classes and state classes get a prefix,
        # since both CoolState and HeatState have a timerOff().
        simple = cls.get("name").rsplit("/", 1)[-1]
        inner = simple.split("$", 1)[1] + "." if "$" in simple else ("" if simple == "SeasonSwitch" else simple + ".")
        for m in cls.findall("method"):
            b = [c for c in m.findall("counter") if c.get("type") == "BRANCH"]
            if b and m.get("name") != "main":
                out.append((inner + m.get("name") + "()", int(b[0].get("covered")), int(b[0].get("missed"))))
    return out


def pipeline_run(runs: Path) -> dict | None:
    """Newest complete pipeline run (runs/<ts>-<id>/ with status.json), read into the pieces the deck shows."""
    import json
    for d in sorted(runs.glob("*-*/status.json"), reverse=True):
        run = d.parent
        if json.loads(d.read_text()).get("status") != "complete" or not (run / "hitl_decisions.json").exists():
            continue
        cases = json.loads((run / "testcases_final.json").read_text())
        cases = cases["cases"] if isinstance(cases, dict) else cases
        out = {"dir": run, "cases": cases, "status": json.loads(d.read_text()),
               "decisions": json.loads((run / "hitl_decisions.json").read_text())}
        for target in ("original", "refactored"):
            attempt = sorted((run / target).glob("attempt-*"))[-1]
            r = json.loads((attempt / "result.json").read_text())
            out[target] = {"dir": run, "covered": r["covered"], "missed": r["missed"], "pct": r["percent"],
                           "tests": r["tests"], "failures": r["failures"], "errors": 0,
                           "attempts": len(list((run / target).glob("attempt-*"))),
                           "methods": methods(attempt / "jacoco.xml")}
        return out
    return None


# ------------------------------------------------------------------- slides

def build(out: Path) -> list[str]:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]
    state = {"n": 0, "sec": ""}
    todos: list[str] = []

    def new(section=None):
        if section is not None:
            state["sec"] = section
        state["n"] += 1
        s = prs.slides.add_slide(blank)
        if state["n"] > 1:
            footer(s, state["n"], state["sec"])
        return s

    def hole(slide, x, y, w, h, owner, what, size=15):
        todos.append(f"slide {state['n']}: {owner}: {what}")
        todo(slide, x, y, w, h, owner, what, size)

    body_w = W - 2 * MARGIN
    orig = latest_run(REPO_ROOT / "runs", "original")
    refac = latest_run(REPO_ROOT / "runs", "refactored")
    pipe = pipeline_run(REPO_ROOT / "runs")
    if pipe:
        orig, refac = pipe["original"], pipe["refactored"]

    # 1. Title -------------------------------------------------------------
    s = new()
    text(s, MARGIN, Inches(1.6), body_w, Inches(1.6),
         "A multi-agent system that tests and refactors SeasonSwitch", size=40, bold=True)
    text(s, MARGIN, Inches(3.2), body_w, Inches(0.5),
         "CSE 4392/5320  ·  Team Assignment 3", size=20, color=MUTED)
    team = [
        ("Kyle Henry (P1, team lead)", "EP and BVA test-generation subagents"),
        ("Loc Nguyen (P2)", "orchestrator skill and activity diagram"),
        ("Talha Nadeem (P3)", "Java build, coverage tooling, pipeline runs, this deck"),
        ("Miguel Oropeza (P4)", "testgen skill and project profiles"),
        ("Jordan Taylor (P5)", "State-pattern refactor and prompt-mutation study"),
    ]
    y = Inches(4.3)
    for who, role in team:
        text(s, MARGIN, y, Inches(3.6), Inches(0.4), who, size=16, bold=True,
             color=AMBER if who.startswith("TODO") else INK)
        text(s, MARGIN + Inches(3.7), y, Inches(8), Inches(0.4), role, size=16, color=MUTED)
        y += Inches(0.45)

    # (a) overview & objectives -------------------------------------------
    s = new("(a) Overview")
    header(s, "The subject: a three-state thermostat",
           "SeasonSwitch keeps one static state and three switch blocks. That's the smell the refactor removes.")
    table(s, MARGIN, Inches(2.1), Inches(7.6), [
        ["From \\ call", "cool()", "heat()", "off()"],
        ["OFF", "AC on, go to COOL", "heater on, go to HEAT", "nothing"],
        ["COOL", "nothing", "AC off, heater on, go to HEAT", "AC off, go to OFF"],
        ["HEAT", "heater off, AC on, go to COOL", "nothing", "heater off, go to OFF"],
    ], [1.3, 2.1, 2.3, 1.9], size=13, row_h=0.62)
    bullets(s, Inches(8.8), Inches(2.1), Inches(3.9), Inches(4.5), [
        ("Timer tick: ", "COOL keeps the AC on while the room is above 68; HEAT keeps the heater on below 77."),
        ("Boundaries: ", "67 / 68 / 69 and 76 / 77 / 78. 68 and 77 are the stop values."),
        ("Not testable: ", "main() waits forever and calls System.exit, so coverage leaves it out."),
    ], size=14)
    text(s, MARGIN, Inches(4.9), Inches(7.6), Inches(1.2),
         "Source: docs/original-behavior.md, from running the program in every mode.", size=12, color=MUTED)

    s = new()
    header(s, "Objectives", "The pipeline runs the assignment's 12 steps in order, with people approving the results at review gates.")
    goals = [
        ("Generate tests", "EP and BVA cases from a project profile, written by two subagents running concurrently."),
        ("Reach full coverage", "100% branch coverage on the original code, measured by JaCoCo."),
        ("Refactor", "Move SeasonSwitch to the State pattern; keep the class name and its public methods."),
        ("Reuse the tests", "Re-target the approved cases at the refactored code and reach 100% again."),
        ("Keep humans in the loop", "Reviewers approve test cases (G1) and refactored code (G3); each decision is recorded."),
    ]
    y = Inches(2.1)
    for i, (lead, rest) in enumerate(goals, 1):
        rect(s, MARGIN, y, Inches(0.5), Inches(0.5), fill=BLUE_TINT, radius=0.5, shape=MSO_SHAPE.OVAL)
        text(s, MARGIN, y, Inches(0.5), Inches(0.5), str(i), size=16, bold=True, color=BLUE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        text(s, MARGIN + Inches(0.75), y - Inches(0.02), Inches(11), Inches(0.9),
             [[(lead, {"bold": True})], [(rest, {"color": MUTED, "size": 15})]], size=17, spacing=1.1)
        y += Inches(0.92)

    # (b) activity diagram -------------------------------------------------
    s = new("(b) Activity diagram")
    header(s, "Activity diagram", "One run of the pipeline, from start to HALT.")
    png = REPO_ROOT / "docs" / "activity.png"
    if png.exists():
        pic = s.shapes.add_picture(str(png), MARGIN, Inches(1.85), height=Inches(5.15))
        pic.line.color.rgb = LINE
        pic.line.width = Pt(0.75)
        bullets(s, MARGIN + pic.width + Inches(0.6), Inches(2.0), body_w - pic.width - Inches(0.6), Inches(4.8), [
            ("Fork and join: ", "EP and BVA generation run in parallel; the merge waits for both and rejects conflicting cases."),
            ("G1, human: ", "the run stops until a person accepts the test cases or asks for changes."),
            ("Repair: ", "a failing build sends the source code back for repair; the tests stay unchanged. At most 5 tries."),
            ("G2 and G4, coverage: ", "continue only with passing tests and zero missed branches; otherwise propose GAP tests, which go back to human review."),
            ("G3, human: ", "a person reviews the refactored code, notes and tests before the tests are re-run on it."),
            ("Source: ", "docs/activity.drawio (Loc), rendered by scripts/render_activity.py."),
        ], size=15)
    else:
        steps = [("testgen", "generate · original", BLUE_TINT), ("G1", "review cases", AMBER_TINT),
                 ("run + repair", "≤ 5 loops", SURFACE), ("coverage gate", "100% branches", GREEN_TINT),
                 ("refactor-state", "prompt mutations", BLUE_TINT), ("G3", "review code", AMBER_TINT),
                 ("testgen", "adapt · refactored", BLUE_TINT), ("coverage gate", "then HALT", GREEN_TINT)]
        bw, gap, y0 = Inches(1.3), Inches(0.24), Inches(2.3)
        x = MARGIN
        for i, (t, sub, fill) in enumerate(steps):
            label_box(s, x, y0, bw, Inches(1.0), t, sub, fill=fill, size=13)
            if i < len(steps) - 1:
                arrow(s, x + bw, y0 + Inches(0.5), x + bw + gap, y0 + Inches(0.5))
            x += bw + gap
        label_box(s, MARGIN, Inches(3.7), Inches(2.8), Inches(0.75), "ep-tests  ∥  bva-tests",
                  "concurrent subagents, then join", fill=WHITE, size=12)
        arrow(s, MARGIN + Inches(0.65), Inches(3.7), MARGIN + Inches(0.65), y0 + Inches(1.0))
        hole(s, MARGIN, Inches(4.9), body_w, Inches(1.6), "P2 (Loc)",
             "Replace this sketch with docs/activity.png (the UML activity diagram); the deck picks it up "
             "automatically on the next build.")

    # (c) architecture -----------------------------------------------------
    s = new("(c) Architecture")
    header(s, "Components, inputs and outputs",
           "The skills are the program and the coding agent's harness runs them. Nothing is compiled or installed.")
    table(s, MARGIN, Inches(2.0), body_w, [
        ["Component", "Owner", "Job", "Input", "Output"],
        ["orchestrator", "P2", "Dispatches the skills, holds the gates, writes STATE.md", "project profile", "runs/<ts>/"],
        ["testgen", "P4", "Full test lifecycle for one target, run twice", "profile, target, mode", "suite + coverage"],
        ["ep-tests", "P1", "Subagent: equivalence-partition cases", "profile", "testcases_ep.json"],
        ["bva-tests", "P1", "Subagent: boundary-value cases", "profile", "testcases_bva.json"],
        ["refactor-state", "P5", "State pattern, driven by a versioned prompt", "original source", "refactored source"],
        ["build + coverage", "P3", "Maven profiles, JaCoCo, scripts/coverage.sh", "target name", "coverage.txt"],
    ], [2.1, 0.8, 4.6, 2.2, 2.2], size=13, row_h=0.56)
    text(s, MARGIN, Inches(6.1), body_w, Inches(0.6),
         "Source: docs/ARCH.md and each skill's frontmatter (id, inputs, outputs, gate), which scripts/validate_skills.py checks in CI.",
         size=12, color=MUTED)

    s = new()
    header(s, "One test suite for both versions",
           "Both classes are named SeasonSwitch, so a Maven profile picks which source folder to compile.")
    code(s, MARGIN, Inches(2.0), Inches(6.6), Inches(4.3), """
<properties>
  <main.src.dir>src/original/java</main.src.dir>
</properties>
<build>
  <sourceDirectory>${main.src.dir}</sourceDirectory>
</build>
<profile>
  <id>refactored</id>
  <properties>
    <main.src.dir>src/refactored/java</main.src.dir>
  </properties>
</profile>""", size=13)
    bullets(s, Inches(7.7), Inches(2.0), Inches(4.9), Inches(4.5), [
        ("mvn -P original test ", "and  mvn -P refactored test  run the same src/test/java."),
        ("scripts/coverage.sh <target> ", "prints  target covered missed pct  for the gate to read."),
        ("Counted per method: ", "jacoco.xml repeats each total at four levels; adding all of them would report four times too much."),
    ], size=14)

    # (d) code per component ----------------------------------------------
    for title, owner, what in [
        ("EP and BVA subagents", "P1 (Kyle)", "Frontmatter, how the profile drives the cases, and one case each from testcases_ep.json and testcases_bva.json."),
        ("Orchestrator", "P2 (Loc)", "The LangGraph graph in harness/graph.py: the parallel EP/BVA fan-out, the G1 and G3 interrupts, the 5-loop caps, and resuming from the SQLite checkpoint."),
    ]:
        s = new("(d) Code")
        header(s, title, "")
        hole(s, MARGIN, Inches(2.0), body_w, Inches(2.2), owner, what)

    s = new("(d) Code")
    header(s, "Refactor skill and prompt mutations",
           "Five prompt versions, each judged by the same 21 tests on the original behavior.")
    code(s, MARGIN, Inches(1.95), Inches(5.3), Inches(4.0), """
interface SeasonState {
  void cool(SeasonSwitch context);
  void heat(SeasonSwitch context);
  void off(SeasonSwitch context);
  void timerOff(SeasonSwitch context);
  void roomActionPerformed(SeasonSwitch context);
}

// SeasonSwitch (the context)
SeasonState getCurrentState() {
  return STATES.getOrDefault(state, NO_OP_STATE);
}
public void cool() { getCurrentState().cool(this); }""", size=11)
    table(s, MARGIN + Inches(5.5), Inches(1.95), body_w - Inches(5.5), [
        ["Ver", "What changed", "Why", "Result"],
        ["v01", "Naive: \"use the State pattern\"", "Baseline", "Did not compile: removed state and the constants the tests use"],
        ["v02", "+ exact public interface, main verbatim", "Make existing tests reusable", "20/21: private state object ignores direct state writes"],
        ["v03", "+ forbid switch/if chains; Room delegates", "Force real delegation", "20/21: same failure, leftover if-chain in setState"],
        ["v04", "+ state stays the source of truth, no-op state, no new branches", "Fix invalid-state handling", "21/21 pass"],
        ["v05", "+ one class per file, mapping-table output", "Structure and documentation", "21/21 pass, 100% branch coverage (excl. main)"],
    ], [0.55, 2.15, 1.55, 2.15], size=11, row_h=0.8)
    rect(s, MARGIN, Inches(6.25), body_w, Inches(0.55), fill=AMBER_TINT, line=AMBER, radius=0.1)
    text(s, MARGIN + Inches(0.3), Inches(6.25), body_w - Inches(0.6), Inches(0.55),
         "Concrete states: OffState, CoolState, HeatState (each owns its transitions), NoOpState (unrecognized values). "
         "Prompts: docs/prompt-mutations/v01–v05.md.",
         size=13, color=AMBER, anchor=MSO_ANCHOR.MIDDLE)

    s = new("(d) Code")
    header(s, "testgen: one skill for the whole test lifecycle",
           "It runs twice: generate on the original, then adapt on the refactored code.")
    phases = [("Merge", "merge_cases.py joins EP + BVA and dedupes"),
              ("G1 review", "review_cases.py records the human decision"),
              ("Write JUnit", "materialize_junit.py from approved cases"),
              ("Run + repair", "up to 5 loops; never weaken an assertion"),
              ("Coverage gate", "exit only at 100% branches")]
    x, bw, gap = MARGIN, Inches(2.25), Inches(0.21)
    for i, (t, sub) in enumerate(phases):
        label_box(s, x, Inches(2.1), bw, Inches(1.25), t, sub, fill=BLUE_TINT if i % 2 == 0 else WHITE, size=14)
        if i < len(phases) - 1:
            arrow(s, x + bw, Inches(2.72), x + bw + gap, Inches(2.72))
        x += bw + gap
    text(s, MARGIN, Inches(3.75), Inches(6.6), Inches(0.35),
         ".agents/testgen/materialize_junit.py", size=12, bold=True, color=MUTED, font=MONO)
    code(s, MARGIN, Inches(4.1), Inches(6.6), Inches(2.2), """
render_cases = deepcopy(cases["cases"])
if mode == "adapt":
    for case in render_cases:
        case["target"] = "refactored"
source = adapter.render(render_cases, profile,
                        output.stem)""", size=13)
    bullets(s, Inches(7.7), Inches(3.75), Inches(4.9), Inches(2.8), [
        ("Merge: ", "EP + BVA cases are joined; conflicts and duplicates are rejected."),
        ("G1 first: ", "no JUnit is generated until a person approves the cases."),
        ("Adapt mode: ", "only the target changes; the expected results stay the same."),
        ("Same checks, new code: ", "the refactored class is held to the original behavior."),
    ], size=14, gap=0.08)

    # (e) tests, results, coverage ----------------------------------------
    s = new("(e) Tests and coverage")
    if pipe:
        import collections, json
        cases = pipe["cases"]
        ep = [c for c in cases if c["method"] == "EP"]
        bva = [c for c in cases if c["method"] == "BVA"]
        units = collections.Counter(c["unit"] for c in ep)
        temps = sorted({c["setup"].get("room.temp") for c in bva})
        header(s, "Original code: test cases from the pipeline",
               f"{len(ep)} EP + {len(bva)} BVA cases, merged with no duplicates or conflicts, approved at G1, then written as JUnit.")
        table(s, MARGIN, Inches(2.0), Inches(6.2), [
            ["Subagent", "Cases", "What they cover"],
            ["ep-tests", str(len(ep)), ", ".join(f"{u} {n}" for u, n in units.items())],
            ["bva-tests", str(len(bva)), "timerOff() in OFF, COOL and HEAT at " + ", ".join(map(str, temps))],
            ["merged", str(len(cases)), "0 removed (dedupe key: unit, setup, inputs)"],
        ], [1.4, 0.9, 3.9], size=13, row_h=0.72)
        text(s, MARGIN, Inches(5.1), Inches(6.2), Inches(1.2),
             f"Plus the 21 hand-written safety-net tests: {pipe['original']['tests']} JUnit tests in total. "
             f"From {pipe['dir'].relative_to(REPO_ROOT)}/testcases_final.json.", size=12, color=MUTED)
        ex_bva = next(c for c in bva if c["setup"].get("room.temp") == 68 and c["setup"].get("state") == "COOL")
        def show(c):
            setup = ", ".join(f"{k}={json.dumps(v)}" for k, v in c["setup"].items())
            exp = ", ".join(f"{k}={json.dumps(v)}" for k, v in c["expected"].items() if k != "stdout")
            return f'{c["id"]}  {c["unit"]}()\n  given  {setup}\n  expect {exp}\n  prints {c["expected"].get("stdout", "").strip()}'
        code(s, Inches(7.1), Inches(2.0), Inches(5.5), Inches(4.3),
             show(ep[0]) + "\n\n" + show(ex_bva), size=11)
    else:
      header(s, "Original code: test cases",
           "21 JUnit tests, one per cell of the (state × event) matrix, plus room ticks.")
      table(s, MARGIN, Inches(2.0), Inches(7.4), [
        ["Group", "Tests", "What they cover"],
        ["cool() / heat() / off()", "9", "every state × command, including no-ops"],
        ["timerOff()", "5", "OFF, and each side of 68 and 77"],
        ["Room tick", "5", "temperature drift per state and device"],
        ["Other", "2", "invalid state ignored; actionPerformed delegates"],
    ], [2.6, 0.9, 3.9], size=14, row_h=0.58)
      hole(s, Inches(8.4), Inches(2.0), Inches(4.2), Inches(3.0), "P1 / P4",
         "These are Jordan's hand-written safety-net tests. Replace or add the pipeline's own case set (testcases_final.json) once a full run exists.", size=13)

    def results(run, title, takeaway, note, missing):
        s = new()
        header(s, title, f"{takeaway} From {run['dir'].relative_to(REPO_ROOT)}." if run else takeaway)
        if not run:
            hole(s, MARGIN, Inches(2.0), body_w, Inches(2.2), *missing)
            return
        stats = [(f"{run['tests'] - run['failures'] - run['errors']}/{run['tests']}", "tests pass"),
                 (f"{run['covered']}/{run['covered'] + run['missed']}", "branches covered"),
                 (f"{run['pct']:g}%", "branch coverage")]
        x = MARGIN
        for big, small in stats:
            text(s, x, Inches(2.0), Inches(3.4), Inches(0.9), big, size=44, bold=True, color=GREEN)
            text(s, x, Inches(2.9), Inches(3.4), Inches(0.4), small, size=15, color=MUTED)
            x += Inches(3.6)
        y, bar_w = Inches(3.7), Inches(6.0)
        for name, cov, miss in run["methods"]:
            total = cov + miss
            text(s, MARGIN, y, Inches(3.9), Inches(0.38), name, size=14, font=MONO, anchor=MSO_ANCHOR.MIDDLE)
            rect(s, MARGIN + Inches(4.0), y + Inches(0.08), bar_w, Inches(0.22), fill=SURFACE, radius=0.5)
            if cov:
                rect(s, MARGIN + Inches(4.0), y + Inches(0.08), int(bar_w * cov / total), Inches(0.22), fill=GREEN, radius=0.5)
            text(s, MARGIN + Inches(10.2), y, Inches(1.8), Inches(0.38), f"{cov}/{total}", size=14, anchor=MSO_ANCHOR.MIDDLE)
            y += Inches(0.48)
        text(s, MARGIN, y + Inches(0.1), body_w, Inches(0.7), note, size=12, color=MUTED)

    results(orig, "Original code: results and branch coverage",
            f"{orig['tests']} tests: {orig['tests'] - 21} generated by the pipeline plus the 21 hand-written ones." if pipe else "",
            "main() (8 branches) is left out: it blocks forever and calls System.exit. JaCoCo 0.8.12, JUnit 5.10.2, JDK 17.",
            ("P3", "Run scripts/coverage.sh original and save the run in runs/."))
    results(refac, "Refactored code: results and branch coverage",
            "The same approved tests, unchanged; only the Maven profile differs." if pipe else "The same 21 tests, unchanged; only the Maven profile differs.",
            "28 branches became 8: the five switch (state) blocks turned into calls on the current state object, "
            "which JaCoCo doesn't count as branches. What's left are the 68/77 checks and the room tick. Every line outside main() is covered.",
            ("P5 + P3", "Needs java/src/refactored (Jordan). Then P3 runs scripts/coverage.sh refactored and saves "
                        "the run; this slide fills itself in on the next build."))

    s = new()
    header(s, "Human-in-the-loop evidence", "Each gate stops the run and records who decided what, and when.")
    if not pipe:
        hole(s, MARGIN, Inches(2.0), body_w, Inches(2.2), "P3 (after the full run)",
             "hitl_decisions.json from G1 and G3: reviewer, timestamp, decision, requested changes, resulting diff.")
    else:
        names = {"review_testcases": "G1  test cases", "review_refactored": "G3  refactored code"}
        rows = [["Gate", "Reviewer", "Decision", "Time (UTC)", "Artifact sha256"]]
        for d in pipe["decisions"]:
            rows.append([names.get(d["gate"], d["gate"]), d["reviewer"], d["decision"],
                         d["timestamp_utc"][:16].replace("T", " "), d["artifact_sha256"][:12] + "…"])
        table(s, MARGIN, Inches(2.0), body_w, rows, [2.4, 4.0, 1.2, 2.2, 2.1], size=13, row_h=0.6)
        counts = pipe["status"]["counts"]
        bullets(s, MARGIN, Inches(4.1), Inches(6.2), Inches(2.4), [
            ("Resumable: ", "the run stops at each gate; resuming needs a decision file whose sha256 matches the reviewed artifact."),
            ("Attempts: ", ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in counts.items()) + " (cap 5)."),
        ], size=14)
        bullets(s, Inches(7.1), Inches(4.1), Inches(5.5), Inches(2.4), [
            ("Gates that held: ", "of 5 runs, one paused for a person after the model's reply was cut off three times, and one was "
                                  "blocked at the merge (EP-12 and BVA-01 expected different results for the same input)."),
            ("Source: ", f"{pipe['dir'].relative_to(REPO_ROOT)}/hitl_decisions.json and STATE.md."),
        ], size=14)

    # (f) lessons ----------------------------------------------------------
    s = new("(f) Lessons learned")
    header(s, "Experience and lessons learned", "Two bullets from each person; P5 collects them.")
    text(s, MARGIN, Inches(1.85), Inches(6), Inches(0.3), "P3", size=12, bold=True, color=MUTED)
    bullets(s, MARGIN, Inches(2.15), Inches(6.0), Inches(2.0), [
        ("Run the build on day one. ", "The scaffold's pom.xml could not be parsed (a \"--\" inside a comment), and nobody noticed until Maven ran."),
        ("Check the coverage arithmetic. ", "Adding up every counter in jacoco.xml looked plausible and was four times too high."),
    ], size=14)
    text(s, MARGIN, Inches(4.1), Inches(6), Inches(0.3), "P5", size=12, bold=True, color=MUTED)
    bullets(s, MARGIN, Inches(4.4), Inches(6.0), Inches(2.3), [
        ("Tests first gave us an objective judge. ", "Writing a 21-test matrix over the original before refactoring made every prompt version a pass/fail result."),
        ("Constraints beat descriptions, but passing tests aren't a design review. ", "Prompts that named what the tests depend on fixed the failures."),
    ], size=14)
    text(s, Inches(7.1), Inches(1.85), Inches(5.5), Inches(0.3), "P4", size=12, bold=True, color=MUTED)
    bullets(s, Inches(7.1), Inches(2.15), Inches(5.5), Inches(2.0), [
        ("Validate before generating. ", "Schema checks and G1 approval kept invalid or outdated cases from becoming tests."),
        ("Separate logic from the project. ", "A reusable testgen tool and a SeasonSwitch adapter made refactored test reuse easier."),
    ], size=14)
    hole(s, Inches(7.1), Inches(4.4), Inches(5.5), Inches(2.0), "P1, P2",
         "Two bullets each.", size=15)

    # (g) conclusion -------------------------------------------------------
    s = new("(g) Conclusion")
    header(s, "Conclusion and future work", "")
    col = (body_w - Inches(0.5)) / 2
    for i, (head, items) in enumerate([
        ("What the system achieved", [
            "Refactored SeasonSwitch to the State pattern with the same public interface, passing all 21 existing tests unmodified",
            "100% branch coverage on the state logic (main() excluded by agreement)",
            "Documented the prompt study across five versions, with a transition matrix for the refactored code",
        ]),
        ("What comes next", [
            "Prompt v06: extract the duplicated \"turn on, start timer, set state, print\" sequences into shared helpers without adding branches",
            "A purer State pattern where the context holds the state object, with adapted tests, to compare against the int-based version",
            "Repeat each prompt several times and across models, since each version was a single run",
            "Try a smaller local model, or run the same pipeline on another project behind the same profile (e.g. grade-classifier)",
        ]),
    ]):
        x = MARGIN + i * (col + Inches(0.5))
        text(s, x, Inches(1.9), col, Inches(0.5), head, size=20, bold=True, color=GREEN if i == 0 else BLUE)
        bullets(s, x, Inches(2.55), col, Inches(4.2), ["•  " + t for t in items], size=15, gap=0.08)

    s = new("Questions")
    text(s, MARGIN, Inches(2.8), body_w, Inches(1.2), "Questions?", size=48, bold=True, align=PP_ALIGN.CENTER)
    text(s, MARGIN, Inches(4.0), body_w, Inches(0.6),
         "github.com/JordanTaylorGit/CSE-4392-Multi-Agent-System", size=16, color=MUTED, align=PP_ALIGN.CENTER)

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    return todos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "slides" / "team3.pptx")
    args = ap.parse_args(argv)
    todos = build(args.out)
    print(f"Wrote {args.out}")
    print(f"{len(todos)} TODOs:" if todos else "No TODOs left.")
    for t in todos:
        print("  " + t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
