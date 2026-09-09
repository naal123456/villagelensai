# Conversational image questions deployment

Date: 2026-09-09
Status: deployed and production-validated; physical-phone UI check pending

## Outcome

Voice questions are now a bounded, image-scoped conversation instead of
independent one-shot requests. Each follow-up includes up to six prior
question/answer turns and the last selected or answered image region. References
such as “this leaf” can therefore remain attached to the same visual subject.
The most recent evidence box stays visible while the next question is recorded
and answered.

The recognized question and Kannada answer are shown in a conversation beneath
the image. Tapping an answer speaks it again. Conversations are held only in the
current browser session and are not stored on the server. Recorded audio is also
not stored.

A visible elapsed-seconds timer starts when recording stops and continues
through transcription and image inference. It stops only when an answer or
error is returned.

The incorrect saved-image limitation was caused by stage-two Google OCR
replacing the stage-one result that contained the `retained` flag. Gallery
captures now carry an explicit top-level saved flag independent of OCR results.
The two bundled demo images also have a dedicated audio-question route, so I1
and I2 no longer need a microphone restriction.

Plant-health prompts describe visible signs but explicitly avoid diagnosing a
disease from a photograph alone.

## Deployment and validation

- Source commit: `280a324`
- Tests: 42/42 passed
- Embedded JavaScript, Python compilation, and diff checks: passed
- Cloud Build: `4f1414ec-a905-4bbe-98fd-20b67c0f56cb` (`SUCCESS`)
- Image digest:
  `sha256:0327e083ef092502a2dce66ebcfe0002a9dd5e9459f9a6630d208ab42ed7d56e`
- Cloud Run revision: `vlens-a-280a324`, 100 percent traffic
- Authenticated production page and gallery: HTTP 200
- All 20 stored gallery captures exposed `retained: true`
- Production image-15 follow-up: HTTP 200 in 16.4 seconds
- The follow-up used a prior “this is a leaf” answer and the leaf region; the
  response discussed that leaf, returned the identical evidence box, described
  visible marks, and retained diagnostic uncertainty
- Limits preserved: minimum zero and maximum one instance, 1 CPU, 2 GiB,
  concurrency eight, and a 90-second request timeout
- No error-level log entry was present after production validation

This validates the server conversation contract and deployed browser assets. It
does not prove the conversation layout, focus persistence, or timer behavior on
a physical tester phone.

## Rollback

Route 100 percent of traffic to `vlens-a-b5de313`. That revision has working
recorded questions and microphone diagnostics but treats each question as a new
conversation and can lose saved status after Google OCR replaces the result.
