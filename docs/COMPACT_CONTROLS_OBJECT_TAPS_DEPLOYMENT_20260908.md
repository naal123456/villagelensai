# Compact controls and object-tap deployment

Date: 2026-09-08
Status: deployed and publicly validated; physical-phone interaction check pending

## Outcome

- The reader now has exactly two compact control rows. Ask and Install are icon
  buttons in the second row, and the camera has a prominent orange treatment.
- The separate full-width green buttons were removed, the owner badge and status
  spacing were reduced, and the image may use up to 74 percent of viewport height.
- Full-frame scene/background boxes are excluded from object mode. Large object
  regions are drawn before small regions so the most specific overlapping region
  receives a touch.
- The contextual prompt now prohibits whole-image, page, background, ground, and
  soil boxes as selectable objects.
- A stopped timer displays a checkmark when stage three completed and an
  exclamation mark when it did not. Cached stage-three evidence displays
  `saved ✓`.

## Field evidence

- Image 9: A2 textbook page; stage three completed in 47.043 seconds, validated,
  medium confidence.
- Image 10: A2 video-camera/power-unit label; stage three completed in 42.565
  seconds, validated, high confidence with independent review requested.
- Image 11: A2 young plant; stage three completed in 39.091 seconds. Its stored
  full-frame soil box is now excluded, leaving young plant, leaf, and irrigation
  pipe as selectable regions.
- The handwriting pair is currently image 21 (A1 close image, 14 transcription
  lines) and image 22 (A1 farther image, no stage-three evidence). Gallery
  positions shift when newer captures are inserted.

## Validation and deployment

- Source commit: `2eb9d8f`.
- Unit and contract tests: 38/38 passed.
- Embedded browser JavaScript parsing and `git diff --check`: passed.
- Cloud Build: `daf3bcc6-3ded-4d54-b56a-35153a6df5cf` (`SUCCESS`).
- Image digest:
  `sha256:a21d736f792deabb8e97dd83e6cb23d6a355cf20ddca138a4a705504d63d2c02`.
- Cloud Run revision: `vlens-a-2eb9d8f`, `us-central1`, 100 percent traffic.
- Public A3 login and reader page passed. The public page contains exactly two
  toolbars, the microphone and install icons, and completion-state markers.
- Public gallery validation confirmed image 11 no longer returns the full-frame
  soil object.
- No error-level log was present for the deployed revision after validation.

Production limits and secret mappings are unchanged. No inference was rerun for
images 9, 10, or 11; their saved evidence was normalized at read time.

## Rollback

Route 100 percent of traffic to `vlens-a-462d113`. No capture or reader evidence
was deleted or rewritten by this deployment.
