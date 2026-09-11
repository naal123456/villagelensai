# General-object camera deployment — 2026-09-10

## Outcome

Version `v2026.09.10.5` removes the paper/page classifier from camera
readiness. The camera is intended for arbitrary text, packages, plants,
equipment, and other objects. The guide box now has one meaning: only the area
inside it is retained. There is no dashed estimated-page outline.

Readiness is based only on light, glare, sharpness, and motion. The shutter is
available even while the guide is yellow. When pressed, the client requests
centre autofocus and metering when the browser exposes those controls, waits
220 milliseconds for finger movement to begin settling, samples four locally
cropped frames over about 640 milliseconds, and retains the highest-scoring
frame. Only that one image is uploaded, so the burst creates no additional OCR
or inference requests.

Autofocus controls are progressive enhancement. Phones that do not expose
`focusMode` or `pointsOfInterest` still receive the local settle-and-select
burst.

## Field-example diagnosis

The two A3 photographs were inspected transiently and were not added to the
repository.

- The user-reported `A3-2F0353` corresponds to stored capture `A3-2F035E`. It
  is a sharp, well-framed yellow pouch of dog treats. The obsolete classifier
  labelled 26.84% of the frame as paper and reported 88.91% page-edge contact,
  demonstrating that colour-neutral page geometry was not a valid camera gate.
- `A3-7CE1C5` is a sharp, well-framed broad-leaf plant. It likewise produced
  page-candidate and page-edge values even though no document was present.
- Stored semantic inference correctly understood both captures: dog treats in
  the first and a banana-like broad-leaf plant, with uncertainty about exact
  species, in the second.

## Verification

- Source commit: `77ef67c`
- Tests: `46/46` passed.
- Python compilation, index JavaScript parse, service-worker JavaScript parse,
  and `git diff --check`: passed.
- Cloud Build: `20b5e82e-db7a-4adc-97df-be8e404cfab0` succeeded.
- Container digest:
  `sha256:69f338f0d251e31d9dfea5edbe5d840ebccb313a2572844b02891ede36be4a53`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated production page contains version `v2026.09.10.5`, the exact
  box-crop explanation, four-frame selection, centre focus request, and no
  page-clipping or page-outline logic.
- These checks do not replace physical camera testing on iPhone Safari and the
  target Android phones.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00043-w4r`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00042-qf8`
