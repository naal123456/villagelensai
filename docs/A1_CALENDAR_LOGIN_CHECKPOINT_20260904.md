# A1 calendar and login checkpoint

Date: 2026-09-04
Status: diagnosis complete; corrections locally validated; not deployed

## Login evidence

Recent Android access-form requests reached the production service. Most
returned HTTP 303, proving that A3–A5 are accepted by the form and server. Three
requests returned 401 because the submitted User or Code was missing/incorrect.
Two requests returned immediate 429 responses while the single Cloud Run
instance was occupied by reader requests. Submitted field values and access
codes were not logged or inspected.

The correction keeps the zero-minimum, one-maximum instance cost boundary but
raises Cloud Run request concurrency and Gunicorn threads from four to eight.
This reserves practical room for short access requests while cloud readers are
waiting on providers. It does not add instances.

## A1 calendar image 3/5

The image is a clear April 2026 wall calendar with large Kannada headings and
weekday labels, English abbreviations, and numbers. Aggregate retained evidence:

| Stage | Words | Kannada regions | Latin regions | Numeric regions | Latency |
|---|---:|---:|---:|---:|---:|
| Tesseract | 62 | 19 | 19 | 22 | 5,506 ms |
| Google document OCR | 191 | 98 | 8 | 52 | 884 ms |
| Vision-language stage | 34 | 0 | 9 | 25 | 21,993 ms |

Google's Kannada geometry covers both the calendar heading and body: 13
Kannada regions occur near the top and 85 in the calendar area. Because English
audio works on the same phone, the reported missing Kannada reading is a phone
speech-synthesis failure rather than missing cloud OCR.

The client correction explicitly selects an exact or language-matched system
voice for each `kn-IN` and `en-IN` speech segment. If Kannada synthesis fails,
the UI now reports that the Kannada voice must be installed in the phone's
Speech Services settings instead of silently stopping continuous playback.

The temporary local image copy will be deleted after validation. No photograph
or raw provider response is committed to the repository.

## Validation

- Focused tests: 18/18 passed.
- Python compilation, JavaScript syntax, and `git diff --check`: passed.
- Deployment and corrected on-device audio are not claimed by this checkpoint.
