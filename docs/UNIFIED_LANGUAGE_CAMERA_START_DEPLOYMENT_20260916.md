# Unified language and camera-start deployment — 2026-09-16

Status: deployed and publicly HTTP-validated; physical-phone camera and audio
confirmation pending.

## Outcome

VillageLens now uses `/a/` as the single reader URL. The page has an
English/Kannada output toggle and remembers the choice on that phone. Existing
`/b/` links redirect to `/a/?lang=en`, so previously shared reviewer links keep
working without maintaining a second client.

The initial screen contains no photograph and requests no audio. A highlighted
instruction block speaks only after a user touches it. The saved-image gallery
loads in the background and no longer opens its first image when loading
finishes. This removes the delayed replacement of an active camera or welcome
screen that looked like a browser reload on slower connections.

The guided camera now asks the user to touch the wanted words or object. That
touch moves the visible crop box, requests camera focus at the touched point
when the browser exposes that control, and applies sharpness/stability analysis
and the four-frame clearest-image selection to the chosen area.

## Reload correction

The deployed page, service worker, and `/health` response now use the identical
version `2026-09-16.1`. The previous page displayed a dot-separated version
while `/health` reported a hyphen-separated value, so every foreground check
could incorrectly decide that the browser was stale. Service-worker activation
no longer independently reloads the page, and a health-discovered update is
deferred while camera, microphone, upload, or reader processing is active.

## Verification

- Source commit: `9dd52ff`
- Cloud Build: `888fbd1a-9741-4341-8342-aa3d41806501`
- Container digest:
  `sha256:8220e21db941f7c411aa7d3887828b729bd2b8e27c337a6d37d468228e20918a`
- Cloud Run revision: `vlens-a-00067-5zb`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight
- Unit tests: `68/68` passed
- Python compilation, embedded browser JavaScript parsing, and
  `git diff --check`: passed
- Public `/health`: HTTP 200, version `2026-09-16.1`, no missing OCR models
- Authenticated `/a/?tester=a3&lang=en`: HTTP 200 with no-store headers, the
  language toggle, silent welcome control, tap-target camera code, and matching
  version
- Legacy `/b/?tester=a3`: HTTP 302 to `/a/?tester=a3&lang=en`
- Error-level logs for the new revision after validation: empty
- No image or paid model call was submitted during deployment validation

## Field check

On iPhone Safari and Android Chrome, confirm that the welcome page stays visible
while the gallery loads, the yellow instruction block speaks only when touched,
and the language button changes all reading output. In the camera, tap a target,
confirm that the yellow box moves there, frame the wanted content, and take the
photo manually. Physical-phone validation is required before calling the camera
and audio interaction ready.

## Rollback

Route traffic back to `vlens-a-00066-vp8`. That revision is the prior
`2026-09-15.6` field build. It retains the former separate `/a/` and `/b/`
behavior and the delayed gallery-opening behavior.
