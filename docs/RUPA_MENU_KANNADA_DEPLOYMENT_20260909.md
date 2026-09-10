# Rupa menu Kannada deployment — 2026-09-09

## Scope

- Capture: `A3-FAC3BC` / `fac3bcfd6b5d43d79fa1652e10159b95`
- Sample registry: `HW-0003`
- Owner-verified region readings:
  - item 1: `ಪುಳಿಯೋಗರೆ`
  - item 2: `ಕಡಲೆಕಾಯಿ`
  - item 3: `ಶಾವಿಗೆ`
  - item 7: `ಒಳಿಗೆ`
- These four regions replace uncertain OCR during touch, sentence, and continuous
  reading. Unverified handwriting remains unchanged.
- Common Latin spellings of Kannada menu terms are normalized to Kannada script
  before speech synthesis so they do not use an English voice.

## Verification

- Source commit: `aff4cc2`
- Container digest:
  `sha256:2542d83374365a8559ad61b16659de64393d4fc5f479ff00b9a8ee210e71138e`
- Tests: `46/46` passed
- Static checks: Python compile, embedded JavaScript parse, JSON parse, and
  `git diff --check` passed.
- Live gallery response for A3 returned four verified regions with the expected
  Kannada strings.
- Live `/api/speech` returned a valid 7.992-second MP3 for the four corrected
  readings in one utterance.
- Physical-phone pronunciation remains to be confirmed by the tester.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00036-d6q`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00035-bdx`

An identical 0%-traffic revision was also created on the older `asia-south1`
service during the pre-traffic region check. It is not part of the production
route and has min instances 0.
