# Passwordless tester links deployment

Date: 2026-09-04
Status: deployed and publicly validated; tester-phone confirmation pending

## Outcome

The owner can send A1–A5 individual links through WhatsApp. A tester taps the
assigned link and is automatically enrolled without selecting a user or typing
the Latin-script access code. Enrollment also issues the versioned access cookie
and expires the host-scoped legacy cookie.

The signed credential is carried after the URL `#` fragment. Browsers do not
send fragments in HTTP requests, so it is absent from Cloud Run request URLs.
The access page exchanges it in a POST body, removes it from the address bar,
and opens the assigned reader. Form bodies and token values are not logged.

Anyone holding a tester's link can access that tester's retained gallery. Links
must therefore be shared only with their assigned tester and are not stored in
the repository. Changing either the access code or session-signing secret
invalidates every link.

## Build and deployment

- Source commit: `df16cc0`
- Cloud Build: `f85c2b06-1d82-4e52-bf80-dbaaa5db8efa` (`SUCCESS`)
- Image digest:
  `sha256:bd19c4209ba241ac95a996eb9c1407c9e6923047d9d943967224f8136390ffae`
- Cloud Run revision: `vlens-a-df16cc0`
- Traffic: 100 percent
- Concurrency: eight
- Minimum instances: zero
- Maximum instances: one

## Validation

- Unit and contract tests: 26/26 passed.
- Python compilation, rendered access-page JavaScript syntax, and
  `git diff --check`: passed.
- Invalid signed links return HTTP 401.
- A1, A2, A3, A4, and A5 were each tested against production: access page HTTP
  200, passwordless exchange HTTP 200, assigned reader HTTP 200.
- Actual signed links were not committed or written to this document.

This validates browser-independent server behavior and rendered JavaScript. It
does not replace the pending tap test from WhatsApp on Eeregowda's and Selvam's
phones.

## Rollback

Route 100 percent of traffic to `vlens-a-93dee44`. The conventional user and
code form remains available in both revisions.
