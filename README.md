# VillageLensAI

VillageLensAI is a phone-oriented guided-reading proof of concept for Kannada and
English text in book pages, signs, billboards, and phone screens.

Status: access-gated stage-one Tesseract API live at
`https://villagelensai.com`.

## Intended experience

A helper installs one Home Screen icon. The tester taps it, captures a still
photograph, and can touch or continuously play recognized words, sentences, and
Kannada explanations. Processing improves in the background without exposing
OCR engines or model names.

## Quality indicators

1. Yellow: repository-local Tesseract `kan+eng` is ready.
2. Light green: Google Vision document OCR is ready.
3. Green: the current vision-language reading is ready.
4. Dark green: a future validated consensus across high-quality readers is ready.

The phone strip displays all four stages. The fourth remains gray until the
multi-reader consensus work is implemented and validated.

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

The tester route is `web/a/index.html`, published at
`https://villagelensai.com/a/` after access-code entry.

See [the Google Cloud POC architecture](docs/GOOGLE_CLOUD_POC.md).

## Current boundary

The `/a` client opens with I2, makes I1 available by swiping, invokes a phone
camera, sends one bounded still image to the same-origin API, and renders the
returned word geometry as touchable underlines. Captures and their stage-one
results are retained in the private `villagelensai-captures` Cloud Storage
bucket and returned in the authenticated gallery, newest first after I2 and I1.
For a new photograph, the browser completes the bounded Tesseract reading first,
then starts Google Vision document OCR and the OpenAI image reader concurrently.
Saved-page navigation makes no new cloud-reader requests. Yellow appears for
Tesseract, light green for Vision, and
green for the current OpenAI reader; dark green remains reserved for validated
multi-reader consensus. The elapsed clock runs until enabled readers finish or
fail. Successful results are reused for saved images, while recent failures use
a short cooldown to avoid repeated paid calls. The OpenAI stage remains gray
when its server-side API secret is not configured. Feedback persistence and
feedback persistence remain future work. Anonymous tester enrollment uses a
dedicated `?tester=a1`-style link; the choice persists on that phone and filters
its saved gallery so test cohorts are not mixed.

The deployed tester page and capture API are protected by a server-side access
code. The code and cookie-signing secret live in Google Secret Manager and are
never sent to GitHub or embedded in browser JavaScript.

The main domain opens an enrollment form with exactly two fields: an anonymous
user selector (`A1` through `A10`) and the shared access code. A successful entry
redirects to that user's reader URL and persists the cohort on the phone.
