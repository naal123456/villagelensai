# Latest capture mixed-script checkpoint

Date: 2026-09-02
Status: diagnostic complete; display-order correction deployed and verified

## Scope

The newest retained phone capture was tested without treating any provider as
ground truth. Raw photographed text and complete provider responses are not
copied into this repository. The comparison uses nine visually confirmed
English checkpoints, script counts, box geometry, and latency.

## Findings

The repository-local English Tesseract model and its embedded dictionary are
installed and active. The failure is detection/selection, not a missing model:

| Reading | Latin candidates | Kannada candidates | Exact English checkpoints |
|---|---:|---:|---:|
| Tesseract `kan+eng`, PSM 6 raw | 33 | 33 | 0/9 |
| Tesseract `kan+eng`, PSM 11 raw | 119 | 37 | 0/9 |
| Tesseract `kan+eng`, PSM 12 raw | 108 | 39 | 0/9 |
| Retained production Tesseract selection | 20 | 8 | 0/9 |
| Google document OCR | 12 | 3 | 8/9 |
| OpenAI stage 3 | 9 | 3 | 5/9 |
| Claude blind reading | both scripts reported | both scripts reported | 9/9 |
| Gemini blind reading | both scripts reported | both scripts reported | 9/9 |

Claude used `claude-sonnet-5` with 7,802 ms latency and two uncertainty spans.
Gemini used `gemini-3.7-flash` with 7,535 ms latency and one uncertainty span.
Both calls used the established `mentra-kannada-reader.v2` blind-reading prompt,
reported Kannada and English, and did not request a retake.

Production's 32-line Tesseract selection cap reduced 205 raw PSM-11 candidates
to a small subset, but simply raising the cap is not justified: none of the nine
visible English checkpoints was exact in any tested Tesseract page mode, and the
additional candidates are largely visual noise from the illustrated cover.

## Geometry diagnosis and decision

The retained stages collapsed from 32 Tesseract lines to 10 Google lines and
then 3 OpenAI lines. Median normalized word-box area increased from `0.000081`
to `0.001196` to `0.016375`; only 4 of 13 OpenAI boxes overlapped a Google box
at IoU 0.1 or better. The stage-3 boxes therefore cannot safely replace the
touch layout.

The client now follows this bounded contract:

- stage 1 remains the local fallback;
- stage 2 Google text and geometry become the stable cloud touch layout;
- stage 3 may add a Kannada meaning but cannot replace stage-2 words or boxes;
- stage 4 remains reserved for validated deterministic consensus. Claude and
  Gemini results are promising evidence, not automatic promotion authority.

## Validation

- Focused API/browser-contract tests: 13/13 passed after the correction.
- Embedded JavaScript syntax, Python compilation, and `git diff --check`: passed.
- Source commit: `ff19439` (`Preserve stable geometry across reader stages`).
- Cloud Build: `39343c38-234f-4d70-b129-53ae2be4d58f`, successful.
- Deployed image digest:
  `sha256:50c0f3eae45c241ea8f54061e93508c7413c4b38ff494b1b7bb6d8545e3a9836`.
- Cloud Run revision `vlens-a-ff19439` serves 100% of traffic in
  `us-central1`; minimum instances remain zero, maximum instances one,
  concurrency four, and timeout 90 seconds.
- The protected access POST returned 303, `/a/` returned 200, and
  `/api/gallery` returned 200.
- The authenticated live HTML SHA-256 exactly matched the tested local HTML
  (`0435f02ab8b63e0ace837271faad5beccfabd72d0a18209c81c7f29dfc1171f0`),
  and its stage contract check passed.
- No paid OCR or language-model request was made during deployment validation.

Rollback revision: `vlens-a-45b3f50`.
