# Exclusive controls and immediate translation deployment

Date: 2026-09-08
Status: deployed and publicly validated; physical-phone interaction check pending

## Outcome

- Exactly one reading control is selected at a time. Starting any control stops
  speech and clears the prior yellow or blue selection.
- The two continuous-reading controls toggle off when touched again and stop
  when any other control is selected.
- Running actions pulse blue; persistent touch modes remain yellow after their
  preparation finishes.
- English-to-Kannada no longer waits for contextual image inference. It first
  reuses the image result, then a persistent phone cache, and finally requests a
  small structured translation from `gpt-5-mini`.
- Object and whole-image explanation explicitly retry stage three when context
  is absent. The timer runs during that retry, including for the two demo images.
- Object, Explain, Ask, and Install now have bilingual visible labels.
- Kannada words selected in EN-to-Kannada mode are spoken directly rather than
  being sent for translation.

## Validation

- Source commit: `462d113`
- Unit and contract tests: 37/37 passed.
- Python compilation, embedded browser JavaScript parsing, and `git diff
  --check`: passed.
- Live direct provider check: `starter` returned valid Kannada in 3.5 seconds.
- Cloud Build: `b59bce15-02ff-45fa-8029-7fc0562fcbf4` (`SUCCESS`).
- Image digest:
  `sha256:3b437dd9af5a4f25f4060f969f6ecd26969cbd094f0a5485697e5f141910e3ae`.
- Cloud Run revision: `vlens-a-462d113`, `us-central1`, 100 percent traffic.
- Public health: HTTP 200; A3 login: HTTP 303; reader page: HTTP 200.
- Public translation check: `power switch` returned valid Kannada with HTTP 200.
- No error-level log was present for the new revision after validation.

The production limits remain minimum zero, maximum one, one CPU, 2 GiB,
concurrency eight, and a 90-second timeout. The existing OpenAI secret mapping,
capture bucket, and runtime service account are unchanged. Gemini is not mapped
or invoked.

These checks do not prove touch toggling, audible Kannada, camera capture, or
installation behavior on Umesh's or Eeregowda's physical phones.

## Rollback

Route 100 percent of traffic back to `vlens-a-bcc3bdf`. This deployment does not
delete or rewrite any retained capture or reader evidence.
