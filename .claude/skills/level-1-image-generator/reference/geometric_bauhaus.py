"""
REFERENCE EXAMPLE - Bauhaus / Swiss geometric composition (1:1)
Prompt this stands in for: "generative geometric art, Bauhaus/Swiss composition
of arcs, circles and lines, bold palette".

Shows: flat color fields, pie slices / rings / arcs, knockout intersections,
a systematic dot grid, and restrained type. Run: python3 geometric_bauhaus.py
"""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from render import Design

random.seed(23)
d = Design("1:1")

CREAM = (240, 232, 210); RED = (221, 57, 44); BLUE = (37, 70, 148)
YEL = (243, 178, 42); INK = (26, 24, 28); TEAL = (42, 148, 138); GRIDC = (231, 222, 199)

d.fill(CREAM)
# faint construction grid
for i in range(1, 12):
    d.line(i / 12, 0, i / 12, 1, 0.0016, GRIDC)
    d.line(0, i / 12, 1, i / 12, 0.0016, GRIDC)

# A. big yellow quarter-circle bleeding from the top-right corner
d.pie(1.0, 0.0, 0.55, 90, 180, YEL)
d.ring(0.775, 0.285, 0.105, 5, INK)          # ring sitting on the yellow field
d.disk(0.605, 0.135, 0.070, RED)             # red dot on yellow

# B. concentric semicircle "sun" bleeding from the bottom-left
for r, c in [(0.32, INK), (0.26, YEL), (0.20, RED), (0.135, BLUE), (0.07, YEL)]:
    d.pie(0.15, 1.0, r, 180, 360, c)

# C. focal two-tone circle (red top / blue bottom)
fx, fy, fr = 0.335, 0.335, 0.135
d.pie(fx, fy, fr, 180, 360, RED)
d.pie(fx, fy, fr, 0, 180, BLUE)
d.line(fx, fy - fr, fx, fy + fr, 0.005, CREAM)   # thin split seam

# small triangle + square trio
d.polygon([(0.085, 0.24), (0.20, 0.24), (0.1425, 0.10)], INK)
d.rect(0.235, 0.135, 0.30, 0.20, TEAL)

# D. decisive rule + yellow semicircle sitting on it + structural lines
d.rect(0.06, 0.652, 0.60, 0.672, INK)
d.pie(0.235, 0.662, 0.085, 180, 360, YEL)
d.line(0.475, 0.05, 0.475, 0.95, 0.0032, INK)
d.rect(0.855, 0.135, 0.885, 0.47, RED)           # bold red vertical bar

# E. overlapping circles with an INK knockout lens
d.disk(0.63, 0.505, 0.115, BLUE)
d.disk(0.745, 0.565, 0.092, RED)
d.intersection(("disk", 0.63, 0.505, 0.115), ("disk", 0.745, 0.565, 0.092), INK)

# F. systematic dot grid (Swiss pulse)
for c in range(5):
    for row in range(5):
        col = BLUE if random.random() > 0.16 else RED
        d.disk(0.615 + c * 0.058, 0.735 + row * 0.058, 0.0145, col)

# G. small accent triad + a few scattered nodes
for i, col in enumerate([YEL, RED, BLUE]):
    d.disk(0.055 + i * 0.052, 0.55, 0.016, col)
for i, (nx, ny) in enumerate([(0.905, 0.63), (0.545, 0.15), (0.70, 0.205)]):
    d.disk(nx, ny, 0.012, TEAL if i % 2 == 0 else INK)

# caption (kept small, in clear space)
d.write(0.028, 0.04, "GEOMETRIC CADENCE", role="grotesque", weight="bold", size=20, color=INK)
d.write(0.028, 0.062, "No. 01  /  ARCS \u00B7 CIRCLES \u00B7 LINES", role="mono", size=15,
        color=(96, 90, 82))

d.save(os.path.join(os.path.dirname(__file__), "out_geometric.png"), grain=2, contrast=1.02)
print("wrote out_geometric.png")
