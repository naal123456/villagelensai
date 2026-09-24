# `/c` isolated test deployment — 2026-09-23

## Outcome

The committed `codex/pi-camera-c` source at `d73ee6e` is deployed to a separate
Cloud Run service for Raspberry Pi pairing tests:

- service: `vlens-pi-c-test`
- region: `us-central1`
- revision: `vlens-pi-c-test-00001-cc7`
- test route:
  `https://vlens-pi-c-test-jgvn2mf6pq-uc.a.run.app/c/`
- traffic: 100 percent within the test service

Production was not modified. `vlens-a` remained on revision
`vlens-a-00076-98l` with 100 percent of its own traffic, and no domain mapping
for `villagelensai.com`, `/a`, or `/b` changed.

## Build evidence

- Cloud Build: `1a2eb812-6ab8-4079-ad45-475ab541441e` (`SUCCESS`)
- image: `gcr.io/villagelensai/vlens-pi-c-test:d73ee6e`
- image digest:
  `sha256:2e9433f653380b6641ab0a66a71f9055c8e1ca2cdae97b4bddceac79c4a73362`
- source bundle: 81 tracked files, 14.8 MiB before compression

Cloud Run, Cloud Build, Container Registry, and Artifact Registry APIs were
already enabled. No API or paid provider was newly enabled.

## Runtime boundary

- minimum instances: zero
- maximum instances: one
- CPU: one
- memory: 2 GiB
- concurrency: eight
- request timeout: 3,600 seconds
- ingress: all, protected by the application access gate
- runtime identity: existing `villagelens-runtime` service account
- secrets: existing access-code and session-signing secrets only
- storage: existing `villagelensai-captures` bucket name

The OpenAI key was deliberately not mapped into the test service. No image was
uploaded and neither Google Vision, Text-to-Speech, OpenAI, nor another provider
was invoked during deployment validation.

## Validation

- Pre-deployment suite: 90/90 tests passed.
- Python compilation, dependency checking, embedded browser JavaScript parsing,
  service-worker parsing, and `git diff --check`: passed.
- Public `/health`: HTTP 200, access gate enabled, no missing local OCR models.
- Unauthenticated `/c/?tester=a1`: HTTP 302 to the access gate with `no-store`.
- Invalid device pairing: HTTP 401 with `PI_PAIRING_CODE_INVALID`.
- A cookie-less browser WebSocket was rejected with HTTP 401, confirming the
  access gate also protects the browser socket.
- An authenticated public browser WebSocket and separately credentialed device
  WebSocket connected successfully. `preview_start` routed to the synthetic
  device, and one 518-byte in-memory JPEG arrived unchanged at the correct
  browser session.
- The temporary pairing/browser session was revoked immediately after the test.
- Error-level logs after these checks were empty.

This proves the deployed pairing and preview transport, not real Pi capture,
gallery retention, OCR/inference, mobile Safari behavior, reconnect behavior,
or long-lived/concurrent WebSocket operation.

## Rollback

Delete only the isolated test service:

```sh
gcloud run services delete vlens-pi-c-test \
  --project villagelensai --region us-central1
```

The image may remain as immutable build evidence or be removed separately after
review. Production does not need a traffic rollback because it never received
this revision. Re-pairing is required after any test-service restart because
session routing is intentionally in memory.
