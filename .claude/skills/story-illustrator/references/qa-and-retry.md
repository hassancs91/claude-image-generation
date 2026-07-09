# QA and Retry — Polishing Images with Corrective Deltas

The skill doesn't auto-QA every image during generation — that adds latency and cost without much benefit. Instead, the user reviews the images (or the QA table, if QA was requested) and flags ones that need polish. This file is how to retry productively.

## When the user flags an image

Examples:
- "Scene 8 — Pip looks gray instead of white"
- "Mia's glasses disappeared in scene 5"
- "Scene 3 has the rabbit twice"
- "The face in scene 6 looks scared, I wanted thoughtful"

Each needs translating into corrective deltas. The goal: regenerate ONLY what's broken while preserving what's right.

## Retry mechanism — single-turn only

**Do not use multi-turn chat for retries.** Multi-turn with multiple references hangs in production. Single-turn is reliable and equivalent quality.

1. Compose a corrective prompt with three parts:
   - The original scene prompt body (verbatim)
   - A **CORRECTIONS** section: exactly what's wrong and what it should be
   - A **KEEP UNCHANGED** section: what's right and must not change
2. Use the **previous attempt's image** as the primary reference, so the model treats it as "this is mostly right, fix these specific things" — not the character/location refs alone.
3. Call the backend with the same model and aspect ratio as the original.
4. Good result → replace the URL in `{slug}_images.json`. Still broken → iterate with new deltas based on the new image.

## Corrective prompt structure

```
[ORIGINAL PROMPT BODY — verbatim]

CORRECTIONS to apply:
1. <issue> — <specific physical/visual fix>
2. <issue> — <specific physical/visual fix>

KEEP UNCHANGED:
- <element that's correct>
- <composition / framing / lighting that's correct>

The ONLY changes are: <one-sentence summary>.
```

## Reference set for the retry

1. The previous attempt's image URL (what's being corrected)
2. Character refs for characters in the scene (identity anchor)
3. Location ref (setting anchor)

Drop the previous-*scene*-cascade ref for the retry — the previous version of THIS image is the right primary reference.

## Translating vague feedback into deltas

Vague feedback isn't actionable — describe the physical setup explicitly.

- **Vague:** "Scene 8 looks wrong" → look at the image, name what's specifically off, confirm with the user.
- **Vague:** "the expression isn't right" → "His face shows fear (wide eyes, open mouth). It should be calm and thoughtful — eyes soft and focused, a small closed-mouth smile, relaxed brow."
- **Specific:** "the bridge isn't connected to anything" → "The rope bridge must attach to the tree trunk on the left with a visible knot, and to the wooden post on the right. It spans the gap with both ends clearly anchored."

## Common issue categories

- **Identity drift** (character looks different) → re-anchor to the character ref: "Match Pip's reference exactly: a single soft white cloud body, tiny round eyes, small smiling mouth."
- **Prop continuity loss** (glasses/pendant missing or on the wrong character) → explicit assignment: "The round glasses belong ONLY to Mia. No other character wears glasses."
- **Color drift** (a white cloud rendered gray) → "Pip is bright soft white, not gray, not blue — clean white with gentle shading."
- **Physical incoherence** (things floating, setups that wouldn't work) → describe it like an engineer: "A is connected to B by the rope; if you removed B, A would fall."
- **Wrong/duplicate character** → explicit placement: "There is only ONE rabbit, sitting at the base of the tree. No second rabbit anywhere."
- **Lighting mismatch** → name source + quality: "Warm afternoon light from the upper left, soft, no harsh shadows."
- **Border / frame drift** (rendered as a matted page) → "Full-bleed illustration — the art reaches all four edges. No paper margin, no frame, no vignette."
- **Hallucinated text** → "No text, no letters, no signs, no writing anywhere in the image."

## Iterative refinement is normal

Fixing one thing sometimes breaks another (fix the pose → a duplicate appears; fix the duplicate → a prop moves). Budget 2–3 retries per problem image before deciding "good enough" or "model limitation."

## Stop criteria

- The user says it looks good.
- Three retries and the issue persists → flag it as a likely model limitation and move on.
- A retry introduced a worse problem → go back to the prior version and try a different corrective angle.

Don't loop indefinitely on one image. The user's time beats perfect pixels on one frame.
