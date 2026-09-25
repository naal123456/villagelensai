# Mentra MiniApp remote-shutter checkpoint — 2026-09-25

## Status

The isolated `/c` source now has a persistent Mentra enrollment and a v2
remote-shutter contract compatible with the current on-phone Mentra MiniApp
SDK. It is locally tested and deployed only to the separate
`vlens-pi-c-test` service. It is not yet physically qualified, and production
promotion is not part of this checkpoint.

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

## Staging deployment

Server commit `391cd16` produced Cloud Build
`57368217-5347-452d-af22-7365b3c702bd` and immutable image digest
`sha256:946da30608e59e036281ca0f1db5492baaab4186f4ee3970b0dbee350611d84a`.
The image is serving 100 percent of staging traffic on revision
`vlens-pi-c-test-00008-5tf`.

The staging service retained its existing runtime identity, private capture
bucket, access and session secrets, one CPU, 2 GiB memory, concurrency eight,
3,600-second timeout, minimum instances zero, and maximum instances one. It has
no OpenAI secret and no Mentra relay hostname allowlist yet.

Public validation confirmed health version `2026-09-25.1`, the protected `/c`
redirect, and a 401 response to an invalid Mentra enrollment code. Error-level
logs for the new revision were empty. No image, gallery upload, OCR, reader,
speech, or other provider request was made. Production remained unchanged at
revision `vlens-a-00081-44t` with 100 percent traffic.

## Rollback

Rollback before production is routing the staging service to its prior
revision, `vlens-pi-c-test-00007-k47`:

```sh
gcloud run services update-traffic vlens-pi-c-test \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-pi-c-test-00007-k47=100
```

Revert the source commit to remove the v2 contract. Revoking the Mentra
enrollment disables its long-lived credential without deleting any previously
accepted gallery capture.
