# Sequential capture labels deployment — 2026-09-10

## Outcome

Version `v2026.09.10.6` replaces the visible random capture suffix with a short
chronological number per tester. Examples are `A1-1`, `A1-2`, `A2-1`, and
`A3-20`. The tester ID continues to identify the owner; the number identifies
that tester's retained image.

Existing retained images receive their chronological labels when the gallery
loads. Newly captured images receive the next number immediately. The original
32-character capture ID remains the internal storage and authorization key, so
no photographs are renamed and existing OCR, inference, conversations, and
ownership remain attached to the same records.

Chronological numbering is independent of storage listing order. Adding newer
images appends to the tester's sequence without changing existing labels.

## Production examples

- Former `A3-52821C`: `A3-15`
- Former `A3-7CE1C5`: `A3-19`
- Former `A3-2F035E`: `A3-20`
- Next A3 capture at deployment verification: `A3-21`

The user-reported `A3-2F0353` was the stored capture formerly displayed as
`A3-2F035E` and is now `A3-20`.

## Verification

- Source commit: `e166608`
- Tests: `47/47` passed, including mixed-tester chronological numbering from an
  intentionally reversed storage listing.
- Python compilation, index JavaScript parse, service-worker JavaScript parse,
  and `git diff --check`: passed.
- Cloud Build: `6f7c5ce9-9519-45cd-be95-1e4085edd8ae` succeeded.
- Container digest:
  `sha256:af30ee3a1114adebdaa28ed3c6cfeb049730845106c563d94945d4f5cdab1686`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated production page contains version `v2026.09.10.6` and consumes
  the server-provided next sequence for immediate capture labels.
- Authenticated A3 gallery returned the three example mappings above and
  `next_capture_sequence: 21`.
- These checks do not replace physical display testing on the target phones.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00044-lpx`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00043-w4r`
