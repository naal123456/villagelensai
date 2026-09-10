# Page capture and one-page teaching deployment — 2026-09-10

## Outcome

Version `v2026.09.10.2` makes green a readiness signal rather than an automatic
shutter. The user decides when to capture. A manual tap samples three preview
frames over 280 milliseconds, scores them locally for sharpness, motion,
darkness, glare, and likely page framing, and uploads only the best frame.

The live guide estimates likely neutral paper coverage. When likely paper runs
into a camera edge, it stays yellow and asks the user in Kannada and English to
move farther away. When the likely page is complete but occupies too little of
the frame, it asks the user to keep the whole page inside the box and move
closer. This is a conservative page heuristic, not semantic object recognition.

New textbook-page inference is instructed to use all readable text and pictures
to teach one page: identify its central topic, connect ideas, simplify difficult
Kannada terms, explain why the topic matters, and give a supported example. It
must report missing edges and must not invent cropped text. Existing cached
inference is preserved and is not regenerated merely by gallery navigation.

## Field-example calibration

Four recent A3 book photographs were inspected transiently and were not added
to the repository. The local heuristic classified the close views
`A3-B91D8B` and `A3-43D96F` as edge-cropped, and `A3-76C5F3` as still touching
an edge. The wider `A3-F20D46` preserved the page but left sufficient unused
surroundings to justify a move-closer suggestion.

A single non-retained live inference check on the complete example produced a
substantially more educational response: it identified a lesson about Hampi's
education system and rocky landscape, simplified the Kannada terms for food
donation and rocky hill, connected the photograph to the text, gave a supported
example, and retained low confidence due to small, tilted text. Provider latency
was 74.132 seconds. This confirms that the richer teaching pass should later
move behind the explicit lightbulb action and receive its own per-image cache;
it should not block immediate OCR.

## Verification

- Source commit: `eaf0e5c`
- Tests: `46/46` passed.
- Python compilation, index JavaScript parse, service-worker JavaScript parse,
  and `git diff --check`: passed.
- Cloud Build: `18c1d931-411e-4cb7-9917-b5af800424e1` succeeded.
- Container digest:
  `sha256:1bfb8f01633c06d72a6a07341820c851b580db8472718098e5388877f5c91749`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated public page contains version `v2026.09.10.2`, both page-framing
  checks, the three-frame selector, and no automatic shutter call.
- Calibration and API checks do not replace physical camera testing on the
  target Android phones and iPhone Safari.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00040-sfb`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00039-4rb`
