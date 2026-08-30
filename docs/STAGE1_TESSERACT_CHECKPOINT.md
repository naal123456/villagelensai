# Stage 1 Tesseract cloud checkpoint

Date: 2026-08-30
Status: local API and real HTTP validation passed; remote container build pending

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

## Runtime boundaries

- Google project: `villagelensai`, billing active.
- Intended region: `asia-south1` (Mumbai).
- Minimum instances: `0`; maximum instances: `1`.
- Pinned Kannada model SHA-256:
  `bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8`.
- Pinned English model SHA-256:
  `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
- `villagelensai.com` is delegated to Cloudflare, with application records
  intentionally unset pending temporary-URL validation.

The local Docker daemon was not running, so the same Dockerfile will be built
and validated through Google Cloud Build. Deployment must reference the commit
containing this checkpoint and retain the limits above.
