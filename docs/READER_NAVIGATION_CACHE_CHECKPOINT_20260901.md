# Reader navigation and cache checkpoint

Date: 2026-09-01
Status: deployed and HTTP-validated

## Product result

- Gallery selection changes immediately and asynchronous results from an older
  selection cannot repaint the newly selected page.
- The previous image dims until the selected image has loaded, making slow
  connections visible instead of leaving an apparently unchanged page.
- Saved-page navigation issues no cloud-reader requests. Successful stage 2 and
  stage 3 readings from a new photograph are cached on the device. Stored
  captures also return their durable cloud evidence from the authenticated
  gallery, so revisiting them restores the best available reading without a
  provider request.
- Failed provider calls show a failed bar and use a five-minute device cooldown
  to avoid a rate-limit retry loop.
- An unconfigured stage 3 now fails before expensive image preparation, and
  temporary PNG preparation no longer spends CPU on compression optimization.
- The quality strip now has four bars: local reading, Google document OCR,
  current vision-language reading, and future validated multi-reader consensus.

## Validation

- Focused Python suite: 13/13 passed.
- Embedded browser JavaScript syntax: passed with `node --check`.
- Python module compilation and `git diff --check`: passed.

Public iPhone Safari camera and Kannada audio validation remains required.

## Live diagnosis of the previous revision

A read-only Cloud Run log check on 2026-09-01 confirmed that the observed 429s
were platform capacity rejections (`no available instance`), not provider quota
responses. Rapid saved-page navigation had filled the single-instance service
with duplicate reads. I2 stage 2 returned 200 after 55.4 seconds and I1 stage 2
returned 200 after 74.4 seconds; stage 3 returned 503 because
`OPENAI_API_KEY` is still not configured. These findings motivated network-free
saved navigation and the stage 3 fast-fail path.

## Deployment evidence

- Source commit: `45b3f50`.
- Cloud Build: `7321acbc-fa82-48e6-9234-ee24a5c94627` (`SUCCESS`).
- Container digest:
  `sha256:497d8e7e3a05d9e3c03f9fe5160073fee089a248f3a47b42b495b6ec2b7eb421`.
- Cloud Run revision: `vlens-a-45b3f50`, 100 percent traffic.
- Limits: minimum zero, maximum one, 1 CPU, 2 GiB, concurrency four, and a
  90-second request timeout. This corrected the previous live maximum of 20.
- Authenticated public checks: access POST 303, `/a/` 200, gallery 200 with I2
  then I1, and all four quality controls present.
- Live I2 stage 2: HTTP 200, 11 words, 6 lines, 1,107 ms provider latency and
  10.43 seconds total including cold start, transfer, and preparation.
- Live I2 stage 3: HTTP 200, Kannada summary present, 9,919 ms provider latency
  and 18.63 seconds total. It returned no validated word boxes, so the client
  correctly retained I2's reviewed gold geometry; this proves connectivity and
  meaning availability, not OCR accuracy.

## Rollback

Route traffic to revision `vlens-a-6c6e2f4`. That revision does not map the
OpenAI secret. Stored captures, cached reader evidence, and Secret Manager
versions are not deleted by rollback.

On 2026-09-01 the Secret Manager resource `villagelens-openai-api-key` was
created and the runtime service account received secret-accessor permission.
After explicit owner authorization, version 1 was transferred directly from the
existing `agentic-ai-lens/.env` file without printing or copying it into this
repository. A non-generating OpenAI `/v1/models` request returned HTTP 200.
Revision `vlens-a-45b3f50` maps this immutable secret version to
`OPENAI_API_KEY`.
