# Building the Self-Contained HTML

The publisher's job is mechanical: gather the pipeline artifacts, embed every image and audio file as a base64 **data URI**, inject them into the player template, and write one `.html` file that works offline.

A ready-to-run script does all of this: [`../assets/build_html.py`](../assets/build_html.py). The skill can run it directly, or do the same steps by hand.

## What it reads

From `stories/<slug>/`:
- `<slug>_scenes.json` — the text + metadata per scene (the spine)
- `<slug>_images.json` — `shots[].path` (the local image file; falls back to `shots[].url`) per scene index, from the illustrator
- `<slug>_audio/<slug>_part_NN.mp3` — one narration clip per scene, from the narrator
- `<slug>_audio/title.mp3` — optional title clip
- the player template at [`../assets/player-template.html`](../assets/player-template.html)

## What it writes

- `<slug>_story.json` — the consolidated story data, with media already embedded as data URIs (handy for re-builds / inspection)
- `<slug>.html` — the single self-contained storybook

## How pairing works

Everything pairs by **scene index**. `scenes[i].index == N` ⇒ image is `images.json.shots[]` where `index == N`, and audio is `<slug>_part_NN.mp3`. The script warns (but doesn't abort) if a scene is missing its image or audio, so you can still preview a partial build.

## Running it

```bash
# from the repo root
python .claude/skills/story-html-publisher/assets/build_html.py <slug>
```

Options:
- `--stories-dir PATH` — base stories dir (default `stories`)
- `--template PATH` — override the player template
- `--out PATH` — override the output path (default `stories/<slug>/<slug>.html`)

It uses the Python standard library only (no `pip install`). On Windows, use `python`; on macOS/Linux, `python3`.

## The data shape injected into the player

The template has two placeholders — `__STORY_TITLE__` and `__STORY_DATA__`. The script replaces `__STORY_DATA__` with JSON of this shape (media as data URIs):

```json
{
  "title": "The Little Cloud",
  "title_audio": "data:audio/mpeg;base64,...",
  "scenes": [
    {
      "index": 1,
      "text": "High in the sky lived a little cloud named Pip.",
      "scene": "wide blue sky",
      "mood": "gentle, bright",
      "image": "data:image/png;base64,...",
      "audio": "data:audio/mpeg;base64,..."
    }
  ]
}
```

The player reads this from `<script id="story-data" type="application/json">` and drives the whole experience — no network, no external files. From this single shape it synthesizes a **dedicated cover slide** (slide 0) at runtime — reusing `scenes[0].image` as a clean full illustration, `title` in the header, and `title_audio` as its narration — then renders each scene as its own page. So `title_audio` is what makes the cover non-silent; nothing else about the data shape changes.

## File-size note

Base64 inflates binary by ~33%. A 9-scene beginner story with ~400 KB images and ~80 KB audio per scene lands around **4–6 MB** of HTML — fine to open, email, or host. For much longer stories, or if size matters, two options:
1. **Compress upstream:** generate/convert images to WebP or compress the PNGs before embedding (smaller source → smaller HTML).
2. **Switch to an assets-folder layout:** instead of embedding, write images/audio next to the HTML and reference them with relative paths. The single-file build is the default because it's the most portable; the assets-folder variant trades portability for size. (This script does single-file; adapt `to_data_uri` to write files + return relative paths if you want the folder variant.)

## Doing it by hand (if you can't run the script)

The steps are simple enough to do inline with `Bash` + a tiny Python snippet:
1. For each scene, read the local image `path` (or `curl` the `url` if no local file) to bytes, base64-encode it, prefix with `data:image/png;base64,`.
2. Read each `<slug>_part_NN.mp3`, base64-encode, prefix with `data:audio/mpeg;base64,`.
3. Build the JSON above.
4. Read the template, string-replace `__STORY_TITLE__` and `__STORY_DATA__` (escape `</` → `<\/` in the JSON so a literal `</script>` can't close the tag early).
5. Write `<slug>.html`.

Running the script is strongly preferred — it handles mime sniffing, missing-asset warnings, and the `</script>` escaping for you.
