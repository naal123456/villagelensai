# Multilingual target-language reading deployment — 2026-09-13

## Outcome

Version `v2026.09.13.2` makes the selected reader language authoritative.
The English `/b/` reader now defaults to word mode and, for Kannada, Tamil,
Telugu, or Hindi text, speaks the source selection and then its English
translation. Kannada `/a/` retains Kannada as its target and can translate
non-Kannada selections into Kannada.

The object-selection action now reads OCR text whose center lies inside the
selected blue region before speaking the region's semantic explanation. The
whole-image action begins with the global identity or short explanation before
walking through highlighted evidence sections, so a model omission in the
section list does not silently drop the image heading.

## Speech

The client no longer depends on a phone having suitable Indian-language voices.
The private `/api/speech` endpoint accepts `kn-IN`, `ta-IN`, `te-IN`, `hi-IN`,
and `en-IN`, validates text against the requested script, and synthesizes a
consistent Indian voice server-side. Kannada, Tamil, Hindi, and Indian English
use WaveNet A; Telugu uses Standard A. Speech is slightly faster than the old
Kannada voice (`0.90` versus `0.82`) and every language/text/voice result is
cached privately under `speech/v2`.

The full teaching prompt now asks for a patient, connected explanation, requires
visible headings before body details, and explicitly rejects mechanical OCR-box
or calendar-cell narration. New semantic cache versions are
`terra-context-v2` and `sol-review-v2`; an older retained image is regenerated
only when visited in that output language, then reused.

## Verification

- Deployable source commit: `8e5feff`
- GitHub Actions run `34777855465`: passed
- Unit tests: `64/64` passed
- Python compilation, embedded browser JavaScript parsing, service-worker
  parsing, and `git diff --check`: passed
- Cloud Build: `958d6150-97a0-4cb4-b8c0-d834329bc3ce`
- Container digest:
  `sha256:c5b3983666fd64b012fbd908f78aa7e02ce70d6d5d9c3d43d676e324d5631fd7`
- Cloud Run revision: `vlens-a-00052-rml`, 100 percent traffic
- Operational limits retained: zero minimum instances, one maximum instance,
  one CPU, 2 GiB memory, concurrency eight, timeout 90 seconds
- Public `/health`: healthy, OCR models present, Luna/Terra/Sol cascade exact,
  stage 4 manual
- Authenticated `/b/`: `v2026.09.13.2`, `terra-context-v2`, `sol-review-v2`
- Live authenticated speech synthesis returned HTTP 200 and valid MP3 audio for
  Kannada, Tamil, Telugu, Hindi, and Indian English
- New-revision warning/error log query: empty after the live checks

Physical listening on the owner's iPhone and field Android phones remains the
required pronunciation and voice-quality acceptance test.

## Rollback

Route traffic back to `vlens-a-00051-xqs`. That revision is version
`v2026.09.13.1` and supports Kannada server speech plus phone-provided English
speech, without multilingual source pronunciation or bilingual word/sentence
reading.

## Incremental touch-reading corrections

- `v2026.09.13.3`, commit `420b366`, Cloud Run revision
  `vlens-a-00053-2lb`: sentence reading reuses the best overlapping Terra/Sol
  transcription, reads the original row, and then reads its English rendering.
- `v2026.09.13.4`, commit `550b90e`, Cloud Build
  `ca247c28-fb1c-4280-9473-d5a81e9ad482`, container digest
  `sha256:0ebaf459bea7bae9cc4ddc2b7e4754e3fa77aa6f0c888e3e520e5ae2ddba81a3`,
  Cloud Run revision `vlens-a-00054-gj6`: word reading aligns a selected source
  token with a multi-item contextual translation retained by an earlier stage.
  On `A2-17`, this maps the seven Kannada calendar weekday labels to Sunday
  through Saturday without an additional model request. All 64 tests and
  browser JavaScript parsing passed; the public English page returned the new
  version and function marker, and the new-revision warning query was empty.

## Button 2 contextual correction

Version `v2026.09.13.3` changes only sentence reading. A selected OCR sentence
is matched by image overlap to the best Terra/Sol contextual transcription.
The reader speaks the original row and then that existing English rendering,
instead of sending an isolated or corrupted OCR string for a context-free
translation. This is especially important for calendar weekday rows.

- Source commit: `420b366`
- Tests: `64/64` passed; Python and JavaScript parsing passed
- Cloud Build: `bbe956e1-1a26-415c-8191-57157a0a0402`
- Container digest:
  `sha256:10b3f2514a9604fe4dbc185c2ca30febc4d9f179b1fedaa407bf173086c51172`

## Semantic calendar correction

Version `v2026.09.13.7` replaces unreliable OCR date-token grouping with a
semantic calendar layer. Terra and Sol return the detected month, year,
weekday-header bounds, and date-grid bounds. The browser derives each weekday
and date cell deterministically, so adjacent dates such as 1 and 2 cannot be
spoken as 12. Calendar dates are also exposed as a dedicated selectable object;
the object reader summarizes the calendar rather than concatenating corrupted
OCR rows.

Stage 4 now appears ready only when quality and independent consensus both
validate. Agreeing cached reviews that used a phrase such as "No material
disagreement" are safely normalized to the empty-disagreement contract, so an
existing Sol result does not need a repeat paid request. Non-ASCII access-code
mistakes are rejected normally instead of raising a string-comparison error.

- Google Cloud project: `villagelensai`
- Source commits: `24447cd`, `59a2a77`, `1dc2b00`
- GitHub Actions run `34786647929`: passed
- Final test suite: `66/66` passed
- Python compilation, embedded JavaScript parsing, service-worker parsing, and
  `git diff --check`: passed
- Final Cloud Build: `c907dff0-8353-4676-a29e-ba486d96f8b7`
- Final container digest:
  `sha256:840310c2c5ec13782f22e643172926441fe53b49302a87fdf15f5a9151deaecf`
- Production revision: `vlens-a-00057-dbt`, 100 percent traffic
- Operational limits retained: zero minimum instances, one maximum instance,
  one CPU, 2 GiB memory, concurrency eight, timeout 90 seconds
- Public `/health`: healthy; authenticated `/b/?tester=a3`: version `.7` and
  calendar reader markers present
- Live `A2-17` stage 3: September 2026 detected with valid weekday and date-grid
  bounds; quality validated
- Live cached `A2-17` stage 4: quality and consensus validated with an empty
  material-disagreement field; no repeat Sol inference was required after `.7`
- Live Kannada wrong-code check: HTTP 401 as expected. The only warning-level
  log entry on the final revision is this intentional 401 request test; no
  application exception was recorded.

Immediate rollback is `vlens-a-00056-qwg`, which retains semantic calendar
reading and the access-code fix but does not normalize already cached agreeing
Sol reviews. Roll back to `vlens-a-00054-gj6` to remove the semantic calendar
layer entirely. Physical iPhone/Android listening and touch accuracy remain
field acceptance checks.
- Cloud Run revision: `vlens-a-00053-2lb`, 100 percent traffic
- Authenticated `/b/`: `v2026.09.13.3` and contextual sentence helpers present
- New-revision warning/error log query: empty
- Immediate rollback: `vlens-a-00052-rml`

## OCR-grounded dense-page reading

Version `v2026.09.13.8` fixes the incomplete English reading reported on
`A3-22` and the missing main-text selection reported on `A3-24`. Stage 3 now
receives the retained Google/Tesseract line text, stable line IDs, and
coordinates as untrusted reading evidence. For a text-rich page, Terra must
identify the primary text region, translate every readable OCR line inside it,
and return the corresponding line IDs. A result covering less than 80 percent
of that region is not marked quality-valid. The completeness gate applies only
to text-rich pages with at least six readable OCR lines, so a photographed
object with a few label or voltage lines is not incorrectly rejected.

The client merges contextual translations into the complete OCR line queue
instead of replacing the queue with whatever subset the model returned. This
keeps untranslated source rows visible and playable. Continuous word and
sentence reading shows progress, continues past an isolated unavailable audio
segment, and reports completion. The main text region is selectable, paragraph
objects use the best overlapping spoken explanation, and sentence overlays
cover the effective merged queue.

- Google Cloud project: `villagelensai`
- Source commit: `ea438b3`
- GitHub Actions run `34803196058`: passed
- Local unit tests: `67/67` passed
- Python compilation, embedded browser JavaScript parsing, service-worker
  parsing, and `git diff --check`: passed
- Cloud Build: `678acd29-eb92-4d92-b6d8-aaf35c262805`
- Container digest:
  `sha256:8abea4b7fdf5e9afcca72dde9697631b557e4684d510120a9efcc97e4c0df94c`
- Production revision: `vlens-a-00058-8bc`, 100 percent traffic
- Operational limits retained: zero minimum instances, one maximum instance,
  one CPU, 2 GiB memory, concurrency eight, timeout 90 seconds
- Public `/health`: healthy; authenticated `/b/?tester=a3`: version `.8`,
  `terra-ocr-grounded-v4`, and `sol-ocr-review-v4`
- Live `A3-22` stage 3 English result: 21 of 22 primary OCR lines translated
  (95.5 percent), quality validated, both historical paragraphs represented,
  and Chitradurga retained rather than replaced by Ballari
- Live `A3-24` stage 3 English result: 14 of 14 primary OCR lines translated,
  quality validated, correct “To Chitradurga” guidebook identity, and a
  selectable main descriptive text block
- No stage-4/Sol request was made during these checks
- Warning/error log query for the new revision: empty after live verification

Immediate rollback is `vlens-a-00057-dbt`. Physical iPhone/Android listening,
continuous-playback completion, and paragraph touch accuracy remain field
acceptance checks.

## Background-audio recovery and primary-page playback

Version `v2026.09.14.1` addresses the field report that audio disappeared after
VillageLens remained in a background browser tab. Hiding the page now cancels
and resolves any active Web Audio or browser-speech promise instead of leaving
the reading loop suspended indefinitely. On the next touch, an interrupted or
closed audio context is resumed or rebuilt before playback. The interface asks
the user to tap a reading button to continue after returning to the page.

The two lower continuous-reading controls now use the stage-3 `primary_text`
region when it is available. On `A3-22`, this retains 138 words across all 22
lines of the clear left-page historical text and excludes 10 partial lines from
the cropped neighboring right page. If no valid primary region or no content
inside it exists, the controls safely fall back to the full OCR queue.

- Source commit: `661cacb`
- GitHub Actions run `34905220355`: passed
- Tests: `67/67` passed; Python and browser JavaScript parsing passed
- Cloud Build: `81aef4a6-0259-4367-8c8e-2173086f7e51`
- Container digest:
  `sha256:ee658e98c4c79ff5b8bbe1026202086c1f5c099b7376998a785f56e017e12a4f`
- Production revision: `vlens-a-00059-wr6`, 100 percent traffic
- Public `/health`: healthy; authenticated `/b/?tester=a3`: version `.14.1`
  with audio-recovery and primary-reading functions present
- Live `A3-22`: existing `terra-ocr-grounded-v4` result remains quality-valid
  with 21 of 22 primary lines translated; no OCR or LLM regeneration was made
- Warning/error log query for the new revision: empty
- Immediate rollback: `vlens-a-00058-8bc`

Background/foreground recovery and audible completion still require physical
Safari and Chrome acceptance tests because a server-side check cannot reproduce
the phones' operating-system audio suspension behavior.

## Foreground version handshake

The first field response after `.14.1` exposed a separate delivery problem:
Cloud Run received no phone, usage, or speech request after the deployment. The
phone was returning to an already-open page whose JavaScript remained in
memory. `Cache-Control: no-store` guarantees a fresh navigation, but cannot
replace code in a page that never navigates.

Version `v2026.09.14.2` publishes `app_version` from `/health`. Whenever a tab
becomes visible, and whenever Safari restores it from its back/forward cache,
the reader compares its in-memory version with the server and reloads itself on
a mismatch. Usage events now include a sanitized client version and a
foreground event, allowing future diagnostics to prove which code a phone was
actually running without recording OCR or spoken content.

- Source commit: `806a2ed`
- GitHub Actions run `34905940016`: passed
- Tests: `67/67` passed; Python and browser JavaScript parsing passed
- Cloud Build: `df70c4e7-fa2e-49b0-a089-b6697feea306`
- Container digest:
  `sha256:41ed2fd89e569e82a840a9625defd20efffcf07767132fe95a0dbafe4281710b`
- Production revision: `vlens-a-00060-8w6`, 100 percent traffic
- Live `/health`: healthy and reports `app_version: 2026-09-14.2`
- Authenticated `/b/?tester=a3`: version `.14.2`, server-version comparison,
  foreground reload, and client-version telemetry markers present
- Warning/error log query for the new revision: empty
- No OCR or LLM request was made for this delivery correction
- Immediate rollback: `vlens-a-00059-wr6`

## Rapid-selection audio synchronization

Version `v2026.09.15.1` fixes the cross-control race reported while advancing
through A3 captures. Live iPhone speech requests were all successful, usually
in 0.5–0.9 seconds, but included 2–4.4 second outliers. During that wait a new
selection updated the highlight, while the older request could finish later and
fall through to Safari's local voice. Translation requests had an equivalent
stale-response window. This produced the observed one-selection-behind audio
for touch words, touch sentences, and lower reading actions.

The shared reading layer now aborts the previous speech and translation HTTP
requests immediately. Each user selection has an independent generation token,
checked after every asynchronous translation, server-speech, decoding, and
playback boundary. A cancelled server request cannot fall through to browser
speech, and an interrupted object reading cannot continue into its explanation.

- Source commit: `93b6841`
- GitHub Actions run `35044165562`: passed
- Tests: `67/67` passed; regression ordering checks prove that stale-generation
  rejection occurs before browser-voice fallback and before translated speech
- Cloud Build: `c823b4dc-520d-4464-8e44-18445a071560`
- Container digest:
  `sha256:77a57d6ee0170dd1c6ef8d6d5be6d5b97d465fe26d4600ea67241ae40faaa2dd`
- Production revision: `vlens-a-00061-x9m`, 100 percent traffic
- Live `/health`: healthy and reports `app_version: 2026-09-15.1`
- Authenticated `/b/?tester=a3`: request cancellation and both generation guards
  present
- Warning/error query on the new revision: empty
- No OCR or LLM request was made for this playback correction
- Immediate rollback: `vlens-a-00060-8w6`

Rapid consecutive taps still require physical Safari acceptance testing; the
server can verify request timing and cancellation code but cannot hear the
device's final audio output.
