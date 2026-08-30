# VillageLensAI

VillageLensAI is a phone-oriented guided-reading proof of concept for Kannada and
English text in book pages, signs, billboards, and phone screens.

Status: stage-one Tesseract API implemented and locally tested; Cloud Run build
and deployment pending.

## Intended experience

A helper installs one Home Screen icon. The tester taps it, captures a still
photograph, and can touch or continuously play recognized words, sentences, and
Kannada explanations. Processing improves in the background without exposing
OCR engines or model names.

## Quality stages

1. Yellow: repository-local Tesseract `kan+eng` is ready.
2. Light green: fast OpenAI whole-image refinement is accepted.
3. Green: careful OpenAI whole-image refinement is accepted.
4. Dark green: deterministic multi-reader consensus is accepted.

The colors are processing/evidence stages, not calibrated accuracy percentages.

## Repository layout

```text
web/                  static HTML, CSS, JavaScript, and PWA assets
api/                  Cloud Run API and recognition orchestration
infra/                Google Cloud deployment configuration
tests/                unit, contract, OCR fixture, and browser tests
docs/                 architecture, operations, and evaluation records
.github/workflows/    tests and controlled deployments
```

The tester route is `web/a/index.html`, ultimately published as
`https://<project-domain>/a`.

See [the Google Cloud POC architecture](docs/GOOGLE_CLOUD_POC.md).

## Current boundary

The `/a` client invokes a phone camera, sends one bounded still image to the
same-origin API, and renders the returned word geometry as touchable underlines.
Only the genuine Tesseract yellow stage is enabled. The API is stateless and
reports that it did not retain the source image. OpenAI, Google Vision, feedback
persistence, device enrollment, and the remaining quality stages are still
disabled.
