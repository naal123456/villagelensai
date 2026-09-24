# Chinese source reading repair from A3-50 — 2026-09-23

Status: implemented and locally validated; not committed, pushed, or deployed.

## Owner observation

The owner tested `A3-50`, a mixed Chinese/English mooncake package, in the
English-output reader. Contextual inference correctly explained the package,
and the translation interaction was useful. Touch word, touch sentence, read
all words, and read all sentences did not pronounce the Chinese characters and
could announce the selected material as English.

The owner authorized inspection of this private capture for diagnosis. No
photograph, recognized field text, provider payload, credential, or access
header was added to Git. The temporary diagnostic copy was deleted.

## Diagnosis

- Stage-one cloud OCR retained 48 words and 19 lines, including 17 Han-text
  word regions. The problem was therefore not simply missing cloud OCR.
- Stage three was quality-valid, translated all 10 expected primary lines, and
  supplied the useful English contextual explanation.
- The browser script detector and speech segmenter supported Arabic, several
  Indic scripts, and Latin text, but not Han characters.
- English translation routing also omitted Han ranges when deciding that mixed
  text was already English.
- The authenticated speech endpoint had no Chinese language/voice mapping.

## Repair

- Identify basic and compatibility Han characters conservatively as “Chinese /
  Han script.” Script alone is not treated as proof of dialect.
- Identify mixed Han/Latin selections as “Chinese / Han script and English”
  instead of choosing English merely because it contains more Latin letters.
- Segment Han and Latin runs independently so the original Chinese can be
  spoken before the English meaning.
- Route Han source speech to configurable `cmn-CN` Google Cloud speech, using
  the standard `cmn-CN-Standard-A` voice by default.
- Treat mixed Chinese/English input as requiring English translation.
- Keep Tesseract `kan+eng` as the immediate result; Google Vision continues to
  supply broader multilingual OCR when available.

Google Cloud also supports Hong Kong Cantonese (`yue-HK`). The initial generic
route uses Mandarin because Han script alone cannot distinguish a reader's
spoken language. A future tester-specific preference can select Mandarin or
Cantonese after the owner confirms the field tester's preference.

## Validation

- Unit and contract tests: 78/78 passed.
- Added server speech coverage for Traditional Chinese Han text.
- Added a mixed Han/Latin English-translation regression test.
- Added client contract checks for Han detection, mixed-script announcement,
  and the Chinese server-speech route.
- Python compilation: passed.
- Embedded browser JavaScript and service-worker parsing: passed.
- `git diff --check`: passed.

No live speech synthesis, provider call, build, deployment, or other billable
validation was performed.

## Deployment and rollback

The proposed application version is `2026-09-23.1`. If deployment is later
authorized, retain Cloud Run minimum zero, maximum one, and concurrency eight;
then verify A3-50 on physical iPhone Safari, including original Chinese speech,
the English meaning, and mixed-script continuous reading.

Until then, production remains `2026-09-17.2` on `vlens-a-00076-98l`.
Rollback after a future deployment would route traffic to that revision.
