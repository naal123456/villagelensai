# A3 review gallery deployment

Date: 2026-09-07
Status: deployed and publicly validated

## Outcome

A3 is now the controlled reviewer session. Its gallery contains every retained
capture across tester IDs, without changing capture ownership. Known owners are
labeled as A1 Eeregowda, A2 Umesh, A3 Reviewer, and A4 Selvan. Other IDs remain
labeled by ID until a name is assigned.

A3 may also resume missing cloud stages for another tester's retained capture.
New evidence remains attributed to the capture's original tester rather than to
A3. A1, A2, A4, and the other non-reviewer sessions continue to receive only
their own retained images. A3 access therefore remains a privileged bearer
session and its passwordless enrollment link should not be shared with field
testers.

Unlike ordinary tester galleries, the A3 review gallery is not truncated to the
20 most recent captures. Images are loaded only when selected; opening the
gallery does not download all source photographs or call inference for all of
them. A saved image with the current contextual evidence reuses that evidence.
An image with old or missing contextual evidence is upgraded once when opened.

## Build and deployment

- Source commit: `af495bb`
- Cloud Build: `e2c78658-d20c-4e77-ab71-a6bb3293c7de` (`SUCCESS`)
- Image digest:
  `sha256:ca70b00d184502205ac913d6c24004f1ecf1ab85da7cd29a0852a3bd1b7ff6bd`
- Cloud Run service: `vlens-a`, `us-central1`
- Cloud Run revision: `vlens-a-af495bb`
- Traffic: 100 percent
- Existing model, secrets, runtime account, and minimum-zero/maximum-one limits
  were preserved.

As with the preceding deployment, Cloud Run created the revision without
automatically changing traffic. Traffic was checked and explicitly routed to
`vlens-a-af495bb`.

## Validation

- Unit and contract tests: 33/33 passed.
- Python compilation, browser/service-worker JavaScript syntax, and
  `git diff --check`: passed.
- Live A3 gallery: review mode enabled, 50 retained captures.
- Live ownership counts: A1 7, A2 11, A3 6, A5 6, and 20 older unassigned
  captures.
- Live A4 gallery: review mode disabled and zero retained captures, consistent
  with Selvan not yet testing.
- Production revision `vlens-a-af495bb` receives 100 percent of traffic.
- No error-level log entry was returned for the new revision after validation.

The validation confirms API isolation and gallery inventory. Visual navigation
through all captures still requires the A3 user's physical iPhone test.

## Rollback

Route 100 percent of traffic to `vlens-a-65f64ae`. No stored capture or reader
evidence needs migration or deletion.
