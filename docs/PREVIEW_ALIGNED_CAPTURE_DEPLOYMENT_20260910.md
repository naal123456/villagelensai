# Preview-aligned capture deployment — 2026-09-10

## Outcome

Version `v2026.09.10.3` aligns the visible camera guide, local quality analysis,
page-edge estimate, and saved JPEG to the same source pixels. The client maps
the guide rectangle through the preview's `object-fit: cover` transform and
crops the uploaded image to that rectangle. Areas visible outside the guide are
no longer included in the saved photograph.

The post-tap burst was removed. The camera now keeps up to four locally rendered
guide crops from the preceding moments. On tap it adds the current frame, selects
only among candidates no older than 900 milliseconds, and penalizes older frames
so the result remains close to what the user saw at the shutter moment. This
prevents lowering the phone after tapping from becoming the selected image.

A dashed inner outline displays the likely page extent detected by the existing
local neutral-paper heuristic. It turns yellow when the estimated page is
clipped. The outer guide remains the exact saved crop. No preview frame is sent
to the server; only the selected guide crop is uploaded.

## Evidence from A3-16BC50

The retained source was temporarily inspected and was not added to the
repository. It is a sharp 1080 by 1920 image of the book and surrounding table.
Its recorded quality was sharpness 22.56, motion 8.87, likely-paper coverage
30.86 percent, and page-edge contact 38.45 percent. The mismatch was therefore
consistent with full-sensor capture plus post-tap candidate selection, rather
than an inference failure.

## Verification

- Source commit: `fd72013`
- Tests: `46/46` passed.
- Python compilation, index JavaScript parse, service-worker JavaScript parse,
  and `git diff --check`: passed.
- Cloud Build: `04096c38-ea20-44e1-802e-6fc4b061769f` succeeded.
- Container digest:
  `sha256:7a1543d7184e18bfcd7d49559d50342c36f4e2250bc1b8bb59cfbf49b376b2d8`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated public page contains version `v2026.09.10.3`, guide-to-source
  mapping, guide crop rendering, detected-page outline, and recent-frame limit.
- Physical equivalence between preview and saved crop still requires testing on
  iPhone Safari and the target Android phones.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00041-xxs`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00040-sfb`
