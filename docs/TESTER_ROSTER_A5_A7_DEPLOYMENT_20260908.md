# Tester roster A5–A7 deployment

Date: 2026-09-08
Status: deployed and publicly validated

## Roster

The established assignments were preserved:

- A1: Eeregowda
- A2: Umesh
- A3: Reviewer
- A4: Selvan

Previously unassigned entries were named:

- A5: Kiran
- A6: Rupa
- A7: Akul

No historical capture identity was changed. A8 through A10 remain available and
unnamed. Passwordless links were generated from the existing secrets, validated
against production, given only to the owner, and not stored in this repository.

## Deployment and validation

- Source commit: `fbd760e`
- Tests: 39/39 passed
- Cloud Build: `1c597167-6b4d-4ae7-bb99-15a54353fe8e` (`SUCCESS`)
- Image digest:
  `sha256:f93ef8eacd5b883be62607ba2bed01e14cbc1e1e5cc973f9512f9b88d1649de7`
- Cloud Run revision: `vlens-a-fbd760e`, 100 percent traffic
- A1, A2, A4, A5, A6, and A7 passwordless exchanges: HTTP 200
- Assigned reader pages after exchange: HTTP 200
- No error-level production logs after deployment

Production limits and secret mappings are unchanged. Route traffic back to
`vlens-a-2eb9d8f` to roll back the visible tester-name additions.
