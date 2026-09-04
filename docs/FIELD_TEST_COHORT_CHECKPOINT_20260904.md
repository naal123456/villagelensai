# Field-test cohort checkpoint

Date: 2026-09-04
Status: field evidence reviewed; corrections deployed and verified

## Participant IDs

The controlled field roster is limited to `A1` through `A10`. The current
operator mapping is:

- `A1`: Umesh
- `A2`: Eeregowda; Samsung SM-M325F confirmed by the owner on 2026-09-04
- `A3` through `A10`: unassigned pending names from the owner

Each phone must enter through its dedicated link once:

- `https://villagelensai.com/a/?tester=a1`
- `https://villagelensai.com/a/?tester=a2`

The anonymous ID persists in browser storage, is shown beside the gallery
position, is attached to capture and reader evidence, and filters that phone's
saved gallery. Historical captures remain `unassigned`; they must not be
retroactively attributed to a participant from device metadata alone.

## Existing device cohorts

The retained September 3 evidence contains three device signatures: Samsung
SM-M325F, OPPO A5 Pro 5G, and one OPPO Reno8 5G capture. The owner subsequently
confirmed that the Samsung belongs to Eeregowda (`A2`). The OPPO cohorts remain
unassigned, and their ownership must not be inferred.
No photographs or raw OCR/provider responses are copied into this repository.

Representative visual and aggregate checks found:

| Device sample | Image condition | Stage 1 | Stage 2 | Stage 3 |
|---|---|---:|---:|---:|
| Samsung SM-M325F | dim, tilted English children's-book stack | 4/11 | 11/11 | 10/11 |
| OPPO A5 Pro 5G | curved, textured, low-contrast printed bag | 0/5 | 3/5 | 4/5 |
| OPPO Reno8 5G | clear bilingual menu | 8/10 | 8/10 | 6/10 |

Scores are exact matches against small sets of visually confirmed English
checkpoints, not overall accuracy estimates.

## Stage-one incident

Production request metadata showed stage-one capture latency from 20 to 82
seconds during the field session, one 503, and several immediate 429 responses.
The browser was starting Tesseract and both cloud readers together on a
single-CPU, one-instance service. Tesseract did complete for retained captures,
but CPU contention and rejected requests made the yellow/orange stage appear
absent.

The local correction:

- runs Tesseract first and starts cloud readers only after stage one renders;
- bounds Tesseract input to a 1600-pixel long edge;
- restores all word and line boxes to original-image coordinates;
- reduces the local OCR timeout from 60 seconds to 20 seconds;
- starts the visible timer immediately and explicitly marks stage-one failure;
- keeps Google text and geometry authoritative when stage two arrives.

Across the three representative retained images, the corrected full capture API
completed locally in 0.78, 0.88, and 1.73 seconds. Tesseract itself took 0.41,
0.57, and 1.40 seconds and returned 25, 32, and 154 selected words respectively.

## Speech and meaning

Mixed Kannada/English lines were previously sent to one Kannada voice whenever
any Kannada character was present. The corrected client splits speech into
script runs and uses `kn-IN` and `en-IN` voices for the corresponding runs.
This addresses mixed-script pronunciation; device voice availability still
requires field verification.

Stage three previously requested a short explanation, which allowed unwanted
inference. Its contract now requests a faithful Kannada rendering without
inventing context, while preserving names, numbers, prices, and uncertainty.
It also returns exact-source English-word translations so Meaning mode can read
a tapped English word in Kannada without replacing stage-two geometry.

## Local validation

- Focused tests: 17/17 passed, including fresh-phone tester enrollment through
  the access-code redirect.
- Python compilation, embedded JavaScript syntax, and `git diff --check`: passed.
- Representative phone-image stage-one API check: 3/3 returned HTTP 200.

## Deployment verification

- Source commit: `fed25e1` (`Preserve tester ID through access enrollment`).
- Cloud Build `a7b6c635-e185-4269-be81-27dd22d2784f`: successful.
- Deployed image digest:
  `sha256:4eabe02237a826ff01e02ec99df622c350082e794aeabca66936d6b8bc1251e0`.
- Cloud Run revision `vlens-a-fed25e1` serves 100% of traffic in
  `us-central1`; minimum instances remain zero, maximum instances one,
  concurrency four, and timeout 90 seconds.
- Protected access returned 303; both A1 and A2 pages returned 200; health
  returned 200 with both local language models present.
- A fresh unauthenticated A1 link returned 302 to an A1-preserving access page;
  the access POST returned 303 to `/a/?tester=a1`, and that page returned 200.
- The authenticated live HTML exactly matched the tested local source and its
  orange-first, translation, and A1–A10 contracts were present.
- The A1 and A2 gallery requests were isolated and currently contain only the
  two shared demo items because historical captures remain unassigned.
- No photograph was uploaded and no paid reader call was made during deployment
  verification.

Immediate rollback revision: `vlens-a-8d4884e`. Pre-field-correction rollback
revision: `vlens-a-ff19439`.

On-device Kannada/English speech quality still requires field verification and
is not claimed by this checkpoint.
