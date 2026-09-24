# Pi persistent enrollment deployment — 2026-09-24

## Outcome

Persistent Pi enrollment is integrated into `main` and deployed to both the
isolated Pi staging service and production. Public route and contract checks
passed without enrolling a synthetic device, uploading a photograph, or
invoking an OCR, inference, speech, or other paid provider.

The real Pi has not yet been re-enrolled. The persistent enrollment object is
absent, so the next `/c` session will correctly display a one-time owner pairing
code. Physical reconnect and camera testing remain pending.

## Source and build

- integrated source commit: `4481128`
- application version: `2026-09-24.1`
- Cloud Build: `2d6957d9-2b25-45fa-96eb-8345f50f0f92` (`SUCCESS`)
- image: `gcr.io/villagelensai/vlens-pi-c-test:4481128`
- immutable digest:
  `sha256:3663d12258b05d756fecfe165a87271ae9f0efff4079632e83d1e609c5bc7e36`

The pre-deployment suite passed 102 tests. Python compilation, embedded browser
JavaScript parsing, service-worker parsing, dependency checking, and
`git diff --check` also passed.

## Staging

- service: `vlens-pi-c-test`
- revision: `vlens-pi-c-test-00005-vs4`
- traffic: 100 percent
- public health: HTTP 200, version `2026-09-24.1`, access gate enabled, no
  missing local OCR models
- authenticated `/a`: HTTP 200
- authenticated `/b`: existing HTTP 302 English redirect
- authenticated `/c`: HTTP 200 with Pi Camera and version marker
- ephemeral browser-session contract: passed, then explicitly revoked
- invalid device pairing: HTTP 401
- error-level revision logs after validation: empty

## Production

- service: `vlens-a`
- region: `us-central1`
- revision: `vlens-a-00079-nqd`
- traffic: 100 percent
- public domain: `https://villagelensai.com`
- public health: HTTP 200, version `2026-09-24.1`, access gate enabled, no
  missing local OCR models
- authenticated `/a`: HTTP 200
- authenticated `/b`: existing HTTP 302 English redirect
- authenticated `/c`: HTTP 200 with Pi Camera and version marker
- ephemeral browser-session contract: passed, then explicitly revoked
- error-level revision logs after validation: empty

The deployed image digest is identical in staging and production. Production
preserves the existing runtime service account, capture bucket, access/session
secret mappings, OpenAI secret and model configuration, one CPU, 2 GiB memory,
concurrency eight, 3,600-second request timeout, minimum instances zero, and
maximum instances one. No service or API was newly enabled.

## Enrollment boundary

The server will create only
`gs://villagelensai-captures/pi-enrollments/v1/default.json` during the real
owner enrollment. That object did not exist during deployment validation. It
will contain the device profile, state, timestamps, and token SHA-256—not the
plaintext token. Browser sessions, commands, preview frames, and capture jobs
remain memory-only.

## Rollback

Return production traffic to the retained prior revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00078-v8p=100
```

For staging, route traffic to `vlens-pi-c-test-00004-wts`. Rollback does not
delete a future enrollment object. If the persistent credential is suspected
of exposure, revoke it through the reviewer endpoint before removing the
Pi-local credential or enrolling a replacement.
