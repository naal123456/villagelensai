# Object inference and clear controls deployment

Date: 2026-09-08
Status: deployed and publicly validated; physical-phone interaction checks pending

## Outcome

VillageLens now presents three active reading stages: immediate repository-local
Tesseract, Google document OCR, and contextual Sol inference. The fourth stage
and its bar were removed from the tester path at the owner's direction after
repeated Gemini availability and access failures. The Gemini key remains in
Secret Manager but is not mapped into Cloud Run, and no client or server request
path invokes it.

The controls now have distinct, non-overlapping purposes:

- top 1 selects and speaks a word;
- top 2 selects and speaks a sentence or a Sol-transcribed handwriting line;
- top 3 is explicitly English-to-Kannada (`EN→ಕ`); a Kannada word is simply
  spoken in Kannada, and a missing translation never falls back to inference;
- top 4 opens the camera;
- bottom 1 continuously reads words;
- bottom 2 continuously reads sentences;
- bottom 3 selects a visible object and explains that object in Kannada; and
- bottom 4 is the only whole-image inference control.

Selected modes have a strong yellow outline. Running playback, inference, and
spoken-question actions pulse blue independently, so a selected top mode and a
running bottom action are both visible. Word, sentence, object, handwriting,
question-answer, and inference evidence regions are highlighted while spoken.

Joined ratings are grouped for both tap and continuous word reading. Examples
include `150 / 300V`, `2.0 HP`, `50Hz`, amps, watts, kilograms, millilitres, and
degrees Celsius. The printed value is preserved while the unit is spoken in
Kannada.

## Contextual inference

Sol `context-v2` adds:

- useful object identity, purpose, and image-region boxes;
- Kannada handwriting transcription by line, with uncertainty and line boxes;
- evidence-linked spoken sections for the global inference;
- explicit confidence and independent-review flags;
- focused handling of numbers and units; and
- capture guidance that distinguishes blur, distance, perspective, cropping,
  low contrast, and difficult handwriting.

The stage-three request uses `gpt-5.6-sol`, image input, no extra reasoning
effort, low verbosity, `store: false`, and a strict structured-output schema.
Implementation follows the official OpenAI model and Responses documentation:

- https://developers.openai.com/api/docs/models/gpt-5.6-sol
- https://developers.openai.com/api/reference/cli/resources/responses/methods/create

Saved `context-v2` results are reused on navigation. Older saved images upgrade
once when opened or explicitly processed, then reuse the server evidence and
phone cache instead of calling Sol again.

## Spoken questions, installation, and telemetry

A large microphone control lets a supported browser capture a Kannada spoken
question about the current saved image. The transcript is sent directly to a
Sol image-question endpoint, is not stored by VillageLens, and the answer's
most relevant region is highlighted while the Kannada answer plays. Unsupported
browsers and unsaved demo images fail explicitly.

The home-screen control is now always visible outside standalone mode. Android
uses the native install prompt when available and otherwise shows Chrome's
Add-to-home-screen instruction. iPhone shows the Safari Share / Add to Home
Screen instruction. The existing Android Web Share Target remains available
after installation; physical Android and iPhone checks are still required.

Privacy-safe telemetry records only tester ID, capture ID, an allow-listed
action name, success, and elapsed milliseconds. It never accepts OCR text,
inference text, spoken-question text, audio, or image bytes. This supports
separate A1/A2/A3 field diagnosis, including Kannada-audio failures.

## Field-image qualification

The selected images were upgraded separately under their existing owners.

### A1 Eeregowda: close Kannada handwriting image

- Google returned 81 word boxes but rendered most Kannada handwriting as Telugu.
- Sol correctly classified it as a Kannada handwritten question-and-answer page
  with seven numbered sections.
- Sol abstained from inventing the sentences: all recovered lines were marked
  uncertain because the right edge is cropped, the page is angled, contrast is
  low, and the writing remains compressed in the full-page photograph.
- The actionable next capture is one question-and-answer section at a time,
  straight above the page, including the full right edge.
- The upgrade completed without an API error in 57.9 seconds. A cached revisit
  completed in 1.7 seconds without a new provider call.

### A2 Umesh: motor control starter image

- Google recovered 37 words, including `150 / 300V`, `MODEL SB-16`, and
  `2.0 HP ONLY`.
- Sol correctly identified the MEECO SONA single-phase control starter and
  explained `150 / 300V` as voltage and `2.0 HP` as motor power.
- Sol identified six selectable regions, including the meter, nameplate,
  enclosure, lower control, indicator lights, and visible wires, while preserving
  uncertainty about the cropped lower unit and meter quantity.
- The upgrade completed without an API error in 76.2 seconds. Subsequent visits
  reuse the saved result.

## Build and deployment

- Final source commit: `bcc3bdf`
- Cloud Build: `8e9fb357-4c62-4ff8-acce-b25a175dbafa` (`SUCCESS`)
- Image digest:
  `sha256:c5f0780238ffa222ea6f8586dfa1d60d21c78ee18ff3655d75781348dffd38b8`
- Cloud Run service: `vlens-a`, `us-central1`
- Cloud Run revision: `vlens-a-bcc3bdf`
- Traffic: 100 percent
- Limits preserved: minimum zero, maximum one, 1 CPU, 2 GiB, concurrency eight,
  and a 90-second request timeout
- Active provider secret: existing OpenAI key only; no Gemini mapping

## Validation

- Unit and contract tests: 35/35 passed.
- Python compilation, embedded browser JavaScript parsing, service-worker
  JavaScript parsing, and `git diff --check`: passed.
- Live Sol `context-v2` demo qualification: 46.390 seconds, four objects, four
  evidence-linked sections, structured output valid.
- Public login: HTTP 303; public reader: HTTP 200; health: HTTP 200.
- Public final reader contained exactly three quality bars and the new translate,
  object, global inference, microphone, and install controls.
- Public controlled capture: immediate Tesseract found 36 words with repository
  Kannada and English models; Google found 11 words; Sol returned four objects
  and three evidence-linked sections.
- The controlled repository-demo capture was permanently removed after the
  smoke test. No tester capture was deleted.

These checks validate the deployed server, public browser assets, provider
contract, caching, and the two saved field-image upgrades. They do not prove
camera behavior, home-screen installation, speech recognition, object tapping,
or audible Kannada on Eeregowda's or Umesh's physical phones.

## Rollback

Route 100 percent of traffic to `vlens-a-e08840f` for the immediately preceding
three-stage revision, or to `vlens-a-1f102d1` for the previous contextual-PWA
release. The `context-v2` evidence files are additive; rollback does not delete
captures or earlier OCR evidence.
