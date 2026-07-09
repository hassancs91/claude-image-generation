"""
Font registry for the prompt-to-design skill.

Fonts are addressed by ROLE (what job the type does in a composition), not by
file name. This lets the composition code stay readable ("give me a heavy
display face") and lets us swap the underlying font in one place.

All bundled fonts are SIL Open Font License; the matching *-OFL.txt files ship
in the fonts/ directory next to the .ttf files.
"""
from pathlib import Path
from PIL import ImageFont

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"

# role -> {weight_key: filename}
# weight_key is one of: regular, bold, medium, italic, bold_italic
REGISTRY = {
    # --- heavy display / poster faces (for HUGE hero words) ---
    "display":        {"regular": "BigShoulders-Regular.ttf", "bold": "BigShoulders-Bold.ttf"},   # tall condensed
    "display_chunky": {"regular": "EricaOne-Regular.ttf",     "bold": "EricaOne-Regular.ttf"},     # fat rounded
    "display_quirk":  {"regular": "Boldonse-Regular.ttf",     "bold": "Boldonse-Regular.ttf"},     # experimental

    # --- clean grotesque (Apple/Swiss neutral workhorse) ---
    "grotesque":      {"regular": "InstrumentSans-Regular.ttf", "bold": "InstrumentSans-Bold.ttf",
                       "italic": "InstrumentSans-Italic.ttf",   "bold_italic": "InstrumentSans-BoldItalic.ttf"},
    "grotesque_alt":  {"regular": "WorkSans-Regular.ttf", "bold": "WorkSans-Bold.ttf",
                       "italic": "WorkSans-Italic.ttf",   "bold_italic": "WorkSans-BoldItalic.ttf"},

    # --- geometric sans (friendly, modern, rounded) ---
    "geometric":      {"regular": "Outfit-Regular.ttf", "bold": "Outfit-Bold.ttf"},

    # --- serifs ---
    "serif":          {"regular": "Lora-Regular.ttf", "bold": "Lora-Bold.ttf",
                       "italic": "Lora-Italic.ttf",   "bold_italic": "Lora-BoldItalic.ttf"},   # readable book serif
    "serif_book":     {"regular": "CrimsonPro-Regular.ttf", "bold": "CrimsonPro-Bold.ttf",
                       "italic": "CrimsonPro-Italic.ttf"},                                       # elegant italic for accents
    "serif_display":  {"regular": "Gloock-Regular.ttf",   "bold": "Gloock-Regular.ttf"},         # high-contrast display serif
    "serif_chic":     {"regular": "YoungSerif-Regular.ttf","bold": "YoungSerif-Regular.ttf"},     # characterful slab-ish serif

    # --- monospace (technical labels, kickers, code vibe) ---
    "mono":           {"regular": "DMMono-Regular.ttf", "bold": "DMMono-Regular.ttf"},
    "mono_alt":       {"regular": "JetBrainsMono-Regular.ttf", "bold": "JetBrainsMono-Bold.ttf"},

    # --- techno / sci-fi (synthwave, futuristic) ---
    "techno":         {"regular": "Tektur-Regular.ttf", "medium": "Tektur-Medium.ttf", "bold": "Tektur-Medium.ttf"},

    # --- pixel / retro-arcade ---
    "pixel":          {"regular": "Silkscreen-Regular.ttf", "bold": "Silkscreen-Regular.ttf"},
    "pixel_alt":      {"regular": "PixelifySans-Medium.ttf", "bold": "PixelifySans-Medium.ttf"},
}

DEFAULT_ROLE = "grotesque"


def font_path(role=DEFAULT_ROLE, weight="regular", italic=False):
    """Resolve a role/weight/italic to an absolute .ttf path (with graceful fallbacks)."""
    fam = REGISTRY.get(role, REGISTRY[DEFAULT_ROLE])
    key = weight
    if italic:
        for cand in (f"{weight}_italic", "bold_italic" if weight == "bold" else "italic", "italic"):
            if cand in fam:
                key = cand
                break
    filename = fam.get(key) or fam.get("bold") or fam.get("regular") or next(iter(fam.values()))
    return str(FONT_DIR / filename)


def load_font(role=DEFAULT_ROLE, size=48, weight="regular", italic=False):
    """Return a PIL FreeType font for the given role. `size` is in pixels."""
    return ImageFont.truetype(font_path(role, weight, italic), int(round(size)))


def list_roles():
    return sorted(REGISTRY.keys())
