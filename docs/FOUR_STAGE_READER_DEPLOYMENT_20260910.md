# Four-stage reader orchestration deployment — 2026-09-10

## Outcome

Version `v2026.09.10.10` restores the agreed four-stage reading pipeline while
keeping every network stage independent:

1. Repository-local Kannada plus English Tesseract provides the immediate
   reading. Google document OCR strengthens the same first bar as soon as it
   returns.
2. `gpt-5.6-sol` on the Fast service lane provides a deliberately small first
   understanding: identity, purpose, up to three useful details, uncertainty,
   and confidence.
3. `gpt-5.6-sol` on the Fast service lane produces the full contextual reading,
   object regions, translation, teaching explanation, and safety context.
4. `gpt-6-astra` on the Fast service lane independently reviews the image and
   the saved Sol analysis. The fourth bar becomes ready only when the structured
   Astra review explicitly agrees with a validated Sol result. A disagreement
   retains Astra's reviewed explanation but does not claim consensus.

Stages 1–3 begin independently. Stage 4 begins after stage 3 so that it can be
an actual review. Each retained result is reused; reopening an image or pressing
inference again does not call the provider again. Failed network stages receive
a five-minute server-side cooldown in addition to the browser cooldown.

Stored images are forwarded to readers as quality-88 JPEG rather than expanded
PNG. A real retry resets the visible timer instead of inheriting the age of the
original capture. A failed upload is marked `NOT SAVED` and does not permanently
advance the phone's tentative sequential label.

Legacy Google evidence formerly stored as stage 2 is recognized as first-stage
OCR and migrated before the new Sol first-pass evidence uses stage 2.

## Reported capture diagnosis

- `A3-21` and `A3-22` were retained and had acceptable sharpness and motion
  measurements. Their Google OCR provider latency was 330 ms and 364 ms.
- The former combined processing route waited for both Google OCR and Sol. This
  hid the completed OCR response until Sol returned or reached its 75-second
  client timeout, which caused bars 2 and 3 to appear together.
- Repeated inference presses retried missing evidence and competed for the
  eight threads on the single controlled Cloud Run instance. The browser timer
  also reused the original capture start time, explaining jumps above 120 and
  190 seconds.
- There was no retained `A3-31` at diagnosis time. It was a phone-local label
  for an attempt that did not reach retained storage; retained A3 numbering had
  reached 28. Failed attempts are now visibly marked and the latest tentative
  sequence is reclaimed.

## Production measurements

Controlled authenticated tests used stored A3 captures and made only one new
provider request per tested stage.

- `A3-22`, stage 1 cached Google OCR: 154 words; endpoint returned in under
  0.5 seconds.
- Initial full-schema Sol Fast experiment: 45.6 seconds provider latency. This
  was rejected as an instant contract.
- `A3-22`, lightweight Sol Fast stage 2: 8.0 seconds provider latency and 10.4
  seconds end to end; structured Kannada validation passed.
- `A3-22`, full Sol stage 3: 52.4 seconds provider latency and 53.1 seconds end
  to end; structured Kannada validation passed.
- Standard-tier Astra experiments on `A3-21` and `A3-22` reached the 75-second
  bound. Astra Fast on `A3-21` completed in 58.8 seconds. It reported a material
  disagreement with Sol, so consensus correctly remained false.
- Cached stage 2, stage 3, and stage 4 endpoint checks returned in 0.68, 0.50,
  and 0.51 seconds without new provider work.

These results validate orchestration and model access, not the semantic
correctness of private photograph content.

## Verification

- Source commit: `6e97e8c` (including orchestration commits `ebd4314`,
  `56aadfa`, and `b8059c7`).
- Tests: `53/53` passed.
- Python compilation, embedded index JavaScript parse, service-worker
  JavaScript parse, and `git diff --check`: passed.
- Cloud Build: `9cacae60-5211-445f-839b-5ba0d68c89a4` succeeded.
- Container digest:
  `sha256:1e6e657d339fcb34f58642c09c7eb0b0fe6eb39ed74868e24382d6ca943f3d92`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated production page contains version `v2026.09.10.10`, four bars,
  `instant-v2`, and `astra-review-v2`.
- This does not replace physical testing on iPhone Safari and the target Android
  phones with Kannada audio.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00047-sdz`
- Traffic: 100%
- Limits: minimum instances zero, maximum instances one, 1 CPU, 2 GiB,
  concurrency 8, timeout 90 seconds
- Immediate rollback revision: `vlens-a-00046-gvj`
- Last pre-four-stage rollback revision: `vlens-a-00044-lpx`
