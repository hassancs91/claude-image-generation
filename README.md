# Claude × Image Generation — a Claude Skill demo

A tiny, end-to-end example of **connecting Claude to an image-generation API** using a [Claude Skill](https://docs.claude.com/en/docs/claude-code/skills). You describe an image in plain English; Claude turns your idea into a strong prompt, calls **Cloudflare Workers AI** (the `flux-1-schnell` model), and saves the picture to disk.

The point of the demo is the middle step — **Claude does the prompt engineering and orchestration**, not just a raw API call.

```
your idea  →  Claude writes an optimized prompt  →  Cloudflare Flux API  →  saved image
```

## What's in here

| File | Purpose |
|------|---------|
| [`img-cf.py`](img-cf.py) | The original bare-bones script — one hardcoded prompt, one API call. The "before". |
| [`.claude/skills/cf-image/`](.claude/skills/cf-image/) | The skill — the "after". |
| ├─ [`SKILL.md`](.claude/skills/cf-image/SKILL.md) | Tells Claude when to trigger and to write a good prompt first. |
| └─ [`generate.py`](.claude/skills/cf-image/generate.py) | CLI: reads keys from `.env`, takes a prompt + output path + steps. |
| [`.env.example`](.env.example) | Template for the API keys. Copy to `.env` and fill in. |

## Setup

1. **Install dependencies**

   ```bash
   pip install requests python-dotenv
   ```

2. **Get Cloudflare credentials** (free tier works)
   - **Account ID:** Cloudflare dashboard → *Workers & Pages* → *Overview* (right sidebar).
   - **API Token:** *My Profile* → *API Tokens* → *Create Token*, with **Workers AI** run permission.

3. **Add your keys**

   ```bash
   cp .env.example .env
   ```

   Then edit `.env`:

   ```
   CF_ACCOUNT_ID=your_cloudflare_account_id
   CF_API_TOKEN=your_cloudflare_api_token
   ```

   `.env` is gitignored — your keys never get committed.

## Use it

### Through Claude (the skill)

Open this folder in [Claude Code](https://docs.claude.com/en/docs/claude-code) and just ask:

- *"generate an image of a mountain lake at sunrise"*
- *"make me a thumbnail for a video about AI agents"*
- *"logo idea for a bakery"*

Claude picks up the `cf-image` skill, expands your request into a detailed Flux prompt, runs the script, and tells you the filename + the exact prompt it used so you can tweak and re-run.

### Directly (the script)

You can also run it yourself:

```bash
python .claude/skills/cf-image/generate.py "a cyberpunk cat coding at night" -o cat.jpg
```

Options: `-o/--output` (default `out.jpg`), `--steps` (default `4`; flux-schnell is tuned for few steps).

## How the skill works

A Claude Skill is just a folder with a `SKILL.md`. The YAML frontmatter's `description` is what Claude reads to decide **when** to use the skill; the markdown body tells it **how**. Here, the body's key instruction is *"write a strong prompt before calling the script"* — that's what makes Claude a useful layer on top of the raw API instead of a passthrough.

## Note on secrets

Keep real keys in `.env` only (never in code). If a token ever lands in a commit, rotate it in the Cloudflare dashboard — the value stays recoverable from git history otherwise.
