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
