# VillageLensAI repository rules

## Scope

This repository owns the deployable VillageLensAI phone web client, cloud API,
infrastructure, deployment workflows, and POC operations documentation.

The `smart-glasses-phase1` repository remains the research and evaluation source.
Move a capability here only through an explicit, tested, commit-backed promotion.

## Safety

- Never commit API keys, service-account keys, access tokens, billing data, user
  photographs, authorization headers, or raw provider request/response logs.
- Keep OpenAI and Google credentials server-side in Google Secret Manager.
- Use repository-local dependencies and models. Do not modify global installs.
- Do not deploy or enable billable resources without explicit owner authorization.
- Keep Cloud Run minimum instances at zero and maximum instances at one until a
  recorded decision changes the controlled POC limits.
- Preserve uncertainty. A completed provider call is not proof of correctness.

## Product constraints

- The tester path is `/a` and must require no typing after helper installation.
- Keep OCR/provider names out of the tester interface.
- Tesseract provides the immediate result even when every cloud reader fails.
- The fourth quality stage represents validated consensus, not completion.
- Video and continuous streaming are outside the POC.

## Change requirements

- Add or update tests for behavioral changes.
- Run format/static checks and the focused test suite before committing.
- Record deployment configuration, validation evidence, and rollback information.
- Do not claim deployment or end-to-end readiness until the public URL is tested
  on iPhone Safari with camera and Kannada audio.
