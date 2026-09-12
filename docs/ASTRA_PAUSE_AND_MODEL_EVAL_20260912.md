# Astra pause and model-evaluation checkpoint — 2026-09-12

## Outcome

Version `v2026.09.12.1` prevents new Astra stage-four calls while model quality,
latency, and cost are evaluated separately.

- The phone requests only stages 1–3 and displays three quality bars.
- The timer completes against stage 3 rather than waiting for an unavailable
  fourth review.
- The stored-capture orchestrator does not schedule stage 4.
- A direct stage-four endpoint request returns `409 READER_DISABLED` before
  loading an image or calling a provider.
- `/health` reports `"astra_reader":"disabled"`.
- Existing private images and cached evidence were not deleted or rewritten.

The general switch is `VILLAGELENS_ASTRA_ENABLED`; its safe default is false.
The current browser also fixes the enabled stage set to 1–3. Re-enabling Astra
therefore requires a reviewed application release as well as an intentional
server configuration change.

## Separate evaluation project

The sibling workspace project `villagelens-model-eval` contains an offline-first
benchmark specification, field-image manifest examples, a blinded review rubric,
a current candidate matrix, and a cost/latency/quality scoring tool. It makes no
provider requests and excludes API keys, raw photographs, and results from
source control.

Initial candidates are:

- `gpt-5.6-sol` as the current quality control;
- `gpt-5.4-mini` as the primary OpenAI cost candidate;
- `gpt-5.4-nano` as a low-cost screening candidate;
- `gpt-5.5` only as a quality counterfactual because its published token prices
  are higher than Sol's;
- Kimi `kimi-k2.6` and `kimi-k3` as multimodal external candidates.

Kimi K2/K2.5 model identifiers are not included because the vendor lists them
as retired. Kimi pricing is intentionally left blank until it is verified for
the applicable account and region.

## Verification

- Source commit: `ff98b06`
- Tests: `61/61` passed
- Python compilation, embedded browser JavaScript parse, service-worker parse,
  evaluation scorer calculation check, and `git diff --check`: passed
- Cloud Build: `6191d8dd-8775-451b-b890-965044983115`
- Container digest:
  `sha256:44babb4b66265ef635c6fdb8d023a94c4f9dd5805d4a855d435676fb31ce37fa`
- Production service: `vlens-a`, `us-central1`
- Production revision: `vlens-a-00050-b5l`, 100 percent traffic
- Public health: status `ok`, access gate enabled, Astra reader disabled, no
  missing local OCR models
- Authenticated public page: version `v2026.09.12.1`, fourth bar hidden, browser
  Astra flag false
- Authenticated direct stage-four request: HTTP 409 `READER_DISABLED`

These checks prove that new Astra inference is disabled. They do not restore the
exhausted OpenAI credit balance, validate Sol output on a phone, or make any
paid benchmark call.

## Rollback

Route traffic to `vlens-a-00049-274` to restore the prior four-stage browser and
Astra orchestration. This rollback would allow new Astra calls again and should
only be used with an explicit cost decision.

