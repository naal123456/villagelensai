# Curved-page advisory deployment — 2026-09-10

## Outcome

Version `v2026.09.10.4` makes page-edge geometry advisory. A curved, partly
arched, or imperfectly detected book page can now reach the ready state and be
captured; an uncertain page edge no longer keeps the camera yellow. The camera
continues to suggest an adjustment, but the user may take the picture.

The camera overlay now explains that the solid outer box is the exact saved
photo area and the dashed line is only an estimated page boundary. Capture uses
the current shutter-moment frame inside the solid guide. The earlier rolling
best-frame choice was removed because it could save a frame different from the
one visible when the user tapped the shutter.

For a generic spoken question such as `ಇದು ಏನು?` (“What is this?”), the saved
semantic scene now returns its detailed teaching explanation when available,
rather than reducing the answer to the short scene label. It remains a cached
answer and does not invoke a new model or add inference cost.

## A3-52821C diagnosis

The test photograph was inspected transiently and was not added to the
repository. It is a sharp photograph of a curved left-hand textbook page, with
the right side incomplete and substantial chair/table background. The old
heuristic reported uncertain/clipped geometry even though the readable portion
was usable. Its stored detailed inference correctly identifies the topic as
`ವಿದ್ಯಾಕೇಂದ್ರ`: temples and monasteries serving as educational and cultural
centres, with learning under a guru. The new generic-question path returns that
full explanation and explicitly notes the missing right edge.

This release does not provide draggable page corners or curved-page
dewarping. Those remain possible follow-up improvements after field testing the
simpler exact-frame behavior.

## Verification

- Source commit: `2bf4756`
- Tests: `46/46` passed.
- Python compilation, index JavaScript parse, service-worker JavaScript parse,
  and `git diff --check`: passed.
- Cloud Build: `a4b400fe-8ae7-4cf2-bcc2-21525cc56aaa` succeeded.
- Container digest:
  `sha256:1606656b0a8c1486b9e673722a199a67bb9ea475e5f2b203fe2b9bd4a321e27f`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated A3 page contains version `v2026.09.10.4`, the solid/dashed
  overlay explanation, advisory page-edge state, and single current-frame
  capture; the removed rolling-frame selector is absent.
- An authenticated production request for `ಇದು ಏನು?` on `A3-52821C` returned
  `answer_source: saved_semantic_scene` with the complete cached teaching
  explanation.
- These checks do not replace physical camera testing on iPhone Safari and the
  target Android phones.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00042-qf8`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00041-xxs`
