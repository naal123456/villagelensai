# Parallel readers deployment checkpoint

Date: 2026-08-30
Status: Google Vision active; OpenAI adapter deployed but credential-blocked

## Deployed behavior

- Tesseract, Google Vision, and OpenAI requests start independently.
- The elapsed clock runs until both cloud requests finish or fail.
- Yellow, light green, and dark green represent stages 1, 2, and 3.
- Provider names remain absent from the tester interface.
- The word control uses Kannada `ಅ`; the sentence control uses `ಅ ಆ ಇ`.
- Validated OpenAI normalized word boxes are converted to page coordinates and
  grouped into sentence lines. I2 keeps its reviewer-approved gold geometry.

## Evidence

- Source commit: `6c6e2f48573000721bd8f979576b49f0ff2107fe`
- Cloud Build: `ee1a5176-3e33-4211-8e2c-599eb40721a1` (`SUCCESS`)
- Container digest: `sha256:58629699f1606bfc1756486ffc6677ad09b87b4724d9ba8d9f98e9099750cffa`
- Cloud Run revision: `vlens-a-6c6e2f4`, 100 percent traffic
- Concurrency: 4, allowing the three reader requests to overlap on the single
  controlled POC instance
- Focused tests: 11/11 passed
- JavaScript and Python syntax checks: passed
- Live Google I2 call: stage 2, 11 words, 6 line groups, 1,331 ms provider latency
- Live OpenAI call: correctly returned `OPENAI_READER_NOT_CONFIGURED`

The Google Vision API is enabled in project `villagelensai`. No project-specific
OpenAI secret existed at deployment time. An unrelated key discovered in a
different repository was deliberately not read, copied, or reused. Stage 3 will
remain gray until the owner installs the intended API key in Secret Manager and
maps it to the Cloud Run environment variable `OPENAI_API_KEY`.

## Rollback

Route traffic to `vlens-a-ffb6318` to restore the Tesseract-only swipe gallery,
or `vlens-a-code2` to restore the earlier minimal shell. Retained captures are
not deleted by either rollback.
