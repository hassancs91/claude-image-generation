"""Generate an image with Cloudflare Workers AI (Flux) and save it to disk.

Reads CF_ACCOUNT_ID and CF_API_TOKEN from the project's .env.

Usage:
    python generate.py "a cyberpunk cat coding at night"
    python generate.py "a serene mountain lake at sunrise" -o lake.jpg --steps 6
"""
import os
import sys
import base64
import argparse

import requests
from dotenv import load_dotenv, find_dotenv

# Walk up from the current working directory to find the project's .env.
load_dotenv(find_dotenv(usecwd=True))

MODEL = "@cf/black-forest-labs/flux-1-schnell"


def main():
    parser = argparse.ArgumentParser(
        description="Generate an image via Cloudflare Workers AI (Flux)."
    )
    parser.add_argument("prompt", help="Text description of the image to generate.")
    parser.add_argument(
        "-o", "--output", default="out.jpg", help="Output file path (default: out.jpg)."
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=4,
        help="Diffusion steps; flux-schnell is tuned for ~4 (default: 4).",
    )
    args = parser.parse_args()

    try:
        account_id = os.environ["CF_ACCOUNT_ID"]
        api_token = os.environ["CF_API_TOKEN"]
    except KeyError as missing:
        sys.exit(f"Missing {missing.args[0]} in environment — set it in .env (see .env.example).")

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{MODEL}"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_token}"},
        json={"prompt": args.prompt, "steps": args.steps},
    )

    data = resp.json()
    image_b64 = data.get("result", {}).get("image")
    if not image_b64:
        sys.exit(f"Cloudflare API error (HTTP {resp.status_code}): {data.get('errors') or data}")

    with open(args.output, "wb") as f:
        f.write(base64.b64decode(image_b64))

    print(f"Saved {args.output}  —  prompt: {args.prompt!r}  ({args.steps} steps)")


if __name__ == "__main__":
    main()
