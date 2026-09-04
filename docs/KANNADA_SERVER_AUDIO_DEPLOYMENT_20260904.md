# Kannada server audio deployment

Date: 2026-09-04
Status: deployed; public API validated; A1 phone listening test pending

## Outcome

Kannada text no longer depends on a Kannada speech voice being installed on the
tester's phone. The authenticated client sends only Kannada speech segments to
the server, receives `audio/mpeg`, and plays it through Web Audio. English keeps
using the phone's system voice.

Audio is cached twice:

- decoded audio remains in the current browser page for repeated taps; and
- synthesized MP3 remains in the private capture bucket under a SHA-256 object
  name, so a new page session does not synthesize the same segment again.

The cache key includes a version and voice identity. It does not contain the
recognized text. Requests are limited to 500 characters and must contain
Kannada script.

## Google configuration

- Project: `villagelensai`
- API enabled: `texttospeech.googleapis.com`
- Voice: `kn-IN-Standard-A`
- Speaking rate: `0.82`
- Authentication: the existing Cloud Run workload service account; no browser
  key and no new stored service-account key
- Cloud Run minimum instances: zero
- Cloud Run maximum instances: one
- Cloud Run concurrency: eight

The shell default pointed at an older project named `missionlens-platform-v1`.
An activation attempt there was rejected because its billing account is closed;
no service was enabled and no billing configuration was changed in that project.
Every successful operation was explicitly scoped to `villagelensai`.

## Build and deployment

- Source commit: `7d9aa90`
- Cloud Build: `c0f0fb10-77fa-4fe3-8019-86761bbda912` (`SUCCESS`)
- Image digest:
  `sha256:c8fdaccc6c0b3d603efce227fa4b7ba6564367042a4432451c6c6c1ad07cb502`
- Cloud Run revision: `vlens-a-7d9aa90`
- Traffic: 100 percent

## Validation

- Focused unit and contract tests: 21/21 passed.
- Python compilation, JavaScript syntax, and `git diff --check`: passed.
- Public health endpoint: HTTP 200, pinned Tesseract models present, access gate
  enabled.
- Fresh A1 login: HTTP 303 followed by reader HTTP 200.
- Fresh A3 login: HTTP 303.
- First authenticated Kannada request: HTTP 200, `audio/mpeg`, 7,872 bytes,
  cache `miss`.
- Repeated identical request: HTTP 200, same byte count, cache `hit`.
- Private bucket contains the expected hashed MP3 object.
- No error-level logs were present for the new revision after these checks.

This establishes server synthesis and delivery, but not audible phone behavior.
Eeregowda's Samsung must be used to confirm volume, Web Audio playback, and the
voice's practical intelligibility.

## Rollback

Route 100 percent of traffic back to `vlens-a-5070aba`. That revision restores
the prior client-side speech behavior. The enabled API and hashed audio object
can remain without affecting the rollback revision.
