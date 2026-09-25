# Mentra MiniApp remote-shutter checkpoint — 2026-09-25

## Status

The isolated `/c` source now has a persistent Mentra enrollment and a v2
remote-shutter contract compatible with the current on-phone Mentra MiniApp
SDK. It is locally tested and not yet physically qualified. The next deployment
target is only the separate `vlens-pi-c-test` service; production promotion is
not part of this checkpoint.

No new cloud service or paid provider is required. Existing Cloud Storage is
used for the credential record and retained gallery image. The Cloud Run test
service must retain minimum instances zero and maximum instances one.

## Contract and privacy boundary

- The owner enrolls the physical Mentra controller once with an expiring
  16-character code. Only the device-token SHA-256, profile identifier,
  enrollment time, and revocation state are persisted in the existing private
  bucket.
- A later `/c` browser press creates a short-lived session for the already
  enrolled controller. Idle polling returns no job and cannot activate the
  camera.
- Each job specifies one 62-degree centered, maximum-size, text-mode still with
  shutter sound and no Mentra gallery copy. It contains no tester identity or
  output language.
- The MiniApp submits a short-lived signed photo URL using a one-job upload
  token. The server permits HTTPS only, rejects credentials, fragments,
  redirects, non-443 ports, and hosts outside the exact
  `VILLAGELENS_MENTRA_PHOTO_HOSTS` allowlist, and bounds both the reported and
  downloaded size.
- The downloaded original is SHA-256 bound before the existing `_ingest_capture`
  helper stores it. The signed URL and Mentra request identifier are excluded
  from capture provenance.

The first physical staging request is designed to fail closed while revealing
only the relay hostname in the MiniApp. The hostname must be observed from the
current firmware and explicitly allowlisted before a photo can enter the
gallery.

## Verification

- Complete server suite: 117/117 tests passed.
- Focused Mentra/API/Pi suite: 107/107 tests passed.
- Python compilation and dependency checking passed.
- Embedded browser JavaScript and service-worker parsing passed.
- `git diff --check` passed.

Coverage includes persistent token hashing and revocation, tester isolation,
identity-free jobs, idle behavior, one-job delivery, exact-host rejection,
reported/downloaded size binding, immutable-source hashing, existing gallery
ingress reuse, and unchanged `/a` and `/b` route behavior.

## Staging and rollback

Build the committed source once and deploy the image first to
`vlens-pi-c-test` with its existing service account, storage bucket, access
secrets, resource limits, and no OpenAI secret. HTTP validation must not submit
an image or invoke a reader provider.

Rollback before production is routing the staging service to its prior
revision. Revert this source commit to remove the v2 contract. Revoking the
Mentra enrollment disables its long-lived credential without deleting any
previously accepted gallery capture.
