#!/usr/bin/env python3
"""
fal_image.py - generate ONE image with a Fal image model and save it locally.

This is the story-illustrator's image backend. It performs the single primitive
the skill needs:

    (prompt, reference image URLs, aspect ratio, model) -> an image

It submits to Fal's queue API, polls until the job is done, downloads the result
to a local file, and prints a one-line JSON result to stdout:

    {"url": "<fal cdn url>", "path": "<local file>", "model": "...", "cost_usd": 0.08}

The agent stores BOTH:
  - "path"  -> durable local copy; the publisher embeds this into the final HTML
              (Fal CDN URLs can age out; the local file never does).
  - "url"   -> the fresh Fal URL; reused as a reference for the next scene during
              the same run (the cascade that carries consistency forward).

Models, endpoints, prices, and aspect handling all come from image-models.json
(same folder). Add or switch models there - no code change needed - as long as the
model accepts reference images.

Auth: set FAL_KEY in the environment (or a .env file at the repo root).

Usage:
  python fal_image.py --model nano-banana-2 --aspect 4:5 \
      --prompt "..." \
      --ref https://.../pip.png --ref https://.../meadow.png \
      --out stories/the-little-cloud/the-little-cloud_images/part_03.png

  # preview the exact request without spending money / hitting the network:
  python fal_image.py --model nano-banana-pro --aspect 4:5 --prompt "..." \
      --ref https://... --out /tmp/x.png --dry-run

Stdlib only - no pip installs required.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(HERE, "image-models.json")
QUEUE_BASE = "https://queue.fal.run"
POLL_INTERVAL_S = 2.0
POLL_TIMEOUT_S = 240.0


# ---------- config / auth ----------

def load_registry(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_dotenv_key():
    """Best-effort: pull FAL_KEY out of a .env file if it isn't already in the env.
    Walks up from CWD looking for a .env (repo root). Keeps it dependency-free."""
    if os.environ.get("FAL_KEY"):
        return
    here = os.getcwd()
    for _ in range(5):
        env_path = os.path.join(here, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        if k.strip() == "FAL_KEY" and not os.environ.get("FAL_KEY"):
                            os.environ["FAL_KEY"] = v.strip().strip('"').strip("'")
            except OSError:
                pass
            return
        parent = os.path.dirname(here)
        if parent == here:
            return
        here = parent


def get_fal_key():
    load_dotenv_key()
    key = os.environ.get("FAL_KEY")
    if not key:
        sys.exit(
            "FAL_KEY is not set. Get a key at https://fal.ai/dashboard/keys and either:\n"
            "  - export FAL_KEY=...   (PowerShell: $env:FAL_KEY=\"...\")\n"
            "  - or put  FAL_KEY=...  in a .env file at the repo root."
        )
    return key


# ---------- aspect ratio ----------

def parse_aspect(aspect):
    try:
        w, h = aspect.lower().split(":")
        return int(w), int(h)
    except Exception:
        return None


def aspect_to_size(aspect, long_edge):
    """Map 'W:H' to an {width,height} dict for models that take image_size."""
    parsed = parse_aspect(aspect)
    if not parsed:
        return {"width": long_edge, "height": long_edge}
    rw, rh = parsed

    def r16(x):
        return max(512, min(4096, int(round(x / 16.0)) * 16))

    if rw >= rh:
        width, height = long_edge, long_edge * rh / rw
    else:
        width, height = long_edge * rw / rh, long_edge
    return {"width": r16(width), "height": r16(height)}


# ---------- request building ----------

def build_input(model_cfg, prompt, refs, aspect, seed, num_images):
    inp = {"prompt": prompt, "num_images": num_images}
    if refs:
        inp["image_urls"] = refs
    if seed is not None:
        inp["seed"] = seed

    aspect_param = model_cfg.get("aspect_param", "aspect_ratio")
    if aspect_param == "image_size":
        long_edge = int(model_cfg.get("image_size_long_edge", 2048))
        inp["image_size"] = aspect_to_size(aspect, long_edge)
    else:
        inp["aspect_ratio"] = aspect
        inp["output_format"] = model_cfg.get("output_format", "png")
        if model_cfg.get("resolution"):
            inp["resolution"] = model_cfg["resolution"]
    return inp


# ---------- HTTP ----------

def _request(url, key, method="GET", body=None):
    headers = {"Authorization": "Key " + key}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        hint = {
            401: "auth - check FAL_KEY",
            403: "auth/permission - check FAL_KEY and model access",
            422: "validation - a parameter is wrong for this model",
            429: "rate limited / out of credits",
        }.get(e.code, "")
        sys.exit("Fal HTTP %d (%s) on %s\n%s" % (e.code, hint, url, detail[:800]))
    except urllib.error.URLError as e:
        sys.exit("Network error talking to Fal: %s" % e)


def submit(endpoint, body, key):
    return _request(QUEUE_BASE + "/" + endpoint, key, method="POST", body=body)


def poll_until_done(status_url, response_url, key):
    deadline = time.time() + POLL_TIMEOUT_S
    while True:
        st = _request(status_url, key, method="GET")
        status = st.get("status")
        if status == "COMPLETED":
            return _request(response_url, key, method="GET")
        if st.get("error") or status in ("FAILED", "ERROR"):
            sys.exit("Fal job failed: %s" % json.dumps(st)[:800])
        if time.time() > deadline:
            sys.exit("Timed out after %ds waiting for Fal (last status: %s)" % (POLL_TIMEOUT_S, status))
        time.sleep(POLL_INTERVAL_S)


def download(url, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "ai-storybook/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(out_path, "wb") as f:
        f.write(r.read())


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Generate one image with a Fal model.")
    ap.add_argument("--model", help="model key from image-models.json (e.g. nano-banana-2)")
    ap.add_argument("--prompt", help="the image prompt")
    ap.add_argument("--out", help="local output path (e.g. stories/<slug>/<slug>_images/part_03.png)")
    ap.add_argument("--ref", action="append", default=[], dest="refs",
                    help="reference image URL; repeat for multiple (order: characters, location, previous scene)")
    ap.add_argument("--aspect", default="4:5", help="aspect ratio, e.g. 4:5 (default), 1:1, 3:4, 16:9")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--num-images", type=int, default=1)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--dry-run", action="store_true", help="print the request that WOULD be sent, then exit")
    ap.add_argument("--check", action="store_true",
                    help="report whether FAL_KEY is resolvable (no network, no spend), then exit")
    args = ap.parse_args()

    if args.check:
        load_dotenv_key()
        ok = bool(os.environ.get("FAL_KEY"))
        print(json.dumps({"fal_key": ok}))
        sys.exit(0 if ok else 1)

    missing = [n for n, v in (("--model", args.model), ("--prompt", args.prompt), ("--out", args.out)) if not v]
    if missing:
        sys.exit("Missing required argument(s): %s" % ", ".join(missing))

    registry = load_registry(args.registry)
    models = registry.get("models", {})
    if args.model not in models:
        sys.exit("Unknown model '%s'. Known: %s" % (args.model, ", ".join(sorted(models))))
    model_cfg = models[args.model]

    if args.refs and not model_cfg.get("supports_refs", False):
        sys.exit("Model '%s' does not accept reference images; it can't carry the cascade." % args.model)

    max_refs = model_cfg.get("max_refs")
    if max_refs and len(args.refs) > max_refs:
        sys.exit("Model '%s' accepts at most %d reference images, but %d were given. Reduce --ref "
                 "count (on a same-place SOFT cut, drop the standalone location ref — the previous-"
                 "scene ref already carries the location)." % (args.model, max_refs, len(args.refs)))

    # Pick the endpoint: with refs -> the image-to-image ("edit") endpoint;
    # without refs (reference plates) -> the text-to-image endpoint.
    endpoint = model_cfg.get("endpoint_edit") if args.refs else model_cfg.get("endpoint_text")
    if not endpoint:
        which = "endpoint_edit" if args.refs else "endpoint_text"
        sys.exit("Model '%s' has no '%s' in image-models.json." % (args.model, which))

    body = build_input(model_cfg, args.prompt, args.refs, args.aspect, args.seed, args.num_images)
    cost = model_cfg.get("cost_per_image_usd")

    if args.dry_run:
        print(json.dumps({"endpoint": endpoint, "input": body, "cost_usd": cost, "out": args.out}, indent=2))
        return

    key = get_fal_key()
    submitted = submit(endpoint, body, key)
    status_url = submitted.get("status_url")
    response_url = submitted.get("response_url")
    if not status_url or not response_url:
        sys.exit("Unexpected submit response: %s" % json.dumps(submitted)[:800])

    result = poll_until_done(status_url, response_url, key)
    images = result.get("images") or []
    if not images or not images[0].get("url"):
        sys.exit("No image in Fal result: %s" % json.dumps(result)[:800])

    url = images[0]["url"]
    download(url, args.out)
    print(json.dumps({
        "url": url,
        "path": args.out,
        "model": args.model,
        "cost_usd": cost,
    }))


if __name__ == "__main__":
    main()
