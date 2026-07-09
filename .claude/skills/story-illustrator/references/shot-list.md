# Shot List — Continuity Rules and Prompt Schema

The shot list is where visual continuity is decided. Get the continuity class right and the cascade just works. Get it wrong and you'll see drift, duplicated objects, and broken state.

## Continuity classification — four cases

Every scene is classified as one of four types. The class determines which references go into the prompt.

### HARD CUT
A deliberate visual break: new location, different time, different scene entirely.

**Triggers:** the location differs from the previous scene; the time of day changes; the story has a transition marker ("the next morning", "later", "meanwhile"); or it's scene 1.

**References:** character refs (those present) + location ref + style descriptor. **No previous-scene ref** — it would fight the new setting.

### SOFT CUT
Same place, same time, next moment or different angle.

**Triggers:** same location and time as the previous scene; continuous action; a new moment within the same scene.

**References:** character refs + location ref + **previous scene image** + style descriptor.

The previous-scene image is what carries the cascade — clothes, hair, body position, mood, lighting, expression all transfer forward. This is the core mechanism that makes consistency work.

### MICRO CUT
Same moment as the previous scene, just a small action change (a turned head, a picked-up object). Rare in storybooks.

**References:** previous scene image is the **dominant** ref (listed first) + character refs as backup + style.

### STATE RESET
A modifier on SOFT cut: same place/time, BUT the character's physical state changed in a way the previous image would carry incorrectly.

**Triggers:** was wet, now dry (or vice versa); changed clothes; got dirty/hurt then clean/better; was holding something, now isn't, AND that change is the point.

**References:** character refs + location ref + style. **Drop the previous-scene ref** — it would carry the OLD state. The character ref provides the clean baseline; describe the new state in prose.

## Ref-set summary

| Continuity | Character refs | Location ref | Previous scene | Style |
|---|---|---|---|---|
| HARD CUT | yes | yes | NO | yes |
| SOFT CUT | yes | yes | YES | yes |
| MICRO CUT | yes | yes | yes (dominant) | yes |
| STATE RESET | yes | yes | NO | yes |

## Scene prompt schema

Style descriptor first (identical across all scenes), then the scene-specific body:

```
[STYLE DESCRIPTOR — exact same text every scene]

[FRAMING] — shot type, angle, composition (prose).
  "Wide establishing shot, slightly elevated angle." / "Close-up, eye-level."

[ACTION] — what's happening in this exact moment (prose).
  "Pip the little cloud drifts low over a green meadow, peeking down at a rabbit."

[STATE DELTAS] — only on SOFT/MICRO cuts where state carries.
  "Same as the moment before; Pip has only drifted a little lower."

[LIGHTING] — source, quality, direction.
  "Warm late-afternoon sunlight, soft and golden."

[EXCLUSIONS] — only when needed.
  "No other characters in this frame."

[no-text + no-border constraints — every prompt]
```

## Anti-redundancy rule

**Do NOT redescribe details that any reference image already carries.** The prompt should describe the moment, the action, framing/lighting, and state deltas — NOT character appearance (the character ref carries it), location features (the location ref carries it), or style (the descriptor carries it).

When you catch yourself writing "Pip, the small white fluffy cloud with a little smiling face, wearing…" — STOP. Just write "Pip" or "the little cloud." Identity comes from the reference image, not the prompt.

## Three exceptions — repeat these even though a ref carries them

Image models routinely drop these at scene scale:

1. **Fine character features on HARD CUTs.** Small accessories/details — glasses, a pendant, a freckle pattern, a always-carried toy — get lost when the only ref is the character ref. On every HARD CUT, repeat the bible's `Distinguishing` field in the prompt body: "Pip's tiny round eyes and small smiling mouth are clearly visible, matching the character reference."

2. **Anatomy-count clauses (non-standard anatomy).** If a character could be mis-duplicated (one tail, two-and-only-two ears, a single horn, no legs on a cloud), include an explicit count in EVERY scene of that character: "Pip is a single soft cloud body with no arms or legs — never split into two clouds." Cost: ~10 words. Cost of omitting: a regen.

3. **Scene-mismatch exclusions.** When the scene's environment differs from a reference's environment (a character ref shot against plain white, used in a forest scene; or a SOFT cascade carrying elements that don't belong), add explicit exclusions: "This is a forest scene — no white studio background, only trees and dappled light."

## Reference order in the API call

The model weights earlier references more. Use:
1. Character refs (identity anchors)
2. Location ref (setting anchor)
3. Previous scene ref (state cascade) — when applicable

For MICRO cuts, put the previous scene first. Don't exceed ~4–5 references in one call — a few well-chosen refs beat ten noisy ones.

## Shot list structure (markdown)

```markdown
# Shot List: <Story Title>
**Total scenes:** N
**Estimated cost:** $K

---

## Scene 1
- **Type:** wide establishing / medium / close-up
- **Angle:** eye-level / low / high
- **Continuity:** HARD CUT / SOFT CUT / MICRO CUT
- **State reset:** yes / no
- **Location:** <name from bible>
- **Time:** <from time variants>
- **Characters present:** <list>
- **Refs to use:** characters=[...], location=<name>, prev=<scene-N or none>
- **Action:** <prose, ≤2 sentences>
- **Lighting:** <prose, ≤1 sentence>
- **Notes:** <flags / special handling>

## Scene 2
...
```

## Sanity checks before generating

1. Does scene 1 establish the setting clearly (wide enough to ground the viewer)? Avoid opening on an extreme close-up.
2. Is there a wide shot at each location change to reorient?
3. Any scene with >4 named characters in frame? Plan the ref budget (drop minor characters from refs, describe inline).
4. Does the shot list span the full emotional arc — the climax AND the quiet aftermath both get a scene?
5. Any scene where state changes mid-action (gets wet, breaks something)? Mark STATE RESET so the cascade doesn't carry the wrong state.

Fix the shot list before generating if any check fails.

## Strong vs. weak scene prompts

**Weak** (redescribes everything, fights the references):
> A meadow scene. Pip is a little white cloud with a round smiling face. Below is a brown rabbit with long ears. The meadow has green grass and yellow flowers and a big oak tree. Pip is floating down to say hello to the rabbit.

**Strong** (only the moment + deltas, trusts the references):
> Medium shot, slightly low angle. Pip drifts low over the meadow, tilting toward a small rabbit who looks up in surprise. Same soft daylight as the last scene, the oak tree now at the right edge of the frame. Pip is a single soft cloud body — never two clouds.
