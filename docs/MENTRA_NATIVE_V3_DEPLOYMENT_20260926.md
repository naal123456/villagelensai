# Mentra native v3 deployment — 2026-09-26

## Outcome

The native Mentra Live bridge contract is deployed to the existing isolated
`/c` staging service and production. The same immutable image is used in both
places. `/a`, `/b`, the Pi camera path, the retained Mentra MiniApp experiment,
gallery, reader, and access gate remain available through their existing
routes.

This deployment did not enroll a phone, connect to glasses, request a photo,
install an iPhone app, enable a service, or update glasses firmware. Native
physical-device qualification remains pending.

## Source and image

- source commit: `0e4e3a4`
- application version: `2026-09-25.2`
- Cloud Build: `031b67ab-860b-4144-ab0c-be9d9a7154d6` (`SUCCESS`)
- image: `gcr.io/villagelensai/vlens-pi-c-test:0e4e3a4`
- immutable digest:
  `sha256:b6b02a6d4b55058866f563d3719f9a7854797b0ebb5a6bdb05c1e04055414271`

The complete local server suite passed 122 tests immediately before the build.

## Staging

- service: `vlens-pi-c-test`
- region: `us-central1`
- revision: `vlens-pi-c-test-00009-snm`
- traffic: 100 percent
- health: HTTP 200, version `2026-09-25.2`, access gate enabled, no missing
  local OCR models
- unauthenticated `/a`, `/b`, and `/c`: existing HTTP 302 access redirects
- unauthenticated native job poll: HTTP 401
- error-level logs after validation: empty

The existing runtime service account, one CPU, 2 GiB memory, concurrency eight,
3,600-second request timeout, minimum instances zero, maximum instances one,
secret mappings, and capture storage configuration were retained.

## Production

- service: `vlens-a`
- public domain: `https://villagelensai.com`
- region: `us-central1`
- revision: `vlens-a-00082-r26`
- traffic: 100 percent
- health: HTTP 200, version `2026-09-25.2`, access gate enabled, no missing
  local OCR models
- unauthenticated `/a`, `/b`, and `/c`: existing HTTP 302 access redirects
- unauthenticated native job poll: HTTP 401
- error-level logs after validation: empty

The production revision uses the same digest and retained the existing runtime
service account, concurrency, timeout, scaling, secrets, and storage boundary.

## Rollback

Return production traffic to the previous revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00081-44t=100
```

Return staging traffic to the previous revision:

```sh
gcloud run services update-traffic vlens-pi-c-test \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-pi-c-test-00008-5tf=100
```

Rollback does not delete enrollment state. If a future device credential is
suspected of exposure, revoke that enrollment separately before reinstalling
or re-enrolling the native app.
