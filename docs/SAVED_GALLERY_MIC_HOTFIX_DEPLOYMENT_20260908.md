# Saved-gallery microphone hotfix deployment

Date: 2026-09-08
Status: deployed and production-page validated; physical-phone recording check pending

## Outcome

The microphone can now start on retained photographs loaded from the gallery.
Gallery records expose their retention state inside `item.result.retained`, while
newly captured records may expose it as `item.retained`. The previous microphone
guard checked only the latter form, so it rejected every previously saved image
before requesting microphone permission.

The guard now accepts either representation. It also shows an explicit crossed
microphone indicator and bilingual explanation when the selected item is a demo
image or the browser does not expose microphone recording.

## Deployment and validation

- Source commit: `4e9dd78`
- Tests: 41/41 passed
- Diff check: passed
- Cloud Build: `152caaf1-0350-46c1-8305-f87a8dcf6dd0` (`SUCCESS`)
- Image digest:
  `sha256:07e65b5e03378963a7f670bf7a72db38aa175bfce84e8cb09530db5da1542ef7`
- Cloud Run revision: `vlens-a-4e9dd78`, 100 percent traffic
- Public A3 access-code login: HTTP 303
- Public authenticated reader page: HTTP 200 and contains the corrected
  saved-gallery retention check
- No error-level Cloud Run log entry was present after the smoke test
- Limits preserved: maximum one instance, 1 CPU, 2 GiB, concurrency eight, and
  a 90-second request timeout; minimum instances remains zero

The earlier recorded-audio server-path validation remains applicable. This
deployment validates the browser asset and production route, but it does not
prove microphone permission or recording on a physical Safari or Chrome phone.

## Rollback

Route 100 percent of traffic to `vlens-a-cdfca0e`. That revision contains the
recorded-audio endpoint but incorrectly rejects retained images loaded from the
gallery.
