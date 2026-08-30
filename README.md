# VillageLensAI

VillageLensAI is a phone-oriented guided-reading proof of concept for Kannada and
English text in book pages, signs, billboards, and phone screens.

Status: repository initialized; cloud recognition is not deployed yet.

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

The initial HTML shell can invoke a phone camera and preview a still image. It
does not upload the image or claim recognition. The next step is to promote the
tested Tesseract capture contract from `smart-glasses-phase1`, containerize it,
and reproduce the yellow stage locally before cloud deployment.
