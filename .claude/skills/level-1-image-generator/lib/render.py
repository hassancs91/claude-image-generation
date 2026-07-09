"""
render.py - the composition engine for the prompt-to-design skill.

Everything is built from code: gradients, mesh fields, glow, grain, shapes,
gradient/chrome type, soft spheres. The `Design` object is the main interface.

Design principles baked in:
  * Work at a supersampled resolution, then downsample with LANCZOS for crisp
    anti-aliased edges. Grain/scanlines are applied AFTER downsample so they
    read as real film grain (1:1 pixels), never blurred.
  * Coordinates are fractions of the final canvas: x in [0,1] across width,
    y in [0,1] down height. Sizes / radii / line widths / font sizes are given
    in FINAL pixels (what you'd see in the exported PNG); the engine scales
    them by the supersample factor internally.

Typical use:
    from render import Design, NEON
    d = Design("9:16")
    d.mesh_gradient([(0.2,0.1,(34,16,74),0.6), (0.8,0.8,(236,98,54),0.4)])
    d.vignette(0.4)
    d.disk(0.5, 0.4, 0.18, (255,90,150), glow={"color":(255,90,150)})
    d.write(0.5, 0.7, "HELLO", role="display", weight="bold", size=200, align="center")
    d.save("out.png", grain=6)
"""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

from fonts import load_font

# ----------------------------------------------------------------------------
# handy palette constants (feel free to ignore and pass your own colors)
# ----------------------------------------------------------------------------
NEON_MAGENTA = (255, 45, 150)
NEON_CYAN = (70, 220, 255)
NEON = NEON_MAGENTA
CREAM = (245, 240, 230)
INK = (26, 24, 28)
CHARCOAL = (29, 29, 31)

# ----------------------------------------------------------------------------
# aspect-ratio presets  ->  (width, height) in final pixels
# ----------------------------------------------------------------------------
ASPECT_PRESETS = {
    "1:1":  (1500, 1500),
    "4:5":  (1080, 1350),
    "5:4":  (1350, 1080),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "2:3":  (1200, 1800),
    "3:2":  (1800, 1200),
    "3:4":  (1200, 1600),
    "4:3":  (1600, 1200),
    "1:2":  (1080, 2160),
    "2:1":  (2160, 1080),
}
MAX_EDGE = 2560          # clamp for speed
MIN_EDGE = 400


def parse_size(spec):
    """Accept a preset key ('9:16'), a 'WxH' string ('1200x1500'), or a (w,h) tuple.
    Returns (width, height) clamped to a sane range."""
    if isinstance(spec, (tuple, list)) and len(spec) == 2:
        w, h = int(spec[0]), int(spec[1])
    elif isinstance(spec, str) and spec in ASPECT_PRESETS:
        w, h = ASPECT_PRESETS[spec]
    elif isinstance(spec, str) and ("x" in spec.lower()):
        a, b = spec.lower().split("x")
        w, h = int(float(a)), int(float(b))
    else:
        raise ValueError(f"Unknown size spec: {spec!r}. Use a preset {list(ASPECT_PRESETS)}, "
                         f"a 'WxH' string, or a (w,h) tuple.")
    # clamp longest edge
    scale = min(1.0, MAX_EDGE / max(w, h))
    w, h = int(round(w * scale)), int(round(h * scale))
    w, h = max(MIN_EDGE, w), max(MIN_EDGE, h)
    return w, h


def auto_supersample(w, h):
    """Pick a supersample factor that keeps the working canvas reasonable."""
    long_edge = max(w, h)
    if long_edge <= 1300:
        return 3
    if long_edge <= 2000:
        return 2
    return 2


def lerp_stops(t, stops):
    """Interpolate an array of positions t in [0,1] through color stops.
    stops = list of (pos, (r,g,b)). Returns array shaped (..., 3)."""
    t = np.asarray(t, dtype=np.float32)
    ts = np.array([s[0] for s in stops], dtype=np.float32)
    cs = np.array([s[1] for s in stops], dtype=np.float32)
    out = np.stack([np.interp(t, ts, cs[:, i]) for i in range(3)], axis=-1)
    return out


def _as_rgba(c, a=255):
    if len(c) == 4:
        return tuple(int(v) for v in c)
    return (int(c[0]), int(c[1]), int(c[2]), int(a))


# ============================================================================
class Design:
    def __init__(self, size="1:1", supersample=None, background=(255, 255, 255)):
        self.W, self.H = parse_size(size)
        self.ss = int(supersample or auto_supersample(self.W, self.H))
        self.Ws, self.Hs = self.W * self.ss, self.H * self.ss
        self.img = Image.new("RGBA", (self.Ws, self.Hs), _as_rgba(background))
        self._mesh = None  # cached coordinate grids

    # ---- coordinate helpers (fractions -> supersampled px) ----
    def X(self, fx):  # across width
        return fx * self.Ws

    def Y(self, fy):  # down height
        return fy * self.Hs

    def S(self, f):   # a length as a fraction of WIDTH
        return f * self.Ws

    def _px(self, size):  # final px -> supersampled px
        return int(round(size * self.ss))

    @property
    def draw(self):
        return ImageDraw.Draw(self.img)

    def _grids(self):
        if self._mesh is None:
            yy, xx = np.mgrid[0:self.Hs, 0:self.Ws].astype(np.float32)
            self._mesh = (xx, yy)
        return self._mesh

    # ---- numpy escape hatches (for custom effects beyond the built-ins) ----
    def coords(self):
        """Return (xx, yy) supersampled pixel-coordinate grids for numpy work."""
        return self._grids()

    def get_rgb(self):
        """Current canvas as a float32 (Hs, Ws, 3) array."""
        return np.asarray(self.img.convert("RGB"), np.float32)

    def set_rgb(self, arr):
        """Replace the whole canvas with an RGB array (use for full-frame effects)."""
        return self._set_bg_array(arr)

    def composite_rgba(self, rgba):
        """Alpha-composite a custom (Hs, Ws, 4) array over the current canvas."""
        self.img = Image.alpha_composite(
            self.img, Image.fromarray(np.clip(rgba, 0, 255).astype("uint8"), "RGBA"))
        return self

    # ---------------------------------------------------------------- BACKGROUNDS
    def fill(self, color):
        self.img.paste(_as_rgba(color), (0, 0, self.Ws, self.Hs))
        return self

    def _set_bg_array(self, arr):
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        rgba = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
        self.img = Image.fromarray(rgba, "RGBA")
        return self

    def linear_gradient(self, stops, angle=90):
        """angle in degrees: 90 = top->bottom (default), 0 = left->right."""
        xx, yy = self._grids()
        rad = math.radians(angle)
        # projection along the gradient direction, normalized to 0..1
        vx, vy = math.cos(rad), math.sin(rad)
        proj = (xx * vx + yy * vy)
        proj = (proj - proj.min()) / (np.ptp(proj) + 1e-6)
        return self._set_bg_array(lerp_stops(proj, stops))

    def radial_gradient(self, stops, center=(0.5, 0.5), radius=0.9):
        xx, yy = self._grids()
        cx, cy = self.X(center[0]), self.Y(center[1])
        r = self.S(radius)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (r + 1e-6)
        return self._set_bg_array(lerp_stops(np.clip(d, 0, 1), stops))

    def mesh_gradient(self, points, gamma=1.0):
        """Smooth 'mesh gradient': Gaussian-weighted blend of colored control points.
        points = list of (fx, fy, (r,g,b), sigma_fraction_of_width)."""
        xx, yy = self._grids()
        acc = np.zeros((self.Hs, self.Ws, 3), np.float32)
        wsum = np.full((self.Hs, self.Ws), 1e-6, np.float32)
        for fx, fy, col, sig in points:
            px, py, s = self.X(fx), self.Y(fy), self.S(sig)
            w = np.exp(-(((xx - px) ** 2 + (yy - py) ** 2) / (2.0 * s * s))).astype(np.float32)
            acc += w[..., None] * np.array(col, np.float32)
            wsum += w
        mesh = acc / wsum[..., None]
        if gamma != 1.0:
            mesh = 255.0 * (np.clip(mesh / 255.0, 0, 1) ** gamma)
        return self._set_bg_array(mesh)

    def overlay_glow(self, center, color, radius, strength=0.4, mode="screen"):
        """Add a soft radial glow onto the current canvas (great behind a subject)."""
        xx, yy = self._grids()
        cx, cy = self.X(center[0]), self.Y(center[1])
        r = self.S(radius)
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * r * r))).astype(np.float32) * strength
        base = np.asarray(self.img.convert("RGB"), np.float32)
        col = np.array(color, np.float32)
        if mode == "add":
            out = base + g[..., None] * col
        elif mode == "blend":
            out = base * (1 - g[..., None]) + col * g[..., None]
        else:  # screen
            out = 255.0 - (255.0 - base) * (255.0 - g[..., None] * col) / 255.0
        return self._set_bg_array(out)

    def vignette(self, strength=0.4, center=(0.5, 0.5), radius=0.75, power=1.6):
        xx, yy = self._grids()
        cx, cy = self.X(center[0]), self.Y(center[1])
        # normalize by the smaller half-extent so it reads round-ish on any ratio
        nx = (xx - cx) / (self.Ws * radius)
        ny = (yy - cy) / (self.Hs * radius)
        r = np.sqrt(nx * nx + ny * ny)
        v = 1.0 - strength * np.clip(r, 0, 1) ** power
        base = np.asarray(self.img.convert("RGB"), np.float32) * v[..., None]
        return self._set_bg_array(base)

    # ---------------------------------------------------------------- GLOW HELPER
    def _glow_stack(self, draw_fn, color, size_hint):
        """Render a shape via draw_fn onto a transparent layer several times with
        increasing blur to build a neon glow. Returns an RGBA layer."""
        layer = Image.new("RGBA", (self.Ws, self.Hs), (0, 0, 0, 0))
        passes = [(0.55, 0.5), (0.24, 0.8), (0.09, 1.0)]  # (blur frac of size_hint, alpha)
        for bf, alpha in passes:
            g = Image.new("RGBA", (self.Ws, self.Hs), (0, 0, 0, 0))
            draw_fn(ImageDraw.Draw(g), _as_rgba(color))
            blur = max(1.0, bf * size_hint)
            g = g.filter(ImageFilter.GaussianBlur(blur))
            if alpha < 1:
                a = g.split()[3].point(lambda v: int(v * alpha))
                g.putalpha(a)
            layer = Image.alpha_composite(layer, g)
        return layer

    def _paint(self, draw_fn, color, glow=None):
        """Draw a shape (optionally with a neon glow underneath)."""
        if glow:
            gc = glow.get("color", color) if isinstance(glow, dict) else glow
            hint = glow.get("size", 0.12 * self.Ws) if isinstance(glow, dict) else 0.12 * self.Ws
            self.img = Image.alpha_composite(self.img, self._glow_stack(draw_fn, gc, hint))
        d = ImageDraw.Draw(self.img)
        draw_fn(d, _as_rgba(color))
        return self

    # ---------------------------------------------------------------- SHAPES
    def _bbox(self, cx, cy, r):
        return [self.X(cx) - self.S(r), self.Y(cy) - self.S(r),
                self.X(cx) + self.S(r), self.Y(cy) + self.S(r)]

    def disk(self, cx, cy, r, color, glow=None):
        return self._paint(lambda d, c: d.ellipse(self._bbox(cx, cy, r), fill=c), color, glow)

    def ellipse(self, cx, cy, rx, ry, color, glow=None):
        box = [self.X(cx) - self.S(rx), self.Y(cy) - self.S(ry),
               self.X(cx) + self.S(rx), self.Y(cy) + self.S(ry)]
        return self._paint(lambda d, c: d.ellipse(box, fill=c), color, glow)

    def ring(self, cx, cy, r, width, color, glow=None):
        w = self._px(width)
        return self._paint(lambda d, c: d.ellipse(self._bbox(cx, cy, r), outline=c, width=w), color, glow)

    def pie(self, cx, cy, r, a0, a1, color, glow=None):
        return self._paint(lambda d, c: d.pieslice(self._bbox(cx, cy, r), a0, a1, fill=c), color, glow)

    def arc(self, cx, cy, r, a0, a1, width, color, glow=None):
        w = self._px(width)
        return self._paint(lambda d, c: d.arc(self._bbox(cx, cy, r), a0, a1, fill=c, width=w), color, glow)

    def rect(self, x0, y0, x1, y1, color, radius=0.0, glow=None):
        box = [self.X(x0), self.Y(y0), self.X(x1), self.Y(y1)]
        rad = self.S(radius)
        if rad > 0:
            return self._paint(lambda d, c: d.rounded_rectangle(box, radius=rad, fill=c), color, glow)
        return self._paint(lambda d, c: d.rectangle(box, fill=c), color, glow)

    def line(self, x0, y0, x1, y1, width, color, glow=None):
        w = self._px(width)
        pts = [self.X(x0), self.Y(y0), self.X(x1), self.Y(y1)]
        return self._paint(lambda d, c: d.line(pts, fill=c, width=w), color, glow)

    def polygon(self, points, color, glow=None):
        pts = [(self.X(px), self.Y(py)) for px, py in points]
        return self._paint(lambda d, c: d.polygon(pts, fill=c), color, glow)

    # ---- knockout: fill the intersection of two shapes with a third color ----
    def _shape_mask(self, shape):
        m = Image.new("L", (self.Ws, self.Hs), 0)
        d = ImageDraw.Draw(m)
        kind = shape[0]
        if kind == "disk":
            _, cx, cy, r = shape
            d.ellipse(self._bbox(cx, cy, r), fill=255)
        elif kind == "pie":
            _, cx, cy, r, a0, a1 = shape
            d.pieslice(self._bbox(cx, cy, r), a0, a1, fill=255)
        elif kind == "rect":
            _, x0, y0, x1, y1 = shape
            d.rectangle([self.X(x0), self.Y(y0), self.X(x1), self.Y(y1)], fill=255)
        else:
            raise ValueError(f"intersection supports disk/pie/rect, got {kind!r}")
        return m

    def intersection(self, shape_a, shape_b, color):
        """Fill the overlap of two shapes. Shapes are tuples:
        ('disk',cx,cy,r) | ('pie',cx,cy,r,a0,a1) | ('rect',x0,y0,x1,y1)."""
        from PIL import ImageChops
        inter = ImageChops.multiply(self._shape_mask(shape_a), self._shape_mask(shape_b))
        self.img.paste(_as_rgba(color), (0, 0), inter)
        return self

    # ---------------------------------------------------------------- SOFT SPHERE
    def gradient_sphere(self, cx, cy, r, colors, light=(-0.34, -0.34),
                        shadow=True, shadow_alpha=0.4, shadow_color=(74, 78, 100),
                        specular=0.16, rim=0.05, glow=None, glow_strength=0.35):
        """A soft, dimensional 'product' orb. `colors` = 2-3 stops blended along a
        diagonal; volume shading lights it from the `light` direction (fractions of r)."""
        xx, yy = self._grids()
        ox, oy, R = self.X(cx), self.Y(cy), self.S(r)
        dx, dy = xx - ox, yy - oy
        dist = np.sqrt(dx * dx + dy * dy)

        if glow:
            self.overlay_glow((cx, cy), glow if not isinstance(glow, dict) else glow.get("color", colors[-1]),
                              radius=r * 2.2, strength=glow_strength, mode="screen")

        if shadow:
            sh = Image.new("L", (self.Ws, self.Hs), 0)
            ImageDraw.Draw(sh).ellipse([ox - 1.35 * R, oy + 0.66 * R, ox + 1.35 * R, oy + 1.16 * R],
                                       fill=int(255 * shadow_alpha))
            sh = sh.filter(ImageFilter.GaussianBlur(0.085 * R))
            s_rgba = Image.new("RGBA", (self.Ws, self.Hs), _as_rgba(shadow_color, 0))
            s_rgba.putalpha(sh)
            self.img = Image.alpha_composite(self.img, s_rgba)

        # diagonal color blend
        stops = colors if isinstance(colors[0], (tuple, list)) else [colors]
        n = len(stops)
        cstops = [(i / (n - 1) if n > 1 else 0.0, stops[i]) for i in range(n)]
        proj = (dx + dy)
        t = np.clip(0.5 + proj / (2 * R * math.sqrt(2)), 0, 1)
        orb = lerp_stops(t, cstops)

        # volume shading + specular from the light point
        lx, ly = ox + light[0] * R, oy + light[1] * R
        dl2 = (xx - lx) ** 2 + (yy - ly) ** 2
        shade = 1.05 - 0.20 * np.clip(dl2 / (R * R), 0, 1.6)
        orb = orb * shade[..., None]
        if specular:
            spec = specular * np.exp(-dl2 / (2 * (0.30 * R) ** 2))
            orb = orb + spec[..., None] * 255.0
        if rim:
            rr = np.clip((dist - 0.86 * R) / (0.14 * R), 0, 1)
            orb = orb * (1 - rim * rr)[..., None]

        orb = np.clip(orb, 0, 255)
        alpha = np.clip((R - dist) / max(1.0, 0.9 * self.ss), 0, 1) * 255.0
        orb_rgba = np.dstack([orb, alpha]).astype(np.uint8)
        self.img = Image.alpha_composite(self.img, Image.fromarray(orb_rgba, "RGBA"))
        return self

    # ---------------------------------------------------------------- TEXT
    def measure(self, text, role="grotesque", weight="regular", size=48, italic=False, tracking=0.0):
        """Return the (width, height) a single line would occupy, in FINAL px."""
        fnt = load_font(role, self._px(size), weight, italic)
        d = ImageDraw.Draw(Image.new("L", (4, 4)))
        widths = [d.textlength(c, font=fnt) for c in text]
        total = sum(widths) + self.S(0) + tracking * self.ss * max(0, len(text) - 1)
        asc, desc = fnt.getmetrics()
        return total / self.ss, (asc + desc) / self.ss

    def fit_size(self, text, target_frac, role="grotesque", weight="bold", italic=False,
                 lo=8, hi=600, tracking=0.0):
        """Largest FINAL-px size so `text` fits within target_frac of the width."""
        target = self.S(target_frac)
        lo_i, hi_i = lo, hi
        while lo_i < hi_i:
            mid = (lo_i + hi_i + 1) // 2
            fnt = load_font(role, self._px(mid), weight, italic)
            d = ImageDraw.Draw(Image.new("L", (4, 4)))
            w = sum(d.textlength(c, font=fnt) for c in text) + tracking * self.ss * max(0, len(text) - 1)
            if w <= target:
                lo_i = mid
            else:
                hi_i = mid - 1
        return lo_i

    def wrap(self, text, max_frac, role="grotesque", weight="regular", size=48, italic=False):
        """Greedy word-wrap into lines that fit max_frac of the width. Returns [str]."""
        fnt = load_font(role, self._px(size), weight, italic)
        d = ImageDraw.Draw(Image.new("L", (4, 4)))
        limit = self.S(max_frac)
        lines, cur = [], ""
        for word in text.split():
            test = (cur + " " + word).strip()
            if d.textlength(test, font=fnt) <= limit or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def _default_glow(self, spec, size):
        """Normalize a glow spec into passes of (blur_px_ss, alpha)."""
        if not spec:
            return None
        color = spec.get("color") if isinstance(spec, dict) else spec
        base = self._px(size)
        passes = [(0.30 * base, 0.55), (0.13 * base, 0.85), (0.055 * base, 1.0)]
        if isinstance(spec, dict) and "passes" in spec:
            passes = [(self._px(b), a) for b, a in spec["passes"]]
        return {"color": color, "passes": passes}

    def write(self, x, y, text, role="grotesque", weight="regular", italic=False, size=48,
              color=(255, 255, 255), gradient=None, align="left", tracking=0.0,
              glow=None, shadow=None, stroke=0, stroke_color=None, return_width=False):
        """Draw ONE line of text.
        x,y are fractions; y is the BASELINE by default.
        align: 'left' (x=left edge) | 'center' (x=center) | 'right' (x=right edge).
        gradient: list of (pos,(r,g,b)) fills the glyphs with a vertical gradient (chrome).
        glow: (r,g,b) or {'color':..,'passes':[(blur_px,alpha),..]} for neon bloom.
        shadow: True or {'color':..,'blur':px,'dx':px,'dy':px,'alpha':0..1}.
        stroke: outline width in final px."""
        px = self._px(size)
        fnt = load_font(role, px, weight, italic)
        trk = tracking * self.ss
        stroke_px = self._px(stroke)
        d0 = ImageDraw.Draw(Image.new("L", (4, 4)))
        widths = [d0.textlength(c, font=fnt) for c in text]
        total = sum(widths) + trk * max(0, len(text) - 1)
        asc, desc = fnt.getmetrics()

        glow = self._default_glow(glow, size)
        pad = int(0.6 * (asc + desc)) + stroke_px * 2 + 10
        if glow:
            pad += int(max(b for b, _ in glow["passes"]) * 2)
        if shadow:
            sb = shadow.get("blur", 0.10 * px) * self.ss if isinstance(shadow, dict) else 0.10 * px
            pad += int(sb * 2 + 0.12 * px)

        Wt = int(total) + 2 * pad
        Ht = int(asc + desc) + 2 * pad
        ox, baseY = pad, pad + asc

        def render_chars(col, dx=0, dy=0, sw=0, sc=None):
            im = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            xx = ox + dx
            for c, w in zip(text, widths):
                if sw:
                    dr.text((xx, baseY + dy), c, font=fnt, fill=col, anchor="ls",
                            stroke_width=sw, stroke_fill=sc or col)
                else:
                    dr.text((xx, baseY + dy), c, font=fnt, fill=col, anchor="ls")
                xx += w + trk
            return im

        layer = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))

        # shadow
        if shadow:
            sc_col = shadow.get("color", (0, 0, 0)) if isinstance(shadow, dict) else (0, 0, 0)
            sdx = (shadow.get("dx", 0) if isinstance(shadow, dict) else 0) * self.ss
            sdy = (shadow.get("dy", 0.05 * size) if isinstance(shadow, dict) else 0.05 * size) * self.ss
            sblur = (shadow.get("blur", 0.09 * size) if isinstance(shadow, dict) else 0.09 * size) * self.ss
            salpha = shadow.get("alpha", 0.5) if isinstance(shadow, dict) else 0.5
            sh = render_chars(_as_rgba(sc_col), dx=sdx, dy=sdy).filter(ImageFilter.GaussianBlur(max(1, sblur)))
            a = sh.split()[3].point(lambda v: int(v * salpha))
            sh.putalpha(a)
            layer = Image.alpha_composite(layer, sh)

        # glow
        if glow:
            for blur, alpha in glow["passes"]:
                g = render_chars(_as_rgba(glow["color"])).filter(ImageFilter.GaussianBlur(max(1, blur)))
                if alpha < 1:
                    a = g.split()[3].point(lambda v: int(v * alpha))
                    g.putalpha(a)
                layer = Image.alpha_composite(layer, g)

        # outline (stroke) drawn as a solid halo when using a gradient fill
        if stroke_px and gradient:
            layer = Image.alpha_composite(layer, render_chars(_as_rgba(stroke_color or INK), sw=stroke_px,
                                                              sc=stroke_color or INK))

        # main fill
        if gradient:
            mask = Image.new("L", (Wt, Ht), 0)
            dm = ImageDraw.Draw(mask)
            xx = ox
            for c, w in zip(text, widths):
                dm.text((xx, baseY), c, font=fnt, fill=255, anchor="ls")
                xx += w + trk
            top = baseY - asc
            h = asc + desc
            grad = lerp_stops(np.linspace(0, 1, h), gradient)
            gimg = np.zeros((Ht, Wt, 3), np.float32)
            gimg[top:top + h, :, :] = grad[:, None, :]
            gi = Image.fromarray(np.clip(gimg, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
            stamp = Image.new("RGBA", (Wt, Ht), (0, 0, 0, 0))
            stamp.paste(gi, (0, 0), mask)
            layer = Image.alpha_composite(layer, stamp)
        else:
            sw = stroke_px if stroke_px else 0
            layer = Image.alpha_composite(layer, render_chars(_as_rgba(color), sw=sw, sc=stroke_color))

        # place: baseline at Y(y); x edge per align
        Xpx = self.X(x)
        if align == "center":
            left = Xpx - total / 2.0
        elif align == "right":
            left = Xpx - total
        else:
            left = Xpx
        self.img.alpha_composite(layer, (int(round(left - ox)), int(round(self.Y(y) - baseY))))
        if return_width:
            return total / self.ss
        return self

    def text_block(self, x, y, text, role="grotesque", weight="regular", size=48, italic=False,
                   color=(255, 255, 255), align="left", max_frac=0.84, line_height=1.16,
                   gradient=None, glow=None, shadow=None, tracking=0.0):
        """Word-wrap `text` and draw it as stacked lines. y is the baseline of the
        FIRST line. Returns the baseline y (fraction) just past the last line."""
        lines = self.wrap(text, max_frac, role, weight, size, italic) if "\n" not in text \
            else text.split("\n")
        adv = (size * line_height) / self.H  # advance as fraction of height
        for i, ln in enumerate(lines):
            self.write(x, y + i * adv, ln, role=role, weight=weight, italic=italic, size=size,
                       color=color, gradient=gradient, align=align, tracking=tracking,
                       glow=glow, shadow=shadow)
        return y + len(lines) * adv

    # ---------------------------------------------------------------- FINISH
    def render(self, grain=0, chroma=0, scanlines=0, saturation=1.0, contrast=1.0, brightness=1.0):
        """Downsample to final resolution and apply post effects (which belong at 1:1)."""
        out = self.img.convert("RGB").resize((self.W, self.H), Image.LANCZOS)
        if scanlines:
            arr = np.asarray(out).astype(np.float32)
            mult = np.ones((self.H, 1, 1), np.float32)
            mult[::3, 0, 0] = 1.0 - scanlines
            arr *= mult
            out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        if grain or chroma:
            arr = np.asarray(out).astype(np.float32)
            if grain:
                arr += np.random.normal(0, grain, (self.H, self.W, 1)).astype(np.float32)
            if chroma:
                arr += np.random.normal(0, chroma, (self.H, self.W, 3)).astype(np.float32)
            out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        if saturation != 1.0:
            out = ImageEnhance.Color(out).enhance(saturation)
        if contrast != 1.0:
            out = ImageEnhance.Contrast(out).enhance(contrast)
        if brightness != 1.0:
            out = ImageEnhance.Brightness(out).enhance(brightness)
        return out

    def save(self, path, **post):
        img = self.render(**post)
        img.save(path)
        return path
