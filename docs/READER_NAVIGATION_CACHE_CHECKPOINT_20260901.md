# Reader navigation and cache checkpoint

Date: 2026-09-01
Status: implemented and locally validated; not deployed

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

Public iPhone Safari validation remains required after an authorized deployment.

## Live diagnosis of the previous revision

A read-only Cloud Run log check on 2026-09-01 confirmed that the observed 429s
were platform capacity rejections (`no available instance`), not provider quota
responses. Rapid saved-page navigation had filled the single-instance service
with duplicate reads. I2 stage 2 returned 200 after 55.4 seconds and I1 stage 2
returned 200 after 74.4 seconds; stage 3 returned 503 because
`OPENAI_API_KEY` is still not configured. These findings motivated network-free
saved navigation and the stage 3 fast-fail path.

## Deployment and rollback

No Cloud Run configuration or traffic was changed by this checkpoint. Existing
limits remain minimum zero, maximum one, and concurrency four. Deploy through
the existing controlled workflow after owner authorization. Roll back by routing
traffic to revision `vlens-a-6c6e2f4`; stored captures and reader evidence are
not deleted by that rollback.

On 2026-09-01 the Secret Manager resource `villagelens-openai-api-key` was
created and the runtime service account received secret-accessor permission.
After explicit owner authorization, version 1 was transferred directly from the
existing `agentic-ai-lens/.env` file without printing or copying it into this
repository. A non-generating OpenAI `/v1/models` request returned HTTP 200. The
secret is not yet mapped to Cloud Run because doing that before the navigation
fix deployment would activate paid calls from the old duplicate-request client.
