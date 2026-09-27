# Mentra native bounded-capture deployment — 2026-09-26

## Outcome

The native Mentra `/c` job contract now requests a medium-size, medium-compressed
still. This replaces the maximum-size, uncompressed Bluetooth request that
terminated the glasses camera service during the first physical retry. The
change does not activate a camera; capture still requires one explicit user
request and retains the shutter sound and hardware camera indication.

## Source and verification

- Source commit: `b0270ea` (`Bound native Mentra Bluetooth photo size`).
- Complete local suite: 123/123 passed.
- Python compilation and `git diff --check`: passed.
- Cloud Build: `83a2d3e5-1c3c-4452-b2cb-1b0a0542fd0c` (`SUCCESS`).
- Image: `gcr.io/villagelensai/vlens-pi-c-test:b0270ea`.
- Immutable digest:
  `sha256:e2bb6ae6f295e5487ba30d97a54b9324ef21215c28a92e5a46358cd6a62b9df2`.

No new service or paid capability was enabled.

## Staging

- Revision: `vlens-pi-c-test-00011-nbg`.
- Traffic: 100 percent.
- Health: HTTP 200, access gate enabled, no missing local OCR models.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302 access redirects.
- Unauthenticated native job poll: HTTP 401.
- Error-level logs after validation: empty.

## Production

- Revision: `vlens-a-00084-vl5`.
- Traffic: 100 percent.
- Health: HTTP 200, access gate enabled, no missing local OCR models.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302 access redirects.
- Unauthenticated native job poll: HTTP 401.
- Error-level logs after validation: empty.

The application version remains `2026-09-25.2` because this is a server-side
capture-contract correction rather than a browser asset change. `/a`, `/b`, the
Pi bridge, gallery, and reader behavior are unchanged.

## Rollback

Return production traffic to the preceding revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00083-wks=100
```

Return staging traffic to the preceding revision:

```sh
gcloud run services update-traffic vlens-pi-c-test \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-pi-c-test-00010-2cd=100
```

Rollback does not delete the device-only iPhone enrollment. Revoke enrollment
separately only for device replacement or credential recovery.
