# Phone microphone diagnostics deployment

Date: 2026-09-09
Status: deployed; physical-phone result pending

## Finding

The reporting iPhone loaded the saved-gallery microphone revision in Chrome and
continued sending normal action events, but production received no
`/ask-audio` request. The A3 gallery contract also contained valid retained
capture IDs. This places the remaining failure before upload, in browser
permission or client-side recording.

## Change

The microphone button and a new sticky bilingual status banner now expose every
client phase:

- `…` while requesting the microphone
- red `⏹` while recording
- `⏳` while preparing and uploading the question
- a persistent explanation with a safe browser error code when permission,
  recording, or upload fails

On iPhone permission denial, the banner points to the Safari or Chrome
microphone setting. The recorder now requests one-second data chunks, following
the WebKit MediaRecorder example. Privacy-safe phase events distinguish tap,
permission, recording, and upload without logging audio or recognized speech.

References:

- https://webkit.org/blog/11353/mediarecorder-api/
- https://support.apple.com/en-euro/guide/iphone/iph168c4bbd5/ios

## Deployment and validation

- Source commit: `b5de313`
- Tests: 41/41 passed
- Embedded JavaScript, Python compilation, and diff checks: passed
- Cloud Build: `175de4c0-5c70-4d4e-a844-e990caa6c009` (`SUCCESS`)
- Image digest:
  `sha256:64f898debb9ac0f2c32d741adbeefabe95926dbbc80763b066161e5bbab399f8`
- Cloud Run revision: `vlens-a-b5de313`, 100 percent traffic
- Authenticated public reader: HTTP 200 and contains the new recording,
  permission, and diagnostic states
- Limits preserved: maximum one instance, 1 CPU, 2 GiB, concurrency eight, and
  a 90-second request timeout; minimum instances remains zero
- No error-level log entry was present after the production smoke test

This validates the deployed client and server assets, not microphone permission
or recording on the physical phone.

## Rollback

Route 100 percent of traffic to `vlens-a-4e9dd78`.
