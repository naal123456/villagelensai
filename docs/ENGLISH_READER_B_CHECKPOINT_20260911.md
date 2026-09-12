# English reader `/b/` checkpoint — 2026-09-11

## Purpose

Add an isolated owner experiment that translates and explains any detected
language in English, while preserving the Kannada-first `/a/` field test.

## Route and access

- English experiment: `/b/?tester=a3`
- Existing Kannada experience: `/a/?tester=<tester-id>`
- The existing access gate and secure access cookie protect both routes.
- An unauthenticated `/b/` request directs to the access screen with A3
  preselected.

## Isolation

- The client sends `X-VillageLens-Output-Language: en` from `/b/` and `kn` from
  `/a/`.
- Browser reader caches include the output language.
- Stored English evidence uses `stage-<number>-en.json`; the existing Kannada
  stage filenames are unchanged.
- English reader failures have independent cooldown records.
- The same retained source photographs and reviewer gallery are available to
  A3, avoiding duplicate photographs.

## Initial scope

- The four reading stages, object selection, global inference, microphone
  questions, conversational context, and camera are reused.
- English output uses the phone's browser English voice.
- `/b/` is deliberately not installable in this checkpoint. It is a browser
  experiment; `/a/` remains the installed Kannada PWA.
- API compatibility field names such as `brief_spoken_kn` remain unchanged
  internally, although their `/b/` values are English.
- A Fast-lane HTTP 429 receives one bounded retry on the provider's default
  service tier. Other failures are not retried by this rule.

## Validation

- `python3 -m py_compile api/app.py`
- `.venv/bin/python -m unittest tests.test_api` — 58 tests passed.
- The embedded browser script compiled successfully with Node `vm.Script`.
- Focused tests cover `/b/` routing, access behavior, English reader validation,
  language request forwarding, and English evidence storage isolation.

Public iPhone Safari camera and English audio validation remains required after
deployment; this checkpoint does not claim that validation.

## Deployment configuration

No new secret, provider, model, service, or billable resource is required. The
existing Cloud Run limits and provider configuration remain unchanged.

## Rollback

Roll back to the preceding Cloud Run revision. This removes `/b/` and the
language-aware request behavior without deleting captures or existing Kannada
evidence. English `stage-*-en.json` evidence may remain inert in storage.
