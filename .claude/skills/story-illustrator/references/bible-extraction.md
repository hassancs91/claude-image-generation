# Bible Extraction — Detailed Process

The bible is the single source of truth for character/location/style consistency. Get it right and the scenes are easy. Get it wrong and you'll fight drift the whole sequence.

## Two-pass approach

### Pass 1: Extract from the story text

Read the story carefully, then identify:

**Cast** — every character who speaks, takes a named action, or is described with any detail, AND who appears in more than one scene (or is the protagonist).

For each consistent character, draft an entry:
- **Name**
- **Age** — explicit if given, inferred reasonably otherwise
- **Build** — average / slim / sturdy / small-for-age / etc.
- **Skin tone**
- **Hair** — color, length, texture
- **Eyes** — color
- **Distinguishing features** — 3–5 max. Pick details that READ in an illustration: a specific clothing item, glasses, a recurring accessory, a particular hairstyle. Avoid abstract personality traits — the model can't render those.
- **Default expression** — calm / lively / curious. The resting face.
- **Clothing** — specific colors and pieces. This is critical for continuity. "A green shirt" is more identifiable than "casual clothes."
- **Consistent** — `true` for recurring cast, `false` for one-scene background characters.

If the story doesn't physically describe a character, **invent distinctive details** — don't leave fields blank. Generic descriptions yield generic outputs which drift between scenes. Choose specific colors, items, and traits, and commit. The user can override after Stage 2.

**Locations** — every place a scene might happen:
- **Type** — bedroom, meadow, kitchen, forest path, etc.
- **Time variants** — does the story span morning/night/seasons? List them.
- **Key features** — 3–7 elements that define the space visually. Be specific. "A bed" is forgettable; "a small bed under the window with a yellow star-patterned blanket and one round cushion" is identifiable.
- **Mood** — peaceful, lively, cozy, a little spooky-but-safe.

### Anchored body-state per location (non-standard anatomy)

For characters with non-standard anatomy — a living cloud, a talking animal walking upright, a fairy, a fish out of water — declare the character's **default body state at each location**: what's touching the ground/water/air, what's visible, how the body relates to its surroundings.

Without this, the illustrator fakes geometries that don't physically work (a cloud "standing" on grass like a person, a fish "sitting" at a table). One line per character per location is enough:

```markdown
### Pip (the little cloud)
- **Anchored body-state per location:**
  - In the sky: floating freely, soft puffy body, small face, no legs — drifting on the wind
  - Near the ground (low over the meadow): hovering just above the grass, casting a small soft shadow, NOT resting on the ground like a solid object
```

Rule of thumb: if a human character could stand or kneel where the scene happens, the non-standard character must be physically reachable / sensible from there.

**Recurring props** — objects mentioned more than once OR critical to a key moment. For each: description, when it appears, who carries it, and (only if visually critical and complex) whether it needs its own reference. Most props can be described in prose.

**Style sheet** — locked from Stage 1. Mirror the agreed style descriptor verbatim.

### Pass 2: Re-validate against the story

Read the story a second time, bible in hand, and check:
1. Does every named character map to a cast entry?
2. Does every scene transition / "they went to…" map to a known location?
3. Is every prop mentioned more than once listed?
4. Any character/location introduced casually that you missed (e.g. "the neighbor", "the old oak")?

For each miss, either **add to the bible** (if visually significant) or **mark inline-only** (appears once, not visually critical — described in the scene prompt where it appears, no reference needed). If Pass 2 surfaces more than 2–3 misses, the bible is too thin — go back through.

## Prop-state tracker (when a prop changes across scenes)

If a single key object visibly changes state — a balloon limp → inflated → popped; a cup empty → full → spilled; a seed → sprout → flower — enumerate its state per scene so the model doesn't default to the neutral version every time:

```markdown
### Prop-state tracker — the balloon
| Scene | State |
|---|---|
| 1–2 | A small limp red balloon, not yet blown up. |
| 3   | The balloon half-inflated. |
| 4–6 | The balloon fully round and bright red, floating on a string. |
| 7   | The balloon popped — a small red scrap on the ground. |
```

Skip this section only when nothing changes state.

## Characters-in-frame map (stories with ≥3 named characters)

Separate from the cast list. The cast says who EXISTS; this map says who must be VISIBLE in each scene's frame — a scene can be "Mia's reaction" while still showing her friends in the background.

```markdown
### Characters in frame — per scene
| Scene | In frame (must be visible) | Notes |
|---|---|---|
| 1 | Mia + Leo + the dog | Establishing wide. |
| 4 | Mia (close) | Solo reaction — just Mia's face. |
| 7 | Mia + Leo | Both at the picnic blanket. |
```

Paste the "In frame" cell directly into the scene prompt as an explicit roster.

## Validation summary at the end of bible.md

```markdown
## Validation
- All character mentions mapped: yes/no
- All location transitions mapped: yes/no
- All recurring props listed: yes/no
- Pass 2 misses: <count>
- Risk flags:
  - [LOW_EVIDENCE] <character>: appearance largely inferred
  - [TIME_INFERRED] story doesn't specify time of day; assumed daytime
```

These flags don't block — they tell the user what's confident vs. inferred.

## Good vs. weak entries

**Weak** (will drift):
> A boy. Brown hair. Casual clothes.

**Strong** (holds consistency):
> A 7-year-old boy with light brown skin and short curly black hair. He wears round glasses, a mustard-yellow t-shirt with a small rocket print, blue shorts, and red sneakers. His default expression is curious and a little shy.

The strong version has **specific colors, specific items, specific details**. Image models render specifics; they invent abstractions, and invent them differently every time. Same for locations:

**Weak:** A bedroom with a desk and a bed.
**Strong:** A small bedroom with a wooden desk under a round window, a blue desk lamp, a single bed against the wall with a yellow star-patterned blanket and one round white cushion, and a low shelf holding a toy train and three picture books.

Distinctive props in a location reference give the model anchors that recur across every scene using that location.
