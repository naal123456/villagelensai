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

1. Yellow changing to light green: repository-local Tesseract `kan+eng`, then
   Google Vision document OCR, is ready.
2. Light green: a compact Luna understanding is ready.
3. Green: the full contextual Terra reading is ready.
4. Dark green: an optional strongest Sol review, requested by tapping the bar.

Stages 1–3 run automatically. Stage 4 never runs automatically and therefore
cannot spend Sol credits until the user explicitly requests it. All three model
stages use Standard processing; Astra is not part of this reader pipeline.

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

An isolated English-output experiment is served at `/b/?tester=a3`. It reuses
the reviewer gallery and reading pipeline but stores browser and cloud evidence
separately from the Kannada-first `/a/` experience.

See [the Google Cloud POC architecture](docs/GOOGLE_CLOUD_POC.md).

## Current boundary

The `/a` client opens with I2, makes I1 available by swiping, invokes a phone
camera, sends one bounded still image to the same-origin API, and renders the
returned word geometry as touchable underlines. Captures and their stage-one
results are retained in the private `villagelensai-captures` Cloud Storage
bucket and returned in the authenticated gallery, newest first after I2 and I1.
For a new photograph, the browser completes the bounded Tesseract reading first,
then sends one small keep-alive request. The server reloads the private stored
image and starts Google Vision document OCR and the OpenAI image reader
concurrently, so the phone does not upload the photograph two more times.
Saved-page navigation reuses complete server evidence without new provider
requests. The elapsed clock runs until the three automatic stages finish or
fail, and runs again when an optional stage-four review is requested. An
incomplete saved image can resume through the same idempotent server endpoint,
while recent failures use a short cooldown to avoid repeated paid calls. An
OpenAI stage remains gray when its server-side API secret is not configured or
funded. Feedback persistence and
Anonymous tester enrollment uses a
dedicated `?tester=a1`-style link; the choice persists on that phone and filters
its saved gallery so test cohorts are not mixed.

The deployed tester page and capture API are protected by a server-side access
code. The code and cookie-signing secret live in Google Secret Manager and are
never sent to GitHub or embedded in browser JavaScript.

The main domain opens an enrollment form with exactly two fields: an anonymous
user selector (`A1` through `A10`) and the shared access code. A successful entry
redirects to that user's reader URL and persists the cohort on the phone.
For field testers who cannot enter the Latin-script code, an owner can provide a
per-tester signed WhatsApp link. Its credential stays in the URL fragment, is
exchanged through a non-logged request body, and is removed from the address bar
before the assigned reader opens.

Kannada segments use authenticated server-generated `kn-IN` audio, so a tester
does not need to install a Kannada voice or change phone settings. Unique audio
segments are cached in the page and under hashed private Cloud Storage object
names; repeated taps do not repeatedly invoke synthesis. English segments keep
using the phone's existing system voice.
