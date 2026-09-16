# Resizable camera frame deployment — 2026-09-16

Status: deployed and publicly HTTP-validated; physical-phone corner dragging and
capture confirmation pending.

## Outcome

- The guided camera frame is no longer fixed to a square. Four large orange
  corner handles let the user independently change its width and height, so a
  book page, calendar, sign, label, plant, or other object can be framed with a
  wide or tall rectangle.
- Dragging is bounded to the visible preview and enforces only a small minimum
  width and height. Releasing a handle asks the camera to focus at the center of
  the newly framed area.
- Existing tap-to-center, tap-to-focus, hardware zoom, pinch zoom, clearest-frame
  selection, and manual capture behavior remain available.
- The home-screen camera control now reproduces the orange toolbar camera
  control, including its border, size, and icon. A localized start label and
  arrow point to it, while touching the camera still opens the preview directly.
- Stage processing, language behavior, OCR, inference, and model routing are
  unchanged.

## Verification

- Application version: `2026-09-16.3`
- Source commit: `601716d`
- Cloud Build: `e1da70d8-dcca-44d0-b82b-05e34e4512d2`
- Container digest:
  `sha256:c338b46eee7bcc81b3eb24a1ba395744d83956be70c5f6f48a08f8c7bcd8baf7`
- Cloud Run revision: `vlens-a-00069-z7s`, 100 percent traffic
- Controlled runtime retained: maximum one instance, concurrency eight
- Unit tests: `68/68` passed
- Python compilation, embedded JavaScript parsing, and `git diff --check`:
  passed
- Public `/health`: HTTP 200, version `2026-09-16.3`, zero missing OCR models,
  stage 4 manual
- Authenticated A3 page: HTTP 200 and contains four corner handles, resize
  interaction logic, localized start label, orange home camera control, and the
  deployed version
- Error-level logs for the new revision after validation: empty
- Public verification did not upload a photograph or invoke a paid model

## Physical-phone check

1. Open the home page and confirm the orange camera looks like the camera in the
   toolbar. Touch it and confirm the camera opens immediately.
2. Drag one orange corner sideways. Confirm the yellow frame becomes wide
   without forcing it back to a square.
3. Drag one corner vertically. Confirm the frame can become a tall rectangle.
4. Reframe a book page or calendar, zoom as needed, and capture it. Confirm the
   saved image corresponds to the rectangular area shown before capture.
5. Confirm tapping inside the preview still moves the frame and that zoom and
   manual capture still work normally.

## Rollback

Route traffic back to `vlens-a-00068-snn`. That revision has camera zoom and the
unified language control, but uses a non-resizable target frame and the larger
green home camera control.
