# `/c` Pi-camera server checkpoint — 2026-09-23

Status: implemented and locally tested on isolated branch
`codex/pi-camera-c`; not deployed and not physically validated.

## Outcome

The VillageLensAI server now has an isolated `/c/` lane for pairing one browser
session with one Raspberry Pi camera. `/a/` and `/b/` retain their existing
routing and phone-camera behavior. The shared reader page exposes its Pi Camera
control only when its path is `/c/`.

The local flow is:

1. An authenticated `/c/` browser creates an eight-hour, tester-bound camera
   session and receives a five-minute one-time pairing code.
2. The Pi exchanges that code over HTTPS for a random device credential. The
   credential is returned once, stored only as a SHA-256 hash on the server,
   and is never put in a URL, capture request, browser event, or log message.
   A paired browser keeps only the opaque session identifier in same-tab
   session storage so an ordinary refresh can reconnect without exposing the
   device credential.
3. Browser and Pi connect outbound to session-scoped WebSocket endpoints.
4. The browser may request a preview bounded to 30 seconds, 640×480, two JPEG
   frames per second, and 300,000 bytes per frame. Preview frames remain only in
   bounded process memory and are removed when preview stops or capture starts.
5. Capture creates a 45-second
   `villagelens.pi-capture-request.v1` bound to the paired device profile.
6. The Pi uploads one selected native still over authenticated HTTPS with its
   SHA-256 and bounded capture-response headers. The server verifies the bytes,
   device profile, job, expiry, four-frame selection, capture timestamp, and
   replay state before invoking the existing retained capture pipeline.
7. A successful upload returns
   `villagelens.pi-upload-acceptance.v1`, appears in the same tester gallery,
   and causes `/c/` to load that item and start the existing automatic reading
   stages. Stage four remains manual.

No OCR, inference, gallery, language, speech, or question implementation was
duplicated. The Pi source is labeled `pi-camera-v1`.

## Server surface

- `GET /c/`
- `POST /api/pi/v1/sessions`
- `GET /api/pi/v1/sessions/<session-id>`
- `DELETE /api/pi/v1/sessions/<session-id>`
- `POST /api/pi/v1/sessions/<session-id>/commands`
- `POST /api/pi/v1/device/pair`
- WebSocket `/api/pi/v1/browser/socket/<session-id>`
- WebSocket `/api/pi/v1/device/socket`
- `POST /api/pi/v1/device/captures/<request-id>`

Browser routes continue to require the existing access cookie. Session and
command calls additionally require the anonymous tester header and enforce
exact tester ownership. The device pairing endpoint accepts only a valid
high-entropy one-time code. Subsequent device traffic requires its bearer
credential; the WebSocket transmits it in the first encrypted message rather
than a URL. Deleting the browser session immediately invalidates its pairing
code and device credential.

## Safety and privacy

- Preview starts only after the user opens Pi Camera and is forcibly bounded.
- There is no background camera URL or indefinite recording command.
- `capture_active` and `capture_inactive` states are delivered to the browser.
- Preview frames are not written to Cloud Storage, Git, logs, or evidence.
- Still-image retention is unchanged from the existing VillageLensAI capture
  path and remains associated with the paired anonymous tester.
- The retained result includes `villagelens.pi-capture-provenance.v1` with the
  request, device profile, burst ID, original capture time, four-frame count,
  selected frame index, source byte count, and source SHA-256. Paths and raw
  camera/provider metadata are excluded.
- Repeated upload of the same request and source hash returns the same
  acceptance without repeating ingestion. A different source for an accepted
  request is rejected.
- No credentials, field photographs, participant identifiers, provider
  payloads, or paid-service configuration were added.

## Local verification

- Full suite: 90/90 tests passed (the original 76 plus 14 Pi bridge tests).
- Pi bridge coverage includes session isolation, pairing expiry and one-time use,
  device-bound capture requests, preview bounds/rate limiting, hash-bound
  idempotent upload, access gating, `/a` and `/b` route preservation, and
  browser/device WebSocket message routing and bounded source provenance.
- A local Gunicorn integration check completed a real browser WebSocket and Pi
  WebSocket handshake, routed `preview_start`, and delivered one synthetic JPEG
  preview to the correct browser session.
- Python compilation, embedded browser JavaScript parsing, dependency checking,
  and `git diff --check` passed.

## Known limits and next gates

- Session routing is intentionally in memory for the one-instance POC. A
  restart requires re-pairing. Multiple Cloud Run instances would require a
  separately authorized shared session service; none was enabled.
- WebSocket duration, reconnect behavior, concurrency, and Cloud Run request
  timeout have not been deployment-tested.
- The Pi-side WebSocket/preview/upload adapter is not yet implemented against
  this server contract. The Pi remains powered off.
- No real camera frame, private gallery item, provider request, public URL, or
  iPhone Safari session was used for this checkpoint.
- Physical end-to-end testing may begin only after the Pi client passes local
  fake-server tests and the received hardware profile is signed off.

## Rollback

Before deployment, discard or do not merge branch `codex/pi-camera-c`. After a
future merge, revert the checkpoint commit to remove `/c`, the Pi bridge module,
`flask-sock`, and the gated Pi controls. Existing `/a` and `/b` routes need no
data or configuration rollback because this change neither migrates storage nor
changes their URLs.
