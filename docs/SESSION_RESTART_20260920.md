# VillageLensAI session restart — 2026-09-20

This is the primary restart file for the VillageLensAI smartphone/web project.
Read it after `AGENTS.md` if the prior Codex conversation is unavailable. It
supersedes `MEMORY_SNAPSHOT_20260917.md` for current state while retaining that
document as historical context.

## Resume instruction

Work in:

```text
/Users/nn/nnagarajayya/missionlens-v2/villagelensai
```

Read, in order:

1. `AGENTS.md`
2. this file
3. `README.md`
4. `docs/IPHONE_PHOTO_IMPORT_DEPLOYMENT_20260918.md`
5. `docs/FOCUS_URDU_LANGUAGE_REUSE_DEPLOYMENT_20260917.md`
6. `docs/CURRENT_ARCHITECTURE_20260912.md`

Then run `git status --short` and preserve any user changes. Do not infer
authorization to deploy, spend money, implement deferred ideas, modify tester
assignments, or access private captures merely from this snapshot.

## Current outcome

VillageLensAI has become a practical multilingual reading and learning tool:

- Eeregowda and Umesh can photograph everyday material and hear Kannada reading
  and contextual meaning.
- A3, the owner/reviewer on iPhone, can photograph or import screenshots and
  saved images containing Kannada or other languages and understand them in
  English.
- The owner physically tested the new Photos flow and described it as
  “excellent.” This is the latest product acceptance signal.
- On 2026-09-22, the owner reported that icon-only capture A3-49 correctly
  identified the windshield-washer-fluid reservoir cap in the frunk of their
  Tesla Model 3 Standard. The result gave the owner enough context to locate
  the washer-fluid refill point after unrelated online videos had been
  misleading. This is qualitative field evidence, not a general accuracy or
  vehicle-maintenance safety claim; the source photograph remains private.
- On 2026-09-23, the owner reported that A3-50, a mixed Chinese/English mooncake
  package, was understood correctly by contextual inference while the word and
  sentence controls misidentified Han text as English and did not pronounce it.
  The authorized diagnosis found that cloud OCR retained Chinese regions and
  stage 3 covered the primary text, but the browser and speech API lacked a Han
  script route. A local `2026-09-23.1` repair adds conservative “Chinese / Han
  script” identification, mixed Chinese/English segmentation, Mandarin server
  speech, and translation routing tests. It has passed 78 tests and static
  checks but is not committed, pushed, or deployed.
- Imported WhatsApp screenshots and saved document photographs use the same
  retained OCR, inference, language, audio, gallery, and question pipeline as
  camera captures.

The product mission remains literacy and useful knowledge access for people
such as Eeregowda and Umesh. Multilingual reading for fluent users and future
school learning are valuable extensions, not replacements for that mission.

## Source and deployed production

- Repository: `https://github.com/naal123456/villagelensai`
- Branch: `main`
- Photo-import code commit: `ce9e2fb`
- Photo-import deployment record commit: `baf3f0b`
- Application version: `2026-09-17.2`
- Cloud project/service/region: `villagelensai` / `vlens-a` / `us-central1`
- Live revision: `vlens-a-00076-98l`, 100 percent traffic
- Image: `gcr.io/villagelensai/vlens-a:ce9e2fb`
- Container digest:
  `sha256:6fd2da9a1d987ba7270e064758f8b817b21ed963148d1ce869ea2d65789b498b`
- Cloud Build: `571feed8-63f5-4e61-8940-ad9a9bdf99c3`
- Public health rechecked 2026-09-20: HTTP 200, access gate enabled, no missing
  OCR models, version `2026-09-17.2`
- Last full local validation: 76/76 tests plus Python compilation, embedded
  JavaScript parsing, and `git diff --check`
- Rollback: route traffic to `vlens-a-00075-mpm` (`2026-09-17.1`)

Documentation-only commits after `ce9e2fb` do not require another deployment.

## Current interface and processing behavior

The unified `/a/?tester=<id>` application toggles output between Kannada and
English. A3 defaults to English. The primary toolbar now has separate sources:

- blue `🖼️` Photos: choose an existing JPEG, PNG, or WebP from the phone;
- orange `📷` Camera: open the guided live camera.

Photos selection is tagged `photo-library-v1`, labeled “Imported photo” in
English, and immediately enters the existing capture pipeline. PDF, DOCX,
multiple-image import, clipboard import, and a native iOS share extension have
not been implemented.

Evidence stages remain:

1. Tesseract `kan+eng` plus Google Vision OCR;
2. automatic `gpt-5.6-luna` compact understanding;
3. automatic `gpt-5.6-terra` contextual understanding; and
4. manual-only `gpt-5.6-sol` strongest review.

Stage 4 must never run automatically. Saved evidence, audio, and visual
analysis are reused. Switching output language translates user-facing narrative
without rerunning image analysis when compatible visual evidence exists.

## Tester roster

- A1: Eeregowda
- A2: Umesh
- A3: owner/reviewer
- A4: Selvan
- A5: Kiran
- A6: Rupa
- A7: Akul
- A8–A10: reserved/unassigned unless the owner explicitly changes them

A3 can review captures across cohorts. Other users see their own captures. Do
not change the roster from inference or rename existing retained captures.

## Confirmed product principles

- Read visible source material first, then explain it in the chosen language.
- Keep inference contextual, human, educational, and grounded in the image.
- Preserve numbers with their units and preserve calendar/table relationships.
- Express uncertainty; a completed model call is not proof of correctness.
- Cache results so navigation and language switching do not repeat paid calls.
- Only one reading/action control is active at a time.
- Keep user questions contextual to the image, selected region, and prior turns.
- Keep credentials, access codes, photographs, audio, personal messages, and
  raw provider payloads out of Git and ordinary logs.
- Imported WhatsApp screenshots are currently retained like camera captures.
  Use non-sensitive samples until a separately authorized temporary/private mode
  is designed.

## Discussed future directions — do not implement yet

The owner explicitly asked to celebrate and discuss these ideas without making
changes. They are not an active implementation request:

### Writing in another language

Potential flow: understand incoming material, compose a reply in English or by
voice, generate a natural target-language response, show the English back-
translation, speak it for verification, then copy/share it. This could help A3
reply in Kannada and eventually help low-literacy users compose messages.

### Learning and schools

Potential learning ladder: alphabet, sound, word, sentence, grammar, object,
concept, practice, and recall. A future school experience should distinguish:

- Read — what does this say?
- Understand — what does this mean?
- Learn — teach it step by step.

For homework, prefer explanation and progressive hints over simply producing
answers. Any school pilot needs permission, age-appropriate behavior, private
captures, minimal collection of names/faces, uncertainty, and special care for
medical, chemical, machinery, or other safety claims.

### Deferred input formats and native integration

- PDF/document upload may be useful later but was deliberately deferred while
  Photos is tested.
- A native iOS Share Extension could eventually support WhatsApp → Share →
  VillageLens. The current iPhone flow is screenshot → VillageLens → Photos.
- General phone/WhatsApp control is not available from the browser POC.

## Parallel project boundaries

- `../villagelens-wearable`: Raspberry Pi autofocus camera as an external eye,
  quality selection, secure capture bridge, physical I/O, calibration, and CAD.
  Its first phase reuses this phone/browser pipeline rather than copying it.
- `../villagelens-model-eval`: repeatable model accuracy, latency, and cost
  evaluation. It must not silently change production routing.
- `../smart-glasses-phase1`: prior research archive, not this deployable app.

## Safe next-turn procedure

1. Ask for or receive the owner's newest test observation; do not invent a new
   feature priority from the deferred ideas above.
2. Identify the exact tester and capture label when diagnosing image behavior.
3. Distinguish cached historical evidence from current-version results.
4. For changes, add focused tests and run the complete suite before committing.
5. For deployment, bump all synchronized version locations, preserve Cloud Run
   minimum zero/maximum one/concurrency eight, verify public health and traffic,
   record the build/digest/revision/rollback, and obtain physical-device
   confirmation before claiming full acceptance.
6. Commit and push documentation snapshots; never put secrets or field content
   into them.

## Suggested prompt for a restarted Codex session

> Work in `/Users/nn/nnagarajayya/missionlens-v2/villagelensai`. Read
> `AGENTS.md` and `docs/SESSION_RESTART_20260920.md` completely before acting.
> Preserve existing user changes and production cost/privacy controls. Continue
> from the deployed iPhone Photos-import milestone only after reviewing the
> owner's newest field feedback. Treat the writing, school-learning, PDF, and
> native-share ideas as deferred discussion unless the owner explicitly asks to
> implement one.
