# A3 owner badge deployment

Date: 2026-09-07
Status: deployed and publicly validated

## Outcome

Every image in the A3 review gallery now has a large, high-contrast ownership
badge above the photograph. Known assignments display as A1 Eeregowda, A2
Umesh, A3 Reviewer, and A4 Selvan. Other assigned captures display their A-ID.
The 20 captures created before tester attribution are explicitly marked
`UNASSIGNED · OLDER CAPTURE`; the system cannot safely infer their owner.

The badge is independent of the small filename and gallery count, which can be
truncated on a phone. Ownership metadata and non-reviewer gallery isolation are
unchanged.

## Stage clarification

This deployment does not activate stage four. Current behavior remains:

1. immediate local OCR;
2. cloud document OCR;
3. Sol object/context inference and Kannada explanation; and
4. reserved independent-model consensus.

The clock stops after stage three because no stage-four request exists yet.
Stage four must compare an independently produced result with stage three and
should turn dark green only when important claims agree. A second billable
provider was not enabled by this display correction.

## Deployment

- Source commit: `1f102d1`
- Cloud Build: `a5391558-d802-488f-a602-3b8993fecbd4` (`SUCCESS`)
- Image digest:
  `sha256:1eb8f98217e095cbe7f66262c5931ef2993ea874f056238e15d637e31325b5ea`
- Cloud Run revision: `vlens-a-1f102d1`, `us-central1`
- Traffic: 100 percent
- Existing secrets, model configuration, and minimum-zero/maximum-one limits
  were preserved.

## Validation and rollback

- Unit and contract tests: 33/33 passed.
- Python and embedded JavaScript syntax checks passed.
- Public reader contains the owner badge and explicit unassigned label.
- No error-level log entry was returned for the revision after validation.

Rollback by routing 100 percent of traffic to `vlens-a-af495bb`.
