# Mobile gallery reliability deployment — 2026-10-06

## Outcome

VillageLensAI `2026-10-06.1` is deployed to staging and production. The repair
responds to field tests on Eeregowda's, Selvan's, Kiran's, and the owner's
phones:

- mobile browsers that opened the app with an unusually wide layout receive a
  larger, full-width fallback interface;
- browser scaling is no longer disabled, and gallery images support bounded
  two-finger zoom plus one-finger panning while enlarged;
- the A3 reviewer has no-typing tester and capture selectors for the large
  shared gallery;
- the current tester and output language are visible beside the version;
- retained captures make one phone-to-server processing request, while the
  server continues to run automatic stages 1–3 concurrently; and
- an empty successful cloud OCR result replaces noisy local OCR instead of
  leaving false reading underlines on non-text images.

Stage 4 remains manual. Tesseract still supplies the immediate result, and no
video, stream, new service, or new paid capability was enabled.

## Field diagnosis

The private screenshots and photographs were inspected locally and were not
added to Git. Retained evidence established that A3-63 completed automatic
stages 1–3 quickly, while A3-64 retained stage 1 during the original phone
session and completed stages 2–3 only when revisited later. The old client sent
three parallel keepalive requests from the phone; the replacement uses the
existing bulk endpoint so a phone maintains one request and the server owns the
parallel work.

A3-63 is the peacock-feather capture. It belongs to A3 because Selvan's phone
was enrolled as A3 when it was taken; it was not renamed. Selvan's correctly
enrolled first capture remains A4-1. A successful but empty cloud OCR result on
A3-63 previously left the immediate local false positives visible, which the
new replacement rule corrects.

## Source and verification

- Source commit: `57387f1` (`Improve mobile gallery reliability and zoom`).
- Application version: `2026-10-06.1`.
- Complete server suite: 125/125 passed.
- Python compilation, embedded JavaScript parsing, service-worker JavaScript
  parsing, and `git diff --check`: passed.
- Cloud Build: `33c02a96-d1ed-4ec3-8ab4-9fb2ca4d7231` (`SUCCESS`).
- Image: `gcr.io/villagelensai/vlens-pi-c-test:57387f1`.
- Immutable digest:
  `sha256:afd4be15d8667756a3712eda0ec5b61bd4451012e733857a8dc680cfb4ab546e`.

## Staging

- Service: `vlens-pi-c-test`, region `us-central1`.
- Revision: `vlens-pi-c-test-00021-zuq`, 100 percent traffic.
- Previous traffic revision: `vlens-pi-c-test-00014-x5x`.
- Candidate health and promoted health: HTTP 200, version `2026-10-06.1`,
  access gate enabled, no missing local OCR models, and stage 4 manual.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302.
- Unauthenticated native device job poll: HTTP 401.
- Error-level candidate logs: empty.

The candidate was created with no traffic, validated through a temporary tag,
and then promoted. The temporary tag was removed afterward.

## Production

- Service: `vlens-a`, region `us-central1`.
- Revision: `vlens-a-00166-tav`, 100 percent traffic.
- Rollback revision: `vlens-a-00087-s9f`.
- Public domain: `https://villagelensai.com`.
- Public health: HTTP 200, version `2026-10-06.1`, access gate enabled, no
  missing local OCR models, and stage 4 manual.
- Unauthenticated `/a`, `/b`, and `/c`: HTTP 302.
- Unauthenticated native device job poll: HTTP 401.
- Error-level candidate and post-promotion logs: empty.

Production uses the exact immutable digest qualified on staging. The
production service did not publish a usable candidate URL, so the no-traffic
revision's digest, readiness, container health, limits, and logs were checked
before promotion; public validation followed immediately after promotion.

Both services retain concurrency eight, a 3,600-second timeout, minimum
instances zero, maximum instances one, and their existing runtime identities
and secret configuration.

## Rollback

Return production traffic to the preceding production revision:

```sh
gcloud run services update-traffic vlens-a \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-a-00087-s9f=100
```

Return staging traffic to its preceding traffic revision:

```sh
gcloud run services update-traffic vlens-pi-c-test \
  --project villagelensai --region us-central1 \
  --to-revisions vlens-pi-c-test-00014-x5x=100
```

## Remaining validation

Automated, candidate, and public-route validation is complete. Physical phone
confirmation is still required for the wide-display fallback, pinch/pan
behavior, long-gallery navigation, and one-request stage reliability. Full
end-to-end readiness is not claimed until the public URL is retested on iPhone
Safari with camera and Kannada audio. The best next field checks are Eeregowda's
small-display phone, Kiran's pinch gesture, and new captures from correctly
enrolled Selvan/A4 and owner/A3 sessions.
