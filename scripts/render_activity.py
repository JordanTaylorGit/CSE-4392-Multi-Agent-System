#!/usr/bin/env python3
"""Render the P2 activity diagram as editable draw.io XML and a matching PNG."""
from __future__ import annotations

import math
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SIZE = (1600, 2320)
COLORS = {"stage": "#EAF0FF", "human": "#FFF0CF", "gate": "#DCF4EA", "loop": "#F0EBFA"}
# id, label, left, top, width, height, type
NODES = [
    ("start", "START\nCreate run workspace + SQLite checkpoint", 500, 130, 600, 80, "stage"),
    ("ep", "EP generation", 450, 280, 320, 80, "stage"),
    ("bva", "BVA generation", 830, 280, 320, 80, "stage"),
    ("merge", "JOIN + DEDUPE\nWait for both generators; reject conflicts", 500, 430, 600, 80, "stage"),
    ("g1", "G1 · HUMAN CASE REVIEW\nInterrupt / persist / resume", 550, 590, 500, 90, "human"),
    ("junit", "Materialize approved JUnit\nP4 project adapter", 550, 740, 500, 80, "stage"),
    ("original", "Build + test original\nMaven / Surefire / JaCoCo", 550, 900, 500, 80, "stage"),
    ("g2", "G2 · COVERAGE\nPassing tests + zero missed branches", 550, 1060, 500, 90, "gate"),
    ("refactor", "State-pattern refactor + compile\nVersion prompt; replace source tree", 550, 1220, 500, 80, "stage"),
    ("g3", "G3 · HUMAN REFACTOR REVIEW\nCode, notes, cases, and tests", 550, 1380, 500, 90, "human"),
    ("adapt", "Adapt target metadata\nReuse approved JUnit unchanged", 550, 1540, 500, 80, "stage"),
    ("refactored", "Build + test refactored\nMaven / Surefire / JaCoCo", 550, 1700, 500, 80, "stage"),
    ("g4", "G4 · COVERAGE\nPassing tests + zero missed branches", 550, 1860, 500, 90, "gate"),
    ("done", "COMPLETE\nBoth targets verified; write report", 550, 2030, 500, 80, "gate"),
    ("repair_o", "Repair original sources\nTests stay unchanged", 1180, 900, 340, 80, "loop"),
    ("gap_o", "Propose original GAP\nNew cases + new JUnit", 70, 1060, 340, 90, "loop"),
    ("repair_r", "Repair refactored sources\nCompile; renew G3", 1180, 1700, 340, 80, "loop"),
    ("gap_r", "Propose refactored GAP\nNew cases + new JUnit", 70, 1860, 340, 90, "loop"),
]
# Source, target, explicit polyline, label, label center (where needed).
EDGES = [
    ("start", "ep", [(680,210),(680,245),(610,245),(610,280)], "parallel", (610,232)),
    ("start", "bva", [(920,210),(920,245),(990,245),(990,280)], "parallel", (990,232)),
    ("ep", "merge", [(610,360),(610,395),(700,395),(700,430)], "", None),
    ("bva", "merge", [(990,360),(990,395),(900,395),(900,430)], "", None),
    ("merge", "g1", [(800,510),(800,590)], "valid", (840,550)),
    ("g1", "junit", [(800,680),(800,740)], "initial accept", (900,710)),
    ("junit", "original", [(800,820),(800,900)], "", None),
    ("original", "g2", [(800,980),(800,1060)], "passing", (866,1020)),
    ("original", "repair_o", [(1050,940),(1180,940)], "failed", (1115,920)),
    ("repair_o", "original", [(1350,900),(1350,855),(940,855),(940,900)], "retry", (1130,840)),
    ("g2", "gap_o", [(550,1105),(410,1105)], "missed > 0", (480,1083)),
    ("gap_o", "g1", [(240,1060),(240,635),(550,635)], "G1", (285,650)),
    ("g1", "original", [(550,660),(455,660),(455,940),(550,940)], "GAP accept:\nappend tests", (365,800)),
    ("g2", "refactor", [(800,1150),(800,1220)], "zero missed", (900,1185)),
    ("refactor", "g3", [(800,1300),(800,1380)], "compiled", (880,1340)),
    ("refactor", "refactor", [(1050,1240),(1390,1240),(1390,1180),(990,1180),(990,1220)], "compile failure: retry", (1250,1160)),
    ("g3", "refactor", [(1050,1425),(1450,1425),(1450,1280),(1050,1280)], "code changes", (1320,1400)),
    ("g3", "adapt", [(800,1470),(800,1540)], "initial accept", (900,1505)),
    ("adapt", "refactored", [(800,1620),(800,1700)], "", None),
    ("g3", "refactored", [(1050,1450),(1100,1450),(1100,1660),(1000,1660),(1000,1700)], "later accept", (1210,1570)),
    ("refactored", "repair_r", [(1050,1740),(1180,1740)], "failed", (1115,1720)),
    ("repair_r", "g3", [(1350,1700),(1350,1490),(1030,1490),(1030,1470)], "compiled", (1400,1600)),
    ("refactored", "g4", [(800,1780),(800,1860)], "passing", (866,1820)),
    ("g4", "gap_r", [(550,1905),(410,1905)], "missed > 0", (480,1883)),
    ("gap_r", "g3", [(240,1860),(240,1425),(550,1425)], "G3", (285,1448)),
    ("g3", "refactored", [(550,1450),(455,1450),(455,1740),(550,1740)], "GAP accept:\nappend tests", (350,1600)),
    ("g4", "done", [(800,1950),(800,2030)], "zero missed", (900,1990)),
]
NOTES = [
    (800, 45, "P2 · LANGGRAPH ACTIVITY", 36),
    (800, 92, "Injected Ollama model · durable human review · measured Java execution", 22),
    (800, 2160, "Rejections return to the producer: G1 → generation or original GAP; G3 → refactor or refactored GAP.", 22),
    (800, 2200, "Generation, refactor, repairs, and GAP proposals: at most 5 attempts per phase/target. Invalid artifacts → BLOCKED.", 22),
    (800, 2240, "Refactored repair compilation failures retry repair. Coverage excludes main(); missing or empty reports cannot pass.", 22),
    (800, 2280, "Graph concurrency does not guarantee simultaneous Ollama inference. Model output never approves a human gate.", 22),
]


def font(size):
    for path in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def render():
    canvas = Image.new("RGB", SIZE, "#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    document = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(document, "diagram", name="P2 activity", id="p2-activity")
    model = ET.SubElement(diagram, "mxGraphModel", page="1", pageWidth=str(SIZE[0]),
                          pageHeight=str(SIZE[1]))
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    for i, (source, target, points, label, center) in enumerate(EDGES):
        draw.line(points, fill="#5F6D86", width=3)
        a, b = points[-2:]
        angle = math.atan2(b[1]-a[1], b[0]-a[0])
        arrow = [b, (b[0]-13*math.cos(angle-0.45), b[1]-13*math.sin(angle-0.45)),
                 (b[0]-13*math.cos(angle+0.45), b[1]-13*math.sin(angle+0.45))]
        draw.polygon(arrow, fill="#5F6D86")
        cell = ET.SubElement(root, "mxCell", id=f"edge{i}", parent="1", edge="1",
                             source=source, target=target,
                             style="endArrow=block;strokeColor=#5F6D86;strokeWidth=2;rounded=0;")
        geometry = ET.SubElement(cell, "mxGeometry", relative="1", attrib={"as": "geometry"})
        array = ET.SubElement(geometry, "Array", attrib={"as": "points"})
        for x, y in points:
            ET.SubElement(array, "mxPoint", x=str(x), y=str(y))
        if label:
            add_label(root, draw, f"label{i}", label, *center, 19)
    for identifier, label, x, y, w, h, kind in NODES:
        color = COLORS[kind]
        draw.rounded_rectangle((x,y,x+w,y+h), radius=14, fill=color, outline="#536480", width=2)
        draw.multiline_text((x+w/2,y+h/2), label, font=font(23), fill="#17263E", anchor="mm", align="center", spacing=8)
        cell = ET.SubElement(root, "mxCell", id=identifier, parent="1", vertex="1", value=label,
                             style=f"rounded=1;whiteSpace=wrap;fillColor={color};strokeColor=#536480;fontSize=23;")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), attrib={"as": "geometry"})
    for i, (x, y, text, size) in enumerate(NOTES):
        add_label(root, draw, f"note{i}", text, x, y, size)
    ET.indent(document)
    ET.ElementTree(document).write(ROOT / "docs/activity.drawio", encoding="utf-8", xml_declaration=True)
    canvas.save(ROOT / "docs/activity.png")


def add_label(root, draw, identifier, text, x, y, size):
    selected = font(size)
    box = draw.multiline_textbbox((x,y), text, font=selected, anchor="mm", align="center")
    draw.rectangle((box[0]-4,box[1]-3,box[2]+4,box[3]+3), fill="white")
    draw.multiline_text((x,y), text, font=selected, fill="#17263E", anchor="mm", align="center")
    cell = ET.SubElement(root, "mxCell", id=identifier, parent="1", vertex="1", value=text,
                         style=f"text;whiteSpace=wrap;fillColor=#FFFFFF;strokeColor=none;fontSize={size};")
    ET.SubElement(cell, "mxGeometry", x=str(box[0]-6), y=str(box[1]-6),
                  width=str(box[2]-box[0]+12), height=str(box[3]-box[1]+12), attrib={"as": "geometry"})


if __name__ == "__main__":
    render()
