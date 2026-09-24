# Pi persistent enrollment deployment — 2026-09-24

## Outcome

Persistent Pi enrollment is integrated into `main` and deployed to both the
isolated Pi staging service and production. The real Pi was enrolled once,
reconnected after later Cloud Run deployments without another pairing code,
provided an explicitly requested preview, and delivered explicitly requested
captures to the existing gallery and reading pipeline.

The latest capture interaction keeps the Pi panel visible, shows an elapsed
timer through camera acquisition, frame selection, upload, and gallery loading,
then transitions directly to the captured gallery item. This removes the
intermediate home-screen flash reported during physical testing.

## Source and build

- latest source commit: `e0e5570`
- application version: `2026-09-24.3`
- Cloud Build: `be3e4353-f67e-4e2b-bfce-aa97ea4eff6e` (`SUCCESS`)
- image: `gcr.io/villagelensai/vlens-pi-c-test:e0e5570`
- immutable digest:
  `sha256:61bafeeba9b467ea979009f08c8888334c92daee9c1ba9ffd74334e53fbbb014`

The latest pre-deployment suite passed 103 tests. Python compilation, embedded browser
JavaScript parsing, service-worker parsing, dependency checking, and
`git diff --check` also passed.

## Staging

- service: `vlens-pi-c-test`
- revision: `vlens-pi-c-test-00007-k47`
- traffic: 100 percent
- public health: HTTP 200, version `2026-09-24.3`, access gate enabled, no
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
- revision: `vlens-a-00081-44t`
- traffic: 100 percent
- public domain: `https://villagelensai.com`
- public health: HTTP 200, version `2026-09-24.3`, access gate enabled, no
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

After the production update, the enrolled Pi agent remained running and had an
established secure connection. Its local credential remained mode `0600`.
This check did not request preview or capture. Error-level logs for the latest
production revision were empty at validation time.

## Enrollment boundary

The server created
`gs://villagelensai-captures/pi-enrollments/v1/default.json` during the real
owner enrollment. It contains the device profile, state, timestamps, and token SHA-256—not the
plaintext token. Browser sessions, commands, preview frames, and capture jobs
remain memory-only.

## Physical findings and follow-up

- A difficult, small-text target reached the gallery and was parsed after
  improving lighting. Reading accuracy differed across existing UI actions;
  the owner retained the private gallery reference for later investigation.
- An earlier upload returned `LOCAL_OCR_UNAVAILABLE` because local OCR exceeded
  its 20-second ceiling. Version `2026-09-24.2` raised that ceiling to 45
  seconds, while Pi upload waits are bounded at 75 seconds.
- These checks qualify the capture bridge interaction, not the temporary camera
  mount or the device for field or wearable use.

## Rollback

Return production traffic to the retained prior revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00080-t6j=100
```

For staging, route traffic to `vlens-pi-c-test-00006-j29`. Rollback does not
delete a future enrollment object. If the persistent credential is suspected
of exposure, revoke it through the reviewer endpoint before removing the
Pi-local credential or enrolling a replacement.
