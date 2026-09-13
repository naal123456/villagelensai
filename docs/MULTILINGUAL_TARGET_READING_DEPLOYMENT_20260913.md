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
- Cloud Run revision: `vlens-a-00053-2lb`, 100 percent traffic
- Authenticated `/b/`: `v2026.09.13.3` and contextual sentence helpers present
- New-revision warning/error log query: empty
- Immediate rollback: `vlens-a-00052-rml`
