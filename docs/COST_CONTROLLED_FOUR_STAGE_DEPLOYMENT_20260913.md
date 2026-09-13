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

## Verification

- Deployable source commit: `48fd584`
- Cloud Build: `5c6ee013-417e-4e60-9480-3b499ff9cd16`
- Container digest:
  `sha256:4c9f5061c160766da948cb614671a8dce8194a12f506c4f8746d4221b9d011ed`
- Cloud Run revision: `vlens-a-00051-xqs`, 100 percent traffic
- Unit tests: `62/62` passed
- Python compilation, embedded browser JavaScript parsing, service-worker
  parsing, and `git diff --check`: passed
- Minimal live access checks: Luna and Terra each returned HTTP 200 through the
  deployed project key on Standard processing, using 14 tokens each
- Public authenticated `/health`: status `ok`, no missing OCR models, exact
  Luna/Terra/Sol model IDs, stage 4 `manual`
- Authenticated `/a/` and `/b/`: version `v2026.09.13.1`, fourth bar visible,
  all three new analysis-version markers present
- New revision warning/error log query: empty after startup and page checks

The deployment verification deliberately did not submit a production image to
Luna, Terra, or Sol. Field-image behavior remains the reviewer test described
below.

## Reviewer test

Open `/b/?tester=a3`, select a known retained image, and allow bars 1–3 to
complete. Confirm that the output is English. The fourth bar should remain
outlined until tapped; tap it once to request the Sol review and confirm that it
turns dark green when the response is validated.

## Rollback

Route traffic back to `vlens-a-00050-b5l`. That revision has Astra disabled and
uses the previous Sol/Sol Fast architecture for stages 2 and 3.
