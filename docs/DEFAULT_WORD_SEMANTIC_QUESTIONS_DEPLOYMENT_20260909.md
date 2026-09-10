# Default word mode and semantic questions — 2026-09-09

## Outcome

Source commit `c0ccf11` is deployed at `https://villagelensai.com/a/` as Cloud
Run revision `vlens-a-00034-wtq`, receiving 100% of traffic.

- Every gallery navigation and new camera capture now restores top button 1 as
  the actual active word-touch mode. Previously the visible state could be
  cleared to `none`, causing taps on recognized words to do nothing.
- Spoken questions remain global by default. A user does not have to identify a
  region before asking a basic question.
- When a current semantic scene is saved, a general question such as “What is
  this?” reuses its Kannada identification. This is faster, avoids a redundant
  model request, and prevents an unhelpful answer consisting only of “this”.
- When the user first selects a blue semantic object, the microphone question
  remains grounded to that object's label and region. Other specific questions
  receive the saved scene description and object map as context.

The resulting interaction is intentionally hybrid: effortless global questions
for first discovery, optional touch-to-narrow for questions about a part. Touch
is not mandatory because that would be difficult for the primary users and
would make “What is this?” unnecessarily complicated.

## Reported capture validation

Protected capture `A2-EE726F` already had saved semantic evidence identifying an
FS-12 video-camera unit, its information label, mounting slot, and cables. A
public authenticated request with `What is this?` returned the saved Kannada
identification, including `FS-12` and `220V-2A`, with
`answer_source=saved_semantic_scene`. No new language-model question call was
needed for that validation.

## Verification

- Python compile, embedded JavaScript parse, and `git diff --check`: passed.
- `.venv/bin/python -m unittest discover -s tests -v`: 44/44 passed.
- Cloud Build `82c8930e-6988-480a-b95e-f800bbab4c3a`: successful.
- Image digest: `sha256:3c04d54aa6947fa7b5d9af96504eb974348c635540a6ee6b8c4f301886fa3bbc`.
- Public authenticated A3 HTML contains the default-word-mode transitions.
- Revision ready and container healthy; CPU 1, memory 2 GiB, concurrency 8,
  timeout 90 seconds, minimum instances 0, maximum instances 1.
- No error-level log entries were present after deployment validation.

Physical touch and microphone behavior still require confirmation on the actual
tester phones.

## Rollback

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00033-72j=100
```
