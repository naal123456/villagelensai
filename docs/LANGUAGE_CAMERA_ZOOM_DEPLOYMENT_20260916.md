# Language control and camera zoom deployment — 2026-09-16

Status: deployed and publicly HTTP-validated; physical-phone zoom and audio-help
confirmation pending.

## Outcome

- The separate language button was removed. The third button in the top row now
  displays the active output language (`ಕ` or `EN`) and switches the entire
  reader between Kannada and English.
- A language change preserves the selected saved image. Word and sentence
  reading continue to speak source text first and the selected-language meaning
  second when translation is needed. Inference and spoken-question answers use
  the selected language; the question itself may be spoken in another language.
- Static menus, camera guidance, and home help are localized to the selected
  language.
- The home screen points to a prominent camera start button. Each compact help
  item speaks its explanation only after it is touched.
- The guided camera requests up to 3840 by 2160 input. Phones exposing camera
  zoom controls receive minus, slider, plus, and pinch zoom. Zoom is
  feature-detected, so unsupported browsers do not receive a nonfunctional
  control. Tap-to-focus/crop and the four-frame clearest-image selection remain.
- Stage 4 remains an optional manual Sol review and is unchanged.

## Field evidence

The implementation was guided by A3-32 and A3-33:

- A3-32 is a close, sharp product-certification label, but the text is sideways
  and local stage-one OCR retained no words. Orientation/contrast recovery is a
  separate OCR improvement; this release does not automatically rotate general
  object photographs.
- A3-33 is globally sharp (`sharpness 27.51`, `motion 9.66`) but the wall
  calendar occupies only a small part of the saved frame. Moving the crop box
  selected the area but could not add calendar pixels. The higher-resolution
  request and real camera zoom target this failure mode.

The reviewer also confirmed successful source-language speech followed by
English meaning and inference on Japanese, Hindi, Tamil, Kannada, and Telugu
content. This release preserves that validated pipeline.

## Verification

- Source commit: `d8e1a76`
- Cloud Build: `e0fa65f5-7b01-4716-a37b-4c3b423522cb`
- Container digest:
  `sha256:0d56ef44462bcfa305bceab6114dfc0192b4ef0416207adf9a1299a22d0eb8d0`
- Cloud Run revision: `vlens-a-00068-snn`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight
- Unit tests: `68/68` passed
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-16.2`, zero missing OCR models,
  stage 4 manual
- Authenticated public page contains the repurposed top language button, home
  camera/help controls, feature-detected zoom implementation, and 4K ideal
  camera request; the separate language button is absent
- Error-level logs for the new revision after validation: empty
- Public verification did not upload a photograph or invoke a paid model

## Physical-phone check

1. Confirm the third top button displays `EN` in English mode and `ಕ` in Kannada
   mode, and returns to the same image after switching.
2. Tap each home help item and confirm it speaks only in the selected language.
3. Open the camera. On a phone that exposes zoom, confirm the minus/slider/plus
   row appears and pinch zoom changes the preview. Tap the distant calendar,
   zoom until it fills the yellow box, and capture manually.
4. Confirm source speech precedes translated speech and that inference and
   microphone answers use the selected language.

## Rollback

Route traffic back to `vlens-a-00067-5zb`. That revision has the separate
language button and tap-selected crop but no camera zoom controls.
