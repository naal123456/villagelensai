# Google Cloud POC architecture

Date: 2026-08-30
Status: repository initialized; Google project and billing authorization pending

## Objective

Run the existing still-photo guided-reading experience independently of the
development Mac for two controlled testers in India. The domain can be attached
after temporary GitHub Pages and Cloud Run URLs pass acceptance testing.

## Architecture

```text
iPhone Safari
  -> GitHub Pages client at /a
  -> Cloud Run API in asia-south1 (Mumbai)
       -> repository-local Tesseract kan+eng
       -> Google Cloud Vision Kannada/English OCR
       -> OpenAI fast whole-image reading
       -> OpenAI careful whole-image reading
       -> deterministic word/line alignment and consensus
       -> browser or Google kn-IN speech
       -> Firestore feedback/result metadata
       -> optional short-lived capture storage
```

GitHub Actions tests and deploys revisions. It does not process interactive
photographs.

## Four-stage contract

All readers start independently and as concurrently as quotas permit.

- **Stage 1, yellow:** Tesseract text and geometry make the image touchable.
- **Stage 2, light green:** fast OpenAI transcription passes schema and spatial
  validation and improves or confirms the displayed reading.
- **Stage 3, green:** careful OpenAI transcription passes the same validation.
- **Stage 4, dark green:** deterministic fusion finds stronger evidence across
  Tesseract, Google Vision, and OpenAI results.

Stage 4 does not advance merely because providers completed. On unresolved
disagreement, it remains incomplete and the best earlier result remains active.
Future Gemini, Claude, or NVIDIA adapters use this same internal contract and do
not add tester-facing provider controls.

Tesseract and Google Vision provide primary geometry. Vision-language models
provide transcription and meaning. Model-proposed coordinates are supporting
evidence rather than the sole location source.

## Access and user interface

The tester does not use email or enter an access code. A helper opens a one-time
invitation URL, registers the phone, approves camera/audio permission, and adds
the `/a` page to the Home Screen. The backend uses a revocable device token,
daily request limit, image-size limit, bounded concurrency, and an emergency
disable switch.

The interface remains icon- and speech-led. It supports one-word touch reading,
continuous words, continuous sentences, sentence meanings, and a whole-page
explanation. Thin underlines identify touch targets; automatic playback displays
only the item currently being spoken.

## Speech

The research POC uses macOS speech for iPhone audio. Cloud Run cannot use that
facility. The deployed application first qualifies browser `kn-IN` speech and
provides a server audio endpoint backed by Google Cloud Text-to-Speech when
needed. Indian honorific and abbreviation normalization remains an application
responsibility.

## Data and evaluation

For each capture, retain structured evidence:

- capture identifier, checksum, bounded metadata, and device label;
- per-reader text, geometry, latency, status, and failure reason;
- displayed result at each stage;
- consensus agreement and unresolved alternatives;
- word/sentence/page feedback and optional reviewer correction;
- provider usage needed to measure cost per page.

Firestore stores results and feedback. Source images remain ephemeral by default.
Selected evaluation captures may enter a dedicated bucket only with controlled
retention and a short lifecycle.

## Cost and credential controls

- Prefer a dedicated Google project for cost and permission isolation.
- Cloud Run region `asia-south1`, minimum instances `0`, maximum instances `1`.
- No Kubernetes cluster, GPU, or self-hosted large vision model.
- Normalize and bound the image before provider fan-out.
- Cap Google Vision and OpenAI requests independently.
- Keep the OpenAI API key only in Google Secret Manager.
- Configure a low OpenAI project budget and Google billing alerts.
- Exclude image bytes, tokens, authorization headers, and credentials from logs.

Free allowances reduce expected POC cost but do not guarantee a zero bill.

## Owner inputs

1. Create or authorize an isolated Google Cloud project and active billing link.
2. Provide only the project ID and confirmation that billing is enabled.
3. Create a dedicated OpenAI API project with a low budget; enter its key
   directly into Secret Manager rather than chat or repository files.
4. Purchase and delegate DNS for the final domain when available.
5. Provide non-personal labels for the two test devices.

## Implementation order

1. Qualify this static camera shell on iPhone Safari.
2. Promote and containerize the tested Tesseract `kan+eng` capture contract.
3. Reproduce the yellow stage locally with fixtures and browser tests.
4. Replace the macOS audio path.
5. Add validated OpenAI fast and careful adapters.
6. Add Google Vision OCR and geometry.
7. Implement deterministic alignment, consensus, and abstention.
8. Add Firestore feedback, device enrollment, quotas, and cost telemetry.
9. Test I1, I2, AC41 gold, English, mixed-script, sign, page, and phone fixtures.
10. Deploy temporary URLs, qualify from the United States and India, and attach
    the final domain only after acceptance passes.

## Acceptance criteria

- One helper-installed icon; no tester login or typing afterward.
- A touchable initial result survives every cloud-reader failure.
- Later stages update without blocking interaction.
- Kannada audio works on iPhone Safari in India.
- Every displayed word is traceable to geometry and reader evidence.
- Uncertainty produces abstention or retake guidance, never false dark green.
- Feedback, latency, and cost evidence are durably recorded.
- Credentials never reach the browser or Git history.
- Runtime stays within recorded request and spending bounds.
