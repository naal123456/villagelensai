# `/c` production integration checkpoint — 2026-09-23

## Status

The isolated Pi-camera branch now contains the complete application source from
main commit `8914f96` plus the tested `/c` bridge. It has not yet been promoted
to production traffic at this checkpoint.

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
