# Pinned Tesseract language data

These files were promoted from the tested `smart-glasses-phase1` checkpoint.
They are repository-local runtime dependencies and do not modify a machine-wide
Tesseract installation.

| Language | SHA-256 |
|---|---|
| Kannada `kan` | `bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8` |
| English `eng` | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |

`kan.traineddata` is the official model downloaded from
`tesseract-ocr/tessdata_fast`. `eng.traineddata` was copied from the Tesseract
5.5.1 Homebrew installation. Both upstream language-data files are Apache-2.0.
