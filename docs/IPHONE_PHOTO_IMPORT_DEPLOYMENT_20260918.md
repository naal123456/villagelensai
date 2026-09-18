# iPhone photo import deployment — 2026-09-18

Status: deployed and publicly infrastructure-validated; physical iPhone Photos
selection and end-to-end screenshot reading pending owner confirmation.

## Goal

Let the A3 reviewer read an existing Kannada WhatsApp screenshot or saved photo
in English without pointing the camera at another screen. PDF/document upload is
deliberately outside this increment.

## Change

- A dedicated blue `🖼️` Photos control now sits beside the orange `📷` Camera
  control in the primary toolbar.
- The Home screen presents both Camera and Photos as equally direct starting
  actions, with English/Kannada labels following the selected output language.
- Photos uses a separate image-only file input without the `capture` attribute,
  so iPhone opens the existing-photo picker rather than the guided live camera.
- A selected JPEG, PNG, or WebP enters the same retained capture, OCR, staged
  inference, language, audio, gallery, and question pipeline as a new camera
  photo. It is tagged internally as `photo-library-v1` and labeled “Imported
  photo” in English mode.
- Selecting a photo implies upload, just like taking a new photograph. No PDF,
  multiple-selection, clipboard, or WhatsApp-native extension was added.

## Verification

- Application version: `2026-09-17.2`
- Source commit: `ce9e2fb`
- Cloud Build: `571feed8-63f5-4e61-8940-ad9a9bdf99c3`
- Container digest:
  `sha256:6fd2da9a1d987ba7270e064758f8b817b21ed963148d1ce869ea2d65789b498b`
- Cloud Run revision: `vlens-a-00076-98l`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight; minimum
  remains the service default zero
- Tests: 76/76 passed, including the new photo-library contract
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-17.2`, zero missing OCR models
- Protected A3 URL: HTTP 302 to the access gate with `no-store`, as expected
- Error-level logs for the new revision after deployment: empty

## Physical iPhone test

1. Take a screenshot of a Kannada WhatsApp message.
2. Open the A3 VillageLens Home screen and confirm `EN` is selected.
3. Tap the blue `🖼️` Photos button, either in the top row or on Home.
4. Select the screenshot. Confirm the live camera does not open.
5. Confirm the image is labeled `A3-<number> · Imported photo`, bar 1 starts,
   and bars 2 and 3 improve the result normally.
6. Touch a Kannada word and sentence; confirm the source is spoken and its
   English meaning follows. Use the lightbulb for the message meaning.
7. Repeat with a saved Kannada document photograph.

## Rollback

Route traffic back to `vlens-a-00075-mpm`. That revision is version
`2026-09-17.1` and does not expose an iPhone photo-library control.
