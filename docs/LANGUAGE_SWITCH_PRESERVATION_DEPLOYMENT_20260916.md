# Language-switch preservation deployment — 2026-09-16

Status: deployed and publicly HTTP-validated; physical Safari/Chrome language
switch and Malayalam audio confirmation pending.

## Outcome

- Changing between English and Kannada retains the selected capture ID in both
  browser history and short-lived session state. The selected image is displayed
  immediately with a localized processing message while the gallery and the
  target-language interpretation load; the home screen is no longer shown as a
  temporary fallback.
- If the exact capture ID is not found, its stable capture code is used as a
  fallback. If neither is available, the interface reports the restoration
  failure instead of silently appearing to discard the image.
- Stage-one OCR text, line boxes, and positions are now language-neutral and
  shared between English and Kannada. Older English-specific OCR remains
  readable for compatibility. Language-specific meanings remain separately
  cached, so each target language is prepared only once.
- Touching text now displays and speaks its detected script language before the
  source and target-language meaning. Supported labels are Kannada, Tamil,
  Telugu, Malayalam, English, and the deliberately cautious `Hindi / Devanagari`
  label because Hindi and several other languages share that script.
- During continuous reading, the language is announced only when it changes.
  The visible label remains on every selected item.
- Malayalam script segmentation and `ml-IN` speech were added. The selected
  Malayalam voice is listed by Google Cloud Text-to-Speech:
  https://docs.cloud.google.com/text-to-speech/docs/list-voices-and-types

## A3-36 evidence

- Capture code: `A3-36`
- Internal capture identity: verified in production but intentionally not
  included in this deployment record.
- Scene label: product packet
- The capture has completed stages one through three in English. The reported
  failure was the language-navigation transition, not loss of the retained
  photograph.
- Public validation used the existing retained capture URL in both English and
  Kannada modes. It did not upload an image, rerun a reader, synthesize speech,
  or invoke a paid inference model.

## Verification

- Application version: `2026-09-16.4`
- Source commit: `693a241`
- Cloud Build: `b8c1c37d-dd09-448e-81d2-10157788667c`
- Container digest:
  `sha256:c2c0e27de01151f5cd417cd384dfd1fa22071a7bd46410418205e773d4d332ce`
- Cloud Run revision: `vlens-a-00070-zdk`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight
- Unit tests: `70/70` passed
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-16.4`, zero missing OCR models
- Authenticated A3-36 English and Kannada pages: HTTP 200 and contain the capture
  restoration, shared-OCR, language-label, and Malayalam logic
- Error-level logs for the new revision after validation: empty

## Physical-phone check

1. Open A3-36 in English and switch to Kannada. Confirm A3-36 remains visible
   immediately and the home screen does not replace it.
2. Switch back to English. Confirm the same capture remains selected.
3. Touch one Tamil region and one Malayalam region. Confirm the language name is
   shown and spoken before the source text and selected-language meaning.
4. Read several adjacent words in one language. Confirm the language name is not
   repeated for every word, but is announced when reading moves to another
   script.
5. Confirm the first OCR bar returns without a duplicate OCR wait after changing
   languages. A target-language inference that has never been prepared may still
   run once; subsequent visits use its language-specific cache.

## Rollback

Route traffic back to `vlens-a-00069-z7s`. That revision has the resizable
camera frame but can show the home screen while a language-switch gallery reload
is in progress, uses separate stage-one OCR evidence, and has no Malayalam
language identification or server speech support.
