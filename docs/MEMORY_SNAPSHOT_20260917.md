# VillageLensAI recovery snapshot — 2026-09-17

Use this document to resume if conversational context is lost. It records the
deployed smartphone project and its relationship to the new wearable project.
Do not treat it as authorization to deploy or spend money; follow `AGENTS.md`.

## Mission and product state

VillageLensAI is a still-image reading and learning assistant designed first
for Kannada-speaking adults with low literacy. Field testing showed that users
value contextual inference especially strongly: Eeregowda used it to understand
a calendar and his daughter's school material; Umesh used it for English labels
on adapters, machinery, and roadside products. The same interface now supports
an English output mode for reading unfamiliar Indian and other scripts.

The phone web application is the current working product. The new
`villagelens-wearable` repository is a dependent hardware track whose first
phase replaces only the phone camera with a Raspberry Pi autofocus camera. It
must reuse this project's session, gallery, language, OCR, inference, question,
and audio behavior through a narrow capture bridge.

## Source and production milestone

- Repository: `https://github.com/naal123456/villagelensai`
- Branch at snapshot creation: `main`
- Source HEAD before this snapshot: `04fc3bd`
- Deployed application source: `ff83086`
- Application version: `2026-09-17.1`
- Cloud Run service: `vlens-a`, project `villagelensai`, region `us-central1`
- Live revision: `vlens-a-00075-mpm`, receiving 100 percent of traffic
- Build: `339c8312-ca91-4175-9ab6-cf8a719e1b0a`
- Container digest:
  `sha256:00c3b6c357aaca48f3a21dddc1e04096d0ce85c3359fd8702710536441548ca5`
- Controlled POC runtime: minimum zero, maximum one, concurrency eight
- Rollback revision: `vlens-a-00074-jmt`
- Last recorded verification: 75/75 tests, public health HTTP 200, no missing
  OCR models, authenticated A3 page HTTP 200, and empty error-level logs after
  deployment validation.

The post-deployment documentation commit did not require a second deployment.
See `docs/FOCUS_URDU_LANGUAGE_REUSE_DEPLOYMENT_20260917.md` for evidence.

## Current reader architecture

One unified route, `/a/?tester=<id>`, toggles output between Kannada and English.
Legacy `/b` redirects into the same application with English selected.

The four visible evidence stages are:

1. repository-pinned Tesseract `kan+eng`, strengthened by Google Vision OCR;
2. `gpt-5.6-luna` compact understanding, automatic;
3. `gpt-5.6-terra` full contextual understanding, automatic; and
4. `gpt-5.6-sol` strongest review, only when the user taps the fourth bar.

The source image is uploaded once. Retained images and complete stage evidence
are reused without repeated model calls. A first switch between English and
Kannada reuses visual analysis and translates only user-facing narrative fields
with `gpt-5-mini`; later switches reuse both stored language results. It should
not rerun 50-second image analysis merely because the output language changed.

The camera remains manual. It captures a four-frame burst inside the adjustable
guide and retains the clearest frame. Camera readiness now tolerates normal hand
tremor and holds green briefly; orange does not prohibit manual capture.

Kannada uses authenticated server-generated speech. English uses the phone
voice. Arabic Unicode script is handled conservatively as “Urdu / Arabic
script” and uses `ur-IN` speech. Language identification should not claim that
script alone proves a precise language.

## Tester roster

- A1: Eeregowda
- A2: Umesh
- A3: owner/reviewer
- A4: Selvan
- A5: Kiran
- A6: Rupa
- A7: Akul
- A8–A10: reserved/unassigned unless a later record says otherwise

A3 can review cross-cohort captures. Other testers see their own captures. Do
not change this roster without an explicit owner instruction.

## Durable product decisions

- Preserve the low-literacy, Kannada-first mission even as multilingual and
  education uses expand.
- Make inference useful and human: identify the object/page, explain its
  purpose and context, preserve numbers with units, teach rather than merely
  repeat OCR, and express uncertainty.
- A completed provider call is not proof of correctness.
- Only one control is active at a time; changing controls stops current audio.
- Spoken questions remain contextual to the selected image, region, and prior
  conversation.
- Cache completed evidence and speech; navigation must not trigger repeated
  paid inference.
- Keep photographs, audio, credentials, access codes, and raw provider payloads
  out of Git.
- Stage 4 is optional and never runs automatically.
- Gemini/Astra experiments are not in the production reader pipeline.
- Continuous video and general control of WhatsApp or other phone applications
  remain outside this browser POC.

## Latest field observations and remaining checks

- A3-42, A3-43, and A3-44 were readable even when the old focus gate stayed
  orange; the relaxed threshold is deployed but still needs physical retesting.
- A3-42 contains Urdu/Arabic script. The missing speech path was repaired and a
  production speech sample returned HTTP 200.
- A3-44 contains stylized Malayalam packaging. OCR missed the stylized product
  word while stronger inference recovered the product identity. Preserve that
  distinction; do not fabricate a word box.
- Confirm on physical iPhone Safari that the relaxed focus state feels stable,
  Urdu speech is audible, and the first language switch retains completed bars.
- Continue testing new camera captures in both output languages. Handwriting,
  curved pages, distant signs, glare, and mixed scripts remain difficult.
- Maintain the handwriting registry; the first samples are valuable evaluation
  evidence, not disposable troubleshooting files.

## Resume procedure

1. Read `AGENTS.md`, this snapshot, `README.md`, and
   `docs/FOCUS_URDU_LANGUAGE_REUSE_DEPLOYMENT_20260917.md`.
2. Run `git status --short` and preserve any user changes.
3. Confirm production health/version before diagnosing a field report.
4. Reproduce against the named tester/image and distinguish cached historical
   evidence from the current pipeline.
5. Add focused tests, run the repository validation suite, document any
   deployment and rollback, then commit before deploying.
6. Never retrieve or print secrets into logs or committed files.

## Parallel project boundaries

- `../villagelens-wearable`: Raspberry Pi camera, quality gate, capture bridge,
  physical I/O, calibration, CAD, and hardware qualification.
- `../villagelens-model-eval`: reproducible model accuracy, latency, and cost
  evaluation; it must not silently change production routing.
- `../smart-glasses-phase1`: research archive, not the deployable web product.
