# Guided capture field-test deployment — 2026-09-09

## Outcome

Source commit `2354eac815f5dcf4d861f5c5a8b797fd5445888c` is deployed to
`https://villagelensai.com/a/` as Cloud Run revision `vlens-a-00033-72j`.
Traffic was explicitly moved to that revision at 100%.

The camera button now opens a transient on-device preview that checks brightness,
dark area, glare, frame-to-frame motion, and edge sharpness. The framing boundary
changes red/yellow/green, short Kannada/English guidance is presented, a stable
green frame is captured after 2.2 seconds, and a large manual capture override is
always available. Preview frames are neither uploaded nor stored; only the final
JPEG is sent through the existing capture pipeline.

New captures store a sanitized set of quality measurements and receive a durable
owner-prefixed code such as `A2-3F91BC`. Gallery display derives a descriptive
label from saved stage-three `scene_type` evidence when available, so a capture
can still be identified after its numeric gallery position changes. Existing
captures also receive a deterministic display code without rewriting stored
photos.

The current retained gallery contains no confirmed handwriting sample. The page
currently appearing as gallery image 11 is printed Kannada, not handwriting.
This deployment therefore does not assign speculative handwriting labels to old
captures. New stable codes should be used when collecting the next close and far
handwriting pair.

## Verification

- `.venv/bin/python -m unittest discover -s tests -v`: 43/43 passed.
- Python compilation, JavaScript parse, and `git diff --check`: passed.
- Cloud Build `6a982580-b607-424a-8473-24c66f5e400f`: success.
- Container digest: `sha256:d2d0e5974ce005cd46408bcfc974028d56a0403d09d58e4da2d389f91dc4f847`.
- Public `/health`: `status=ok`, access gate enabled, no missing models.
- Authenticated public A3 page contains the guided camera, local analyzer, and
  capture-quality metadata contract.
- Revision ready; container healthy; CPU 1, memory 2 GiB, concurrency 8,
  timeout 90 seconds, max instances 1. Min instances is 0 (the min-scale
  annotation is absent, which is the Cloud Run zero default).

Physical camera behavior and Kannada guidance still require testing on the actual
Android phones and iPhone Safari. This record does not claim that phone-level
validation has completed.

## Rollback

Route traffic back to the preceding known-good revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-280a324=100
```
