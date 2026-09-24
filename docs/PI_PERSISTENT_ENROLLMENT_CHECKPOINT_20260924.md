# Pi persistent enrollment checkpoint — 2026-09-24

## Status

Implemented and tested on isolated branch `codex/pi-persistent-enrollment`.
The later production outcome is recorded in
`PI_PERSISTENT_ENROLLMENT_DEPLOYMENT_20260924.md`. No new service or paid
provider was enabled.

## Contract

- One active default Pi enrollment is stored in the existing private capture
  bucket at `pi-enrollments/v1/default.json`.
- The record contains schema, device profile ID, SHA-256 of the random device
  token, state, and timestamps. The plaintext token is returned only once to
  the enrolling Pi and is never persisted by the server.
- A persistent Pi may connect before a browser session exists. That connection
  is inactive: it receives no preview or capture command.
- Pressing Pi Camera under `/c` creates a fresh ephemeral browser session and
  binds the enrolled Pi without showing a pairing code. Browser session state,
  commands, preview frames, and jobs remain memory-only.
- The active session cannot be replaced while it has a live preview or an
  unuploaded capture. An idle session may be replaced by another tester.
- Only the existing reviewer role (A3) may call the device-revocation endpoint.

## Safety and privacy

No continuous camera feed, automatic preview, face recognition, person
tracking, or public camera URL was added. Preview and capture still require an
explicit Pi Camera interaction, and capture requires its own explicit press.
The existing bounded preview, finite four-frame capture, original SHA-256, and
gallery ingest boundary remain unchanged.

## Deployment behavior

The enrollment record survives a Cloud Run deploy, process restart, or
scale-to-zero. Ephemeral browser work does not survive; a tester presses Pi
Camera again after an interruption. A connected Pi WebSocket keeps an instance
active while connected. When the Pi is off, the existing minimum-instance zero
configuration can scale down.

## Rollback

Before deployment, abandon this branch. After a future deployment, return
traffic to the previous revision and stop the Pi agent. For suspected credential
exposure, revoke the profile, delete the Pi-local credential, and enroll a new
credential through an explicit owner action.
