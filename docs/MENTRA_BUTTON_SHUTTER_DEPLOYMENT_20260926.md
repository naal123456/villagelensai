# Mentra physical-button shutter deployment — 2026-09-26

## Outcome

The isolated `/c` Mentra experience now arms the authenticated tester's private
gallery when its Mentra Camera panel opens. The enrolled native iPhone bridge
can claim that one bounded job after a glasses short-button event and upload
the original through the existing v3 ingest contract. The remote browser/app
button remains available as a bounded alternative.

No stream, video, automatic capture, firmware update, new service, or new paid
capability was enabled. `/a` and `/b` do not display or arm this control.

## Source and verification

- Source commit: `d61e573` (`Arm Mentra gallery for glasses button capture`).
- Application version: `2026-09-26.1`.
- Complete server suite: 125/125 passed.
- Python static compilation: passed.
- Matching native Swift contract suite: 11/11 passed.
- Matching wearable suite: 37/37 passed.
- Cloud Build: `3c837d18-d1a3-40f0-8c80-a85de32e0065` (`SUCCESS`).
- Image: `gcr.io/villagelensai/vlens-pi-c-test:d61e573`.
- Immutable digest:
  `sha256:bf6aa4dbe1e28cb3f99109e039b324ac863071a85b15bcf444c8b001f31283a3`.

## Safety and routing

- Opening authenticated `/c` creates one short-lived, tester-bound session but
  does not activate the camera.
- The existing single-active-device-session rule prevents simultaneous tester
  galleries from arming the one enrolled glasses profile.
- The authenticated device claim accepts only `browser-control` or
  `glasses-button`; the selected value is retained in capture provenance.
- Long presses, unarmed presses, disconnected presses, and presses while the
  native app is preparing or busy cannot produce a VillageLens photograph.
- The camera light, shutter sound, original-source hash preservation, and
  existing gallery ownership boundary remain unchanged.

## Staging

- Service: `vlens-pi-c-test`, region `us-central1`.
- Revision: `vlens-pi-c-test-00014-x5x`, 100 percent traffic.
- Previous revision: `vlens-pi-c-test-00013-qss`.
- Health: HTTP 200, version `2026-09-26.1`, access gate enabled, no missing
  local OCR models.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302.
- Unauthenticated native device job poll: HTTP 401.
- Error-level validation logs: empty.

The candidate was created with no traffic, validated through a temporary tag,
then promoted. The temporary tag was removed afterward.

## Production

- Service: `vlens-a`, region `us-central1`.
- Revision: `vlens-a-00087-s9f`, 100 percent traffic.
- Previous revision: `vlens-a-00086-7xv`.
- Health: HTTP 200, version `2026-09-26.1`, access gate enabled, no missing
  local OCR models.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302.
- Unauthenticated native device job poll: HTTP 401.
- Error-level validation logs: empty.

Both services retain concurrency eight, a 3,600-second timeout, the existing
runtime service account, minimum instances zero, and maximum instances one.
Production uses the exact digest qualified on staging. The service did not
publish a usable tagged candidate URL, so post-promotion public validation was
performed immediately with the prior revision retained for rollback. The
temporary production tag was then removed.

## Remaining qualification

The updated signed iPhone app must still be installed and the button-to-gallery
path physically tested. Do not claim physical completion or field readiness
from deployment checks alone. No photograph, tester URL, request identifier,
device credential, authorization header, or provider response is in this
record.

## Rollback

Return production traffic to the preceding revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00086-7xv=100
```

Return staging traffic to the preceding revision:

```sh
gcloud run services update-traffic vlens-pi-c-test \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-pi-c-test-00013-qss=100
```

Rollback does not remove the device-only Keychain enrollment. Revoke it only
for device replacement or credential recovery.
