# Relaxed camera stability deployment — 2026-09-09

## Outcome

The guided camera now distinguishes useful sharp detail from ordinary hand
tremor. A clearly sharp frame accepts motion up to 24; a marginal frame retains
the stricter limit of 16. The previous single motion limit was 10. The minimum
sharpness requirement remains 4.5, while the uninterrupted green hold before
automatic capture was reduced from 2.2 seconds to 1.2 seconds.

Darkness and glare thresholds are unchanged. The large manual capture control
remains available. Preview analysis still runs locally on the phone and does not
upload frames or add provider calls.

## Verification

- Source commit: `6ac1552`
- Tests: `46/46` passed.
- Python compilation, embedded JavaScript parse, and `git diff --check`: passed.
- Cloud Build: `6630d558-dbd1-4d62-b1f2-4fa0d7ebaa3d` succeeded.
- Container digest:
  `sha256:cfc92e293332e02e95c2c14262ef5686cb33b66073b2db31b972cf3ae8154359`
- Public `/health`: status `ok`, access gate enabled, no missing models.
- The authenticated public tester page contains the 1.2-second hold and adaptive
  motion thresholds.
- Physical behavior still requires field testing on the actual phones.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00038-jsh`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00036-d6q`
