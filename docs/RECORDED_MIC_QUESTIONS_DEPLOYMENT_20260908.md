# Recorded microphone questions deployment

Date: 2026-09-08
Status: deployed and server-path validated; physical-phone permission check pending

## Outcome

The microphone no longer depends on browser `SpeechRecognition`, which could be
present but fail without useful feedback. On a saved photograph, the first tap
records through the phone microphone and the second tap submits the question.
Recording stops automatically after 15 seconds. Selecting another control
cancels the recording.

The interface visibly reports microphone permission, active recording, question
preparation, and failures in Kannada and English. Audio is accepted up to 4 MiB,
transcribed using `gpt-4o-mini-transcribe`, and passed to the existing contextual
image question reader. Neither recorded audio nor its transcript is stored by
VillageLens.

The transcription integration follows the official OpenAI model documentation:
https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe

## Deployment and validation

- Source commit: `cdfca0e`
- Tests: 41/41 passed
- Browser JavaScript parse, Python compilation, and diff checks: passed
- Live direct transcription contract: synthetic speech was transcribed exactly
- Cloud Build: `d4eb24d4-09e8-4edd-95dc-04f220260c66` (`SUCCESS`)
- Image digest:
  `sha256:408f500cb09dae2aa44e3a95eaa9b0daf7eaebc3eb901b035e91bb9c03583381`
- Cloud Run revision: `vlens-a-cdfca0e`, 100 percent traffic
- Public reader contains MediaRecorder capture and no browser SpeechRecognition path
- Public end-to-end audio question: HTTP 200 in 15.5 seconds, Kannada answer and
  evidence region returned
- No error-level production logs after validation

Production instance, resource, timeout, storage, and secret limits are unchanged.
The remaining validation is a real microphone-permission and audible-answer test
on the physical iPhone and Android tester phones.

## Rollback

Route traffic back to `vlens-a-fbd760e`. That revision retains the older browser
speech-recognition behavior.
