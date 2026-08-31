# Swipe gallery deployment checkpoint

Date: 2026-08-30
Status: deployed and HTTP-validated

## Product result

- The approved two-strip reading controls are restored at `/a/`.
- I2 is the default page and uses the independently reviewed eight-word gold
  geometry and text.
- I1 is the second page. Horizontal swipe or the previous/next controls move
  between pages.
- New camera captures are added after the two seed pages and are retained with
  their stage-one Tesseract result for later testing.
- Meaning controls remain visible but explicitly unavailable until a validated
  cloud reader is connected; the interface does not invent an explanation.

## Deployment evidence

- Source commit: `ffb63188a9b7e9fcd8c005b5cc00ebf2e50f669e`
- Cloud Build: `47ba6829-8ef5-40aa-ab9b-bf2a1b38ebee` (`SUCCESS`)
- Container digest: `sha256:c921b1999267b2e2da15176f45b5cb656b55a5700eacb0d770f88fb77b7db49f`
- Cloud Run revision: `vlens-a-ffb6318`, 100 percent traffic
- Public tester URL: `https://villagelensai.com/a/`
- Generated Cloud Run URL: disabled
- Runtime limits: minimum 0, maximum 1, 1 CPU, 2 GiB, concurrency 1,
  request timeout 90 seconds

Unauthenticated validation returned the expected redirect to `/access`.
Authenticated validation returned `villagelens.gallery.v1` with `demo-i2` and
`demo-i1` as the first two items and confirmed the restored control identifiers.
The focused test suite passed 9/9, `git diff --check` passed, and the embedded
JavaScript passed `node --check` before deployment.

## Capture retention

- Bucket: `gs://villagelensai-captures`, region `us-central1`
- Uniform bucket-level access: enabled
- Public access prevention: enforced
- Runtime identity: `villagelens-runtime@villagelensai.iam.gserviceaccount.com`
- Runtime bucket role: `roles/storage.objectAdmin`
- Automatic lifecycle deletion: none during the controlled evaluation

The browser never receives bucket credentials or a public object URL. It reads
stored images through the access-gated same-origin API.

## Rollback

Route Cloud Run traffic back to revision `vlens-a-code2`. That revision uses
container digest
`sha256:1c4765f824f38e859e210f693d78c28319650e54ea024c9f93e93dd996eaac70`.
Rollback does not delete retained captures.
