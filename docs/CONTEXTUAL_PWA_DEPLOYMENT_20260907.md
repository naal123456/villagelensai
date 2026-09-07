# Contextual inference and Android PWA deployment

Date: 2026-09-07
Status: deployed and publicly validated; physical Android install/share test pending

## Outcome

VillageLens now keeps the existing elapsed-time clock running until cloud
processing completes or fails. The fast OCR readers remain responsible for
word and line geometry. The third stage no longer generates duplicate boxes;
it concentrates on English-to-Kannada translations and contextual image
understanding.

The third-stage structured result now includes:

- visible objects and their likely purposes;
- what the image or document is and what it is used for;
- important details, any action needed, safety warnings, and uncertainty;
- a short spoken Kannada explanation for the meaning button; and
- a more detailed spoken Kannada explanation for the whole-page button.

Calendar guidance explicitly summarizes the month, year, highlighted date, and
notable events instead of mechanically reciting the date grid. Electrical,
motor, adapter, switch, and medicine guidance is constrained to visible or
strongly supported facts and does not provide wiring, repair, energizing, or
medication instructions. Plant, disease, and specialist identification remain
outside this version.

OpenAI stage three now uses `gpt-5.6-sol` with no extra reasoning effort, low
verbosity, image input, and a strict structured-output schema. The project key's
access to the model was checked without exposing the key. The change follows
the official model and Responses API documentation:

- https://developers.openai.com/api/docs/models/gpt-5.6-sol
- https://developers.openai.com/api/reference/cli/resources/responses/methods/create

The analysis schema is versioned as `context-v1`. Existing saved images with an
older mechanical result are upgraded once when revisited; the upgraded result
is then retained server-side and cached on the phone. Current results do not
repeat a model request during normal gallery navigation.

The `/a/` reader is now an installable Android progressive web app. It has an
app icon, standalone launch behavior, a Kannada installation button when Chrome
offers installation, and an Android Web Share Target for JPEG, PNG, and WebP
images. A tester cookie restores the assigned A1-A10 identity when the home
screen icon or share target opens `/a/`, so the tester does not need to type the
identifier again while the 30-day access cookie is valid. Shared images are
held briefly in private browser cache, consumed once, and then processed by the
normal capture path. The service worker does not cache gallery images, API
results, or other private application data.

The fourth bar remains gray. It is still reserved for later independent
provider consensus rather than ordinary completion.

## Performance qualification

Three controlled calls used the repository demo image; no tester photograph was
used and no raw provider response was retained.

- The initial Sol contract took 48.304 seconds and revealed that duplicate word
  geometry was consuming unnecessary work.
- Removing that geometry and using no extra reasoning reduced the local check
  to 31.130 seconds.
- The deployed public check completed in 29.689 seconds, identified four visible
  objects, returned brief and detailed Kannada, and passed output validation.

This is a substantial stage-three improvement, but it is not instant. Tesseract
and Google continue to provide earlier usable results while the clock shows that
contextual inference is still active. No premium service tier or additional
provider was enabled.

## Build and deployment

- Source commit: `65f64ae`
- Cloud Build: `c933d087-907d-4ae6-a1a7-533e3cdd1d89` (`SUCCESS`)
- Image digest:
  `sha256:61e7bb4079a31fb943091a0b3f55a40b667edf39ea55fd2ab12144bf43cf9c00`
- Cloud Run service: `vlens-a`, `us-central1`
- Cloud Run revision: `vlens-a-65f64ae`
- Traffic: 100 percent
- Limits preserved: minimum zero, maximum one, 1 CPU, 2 GiB, concurrency eight,
  and a 90-second request timeout
- Existing runtime service account and Secret Manager mappings were preserved.

Cloud Run created the revision without initially changing traffic. The traffic
assignment was checked and then explicitly moved to `vlens-a-65f64ae`.

## Validation

- Unit and contract tests: 33/33 passed.
- Python compilation, service-worker JavaScript syntax, embedded browser
  JavaScript syntax, and `git diff --check`: passed.
- Cloud Build container creation: passed.
- Public health endpoint: HTTP 200.
- Public A3 access-code login: HTTP 303.
- Public manifest: HTTP 200, standalone display and `/a/share-target` contract.
- Public service worker: HTTP 200 with the one-use shared-image contract.
- Public installed/share launch restored A3 from its server cookie and preserved
  the pending shared-image flag.
- Public stage-three request: HTTP 200, `gpt-5.6-sol`, `context-v1`, four objects,
  brief and detailed Kannada present, and `quality_validated: true`.
- No error-level Cloud Run log entry was present for revision `vlens-a-65f64ae`
  after the smoke tests.

This validates the deployed server, browser assets, model contract, and public
HTTP paths. It does not prove Android home-screen installation, Android share
sheet behavior, camera behavior, or audible Kannada on a physical tester phone;
those field checks remain required.

## Rollback

Route 100 percent of traffic to `vlens-a-551f922`. Stored captures remain
compatible. A rollback will continue to read older stage evidence; the new
`context-v1` files are additive and are not deleted.
