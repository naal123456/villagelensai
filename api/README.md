# API

The initial Cloud Run API exposes:

- `GET /healthz` for pinned-model readiness;
- `GET /a/` for the tester camera client;
- `POST /api/capture` for bounded JPEG, PNG, or WebP input and stage-one
  repository-local Tesseract `kan+eng` geometry.

It is stateless and does not retain uploaded bytes. OpenAI, Google Vision,
feedback persistence, and device enrollment are not enabled in this slice.
