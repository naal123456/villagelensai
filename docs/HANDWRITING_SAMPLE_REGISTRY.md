# Handwriting sample registry

This registry keeps VillageLens handwriting examples identifiable even as new
photos change their gallery positions. The machine-readable source is
[`handwriting_samples.json`](handwriting_samples.json). It stores protected
capture references and quality observations, never image bytes or photographed
page contents.

## Foundational pair

| Sample | Stable capture | Session | View | Qualification |
|---|---|---|---|---|
| HW-0001 | A1-185142 | A1 / Eeregowda | Close | Larger, clearer writing; several line endings cropped on the right |
| HW-0002 | A1-4E3077 | A1 / Eeregowda | Overview | Nearly complete page and stronger context; writing is smaller |
| HW-0003 | A3-FAC3BC | A3 / Reviewer; written by Rupa | Mixed-script menu list | Thursday column mostly visible; Friday column cropped; difficult transliteration and Kannada mix |

Both were captured seven seconds apart and form `HW-PAIR-0001`. The close image
may have been made by a helper demonstrating how to frame the page. That is not
confirmed, because the tester ID identifies the active phone session rather than
the photographer.

`HW-0003` is the first confirmed handwriting sample authored by Rupa. It is a
particularly useful hard case: a two-day food menu written using both Latin
transliteration and Kannada, with overwriting and a cropped right column. Literal
OCR pronunciation is not a sufficient evaluation for this sample; document
purpose, likely food names, uncertainty, and audio continuity must be scored
separately.

Owner-verified readings for `HW-0003` are: item 1 `Puliyogare` →
`ಪುಳಿಯೋಗರೆ` (spicy tamarind rice), item 2 → `ಕಡಲೆಕಾಯಿ` (groundnuts),
item 3 `Shavige` → `ಶಾವಿಗೆ` (vermicelli food), and item 7 `Ollige` →
`ಒಳಿಗೆ`. These corrections are attached to their image regions in the tester
application. They override literal OCR for touch and continuous reading without
silently treating the remaining uncertain handwriting as verified truth.

## Accumulation rules

Each new handwriting example should receive:

- an immutable sequential sample ID;
- its permanent capture code and full protected capture ID;
- tester session and capture time, with photographer kept separate;
- language, handwriting/content type, and overview/close/section view;
- observable blur, lighting, angle, glare, cropping, and distance limitations;
- a pair or series ID when the user retries the same page;
- later OCR/inference evaluation results recorded separately from visual ground
  truth.

Gallery numbers such as “image 21” must not be used as identifiers. A model
description is also not ground truth. Ambiguous ownership, content, or quality
must remain explicitly unconfirmed until a human reviewer verifies it.
