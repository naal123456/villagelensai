# Mentra native capture-contract v3 deployment — 2026-09-26

## Outcome

The isolated Mentra `/c` native job now uses contract
`villagelens.mentra-native-photo-job.v3`. It keeps automatic transfer, normal
photo mode, 62-degree center framing, shutter sound, and no extra gallery copy,
but requests `max` size with `none` compression. This matches the 4032 by 3024
format of the known-good stock Mentra still while changing only capture format
from the preceding physical test.

Capture remains inactive until one explicit user request. No new service or
paid capability was enabled, and no photograph or provider call was used for
deployment verification.

## Source and verification

- Source commit: `16b665d` (`Match native Mentra capture format`).
- Complete local server suite: 123/123 passed.
- Matching native Swift contract suite: 8/8 passed.
- Matching wearable suite: 37/37 passed.
- Cloud Build: `d6c0d5d4-ecc3-431a-922f-ca631e875a3a` (`SUCCESS`).
- Image: `gcr.io/villagelensai/vlens-pi-c-test:16b665d`.
- Immutable digest:
  `sha256:e30ea02a08b46334e6a9b750c92bc759aec939c7d422a8522e6ac5d234baa7bf`.

## Staging

- Revision: `vlens-pi-c-test-00013-qss`.
- Traffic: 100 percent.
- Health: HTTP 200, access gate enabled, no missing local OCR models.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302 access redirects.
- Unauthenticated native job poll: HTTP 401.
- Error-level logs after validation: empty.

Cloud Run created the new ready revision before changing traffic. Traffic was
therefore explicitly moved to `vlens-pi-c-test-00013-qss` and every validation
was repeated against the active revision.

## Production

- Revision: `vlens-a-00086-7xv`.
- Traffic: 100 percent.
- Health: HTTP 200, access gate enabled, no missing local OCR models.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302 access redirects.
- Unauthenticated native job poll: HTTP 401.
- Error-level logs after validation: empty.

Production uses the same immutable digest as staging. `/a`, `/b`, the Pi path,
gallery, reader, and access behavior were not changed by this contract-only
deployment.

## Rollback

Return production traffic to the preceding revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00085-55k=100
```

Return staging traffic to the preceding revision:

```sh
gcloud run services update-traffic vlens-pi-c-test \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-pi-c-test-00012-2dg=100
```

Rollback does not remove the device-only iPhone enrollment. Revoke enrollment
separately only for device replacement or credential recovery.
