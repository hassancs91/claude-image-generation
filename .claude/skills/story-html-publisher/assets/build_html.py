#!/usr/bin/env python3
"""
build_html.py — assemble a self-contained storybook HTML from pipeline artifacts.

Reads the per-story artifacts in stories/<slug>/:
  - <slug>_scenes.json   (text + metadata per scene)        [from scene-splitter]
  - <slug>_images.json   (image URL/path per scene)         [from story-illustrator]
  - <slug>_audio/         <slug>_part_NN.mp3 (+ optional title.mp3, manifest.json)
                                                             [from story-narrator]

Downloads/reads every image and audio file, embeds them as base64 data URIs,
injects them into the player template, and writes:
  - <slug>_story.json    (the consolidated data, with data URIs)
  - <slug>.html          (the single self-contained storybook)

Usage:
  python build_html.py <slug> [--stories-dir PATH] [--template PATH] [--out PATH]

Stdlib only — no pip installs required.
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "player-template.html")


def sniff_image_mime(data: bytes, hint: str = "") -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    h = hint.lower()
    if h.endswith(".jpg") or h.endswith(".jpeg"):
        return "image/jpeg"
    if h.endswith(".webp"):
        return "image/webp"
    if h.endswith(".gif"):
        return "image/gif"
    return "image/png"


def fetch_bytes(src: str, base_dir: str) -> bytes:
    """src may be an http(s) URL or a local path. Local paths resolve as: absolute →
    as-is; otherwise try relative to CWD (repo-root-relative, e.g.
    'stories/<slug>/<slug>_images/part_01.png') then relative to base_dir (the
    working dir, e.g. '<slug>_images/part_01.png'). Both conventions work."""
    if src.startswith("http://") or src.startswith("https://"):
        req = urllib.request.Request(src, headers={"User-Agent": "ai-storybook/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    if os.path.isabs(src) or os.path.exists(src):
        path = src
    else:
        path = os.path.join(base_dir, src)
    with open(path, "rb") as f:
        return f.read()


def to_data_uri(data: bytes, mime: str) -> str:
    return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--stories-dir", default="stories")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    slug = args.slug
    work = os.path.join(args.stories_dir, slug)
    if not os.path.isdir(work):
        sys.exit("Working dir not found: %s" % work)

    scenes_path = os.path.join(work, "%s_scenes.json" % slug)
    images_path = os.path.join(work, "%s_images.json" % slug)
    audio_dir = os.path.join(work, "%s_audio" % slug)

    scenes_doc = load_json(scenes_path)
    images_doc = load_json(images_path)

    title = scenes_doc.get("story_title") or slug.replace("-", " ").title()
    scenes = scenes_doc["scenes"]

    # Map scene index -> image src. Prefer the durable local "path" (a stale Fal
    # CDN URL would break the build); fall back to "url" for older registries.
    img_by_index = {}
    for shot in images_doc.get("shots", []):
        img_by_index[int(shot["index"])] = shot.get("path") or shot.get("url")

    out_scenes = []
    for sc in scenes:
        i = int(sc["index"])
        entry = {
            "index": i,
            "text": sc.get("text", ""),
            "scene": sc.get("scene", ""),
            "mood": sc.get("mood", ""),
        }
        # image
        src = img_by_index.get(i)
        if not src:
            print("  ! WARNING: no image for scene %d" % i)
        else:
            raw = fetch_bytes(src, work)
            entry["image"] = to_data_uri(raw, sniff_image_mime(raw, src))
            print("  + scene %02d image  (%d KB)" % (i, len(raw) // 1024))
        # audio
        mp3 = os.path.join(audio_dir, "%s_part_%02d.mp3" % (slug, i))
        if os.path.exists(mp3):
            with open(mp3, "rb") as f:
                raw = f.read()
            entry["audio"] = to_data_uri(raw, "audio/mpeg")
            print("  + scene %02d audio  (%d KB)" % (i, len(raw) // 1024))
        else:
            print("  ! WARNING: no audio for scene %d (%s)" % (i, mp3))
        out_scenes.append(entry)

    story_data = {"title": title, "scenes": out_scenes}

    # Optional title clip
    title_mp3 = os.path.join(audio_dir, "title.mp3")
    if os.path.exists(title_mp3):
        with open(title_mp3, "rb") as f:
            raw = f.read()
        story_data["title_audio"] = to_data_uri(raw, "audio/mpeg")
        print("  + title audio     (%d KB)" % (len(raw) // 1024))

    # Persist the consolidated JSON (with data URIs) for re-use / inspection
    story_json_path = os.path.join(work, "%s_story.json" % slug)
    with open(story_json_path, "w", encoding="utf-8") as f:
        json.dump(story_data, f, ensure_ascii=False)

    # Inject into the template
    with open(args.template, "r", encoding="utf-8") as f:
        tpl = f.read()
    # json.dumps is safe to drop inside a <script type="application/json"> block,
    # but escape any "</" so a literal </script> in text can't close the tag early.
    data_json = json.dumps(story_data, ensure_ascii=False).replace("</", "<\\/")
    html = tpl.replace("__STORY_TITLE__", title).replace("__STORY_DATA__", data_json)

    out_path = args.out or os.path.join(work, "%s.html" % slug)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print("\nWrote %s (%.1f MB), %d scenes." % (out_path, size_mb, len(out_scenes)))
    print("Open it in any browser — it is fully self-contained.")


if __name__ == "__main__":
    main()
