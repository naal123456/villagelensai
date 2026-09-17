# Focus, Urdu audio, and language reuse deployment — 2026-09-17

Status: deployed and publicly HTTP-validated; physical iPhone Safari camera and
audio confirmation pending.

## Field evidence

- A3-42, A3-43, and A3-44 were visually readable despite the camera frame not
  reliably becoming green. Their retained burst metrics had motion values of
  10.48, 10.43, and 14.33 respectively; all were below the earlier live-frame
  threshold for a clearly sharp target.
- A3-42 is a multilingual incense package. The Arabic-script phrase
  `سیندر وُوڈ` is Urdu for sandalwood. Production logs showed repeated HTTP 400
  responses from `/api/speech` while that source text was selected because the
  web client and server had no Arabic-script/Urdu speech mapping.
- A3-44 clearly shows the Malayalam words for Roja betel nut. Cloud OCR retained
  the Malayalam word for betel nut but omitted the stylized Roja word. The
  stronger reader recovered the product identity as Roja from the full image,
  but exact word-level OCR remains imperfect for that stylized lettering.
- The first English/Kannada switch for a capture with only one language result
  repeated the image analysis. Production request evidence showed stage-three
  calls of 49.74 seconds for A3-43 and 49.14 seconds for A3-44. Later switches
  were fast only because both language-specific results had then been stored.

## Repair

- A readable live frame now tolerates ordinary hand tremor up to a higher motion
  threshold, and the green state remains stable for 1.8 seconds. Darkness,
  glare, or a genuinely soft frame still immediately clears readiness. The
  camera remains manual and the four-frame burst still chooses the clearest
  saved frame.
- Arabic Unicode script is segmented independently and sent to an `ur-IN`
  Google Cloud voice. The interface identifies it conservatively as “Urdu /
  Arabic script,” because script alone cannot prove the language.
- A first output-language switch now preserves completed bar state in the
  same-tab handoff. If the requested target-language result is absent but the
  other language has a current result, the server preserves OCR evidence,
  image geometry, objects, boxes, confidence, and model analysis. It sends only
  the user-facing narrative fields through the text-only `gpt-5-mini`
  translation path, stores that derivative, and never submits the image to Luna,
  Terra, or Sol for that adaptation. A translation failure falls back to the
  existing image reader so the feature remains available.

## Verification

- Application version: `2026-09-17.1`
- Source commit: `ff83086`
- Cloud Build: `339c8312-ca91-4175-9ab6-cf8a719e1b0a`
- Container digest:
  `sha256:00c3b6c357aaca48f3a21dddc1e04096d0ce85c3359fd8702710536441548ca5`
- Cloud Run revision: `vlens-a-00075-mpm`, 100 percent traffic
- Controlled runtime retained: minimum zero instances, maximum one instance,
  concurrency eight
- Unit tests: `75/75` passed
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-17.1`, zero missing OCR models
- Authenticated A3 page: HTTP 200 with deployed Urdu segmentation, stabilized
  camera readiness, preserved-stage handoff, and matching visible version
- Exact A3-42 Urdu speech sample: HTTP 200, `audio/mpeg`, 13,056 bytes
- A3-44 stage-three Kannada-to-English adaptation: HTTP 200 in 7.83 seconds;
  metadata records `gpt-5-mini`, retains the completed Terra analysis, four
  object boxes, and validated quality
- A3-44 stage-two adaptation: HTTP 200 in 3.47 seconds and retains the completed
  Luna analysis
- Error-level logs after production validation: empty
- No field-test photograph was committed to Git; temporary diagnostic copies
  were deleted after inspection

## Physical-phone check

1. Open the camera and frame a clear package like A3-42 or A3-44. Confirm the
   box becomes green without requiring an unnaturally motionless hold.
2. Open A3-42 in word or sentence mode and touch the Urdu phrase. Confirm the
   source phrase is spoken and identified as Urdu / Arabic script.
3. Capture a new image, wait for bars two and three, then change English to
   Kannada or Kannada to English. Confirm the completed bars remain green and
   the translated meaning arrives in seconds rather than rerunning a roughly
   50-second visual analysis.
4. On A3-44, compare word mode with the third bar. The stronger reader should
   identify the packet as Roja, while the missing stylized Malayalam word box
   remains recorded as a stage-one OCR limitation rather than fabricated text.

## Rollback

Route traffic back to `vlens-a-00074-jmt`. That revision contains the overlay
and Safari handoff repair but lacks Urdu speech, stable green-focus hysteresis,
and text-only reuse of completed analysis across output languages.
