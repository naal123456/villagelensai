# `/c` production integration checkpoint — 2026-09-23

## Status

The isolated Pi-camera branch now contains the complete application source from
main commit `8914f96` plus the tested `/c` bridge. The combined application was
promoted to production only after the separate test service passed the HTTP and
WebSocket checks below.

## Integrated behavior

- `/a` and `/b` retain the Chinese/Han source-reading update and application
  version advances to `2026-09-23.2` for the combined build.
- `/c` reuses the same gallery, OCR, reader, language, speech, questions, and
  signed-access implementation while exposing its Pi Camera control.
- Existing passwordless tester links default to `/a` exactly as before.
- A signed tester link deliberately opened through `/access?next=c` now carries
  the validated anonymous tester into `/c` without asking them to type the
  shared access code. The signed credential remains in the URL fragment and is
  removed before the exchange request, as in the existing `/a` flow.
- Pairing remains an owner/bench workflow in this revision. The longer-term
  shared-Pi enrollment design is not claimed complete.

## Verification

- Combined suite: 93/93 tests passed.
- Focused `/a` signed-link compatibility, `/c` passwordless signed-link,
  fragment handling, and `/a`/`/b`/`/c` route-isolation tests passed.
- Python compilation, dependency checking, embedded JavaScript parsing,
  service-worker parsing, and `git diff --check` passed.
- The merge from main completed without a conflict; both `api/app.py` and
  `web/a/index.html` were merged automatically and then covered by the combined
  suite.

## Promotion gates

1. Rebuild and redeploy `vlens-pi-c-test` from this combined commit.
2. Verify health version `2026-09-23.2`, protected `/a`, `/b`, and `/c` routes,
   passwordless `/c` exchange, and public WSS preview with synthetic bytes only.
3. Confirm production `vlens-a` has not moved during staging validation.
4. Deploy the same immutable image to a new `vlens-a` revision with the existing
   limits and secret mappings, retaining the preceding revision for immediate
   rollback.
5. Do not upload a field image or invoke reader providers as part of deployment
   validation.

## Deployment outcome

The source at commit `e8bf8be` was built once and identified by immutable image
digest:

`sha256:ca7afbebb8c365f4d76a8c8c3dc3deaa697b796988ccb9a210931ba0887898d4`

The image was first deployed to `vlens-pi-c-test`. After the combined checks,
the test service was left on revision `vlens-pi-c-test-00003-9kz` with:

- minimum instances zero and maximum instances one;
- one CPU, 2 GiB memory, concurrency eight, and a 3,600-second request timeout;
- no OpenAI credential mapping; and
- 100 percent test-service traffic on the validated revision.

The same digest was then promoted to production as revision
`vlens-a-00077-b22`. Production retains its existing runtime identity, capture
bucket, access/session secrets, OpenAI secret, reader-model settings, one CPU,
2 GiB memory, concurrency eight, zero minimum instances, and one maximum
instance. The request timeout changed from 90 to 3,600 seconds so an active,
bounded WebSocket bridge is not terminated by the HTTP request ceiling.

Production traffic is 100 percent on `vlens-a-00077-b22`. The preceding
revision `vlens-a-00076-98l` remains available for rollback.

## Deployed validation

On both the separate test service and `https://villagelensai.com`:

- `/health` returned HTTP 200, application version `2026-09-23.2`, and an
  enabled access gate;
- an existing signed tester link still resolved to `/a/?tester=a5`;
- the same signed identity with the explicit Pi-lane intent resolved to
  `/c/?tester=a5` without requiring the tester to type an access code;
- authenticated `/a`, `/b`, and `/c` requests returned the combined version,
  with `/b` retaining its existing English redirect and `/c` containing the Pi
  Camera control;
- an authenticated synthetic device and browser completed public WSS
  handshakes, received `preview_start`, and transferred one 518-byte in-memory
  JPEG marker byte-for-byte; and
- the temporary browser/device session was revoked immediately.

The first signed-link diagnostic failed because the validation command had
removed trailing bytes from the stored session secret. Repeating the check with
the secret preserved byte-for-byte succeeded against the active access-code
version. No secret or token was printed or persisted.

Error-level logs for the final staging and production validation windows were
empty. No field photograph, capture upload, gallery object, OCR request,
inference request, speech request, or other provider call was made.

## Rollback

Route all production traffic back to the retained preceding revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00076-98l=100
```

This rollback restores the preceding application revision. Its original
90-second request timeout would require a separate configuration update because
the timeout belongs to the service revision template rather than traffic
routing.

## Long-WebSocket repair and physical gallery checkpoint

The first supervised production Pi burst exposed a second 90-second ceiling in
the container command: Cloud Run allowed 3,600 seconds, but Gunicorn still used
`--timeout 90`. The Pi safely preserved all four originals, but the socket
closed before its inactive acknowledgement and normal upload. The selected
original was recovered through the existing hash-bound upload contract within
the job's ten-minute grace window; the owner confirmed that it appeared in the
phone gallery.

Commit `844487d` changes the Gunicorn timeout to 3,600 seconds and adds a
regression test that binds the container timeout to the bounded Pi session.
The combined suite passed 94/94 tests. Cloud Build
`83e475f4-b370-48bf-992d-1fa7cbf10a89` produced immutable image digest:

`sha256:aa14ec4cff763353e0c77c76b68d25adcc31e13898bd285c5a69be350bc73741`

The image was deployed first to staging revision
`vlens-pi-c-test-00004-wts`. A synthetic device WebSocket remained
authenticated for 95.3 seconds, then received a fresh `preview_start` command;
no image, upload, or provider was used, and the temporary session was revoked.

The exact digest was promoted to production revision `vlens-a-00078-v8p`,
which serves 100 percent of traffic with minimum instances zero, maximum one,
concurrency eight, and both Cloud Run and Gunicorn request ceilings at 3,600
seconds. Public health returned application version `2026-09-23.2`, and
error-level logs for the new revision were empty. The prior working application
revision `vlens-a-00077-b22` remains available for emergency rollback:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00077-b22=100
```

That rollback reintroduces the 90-second Gunicorn limit. The production
revision restart invalidated the temporary in-memory Pi pairing session but did
not remove the accepted gallery object or any Pi-local original.
