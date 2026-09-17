# Gallery refresh repair deployment — 2026-09-16

Status: deployed and publicly HTTP-validated; physical Safari refresh and
language-switch confirmation pending.

## Incident and cause

- Version `2026-09-16.4` wrote every selected capture into browser history.
  Consequently, an ordinary refresh restored the last capture instead of opening
  Home.
- The reviewer gallery loaded Cloud Storage result and stage records serially.
  Production requests took approximately 12 to 27 seconds, during which the
  navigation arrows appeared usable despite having no gallery data.
- A stage object was listed and then became unavailable before download. The
  resulting 404 escaped the per-stage handler and caused the whole gallery to
  fall back to demo items. The requested capture was then not found, so the
  client displayed Home in the language encoded by the stale URL.
- A later OpenAI stage-three timeout was separate from the gallery failure and
  must not affect basic navigation.

## Repair

- Ordinary refresh is no longer a deep-link restore. A stale `view` parameter
  without the short-lived same-tab language-switch handoff is removed and Home
  opens immediately.
- A3 Home defaults to English when no explicit active language transition is in
  progress. Other tester defaults remain unchanged.
- Only pressing the language button creates the temporary capture handoff. Once
  the same capture opens in the target language, the URL is cleaned so a later
  refresh returns to Home.
- Previous/next arrows are disabled and animated while the gallery is loading.
  During a language handoff, the clock counts and the status explicitly says the
  arrows will work when saved images are ready.
- Gallery result records now load with a bounded pool of eight storage workers.
  Missing or concurrently replaced result/stage objects are skipped individually
  and cannot discard the rest of the gallery.

## Verification

- Application version: `2026-09-16.5`
- Source commit: `ba90357`
- Cloud Build: `2248d188-fd01-4f4e-85c5-1548bff0336d`
- Container digest:
  `sha256:6b109377a3bd00112d60015e22dd34231e259d876ad1771371b917e8c1df9be0`
- Cloud Run revision: `vlens-a-00071-rc5`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight
- Unit tests: `71/71` passed
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-16.5`
- Authenticated A3 gallery: HTTP 200, 105 items, A3-36 present
- Measured authenticated production gallery response: 5.15 seconds, down from
  the observed 12–27 second serial-loading range
- Protected page contains stale-view cleanup, A3 English default, and visible
  gallery-loading feedback
- Error-level logs for the new revision after full gallery validation: empty
- Validation did not upload a photograph or invoke OCR, speech, or inference

## Physical-phone check

1. Refresh the old A3 image URL. Confirm it redirects to A3 Home in English.
2. Confirm Home appears immediately rather than waiting for the gallery.
3. Press an arrow as soon as Home opens. It should remain disabled/animated
   until the saved gallery is ready, then work normally.
4. Open A3-36, switch English to Kannada, and confirm A3-36 remains visible while
   the timer and loading explanation run.
5. After the switch completes, refresh. Confirm Home opens in English.

## Rollback

Route traffic back to `vlens-a-00070-zdk`. That revision preserves a capture
across language switching and identifies source languages, but has the refresh,
serial-gallery, and missing-stage failure described above.
