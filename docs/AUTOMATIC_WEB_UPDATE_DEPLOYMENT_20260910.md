# Automatic web update deployment — 2026-09-10

## Outcome

All tester sessions now request the main `/a/` application page with
`Cache-Control: no-store, max-age=0`. This applies equally to ordinary browser
links and home-screen launches. The manifest and service worker use explicit
revalidation headers.

On every launch, the application registers its service worker with
`updateViaCache: none` and explicitly checks for an update. If a new worker takes
control of an already-running installed application, the application reloads
once. New installations do not receive an unnecessary first-launch reload.

The top status row displays `v2026.09.10.1`, allowing remote support to identify
a stale screen from a screenshot or phone call. The install action now gives
spoken Kannada guidance when native installation is not directly available and
reports whether an Android native prompt was accepted or cancelled.

Phone operating systems still require a person to approve installation once.
In particular, iOS requires Safari Share followed by Add to Home Screen; a web
application cannot bypass that security requirement. Updates after that initial
installation require no tester action.

## Verification

- Source commit: `f8304aa`
- Tests: `46/46` passed.
- Python compilation, index JavaScript parse, service-worker JavaScript parse,
  and `git diff --check`: passed.
- Cloud Build: `2e747246-fe8f-4a3c-a086-175cb48b2dbd` succeeded.
- Container digest:
  `sha256:c5e8af23e0aae6866cc1b1a6b68b076504c3cb94f03ee81f5b88dd7ad26332e1`
- Public health: status `ok`, access gate enabled, no missing models.
- Authenticated public page returned `Cache-Control: no-store, max-age=0` and
  contained the visible version and forced update check.
- Public service worker returned `Cache-Control: no-cache, max-age=0` and the
  expected application version.
- Installation and update behavior still require confirmation on the field
  Android phones and iPhone Safari.

## Deployment

- Production service: `vlens-a`, `us-central1`
- Revision: `vlens-a-00039-4rb`
- Traffic: 100%
- Limits: min 0, max 1, 1 CPU, 2 GiB, concurrency 8, timeout 90 seconds
- Rollback revision: `vlens-a-00038-jsh`
