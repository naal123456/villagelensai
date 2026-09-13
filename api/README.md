# API

The initial Cloud Run API exposes:

- `GET|POST /access` for the server-side tester access-code gate;
- `GET /health` for pinned-model readiness (`/healthz` remains a local alias,
  but Cloud Run reserves paths ending in `z`);
- `GET /a/` for the tester camera client;
- `GET /api/gallery` for I2, I1, and retained test captures;
- `GET /api/captures/<id>/image` for authenticated private capture retrieval;
- `POST /api/capture` for bounded JPEG, PNG, or WebP input and stage-one
  repository-local Tesseract `kan+eng` geometry and optional durable retention.
- `POST /api/read/1` for Google Vision document OCR geometry;
- `POST /api/read/2` for compact Luna whole-image understanding;
- `POST /api/read/3` for a structured Terra reading and Kannada or English
  page explanation;
- `POST /api/captures/<id>/process/4` for a manually requested Sol review of
  the retained image and its Terra result.

When `VILLAGELENS_CAPTURE_BUCKET` is set, source images and structured results
are stored privately under `captures/<id>/`; without it, capture still succeeds
but returns `retained: false`. When
`VILLAGELENS_ACCESS_CODE` and `VILLAGELENS_SESSION_SECRET` are supplied, all
tester and capture routes require a signed, HttpOnly, Secure cookie. Supplying
only one access secret fails readiness and fails closed. The OpenAI adapter
requires `OPENAI_API_KEY` only on the server. Stage models default to
`gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`; each can be pinned through
its corresponding `VILLAGELENS_OPENAI_STAGE_*_MODEL` environment variable.
