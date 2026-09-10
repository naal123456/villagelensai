# Unified Kannada audio repair — 2026-09-09

## Outcome

Source commit `2210a9d` is deployed at `https://villagelensai.com/a/` as Cloud
Run revision `vlens-a-00035-bdx`, receiving 100% of production traffic.

The reported audio failures shared one client-side cause. Mixed answers were
split at every Kannada/Latin transition. An answer beginning `ಇದು FS-12...`
therefore played `ಇದು` using server Kannada speech, then attempted a separate
browser utterance for `FS`, where mobile playback could stop. The complete text
remained visible and could be replayed later from a fresh touch, matching the
field observations.

Mixed Kannada answers are now normalized and sent to the Kannada speech service
as continuous bounded chunks. Model identifiers, digits, and units stay within
the same audio stream. A short silent Web Audio buffer is also started directly
from user touches, including the tap that ends microphone recording, to preserve
mobile-browser playback authorization while the answer is processed.

Question inference now explicitly honors requests to read numbers in Kannada:
it must use Kannada number words and explain the number's unit or calendar role,
not merely repeat digits. Future handwriting analysis first identifies a list's
likely purpose and organization, then uses that context for plausible readings
while abstaining when the letters do not support one.

## Field samples

- `A2-EE726F`: the visible answer contains mixed Kannada, `FS-12`, and
  `220V-2A`; this was the direct reproduction pattern for the `ಇದು` truncation.
- `A1-892F9F`: the calendar follow-up establishes a requirement to speak
  relevant dates and numbers using Kannada number words.
- `A3-FAC3BC`: registered as handwriting sample `HW-0003`, authored by Rupa.
  It is a two-day meal menu mixing Latin transliteration and Kannada. The
  Thursday column is mostly visible; much of Friday is cropped. Saved semantic
  evidence already identifies the menu and likely foods, while literal line OCR
  remains low-confidence and mechanically reads list numbers.

## Verification

- Python compile, JavaScript parse, JSON parse, and `git diff --check`: passed.
- `.venv/bin/python -m unittest discover -s tests -v`: 45/45 passed.
- Cloud Build `43257b41-19a3-489f-9d67-e6920965ab5f`: successful.
- Image digest: `sha256:905931250d6508b90e2526cf18efcb8585b5f4468bdbb865f6f5516f19f8f36e`.
- Public authenticated A3 HTML contains unified speech chunks and touch-based
  audio unlocking.
- A public mixed Kannada/Latin/number synthesis returned HTTP 200, audio/mpeg,
  51,648 bytes, and 6.456 seconds of audio.
- Revision ready and container healthy; CPU 1, memory 2 GiB, concurrency 8,
  timeout 90 seconds, minimum instances 0, maximum instances 1.
- No error-level revision logs appeared after validation.

Actual audible completeness and pronunciation still require confirmation on the
reporting iPhone and Android phones.

## Rollback

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00034-wtq=100
```
