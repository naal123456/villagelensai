# Cost-controlled four-stage reader deployment — 2026-09-13

## Intended outcome

Version `v2026.09.13.1` replaces the former Sol/Sol/Astra reader arrangement
with the first cost-controlled model cascade:

| Stage | Model | Processing | Invocation |
|---|---|---|---|
| 1 | Tesseract `kan+eng` plus Google document OCR | local plus cloud OCR | automatic |
| 2 | `gpt-5.6-luna` | Standard | automatic, compact contract |
| 3 | `gpt-5.6-terra` | Standard | automatic, full teaching contract |
| 4 | `gpt-5.6-sol` | Standard | manual tap only, reviews Terra |

Astra is not used. Loading or navigating to an image cannot invoke stage 4.
The fourth bar remains visible so a user can deliberately request the strongest
reading after stage 3 finishes.

## Cache boundary

Old browser entries use the `villagelens.reader.v1` namespace. This release uses
`villagelens.reader.v2` and validates these server evidence versions:

- `luna-compact-v1`
- `terra-context-v1`
- `sol-review-v1`

Old Sol stage-2/stage-3 evidence and Astra stage-4 evidence are not accepted as
current results. They are replaced at the same private stage object name when
that stage is successfully reprocessed. Each new model/language/stage result is
then reused after its first successful run.

## Cost behavior

- No Fast/Priority tier is requested by stages 2–4.
- Stage 4 has no automatic call path.
- Existing per-stage locks and five-minute failure cooldowns remain active.
- Kannada and English evidence remain separately stored and cached.
- The spoken-question endpoint uses Terra Standard rather than Sol.

## Verification to record after deployment

- source commit and Cloud Build ID;
- container digest and Cloud Run revision;
- unit, Python, embedded-JavaScript, and service-worker checks;
- `/health` model IDs and manual stage-4 state;
- authenticated `/a/` and `/b/` version and four-bar visibility;
- evidence that stages 2 and 3 return Luna/Terra Standard; and
- evidence that stage 4 remains absent until explicitly requested.
