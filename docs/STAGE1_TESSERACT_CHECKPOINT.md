# Stage 1 Tesseract cloud checkpoint

Date: 2026-08-30
Status: local and deployed real-HTTP validation passed

## Scope

This checkpoint implements only the first yellow quality stage:

- stateless JPEG, PNG, or WebP upload;
- EXIF orientation normalization and bounded image dimensions;
- repository-local Tesseract `kan+eng` execution;
- word and line geometry with a 32-region UI cap;
- thin, touchable word underlines and browser `kn-IN`/`en-IN` speech;
- no source-image retention;
- no OpenAI, Google Vision, Firestore, device enrollment, or custom-domain DNS.

## Automated validation

```text
.venv/bin/python -m unittest discover -s tests -v
Ran 4 tests
OK
```

The tests cover the tester route, pinned-model health, invalid media rejection,
stage-one geometry, no-retention reporting, and `no-store` API responses.

## Real fixture validation

The Gunicorn Cloud Run entrypoint was started at `127.0.0.1:8080`. Health and
tester routes returned HTTP 200. A real HTTP `POST /api/capture` used the
existing I2 iPhone fixture and returned:

```json
{
  "schema": "villagelens.capture.v1",
  "stage": 1,
  "stage_state": "initial_reading",
  "image_size": {"width": 3024, "height": 4032},
  "word_count": 51,
  "line_count": 32,
  "latency_ms": 7576,
  "retained": false
}
```

This proves transport, model loading, OCR execution, TSV parsing, region
selection, and response formation. It is not an accuracy score; I2 remains a
mixed illustration/stylized-title case and the returned text contains errors.

## Deployed validation

- Runtime source commit: `5993036`.
- Cloud Build ID: `6be298bf-98fe-4164-960b-ae3525e8d491` (`SUCCESS`).
- Image digest:
  `sha256:acd8fca39b6ff76bf38c130cd7a4188357ce4b183a1a4f6db25899df9fd046a9`.
- Cloud Run service: `vlens-a`, region `us-central1`, revision
  `vlens-a-00002-8pl`.
- Temporary tester URL:
  `https://vlens-a-816984866085.us-central1.run.app/a/`.
- `GET /a/`: HTTP 200; `GET /`: HTTP 302 to `/a/`.
- Public I2 `POST /api/capture`: HTTP 200 in 69.9 seconds from a cold,
  one-CPU instance; 47 selected words, 32 lines, and `retained: false`.

The deployed result proves the public still-photo path. It is not a recognition
accuracy result. The cold full-resolution latency is a measured optimization
target.

Cloud Run currently intercepts paths ending in `z` in some projects, including
`/healthz`, with a Google-front-end 404 before the container. `/health` is the
canonical readiness endpoint; `/healthz` remains only a local compatibility
alias.

## Runtime boundaries

- Google project: `villagelensai`, billing active.
- Current temporary region: `us-central1`; intended later region:
  `asia-south1` (Mumbai).
- Minimum instances: `0`; maximum instances: `1`.
- Pinned Kannada model SHA-256:
  `bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8`.
- Pinned English model SHA-256:
  `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
- `villagelensai.com` is delegated to Cloudflare, with application records
  intentionally unset pending temporary-URL validation.

The local Docker daemon was not running, so Google Cloud Build performed and
passed the container build. The deployment references the immutable digest
above and uses one CPU, 2 GiB memory, concurrency `1`, a 90-second timeout,
minimum instances `0`, and maximum instances `1`.
