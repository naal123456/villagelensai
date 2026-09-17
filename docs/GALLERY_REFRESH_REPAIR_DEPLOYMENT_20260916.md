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

## A3 default-language follow-up

Physical testing exposed that an explicit stale `lang=kn` URL still overrode
the A3 English default in version `2026-09-16.5`. Version `2026-09-16.7` moves
the rule to the server: an unmarked A3 Kannada request redirects to
`/a/?tester=a3&lang=en`, while a newly initiated image-language transition is
marked with `switch=1` and remains allowed. The Kannada subtitle was also
removed from the first English welcome box.

- Final source commit: `9830f73`
- Final Cloud Build: `f5a927a8-eda2-4d57-85c5-26759d97d8d7`
- Final container digest:
  `sha256:b6a6d699a7beccb7c83c50c755bfbfe855b1aeba48e6df152e662e0c1876776c`
- Final Cloud Run revision: `vlens-a-00073-gv6`, 100 percent traffic
- Unit tests: `72/72` passed
- Public stale A3 Kannada URL: HTTP 302 to the English A3 URL
- Public marked Kannada switch and English Home: HTTP 200
- Public English welcome box contains no Kannada subtitle
- Error-level logs after validation: empty
- Roll back this follow-up to `vlens-a-00071-rc5` if necessary

## Overlay geometry and Safari language-handoff follow-up

Field testing of A3-37 and A3-38 exposed two independent issues. The SVG
selection layer filled the whole stage even when a portrait image rendered
narrower than that stage, so a valid box could appear beside the photograph.
A3-38 also retained older stage-three coordinates expressed on an apparent
0–100 basis despite the 0–1000 model contract, producing very small boxes.
Finally, Safari could lose the session-storage handoff during a language
navigation, causing an otherwise valid Kannada switch to be treated as a stale
URL and redirected to English Home.

Version `2026-09-16.8` aligns the SVG layer to the photograph's actual rendered
rectangle after image load, gallery navigation, and viewport resize. New model
responses detect a consistent 0–100 coordinate basis, and retained results with
the same unmistakable scale pattern are repaired in memory without rerunning a
model or rewriting the stored evidence. A marked `switch=1` request carrying a
valid capture identifier is now a sufficient language handoff even if Safari
has discarded session storage; unmarked stale A3 Kannada URLs still redirect
to English Home.

- Source commit: `8260a4a`
- Cloud Build: `c8417cea-6a6f-42f9-806e-860951fee57b`
- Container digest:
  `sha256:c80c4c73e9b6b341034535ebed636cc6129646dbbb7e6bfacaa40a22083e1daf`
- Cloud Run revision: `vlens-a-00074-jmt`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight
- Unit tests: `73/73` passed
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-16.8`, zero missing OCR models
- Public stale A3 Kannada URL: HTTP 302 to the English A3 URL
- Authenticated marked A3 Kannada switch: HTTP 200 with the selected capture
- Authenticated A3 gallery: HTTP 200 in 3.83 seconds; A3-38 reports
  `box_scale_repaired: percent-to-pixels` and full-image box dimensions
- Deployed page contains image-aligned overlay and marked-switch handling
- Error-level logs after production validation: empty
- Validation did not upload a photograph or invoke OCR, speech, or inference
- Physical A3 Safari confirmation remains pending

Roll back this follow-up to `vlens-a-00073-gv6` if necessary.
