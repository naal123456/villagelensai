# A4 access-cookie migration

Date: 2026-09-04
Status: deployed and publicly validated; Selvam phone retest pending

## Production evidence

The Android sequence associated with Selvam's A4 attempt showed:

- `POST /access` returned HTTP 303, proving the server accepted both A4 and the
  submitted access code;
- the immediate `GET /a/?tester=a4` returned HTTP 302; and
- the browser then loaded `/access?tester=a4`.

The failure therefore occurred during session-cookie use, after credential
validation. Cookie values are intentionally absent from request logs. The
behavior is consistent with a stale or duplicate legacy cookie: Werkzeug keeps
duplicate cookie values, while the old implementation checked only the first.

## Server-side correction

- New logins receive `villagelens_access_v2`.
- A successful login expires the host-scoped `villagelens_access` cookie.
- Still-valid legacy cookies remain accepted so existing testers are not
  unnecessarily logged out.
- If duplicate legacy cookies arrive, every value is checked and any valid one
  grants access.

The tester does not need to open browser settings or clear cookies. Selvam only
needs to submit A4 and the shared code once more.

## Build and deployment

- Source commit: `93dee44`
- Cloud Build: `e350f200-02f5-4571-b498-45c7a5d364da` (`SUCCESS`)
- Image digest:
  `sha256:7ad27ee93ff46066cd69a5e4c5885533bb37054c3a265a43f36b82264ace6405`
- Cloud Run revision: `vlens-a-93dee44`
- Traffic: 100 percent
- Concurrency: eight
- Minimum instances: zero
- Maximum instances: one

## Validation

- Unit and contract tests: 23/23 passed.
- Python compilation and `git diff --check`: passed.
- Public test began with an intentionally stale legacy cookie.
- A4 login returned HTTP 303 and `/a/?tester=a4` returned HTTP 200.
- The resulting browser session contained only `villagelens_access_v2`.
- The A4-filtered gallery returned HTTP 200.
- Public health returned HTTP 200.
- No error-level logs were present for the revision after validation.

This validates the server migration but does not substitute for the pending
retest on Selvam's actual phone.

## Rollback

Route traffic to `vlens-a-7d9aa90`. Existing `v2` cookies would not be
recognized by that revision, so affected testers would need to log in again.
