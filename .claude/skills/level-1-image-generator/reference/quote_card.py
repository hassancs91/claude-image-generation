"""
REFERENCE EXAMPLE - Typographic quote card on a mesh gradient (9:16)
Prompt this stands in for: "typographic quote card, huge bold type over a mesh
gradient with subtle grain, premium story/reel cover".

Shows: mesh_gradient, vignette, huge fitted headline with a soft shadow, an
italic-serif accent word, a colored accent word, kicker + hairline + handle.
Run: python3 quote_card.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from render import Design

d = Design("9:16")                        # 1080 x 1920

CREAM = (245, 240, 230); MUTED = (214, 201, 226); GOLD = (245, 197, 96)
CHAR = (29, 29, 31); GRAY = (112, 112, 118); ACCENT = (111, 116, 230)

# --- rich jewel-tone mesh with a warm coral corner, deepened by a vignette ---
d.mesh_gradient([
    (0.12, 0.06, (34, 16, 74), 0.60), (0.90, 0.05, (98, 30, 152), 0.52),
    (0.74, 0.40, (196, 32, 132), 0.46), (0.14, 0.54, (40, 34, 122), 0.52),
    (0.93, 0.80, (236, 98, 54), 0.40), (0.33, 0.93, (58, 20, 96), 0.52),
    (0.60, 0.19, (30, 118, 166), 0.28), (0.99, 0.42, (150, 30, 128), 0.34),
])
d.vignette(0.42, center=(0.5, 0.46), radius=0.72)

LEFT = 0.088
SH = {"color": (14, 6, 26), "blur": 0.010 * d.W, "dy": 0.006 * d.H, "alpha": 0.55}

# --- kicker + hairline rule + slide number ---
d.write(LEFT, 0.118, "FIELD NOTES", role="grotesque", weight="bold", size=27,
        color=(228, 220, 232), tracking=6)
d.line(LEFT, 0.128, LEFT + 0.24, 0.128, 0.0016, (228, 220, 232))
d.write(LEFT + 0.255, 0.118, "01", role="mono", size=24, color=(228, 220, 232))

# --- huge headline; "quietly." in italic serif, "noise." in gold ---
S = d.fit_size("work make", 0.83, role="grotesque", weight="bold")
adv = S * 1.0 / d.H
y0 = 0.525 - 2 * adv                       # 5 lines centered on the 3rd
d.write(LEFT, y0 + 0 * adv, "Build", role="grotesque", weight="bold", size=S, color=CHAR, shadow=SH)
d.write(LEFT, y0 + 1 * adv, "quietly.", role="serif_book", italic=True, size=int(S * 1.16),
        color=MUTED, shadow=SH)
d.write(LEFT, y0 + 2 * adv, "Let the", role="grotesque", weight="bold", size=S, color=CHAR, shadow=SH)
d.write(LEFT, y0 + 3 * adv, "work make", role="grotesque", weight="bold", size=S, color=CHAR, shadow=SH)
w = d.write(LEFT, y0 + 4 * adv, "the ", role="grotesque", weight="bold", size=S, color=CHAR,
            shadow=SH, return_width=True)
d.write(LEFT + w, y0 + 4 * adv, "noise.", role="grotesque", weight="bold", size=S, color=GOLD, shadow=SH)

# --- handle ---
d.write(LEFT, 0.945, "@yourhandle", role="mono", size=26, color=(232, 224, 236), tracking=2)

d.save(os.path.join(os.path.dirname(__file__), "out_quote.png"),
       grain=6, chroma=2, saturation=1.14, contrast=1.04)
print("wrote out_quote.png")
