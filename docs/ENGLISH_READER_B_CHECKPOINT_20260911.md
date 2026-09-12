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

The protected production page was verified to contain version
`v2026.09.11.1` and the English output-language header. Public health returned
`ok`, with the access gate enabled and both local OCR models present.

A controlled stage-two production request used the repository demo image, not
a private tester photograph. Both Fast and default service tiers returned HTTP
429. A minimal diagnostic request established the provider error as
`insufficient_quota` with code `credit_balance_exhausted`. Therefore the route
is deployed, but model-backed English inference cannot be claimed ready until
the OpenAI project has credits or a deliberately selected funded provider is
configured. This same account condition affects the model-backed stages on
`/a/`; local and Google OCR are separate.

Public iPhone Safari camera and English audio validation also remains required;
this checkpoint does not claim that physical validation.

## Deployment configuration

No new secret, provider, model, service, or billable resource is required. The
existing Cloud Run limits and provider configuration remain unchanged.

- Source commits: `470455c`, `05a38f7`
- Cloud Build: `d8f8ec68-3cbc-4fc0-8da3-1c7f36fff7bb`
- Container digest:
  `sha256:085bf8682182c1147e6aa42d83f19376ba5ceb3cc025489d7b36187b50b4cda2`
- Production service: `vlens-a`, `us-central1`
- Production revision: `vlens-a-00049-274`, 100 percent traffic

## Rollback

Route traffic to `vlens-a-00047-sdz` to remove `/b/` and the language-aware
request behavior without deleting captures or existing Kannada evidence.
Revision `vlens-a-00048-klv` retains `/b/` without the bounded Fast-to-default
429 fallback. English `stage-*-en.json` evidence may remain inert in storage.
