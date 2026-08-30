# API

The initial Cloud Run API exposes:

- `GET|POST /access` for the server-side tester access-code gate;
- `GET /health` for pinned-model readiness (`/healthz` remains a local alias,
  but Cloud Run reserves paths ending in `z`);
- `GET /a/` for the tester camera client;
- `POST /api/capture` for bounded JPEG, PNG, or WebP input and stage-one
  repository-local Tesseract `kan+eng` geometry.

It is stateless and does not retain uploaded bytes. When
`VILLAGELENS_ACCESS_CODE` and `VILLAGELENS_SESSION_SECRET` are supplied, all
tester and capture routes require a signed, HttpOnly, Secure cookie. Supplying
only one secret fails readiness and fails closed. OpenAI, Google Vision,
feedback persistence, and device enrollment are not enabled in this slice.
