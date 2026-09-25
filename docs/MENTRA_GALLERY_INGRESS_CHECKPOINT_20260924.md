# Mentra Live gallery ingress checkpoint — 2026-09-24

## Status

The isolated `/c` implementation now has a tested, still-photo-only Mentra
ingress contract. It is not deployed and has not yet been exercised with the
physical glasses. No paid service, continuous stream, camera recording, or new
cloud resource was enabled.

## Boundary

The browser owner explicitly presses Mentra Camera and then requests one photo.
That creates an expiring browser session and a one-time companion pairing code.
The companion exchanges the code for a single request identifier, short-lived
bearer credential, and HTTPS webhook URL. The credential is returned only to
the companion and stored server-side only as a SHA-256 digest.

The official Mentra SDK can then issue `requestPhoto` with that request
identifier, webhook, and authorization token. The server accepts only the
SDK's multipart `photo` plus matching `requestId`, enforces the configured
image-size and media-type limits, hashes the original bytes, and calls the same
`_ingest_capture` helper used by the phone and Pi paths. It does not copy the
gallery, OCR, language, or reader pipeline.

The capture is recorded as `mentra-live-v1` with
`villagelens.mentra-capture-provenance.v1`, including the request identifier,
device model, explicit-still mode, SDK webhook transport, receive time, source
byte count, and source SHA-256. Retries of identical bytes are idempotent;
different bytes for a completed request fail closed.

Browser polling reports only `waiting_for_companion`, `waiting_for_photo`, or
`complete`. On completion, `/c` loads the existing gallery and opens the new
capture directly. Pairing and upload state is memory-only and intentionally
expires. Tester identity and language are not sent to the companion or glasses.

## Why Bluetooth is not the image transport

Mentra's public Bluetooth SDK uses Bluetooth for discovery, connection,
commands, buttons, and status. Its photo API sends the capture command over
Bluetooth, then delivers the photo to an HTTPS webhook. RTMP, SRT, and WHIP
streaming require a reachable network endpoint and active glasses Wi-Fi. The
VillageLens target is therefore BLE control plus Wi-Fi media, not multi-megabyte
image transfer over BLE.

Primary references:

- https://github.com/Mentra-Community/Mentra-Bluetooth-SDK-Starter-Kit/blob/main/docs/api-reference.md
- https://github.com/Mentra-Community/Mentra-Bluetooth-SDK-Starter-Kit/blob/main/docs/hardware-integration.md
- https://mentraglass.com/live

The SDK and example applications are published source. That does not establish
that Mentra's production PCB layout, optical stack, antenna design, battery
packaging, injection-moulding CAD, or complete manufacturing files are open.
Do not treat public software access as a license or mechanical specification
for cloning the product.

## Verification

Deterministic coverage includes:

- valid tester and language requirements;
- tester-isolated browser status;
- one-time, expiring pairing;
- no tester identity in the companion contract;
- bearer authorization before multipart photo processing;
- matching request identifier and supported media type;
- existing gallery-ingest reuse and Mentra provenance;
- immutable source hashing, idempotent retry, and source-conflict rejection;
- access-gate behavior; and
- `/c` UI markers while `/a` and `/b` route behavior remains unchanged.

The complete server suite passes 110 tests. Embedded browser JavaScript,
service-worker JavaScript, Python compilation, and whitespace checks pass.

## Remaining physical work

1. Build or install a pinned native iOS companion using the official Mentra
   SDK; normal iPhone Safari cannot replace that native BLE integration.
2. Pair the physical glasses and verify their current firmware capabilities.
3. Request one non-sensitive still with the camera light and sound active.
4. Confirm source hash, dimensions, gallery arrival, reading, and timing.
5. Compare that image with the Pi Camera Module 3 on the same target, distance,
   and lighting.
6. Consider a finite live-preview experiment only after still capture passes.

The wide fixed-focus camera remains an evaluation candidate. It must not replace
the Pi autofocus reference until text-pixel density, readability, latency, and
repeatability are measured.

## Rollback

Before deployment, rollback is reverting this isolated commit. After a future
deployment, route traffic to the prior production revision and stop using the
Mentra companion. All sessions and upload credentials are ephemeral; rollback
does not delete already retained gallery captures.
