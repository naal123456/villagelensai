from __future__ import annotations

import io
import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from api.app import (
    _access_token, _filter_local_regions, _normalize_stage_three,
    _openai_question, _openai_reader, _openai_transcribe, _openai_translate, _parse_tsv,
    _process_stored_capture, _process_stored_stage, _saved_scene_identity_answer,
    _tester_link_token, app,
)


TSV = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
1\t1\t0\t0\t0\t0\t0\t0\t320\t120\t-1\t
5\t1\t1\t1\t1\t1\t10\t20\t100\t30\t91.5\tಕನ್ನಡ
5\t1\t1\t1\t1\t2\t120\t20\t80\t30\t88.0\ttext
"""


def image_bytes(width: int = 320, height: int = 120) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="JPEG")
    return output.getvalue()


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(
            TESTING=True,
            VILLAGELENS_ACCESS_CODE="",
            VILLAGELENS_SESSION_SECRET="",
        )
        self.client = app.test_client()

    def enable_access_gate(self) -> None:
        app.config.update(
            VILLAGELENS_ACCESS_CODE="test-code",
            VILLAGELENS_SESSION_SECRET="test-session-secret",
        )

    def test_tester_page_is_served(self) -> None:
        response = self.client.get("/a/")
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertIn(b"VillageLensAI", response.data)
        self.assertIn(b'id="mode-word"', response.data)
        self.assertIn(b'id="play-sentences"', response.data)
        self.assertIn(b'id="mode-translate"', response.data)
        self.assertIn(b'id="select-object"', response.data)
        self.assertIn(b'id="infer-global"', response.data)
        self.assertIn(b'id="ask"', response.data)
        self.assertIn(b'id="quality-4"', response.data)
        self.assertIn(b'id="owner-badge"', response.data)
        self.assertIn(b'id="app-version"', response.data)
        self.assertIn(b'v2026.09.11.1', response.data)
        self.assertIn(b"'UNASSIGNED \xc2\xb7 OLDER CAPTURE'", response.data)
        self.assertIn(b"`${owner}${ownerName}`", response.data)
        self.assertIn(b'navigationGeneration', response.data)
        self.assertIn(b'nextCaptureSequence', response.data)
        self.assertIn(b'payload.next_capture_sequence', response.data)
        self.assertIn(b'localStorage.setItem', response.data)
        self.assertIn(b'X-VillageLens-Tester-ID', response.data)
        self.assertIn(b'function speechSegments', response.data)
        self.assertIn(b'function speechChunks', response.data)
        self.assertIn(b'function applyVerifiedReadingRegions', response.data)
        self.assertIn('ಪುಳಿಯೋಗರೆ'.encode(), response.data)
        self.assertIn('ಶಾವಿಗೆ'.encode(), response.data)
        self.assertIn(b"playKannada(prepared,generation)", response.data)
        self.assertIn(b'unlockAudioPlayback', response.data)
        self.assertIn(b'function voiceFor', response.data)
        self.assertIn(b"fetch('/api/speech'", response.data)
        self.assertIn(b'function playKannada', response.data)
        self.assertIn(b'speechAudioCache', response.data)
        self.assertIn(b'keepalive:true', response.data)
        self.assertIn(b'/process/${stageNumber}', response.data)
        self.assertIn(b'Promise.all(primary.map(stageNumber=>processStoredReader', response.data)
        self.assertIn(b"const missing=[1,2,3,4]", response.data)
        self.assertIn(b"requested.includes(4)&&readCachedStage(item,3)", response.data)
        self.assertIn(b'item.cloudStartedAt=item.cloudAttempted?Date.now()', response.data)
        self.assertIn(b'nextCaptureSequence===captureSequence+1', response.data)
        self.assertIn(b'NOT SAVED', response.data)
        self.assertNotIn(b'Speech Services', response.data)
        self.assertIn(b'function translatedWord', response.data)
        self.assertIn(b'function loadSharedImage', response.data)
        self.assertIn(b"serviceWorker.register('/a/sw.js'", response.data)
        self.assertIn(b"updateViaCache:'none'", response.data)
        self.assertIn(b'await registration.update()', response.data)
        self.assertIn(b"addEventListener('controllerchange'", response.data)
        self.assertIn(b"location.reload()", response.data)
        self.assertIn(b'id="install"', response.data)
        self.assertIn(b'class="toolbar action-toolbar"', response.data)
        action_toolbar = response.data.split(b'class="toolbar action-toolbar"', 1)[1].split(b'</nav>', 1)[0]
        self.assertIn(b'id="ask"', action_toolbar)
        self.assertIn(b'id="install"', action_toolbar)
        self.assertIn(b'id="camera"', response.data)
        self.assertIn(b'id="camera-guide"', response.data)
        self.assertIn(b'id="camera-preview"', response.data)
        self.assertIn(b'id="camera-capture"', response.data)
        self.assertIn(b'function analyzeCameraFrame', response.data)
        self.assertIn(b'function cameraQualityState', response.data)
        self.assertIn(b"clearlySharp?24:16", response.data)
        self.assertNotIn(b'page_clipped', response.data)
        self.assertNotIn(b'page_too_small', response.data)
        self.assertIn(b'function cameraGuideSourceRect', response.data)
        self.assertIn(b'function drawCameraGuideFrame', response.data)
        self.assertNotIn(b'function renderPageOutline', response.data)
        self.assertIn(b'Only the area inside the box is saved', response.data)
        self.assertIn(b'captureBurstFrames=4', response.data)
        self.assertIn(b'function cameraFrameScore', response.data)
        self.assertIn(b"requestCenterFocus('single-shot')", response.data)
        self.assertIn(b'settings.pointsOfInterest=[{x:.5,y:.5}]', response.data)
        self.assertIn(b'burst_frames:captureBurstFrames', response.data)

        self.assertNotIn(b'cameraCandidates', response.data)
        camera_guide = response.data.split(b'function updateCameraGuide', 1)[1].split(
            b'async function openGuidedCamera', 1,
        )[0]
        self.assertNotIn(b'captureGuidedPhoto', camera_guide)
        self.assertIn(b'function captureGuidedPhoto', response.data)
        self.assertIn(b"facingMode:{ideal:'environment'}", response.data)
        self.assertIn(b"source:'guided-camera-v1'", response.data)
        self.assertIn(b"X-VillageLens-Capture-Quality", response.data)
        self.assertIn(b'function selectableObjects', response.data)
        self.assertIn(b"?'review \xe2\x9c\x93'", response.data)
        self.assertIn(b'function clearControls', response.data)
        self.assertIn(b'function startAction', response.data)
        self.assertIn(b'function defaultWordMode', response.data)
        self.assertIn(b"stop(); defaultWordMode(); const navigation", response.data)
        self.assertIn(b'function ensureContext', response.data)
        self.assertIn(b'function chooseObjectMode', response.data)
        self.assertIn(b"fetch('/api/translate'", response.data)
        self.assertIn(b'villagelens.translation.v1:', response.data)
        self.assertIn(b"if (activeControl===id) { stop(); return false; }", response.data)
        self.assertIn(b"result.detailed_spoken_kn", response.data)
        self.assertIn(b"analysisVersion='context-v2'", response.data)
        self.assertIn(b"function groupedWords", response.data)
        self.assertIn(b"const semanticGroup=groupedWords", response.data)
        self.assertIn(b"function renderObjects", response.data)
        self.assertIn(b"function addFocus", response.data)
        self.assertIn(b"function askImageQuestion", response.data)
        self.assertIn(b'navigator.mediaDevices.getUserMedia', response.data)
        self.assertIn(b"new MediaRecorder", response.data)
        self.assertIn(b'/ask-audio`', response.data)
        self.assertNotIn(b'webkitSpeechRecognition', response.data)
        self.assertIn(b'item.retained||item.result&&item.result.retained', response.data)
        self.assertIn(b'id="mic-status"', response.data)
        self.assertIn(b'id="conversation"', response.data)
        self.assertIn(b'function renderConversation', response.data)
        self.assertIn(b'function startMicTimer', response.data)
        self.assertIn(b"form.append('history'", response.data)
        self.assertIn(b"form.append('focus_box'", response.data)
        self.assertIn(b'/api/demos/${item.id}/ask-audio', response.data)
        self.assertIn(b"recorder.start(1000)", response.data)
        self.assertIn(b"track('question_permission')", response.data)
        self.assertIn(b'iPhone Settings', response.data)
        self.assertIn(b"fetch('/api/events'", response.data)
        self.assertIn(b"Add to Home Screen", response.data)
        self.assertNotIn(b'id="mode-meaning"', response.data)
        self.assertNotIn(b'id="play-meanings"', response.data)
        self.assertIn(b"?'review \xe2\x9c\x93'", response.data)
        stage_three = response.data.split(b"if ([2,3,4].includes(stageNumber))", 1)[1].split(
            b"if (gallery[galleryIndex]===item)", 1,
        )[0]
        self.assertNotIn(b"item.result=value", stage_three)
        self.assertIn(b"copyMeaning(item.result,item)", stage_three)
        capture_flow = response.data.split(b"async function useCapture", 1)[1].split(
            b"$('mode-word').onclick", 1,
        )[0]
        self.assertLess(capture_flow.index(b"beginTimer(item,item.startedAt)"), capture_flow.index(
            b"fetch('/api/capture'",
        ))
        self.assertLess(capture_flow.index(b"fetch('/api/capture'"), capture_flow.index(
            b"await startCloudReaders(item,file)",
        ))
        self.assertIn(b"$('quality-1').classList.add('failed')", capture_flow)
        self.assertNotIn(b"Math.min", response.data.split(b"function beginTimer", 1)[1].split(
            b"function cacheKey", 1,
        )[0])
        self.assertIn(b"Swipe the page", response.data)
        self.assertIn("ಅ ಆ ಇ".encode(), response.data)

    def test_english_reader_page_is_isolated_at_b(self) -> None:
        response = self.client.get("/b/?tester=a3")
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store, max-age=0")
        self.assertIn(b"const englishMode=location.pathname==='/b/'", response.data)
        self.assertIn(b"'X-VillageLens-Output-Language':outputLanguage", response.data)
        self.assertIn(b"Translate selected word to English", response.data)

    def test_protected_english_reader_routes_reviewer_to_access(self) -> None:
        self.enable_access_gate()
        response = self.client.get("/b/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/access?tester=a3")

    def test_demo_assets_are_served(self) -> None:
        image = self.client.get("/a/demo/i2.jpeg")
        scene = self.client.get("/a/demo/i1-scene.json")
        gold = self.client.get("/a/demo/i2-gold.json")
        self.addCleanup(image.close)
        self.addCleanup(scene.close)
        self.addCleanup(gold.close)
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.content_type, "image/jpeg")
        self.assertEqual(scene.status_code, 200)
        self.assertEqual(scene.get_json()["image_size"], {"width": 3024, "height": 4032})
        self.assertEqual(gold.get_json()["status"], "reviewed-independent-qualification")

    def test_unknown_demo_asset_is_rejected(self) -> None:
        response = self.client.get("/a/demo/unknown.jpeg")
        self.assertEqual(response.status_code, 404)

    def test_installable_app_assets_and_share_target_are_served(self) -> None:
        manifest = self.client.get("/a/manifest.webmanifest")
        worker = self.client.get("/a/sw.js")
        icon = self.client.get("/a/icon-192.png")
        self.addCleanup(manifest.close)
        self.addCleanup(worker.close)
        self.addCleanup(icon.close)

        value = manifest.get_json()
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(value["start_url"], "/a/")
        self.assertEqual(value["display"], "standalone")
        self.assertEqual(value["share_target"]["action"], "/a/share-target")
        self.assertEqual(value["share_target"]["params"]["files"][0]["name"], "image")
        self.assertEqual(worker.status_code, 200)
        self.assertEqual(manifest.headers["Cache-Control"], "no-cache, max-age=0")
        self.assertEqual(worker.headers["Cache-Control"], "no-cache, max-age=0")
        self.assertEqual(worker.headers["Service-Worker-Allowed"], "/a/")
        self.assertIn(b"APP_UPDATED", worker.data)
        self.assertIn(b"event.request.formData()", worker.data)
        self.assertEqual(icon.status_code, 200)
        self.assertEqual(icon.content_type, "image/png")

    @patch("api.app._storage_bucket", return_value=None)
    @patch("api.app._synthesize_kannada", return_value=b"mp3-audio")
    def test_kannada_speech_is_synthesized_server_side(
        self, synthesize: object, storage_bucket: object,
    ) -> None:
        response = self.client.post("/api/speech", json={"text": " ಕನ್ನಡ  ಪದ "})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "audio/mpeg")
        self.assertEqual(response.data, b"mp3-audio")
        self.assertEqual(response.headers["X-VillageLens-Speech-Cache"], "miss")
        self.assertEqual(response.headers["Cache-Control"], "private, max-age=604800")
        synthesize.assert_called_once_with("ಕನ್ನಡ ಪದ")

    @patch("api.app._storage_bucket", return_value=None)
    @patch("api.app._synthesize_kannada", return_value=b"mixed-mp3")
    def test_mixed_kannada_numbers_and_units_are_one_server_utterance(
        self, synthesize: object, storage_bucket: object,
    ) -> None:
        response = self.client.post(
            "/api/speech", json={"text": "ಇದು FS-12. ಒಳಹರಿವು 220 ವೋಲ್ಟ್ 2 ಆಂಪಿಯರ್."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"mixed-mp3")
        synthesize.assert_called_once_with(
            "ಇದು FS-12. ಒಳಹರಿವು 220 ವೋಲ್ಟ್ 2 ಆಂಪಿಯರ್.",
        )

    @patch("api.app._synthesize_kannada")
    @patch("api.app._storage_bucket")
    def test_kannada_speech_reuses_private_object_cache(
        self, storage_bucket: object, synthesize: object,
    ) -> None:
        blob = storage_bucket.return_value.blob.return_value
        blob.exists.return_value = True
        blob.download_as_bytes.return_value = b"cached-mp3"
        blob.content_type = "audio/mpeg"

        response = self.client.post("/api/speech", json={"text": "ಕನ್ನಡ"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"cached-mp3")
        self.assertEqual(response.headers["X-VillageLens-Speech-Cache"], "hit")
        synthesize.assert_not_called()
        cache_name = storage_bucket.return_value.blob.call_args.args[0]
        self.assertRegex(cache_name, r"^speech/v1/[0-9a-f]{64}\.mp3$")
        self.assertNotIn("ಕನ್ನಡ", cache_name)

    def test_kannada_speech_rejects_invalid_text(self) -> None:
        latin = self.client.post("/api/speech", json={"text": "English only"})
        empty = self.client.post("/api/speech", json={"text": ""})
        long_text = self.client.post("/api/speech", json={"text": "ಕ" * 501})

        self.assertEqual(latin.status_code, 400)
        self.assertEqual(latin.get_json()["error"], "SPEECH_LANGUAGE_UNSUPPORTED")
        self.assertEqual(empty.get_json()["error"], "SPEECH_TEXT_REQUIRED")
        self.assertEqual(long_text.get_json()["error"], "SPEECH_TEXT_TOO_LONG")

    @patch("api.app.requests.post")
    def test_openai_translation_uses_fast_structured_response(self, provider: object) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"output": [{"content": [{
            "type": "output_text", "text": json.dumps({"translation_kn": "ಸ್ಟಾರ್ಟರ್"}),
        }]}]}

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            value = _openai_translate("starter")

        self.assertEqual(value["translation_kn"], "ಸ್ಟಾರ್ಟರ್")
        request_payload = provider.call_args.kwargs["json"]
        self.assertEqual(request_payload["model"], "gpt-5-mini")
        self.assertFalse(request_payload["store"])
        self.assertEqual(request_payload["reasoning"]["effort"], "minimal")
        self.assertNotIn("input_image", str(request_payload))

    @patch("api.app._openai_translate", return_value={
        "translation_kn": "ವಿದ್ಯುತ್ ಸ್ವಿಚ್", "model": "gpt-5-mini",
    })
    def test_translation_endpoint_contract(self, translate: object) -> None:
        response = self.client.post("/api/translate", json={"text": " power   switch "})
        no_english = self.client.post("/api/translate", json={"text": "ಕನ್ನಡ"})
        too_long = self.client.post("/api/translate", json={"text": "a" * 81})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["translation_kn"], "ವಿದ್ಯುತ್ ಸ್ವಿಚ್")
        translate.assert_called_once_with("power switch")
        self.assertEqual(no_english.get_json()["error"], "TRANSLATION_LANGUAGE_UNSUPPORTED")
        self.assertEqual(too_long.get_json()["error"], "TRANSLATION_TEXT_TOO_LONG")

    def test_gallery_starts_with_i2_then_i1(self) -> None:
        response = self.client.get("/api/gallery")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()["items"]
        self.assertEqual([item["id"] for item in items[:2]], ["demo-i2", "demo-i1"])
        self.assertEqual(items[0]["result_url"], "/a/demo/i2-gold.json")

    @patch("api.app._storage_bucket")
    def test_gallery_reuses_stored_cloud_evidence(self, storage_bucket: object) -> None:
        capture_id = "a" * 32
        result_blob = MagicMock(name="result_blob")
        result_blob.name = f"captures/{capture_id}/result.json"
        result_blob.download_as_text.return_value = json.dumps({
            "capture_id": capture_id, "captured_at": "2026-08-30T00:00:00+00:00",
            "label": "Captured page", "tester_id": "a1", "words": [], "lines": [],
        })
        stage_blob = MagicMock(name="stage_blob")
        stage_blob.name = f"captures/{capture_id}/stage-2.json"
        stage_blob.download_as_text.return_value = json.dumps({
            "stage": 2, "reader": "cloud_ocr", "words": [],
        })
        storage_bucket.return_value.list_blobs.return_value = [result_blob, stage_blob]

        items = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "A1"},
        ).get_json()["items"]

        self.assertEqual(items[2]["stage1"], {
            "stage": 1, "reader": "cloud_ocr", "words": [],
        })
        self.assertTrue(items[2]["retained"])
        self.assertEqual(items[2]["capture_code"], "A1-1")
        self.assertEqual(items[2]["capture_sequence"], 1)
        other_items = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "a2"},
        ).get_json()["items"]
        self.assertEqual(len(other_items), 2)
        reviewer = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "a3"},
        ).get_json()
        self.assertTrue(reviewer["review_mode"])
        self.assertEqual(len(reviewer["items"]), 3)
        self.assertEqual(reviewer["items"][2]["tester_id"], "a1")
        self.assertEqual(reviewer["items"][2]["tester_name"], "Eeregowda")
        self.assertEqual(reviewer["next_capture_sequence"], 1)

    @patch("api.app._storage_bucket")
    def test_gallery_assigns_stable_chronological_codes_per_tester(
        self, storage_bucket: object,
    ) -> None:
        captures = [
            ("a" * 32, "2026-09-01T10:00:00+00:00", "a3"),
            ("b" * 32, "2026-09-01T11:00:00+00:00", "a1"),
            ("c" * 32, "2026-09-01T12:00:00+00:00", "a3"),
        ]
        blobs = []
        for capture_id, captured_at, tester_id in captures:
            blob = MagicMock()
            blob.name = f"captures/{capture_id}/result.json"
            blob.download_as_text.return_value = json.dumps({
                "capture_id": capture_id, "captured_at": captured_at,
                "label": "Captured photo", "tester_id": tester_id,
            })
            blobs.append(blob)
        storage_bucket.return_value.list_blobs.return_value = list(reversed(blobs))

        gallery = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "a3"},
        ).get_json()
        stored = gallery["items"][2:]

        self.assertEqual([item["capture_code"] for item in stored], [
            "A3-2", "A1-1", "A3-1",
        ])
        self.assertEqual(gallery["next_capture_sequence"], 3)
        self.assertEqual(stored[0]["result"]["capture_code"], "A3-2")

    @patch("api.app._storage_bucket")
    def test_gallery_attaches_owner_verified_handwriting_regions(
        self, storage_bucket: object,
    ) -> None:
        capture_id = "fac3bcfd6b5d43d79fa1652e10159b95"
        result_blob = MagicMock()
        result_blob.name = f"captures/{capture_id}/result.json"
        result_blob.download_as_text.return_value = json.dumps({
            "capture_id": capture_id, "captured_at": "2026-09-10T01:57:49+00:00",
            "label": "Captured page", "tester_id": "a3", "words": [], "lines": [],
        })
        storage_bucket.return_value.list_blobs.return_value = [result_blob]

        item = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "a3"},
        ).get_json()["items"][2]

        self.assertEqual([region["label"] for region in item["verified_regions"]], [
            "Puliyogare", "Kadle kai", "Shavige", "Ollige",
        ])
        self.assertEqual(item["result"]["verified_regions"][1]["spoken_kn"], "ಎರಡು. ಕಡಲೆಕಾಯಿ.")

    def test_health_reports_pinned_models(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    @patch("api.app._storage_bucket")
    def test_named_tester_roster_is_reported_to_reviewer(self, storage_bucket: object) -> None:
        values = []
        for tester_id in ("a4", "a5", "a6", "a7"):
            blob = MagicMock()
            blob.name = f"captures/{tester_id * 16}/result.json"
            blob.download_as_text.return_value = json.dumps({
                "capture_id": tester_id * 16, "captured_at": tester_id,
                "label": "Captured page", "tester_id": tester_id,
            })
            values.append(blob)
        storage_bucket.return_value.list_blobs.return_value = values

        items = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "a3"},
        ).get_json()["items"][2:]

        self.assertEqual({item["tester_id"]: item["tester_name"] for item in items}, {
            "a4": "Selvan", "a5": "Kiran", "a6": "Rupa", "a7": "Akul",
        })

    @patch("api.app._store_capture", return_value=False)
    @patch("api.app.subprocess.run")
    def test_tester_roster_accepts_a10_and_rejects_a11(
        self, run: object, store: object,
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout=TSV, stderr="")

        accepted = self.client.post(
            "/api/capture", data=image_bytes(), content_type="image/jpeg",
            headers={"X-VillageLens-Tester-ID": "A10"},
        ).get_json()
        rejected = self.client.post(
            "/api/capture", data=image_bytes(), content_type="image/jpeg",
            headers={"X-VillageLens-Tester-ID": "A11"},
        ).get_json()

        self.assertEqual(accepted["tester_id"], "a10")
        self.assertEqual(rejected["tester_id"], "unassigned")

    def test_access_gate_protects_page_and_api(self) -> None:
        self.enable_access_gate()
        page = self.client.get("/a/")
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.headers["Location"], "/access")
        api_response = self.client.post(
            "/api/capture", data=image_bytes(), content_type="image/jpeg",
        )
        self.assertEqual(api_response.status_code, 401)
        self.assertEqual(api_response.get_json()["error"], "ACCESS_REQUIRED")

    def test_correct_access_code_sets_secure_cookie(self) -> None:
        self.enable_access_gate()
        app.config["VILLAGELENS_ACCESS_CODE"] = "test-code\n"
        response = self.client.post(
            "/access", data={"code": "test-code", "tester": "a1"},
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/a/?tester=a1")
        cookies = response.headers.getlist("Set-Cookie")
        cookie = next(value for value in cookies if value.startswith("villagelens_access_v2="))
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertTrue(any(value.startswith("villagelens_access=;") for value in cookies))
        token = cookie.split(";", 1)[0].split("=", 1)[1]
        self.client.set_cookie("villagelens_access_v2", token, secure=True)
        allowed = self.client.get("/a/?tester=a1", base_url="https://localhost")
        self.addCleanup(allowed.close)
        self.assertEqual(allowed.status_code, 200)

    def test_signed_tester_link_enrolls_without_password(self) -> None:
        self.enable_access_gate()
        with app.test_request_context("/"):
            token = _tester_link_token("a4")

        response = self.client.post("/access/link", data={"token": token})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["destination"], "/a/?tester=a4")
        cookies = response.headers.getlist("Set-Cookie")
        self.assertTrue(any(value.startswith("villagelens_access_v2=") for value in cookies))
        self.assertTrue(any(value.startswith("villagelens_tester_v1=a4") for value in cookies))
        page = self.client.get("/a/?tester=a4", base_url="https://localhost")
        self.addCleanup(page.close)
        self.assertEqual(page.status_code, 200)

        installed = self.client.get("/a/?shared=1", base_url="https://localhost")
        self.assertEqual(installed.status_code, 302)
        self.assertEqual(installed.headers["Location"], "/a/?tester=a4&shared=1")

    def test_invalid_tester_link_is_rejected(self) -> None:
        self.enable_access_gate()
        response = self.client.post("/access/link", data={"token": "a4.not-valid"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "ACCESS_LINK_INVALID")

    def test_access_page_consumes_link_fragment_without_logging_it(self) -> None:
        self.enable_access_gate()
        response = self.client.get("/access")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"location.hash.slice(1)", response.data)
        self.assertIn(b"fetch('/access/link'", response.data)
        self.assertIn(b"history.replaceState", response.data)

    def test_valid_legacy_cookie_remains_accepted(self) -> None:
        self.enable_access_gate()
        with app.test_request_context("/"):
            token = _access_token()
        self.client.set_cookie("villagelens_access", token, secure=True)

        response = self.client.get("/a/?tester=a2", base_url="https://localhost")
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)

    def test_valid_cookie_survives_duplicate_stale_legacy_cookie(self) -> None:
        self.enable_access_gate()
        with app.test_request_context("/"):
            token = _access_token()
        client = app.test_client(use_cookies=False)

        response = client.get(
            "/a/?tester=a4",
            base_url="https://localhost",
            headers={"Cookie": f"villagelens_access=stale.invalid; villagelens_access={token}"},
        )
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)

    def test_fresh_phone_access_preserves_tester_enrollment(self) -> None:
        self.enable_access_gate()

        protected = self.client.get("/a/?tester=A10")
        self.assertEqual(protected.status_code, 302)
        self.assertEqual(protected.headers["Location"], "/access?tester=a10")
        invalid = self.client.get("/a/?tester=a11")
        self.assertEqual(invalid.headers["Location"], "/access")
        access_page = self.client.get(protected.headers["Location"])
        self.assertIn(b'<label for="tester">User</label>', access_page.data)
        self.assertIn(b'<label for="code">Code</label>', access_page.data)
        self.assertIn(b'<option value="a10" selected>A10</option>', access_page.data)
        accepted = self.client.post(
            "/access", data={"code": "test-code", "tester": "a10"},
        )
        self.assertEqual(accepted.status_code, 303)
        self.assertEqual(accepted.headers["Location"], "/a/?tester=a10")

    def test_main_domain_requires_user_and_code_even_with_access_cookie(self) -> None:
        self.enable_access_gate()
        accepted = self.client.post(
            "/access", data={"code": "test-code", "tester": "a2"},
        )
        self.assertEqual(accepted.status_code, 303)

        root = self.client.get("/")
        self.assertEqual(root.status_code, 302)
        self.assertEqual(root.headers["Location"], "/access")
        form = self.client.get(root.headers["Location"])
        self.assertEqual(form.status_code, 200)
        self.assertEqual(form.data.count(b'<select id="tester"'), 1)
        self.assertEqual(form.data.count(b'<input id="code"'), 1)

        missing_user = self.client.post("/access", data={"code": "test-code"})
        self.assertEqual(missing_user.status_code, 401)
        self.assertIn(b"Choose a user", missing_user.data)

    def test_capture_rejects_non_image(self) -> None:
        response = self.client.post("/api/capture", data=b"hello", content_type="text/plain")
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.get_json()["error"], "CAPTURE_MEDIA_TYPE_UNSUPPORTED")

    def test_tesseract_quote_does_not_swallow_following_rows(self) -> None:
        quoted = TSV.replace("91.5\tಕನ್ನಡ", '91.5\t"').replace("88.0\ttext", "88.0\tnext")

        words, lines = _parse_tsv(quoted)

        self.assertEqual([word["text"] for word in words], ['"', "next"])
        self.assertEqual(lines[0]["text"], '" next')

    def test_low_confidence_isolated_kannada_noise_is_removed(self) -> None:
        words, lines = _parse_tsv(TSV.replace("91.5\tಕನ್ನಡ", "30.0\tಕ"))

        filtered_words, filtered_lines = _filter_local_regions(words, lines)

        self.assertEqual([word["text"] for word in filtered_words], ["text"])
        self.assertEqual(filtered_lines[0]["text"], "text")

    @patch("api.app._store_capture", return_value=False)
    @patch("api.app.subprocess.run")
    def test_capture_returns_stage_one_geometry_without_retention(
        self, run: object, store: object,
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout=TSV, stderr="")
        response = self.client.post(
            "/api/capture", data=image_bytes(), content_type="image/jpeg",
            headers={"X-VillageLens-Tester-ID": "A2"},
        )
        self.assertEqual(response.status_code, 200)
        value = response.get_json()
        self.assertEqual(value["stage"], 1)
        self.assertEqual(value["lines"][0]["text"], "ಕನ್ನಡ text")
        self.assertEqual(
            value["words"][0]["box"], {"x": 10, "y": 20, "width": 100, "height": 30},
        )
        self.assertFalse(value["retained"])
        self.assertEqual(value["tester_id"], "a2")
        self.assertEqual(value["reader"]["input_size"], {"width": 320, "height": 120})
        self.assertIn("eng+kan", run.call_args.args[0])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    @patch("api.app._store_capture", return_value=False)
    @patch("api.app.subprocess.run")
    def test_guided_capture_stores_bounded_quality_and_durable_code(
        self, run: object, store: object,
    ) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout=TSV, stderr="")
        response = self.client.post(
            "/api/capture", data=image_bytes(), content_type="image/jpeg",
            headers={
                "X-VillageLens-Tester-ID": "A2",
                "X-VillageLens-Capture-ID": "f" * 32,
                "X-VillageLens-Capture-Source": "guided-camera-v1",
                "X-VillageLens-Capture-Quality": json.dumps({
                    "brightness": 121.238, "sharpness": 14.126,
                    "motion": 2.5, "glare_percent": 3.1,
                    "page_candidate_percent": 48.567, "page_edge_percent": 12.345,
                    "burst_frames": 3, "auto_captured": False,
                    "private_note": "discard me",
                }),
            },
        )

        value = response.get_json()
        self.assertEqual(value["capture_code"], "A2-FFFFFF")
        self.assertEqual(value["capture_source"], "guided-camera-v1")
        self.assertEqual(value["capture_quality"], {
            "brightness": 121.24, "sharpness": 14.13, "motion": 2.5,
            "glare_percent": 3.1, "page_candidate_percent": 48.57,
            "page_edge_percent": 12.35, "burst_frames": 3.0,
            "auto_captured": False,
        })
        self.assertNotIn("private_note", value["capture_quality"])
        self.assertEqual(store.call_args.args[2]["capture_code"], "A2-FFFFFF")

    @patch("api.app._store_capture", return_value=False)
    @patch("api.app.subprocess.run")
    def test_capture_downscales_local_ocr_and_restores_geometry(
        self, run: object, store: object,
    ) -> None:
        observed: dict[str, tuple[int, int]] = {}

        def inspect_ocr_image(command: list[str], **_: object) -> subprocess.CompletedProcess:
            with Image.open(command[1]) as image:
                observed["size"] = image.size
            return subprocess.CompletedProcess([], 0, stdout=TSV, stderr="")

        run.side_effect = inspect_ocr_image
        response = self.client.post(
            "/api/capture", data=image_bytes(2400, 1200), content_type="image/jpeg",
            headers={"X-VillageLens-Tester-ID": "not-allowed"},
        )
        value = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed["size"], (1600, 800))
        self.assertEqual(value["reader"]["input_size"], {"width": 1600, "height": 800})
        self.assertEqual(
            value["words"][0]["box"], {"x": 15, "y": 30, "width": 150, "height": 45},
        )
        self.assertEqual(value["tester_id"], "unassigned")

    @patch("api.app._store_reader_evidence")
    @patch("api.app._vision_reader")
    def test_stage_one_cloud_ocr_contract(self, reader: object, store: object) -> None:
        reader.return_value = {
            "schema": "villagelens.reader.v1", "stage": 2, "reader": "cloud_ocr",
            "image_size": {"width": 320, "height": 120}, "words": [], "lines": [],
        }
        capture_id = "a" * 32
        response = self.client.post(
            "/api/read/1", data=image_bytes(), content_type="image/jpeg",
            headers={"X-VillageLens-Capture-ID": capture_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stage"], 1)
        store.assert_called_once_with(capture_id, 1, reader.return_value)

    @patch("api.app._store_reader_evidence")
    @patch("api.app._openai_reader")
    def test_stage_two_uses_sol_fast_first_pass(self, reader: object, store: object) -> None:
        reader.return_value = {
            "schema": "villagelens.reader.v1", "stage": 2,
            "reader": "vision_language", "analysis_version": "instant-v2",
            "summary_kn": "ಇದು ಪುಸ್ತಕ.",
        }
        capture_id = "9" * 32
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            response = self.client.post(
                "/api/read/2", data=image_bytes(), content_type="image/jpeg",
                headers={"X-VillageLens-Capture-ID": capture_id},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["analysis_version"], "instant-v2")
        self.assertEqual(reader.call_args.kwargs["stage"], 2)
        self.assertEqual(reader.call_args.kwargs["service_tier"], "fast")
        self.assertTrue(reader.call_args.kwargs["quick"])
        store.assert_called_once_with(capture_id, 2, reader.return_value)

    @patch("api.app.requests.post")
    def test_quick_reader_uses_small_low_detail_contract(self, provider: object) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"service_tier": "priority", "output": [{"content": [{
            "type": "output_text", "text": json.dumps({
                "scene_type": "adapter", "what_is_it_kn": "ಇದು ವಿದ್ಯುತ್ ಅಡಾಪ್ಟರ್.",
                "what_it_does_kn": "ಇದು ವಿದ್ಯುತ್ ಒದಗಿಸುತ್ತದೆ.",
                "brief_spoken_kn": "ಇದು ವಿದ್ಯುತ್ ಅಡಾಪ್ಟರ್.",
                "important_points_kn": ["ವೋಲ್ಟೇಜ್ ನೋಡಿ."], "uncertainty_kn": "",
                "confidence": "high",
            }),
        }]}]}

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            value = _openai_reader(
                image_bytes(), "image/jpeg", 320, 120, stage=2,
                model="gpt-5.6-sol", service_tier="fast",
                analysis_version="instant-v2", quick=True,
            )

        payload = provider.call_args.kwargs["json"]
        schema = payload["text"]["format"]["schema"]
        self.assertEqual(payload["max_output_tokens"], 700)
        self.assertEqual(payload["input"][0]["content"][1]["detail"], "low")
        self.assertNotIn("objects", schema["properties"])
        self.assertIn("Do not transcribe", payload["input"][0]["content"][0]["text"])
        self.assertTrue(value["quality_validated"])

    @patch("api.app.requests.post")
    def test_quick_reader_can_return_english_for_any_source_script(self, provider: object) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"service_tier": "priority", "output": [{"content": [{
            "type": "output_text", "text": json.dumps({
                "scene_type": "book", "what_is_it_kn": "This is a Kannada-language book.",
                "what_it_does_kn": "It teaches the subject shown on this page.",
                "brief_spoken_kn": "This is a Kannada book translated and explained in English.",
                "important_points_kn": ["The visible page contains a lesson."],
                "uncertainty_kn": "Some smaller text is unclear.", "confidence": "medium",
            }),
        }]}]}

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            value = _openai_reader(
                image_bytes(), "image/jpeg", 320, 120, stage=2,
                model="gpt-5.6-sol", service_tier="fast",
                analysis_version="instant-v2", quick=True, output_language="en",
            )

        prompt = provider.call_args.kwargs["json"]["input"][0]["content"][0]["text"]
        self.assertIn("OUTPUT LANGUAGE OVERRIDE", prompt)
        self.assertEqual(value["output_language"], "en")
        self.assertTrue(value["quality_validated"])

    @patch("api.app._store_reader_evidence")
    @patch("api.app._openai_reader")
    def test_english_stage_request_uses_separate_processing_and_storage(
        self, reader: object, store: object,
    ) -> None:
        reader.return_value = {
            "schema": "villagelens.reader.v1", "stage": 2,
            "reader": "vision_language", "analysis_version": "instant-v2",
            "output_language": "en", "summary_kn": "This is a book.",
        }
        capture_id = "8" * 32
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            response = self.client.post(
                "/api/read/2", data=image_bytes(), content_type="image/jpeg",
                headers={"X-VillageLens-Capture-ID": capture_id,
                         "X-VillageLens-Output-Language": "en"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(reader.call_args.kwargs["output_language"], "en")
        store.assert_called_once_with(capture_id, 2, reader.return_value, "en")

    @patch("api.app._store_reader_evidence")
    @patch("api.app.requests.post")
    def test_stage_three_returns_translations_and_contextual_kannada(
        self, provider: object, store: object,
    ) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"service_tier": "priority", "output": [{"content": [{
            "type": "output_text",
            "text": json.dumps({
                "words": [], "lines": [],
                "translations": [{"source": "book", "translation_kn": "ಪುಸ್ತಕ"}],
                "scene_type": "book",
                "objects": [{"name": "book", "name_kn": "ಪುಸ್ತಕ",
                             "purpose_kn": "ಓದಲು ಬಳಸುವ ಪುಸ್ತಕ", "evidence": "visible pages",
                             "uncertain": False, "box": [100, 100, 500, 700]}],
                "what_is_it_kn": "ಇದು ಒಂದು ಪುಸ್ತಕ.",
                "what_it_does_kn": "ಇದನ್ನು ಓದಲು ಬಳಸುತ್ತಾರೆ.",
                "important_points_kn": ["ಮುಖಪುಟದಲ್ಲಿ ಹೆಸರು ಇದೆ."],
                "action_needed_kn": "",
                "warning_kn": "",
                "uncertainty_kn": "",
                "brief_spoken_kn": "ಇದು ಓದಲು ಬಳಸುವ ಪುಸ್ತಕ.",
                "detailed_spoken_kn": "ಇದು ಒಂದು ಪುಸ್ತಕ. ಮುಖಪುಟದಲ್ಲಿ ಹೆಸರು ಇದೆ.",
                "transcription_kn": [],
                "spoken_sections": [{"text_kn": "ಇದು ಒಂದು ಪುಸ್ತಕ.", "box": [100, 100, 500, 700]}],
                "confidence": "high", "needs_independent_review": False,
            }),
        }]}]}
        capture_id = "b" * 32

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            response = self.client.post(
                "/api/read/3", data=image_bytes(), content_type="image/jpeg",
                headers={
                    "X-VillageLens-Capture-ID": capture_id,
                    "X-VillageLens-Tester-ID": "A1",
                },
            )

        value = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(value["translations"][0]["translation_kn"], "ಪುಸ್ತಕ")
        self.assertEqual(value["objects"][0]["name_kn"], "ಪುಸ್ತಕ")
        self.assertEqual(value["summary_kn"], value["brief_spoken_kn"])
        self.assertTrue(value["quality_validated"])
        self.assertEqual(value["analysis_version"], "context-v2")
        self.assertEqual(value["objects"][0]["box"], {"x": 32, "y": 12, "width": 160, "height": 84})
        self.assertEqual(value["tester_id"], "a1")
        request_payload = provider.call_args.kwargs["json"]
        prompt = request_payload["input"][0]["content"][0]["text"]
        self.assertIn("Identify up to six useful visible objects", prompt)
        self.assertIn("handwritten list, first identify its likely purpose", prompt)
        self.assertIn("use all readable text and pictures to teach the page", prompt)
        self.assertIn("detailed_spoken_kn should be five to eight short teaching sentences", prompt)
        self.assertIn("rather than reciting the grid", prompt)
        self.assertIn("Never invent", prompt)
        self.assertIn("translations", request_payload["text"]["format"]["schema"]["required"])
        self.assertIn("objects", request_payload["text"]["format"]["schema"]["required"])
        self.assertIn("brief_spoken_kn", request_payload["text"]["format"]["schema"]["required"])
        self.assertIn("transcription_kn", request_payload["text"]["format"]["schema"]["required"])
        self.assertIn("spoken_sections", request_payload["text"]["format"]["schema"]["required"])
        self.assertNotIn("words", request_payload["text"]["format"]["schema"]["properties"])
        self.assertEqual(request_payload["reasoning"]["effort"], "none")
        self.assertEqual(request_payload["service_tier"], "fast")
        self.assertEqual(request_payload["text"]["verbosity"], "low")
        self.assertEqual(value["service_tier"], "priority")
        store.assert_called_once_with(capture_id, 3, value)

    @patch("api.app.requests.post")
    def test_astra_review_requires_explicit_consensus(self, provider: object) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"service_tier": "default", "output": [{"content": [{
            "type": "output_text", "text": json.dumps({
                "translations": [], "scene_type": "book", "objects": [],
                "what_is_it_kn": "ಇದು ಪುಸ್ತಕ.", "what_it_does_kn": "ಇದನ್ನು ಓದಲು ಬಳಸುತ್ತಾರೆ.",
                "important_points_kn": [], "action_needed_kn": "", "warning_kn": "",
                "uncertainty_kn": "", "brief_spoken_kn": "ಇದು ಪುಸ್ತಕ.",
                "detailed_spoken_kn": "ಇದು ಓದಲು ಬಳಸುವ ಪುಸ್ತಕ.", "transcription_kn": [],
                "spoken_sections": [], "confidence": "high",
                "needs_independent_review": False, "agrees_with_sol": True,
                "material_disagreement_kn": "",
            }),
        }]}]}

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            value = _openai_reader(
                image_bytes(), "image/jpeg", 320, 120, stage=4,
                model="gpt-6-astra", service_tier="fast",
                analysis_version="astra-review-v2",
                prior_analysis={"brief_spoken_kn": "ಇದು ಪುಸ್ತಕ."},
            )

        payload = provider.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "gpt-6-astra")
        self.assertEqual(payload["service_tier"], "fast")
        self.assertEqual(payload["reasoning"]["effort"], "low")
        self.assertEqual(provider.call_args.kwargs["timeout"], 85)
        self.assertIn("Earlier Sol analysis", payload["input"][0]["content"][0]["text"])
        self.assertIn("agrees_with_sol", payload["text"]["format"]["schema"]["required"])
        self.assertTrue(value["consensus_validated"])

    def test_mixed_script_kannada_output_is_not_marked_ready(self) -> None:
        value = _normalize_stage_three({
            "translations": [
                {"source": "Supreme", "translation_kn": "ಸुप್ರೀಮ್"},
                {"source": "book", "translation_kn": "ಪುಸ್ತಕ"},
            ],
            "summary_kn": "ಚಿತ್ರದಲ್ಲ ಕಾಣುತ್ತದೆ",
        })

        self.assertEqual(value["translations"], [
            {"source": "book", "translation_kn": "ಪುಸ್ತಕ"},
        ])
        self.assertEqual(value["summary_kn"], "ಚಿತ್ರದಲ್ಲ ಕಾಣುತ್ತದೆ")
        self.assertFalse(value["quality_validated"])

    def test_kannada_context_allows_normal_unicode_punctuation(self) -> None:
        value = _normalize_stage_three({
            "analysis_version": "context-v2",
            "translations": [],
            "scene_type": "calendar",
            "objects": [],
            "what_is_it_kn": "ಇದು “ಸೆಪ್ಟೆಂಬರ್” ತಿಂಗಳ ಕ್ಯಾಲೆಂಡರ್.",
            "what_it_does_kn": "ಇದು ದಿನಾಂಕಗಳನ್ನು ತೋರಿಸುತ್ತದೆ.",
            "important_points_kn": ["ಮುಖ್ಯ ದಿನಾಂಕ—ಏಳು."],
            "action_needed_kn": "",
            "warning_kn": "",
            "uncertainty_kn": "",
            "brief_spoken_kn": "ಇದು ಸೆಪ್ಟೆಂಬರ್ ಕ್ಯಾಲೆಂಡರ್.",
            "detailed_spoken_kn": "ಇದು “ಸೆಪ್ಟೆಂಬರ್” ತಿಂಗಳ ಕ್ಯಾಲೆಂಡರ್—ದಿನಾಂಕಗಳನ್ನು ತೋರಿಸುತ್ತದೆ.",
        })

        self.assertTrue(value["quality_validated"])

    def test_full_frame_object_box_is_not_selectable(self) -> None:
        value = _normalize_stage_three({
            "analysis_version": "context-v2",
            "image_size": {"width": 3072, "height": 4096},
            "translations": [], "scene_type": "plant", "summary_kn": "ಇದು ಸಸ್ಯ.",
            "objects": [
                {"name": "soil", "name_kn": "ಮಣ್ಣು", "purpose_kn": "ಸಸ್ಯದ ನೆಲ",
                 "evidence": "background", "uncertain": False,
                 "box": {"x": 0, "y": 0, "width": 3072, "height": 4096}},
                {"name": "leaf", "name_kn": "ಎಲೆ", "purpose_kn": "ಸಸ್ಯದ ಎಲೆ",
                 "evidence": "visible leaf", "uncertain": False,
                 "box": {"x": 1161, "y": 1028, "width": 553, "height": 1614}},
            ],
        })

        self.assertEqual([item["name"] for item in value["objects"]], ["leaf"])

    @patch("api.app._process_stored_capture")
    def test_stored_capture_processing_contract(self, process: object) -> None:
        capture_id = "c" * 32
        process.return_value = ({2: {"stage": 2, "words": []}}, {3: "READER_FAILED"})

        response = self.client.post(
            f"/api/captures/{capture_id}/process",
            headers={"X-VillageLens-Tester-ID": "A5"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stages"]["2"]["stage"], 2)
        self.assertEqual(response.get_json()["errors"]["3"], "READER_FAILED")
        self.assertFalse(response.get_json()["complete"])
        process.assert_called_once_with(capture_id, "a5")

    @patch("api.app._process_stored_stage")
    def test_stored_stage_processing_returns_independently(self, process: object) -> None:
        capture_id = "e" * 32
        process.return_value = {"stage": 2, "latency_ms": 321, "words": []}

        response = self.client.post(
            f"/api/captures/{capture_id}/process/2",
            headers={"X-VillageLens-Tester-ID": "A3"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"]["latency_ms"], 321)
        process.assert_called_once_with(capture_id, "a3", 2)

        missing = self.client.post(f"/api/captures/{capture_id}/process/5")
        self.assertEqual(missing.status_code, 404)

    @patch("api.app._store_reader_evidence")
    @patch("api.app._reader_cooling_down", return_value=False)
    @patch("api.app._vision_reader")
    @patch("api.app._storage_bucket")
    def test_stored_stage_forwards_compact_jpeg_independently(
        self, storage_bucket: object, vision: object, cooling: object, store: object,
    ) -> None:
        capture_id = "f" * 32
        source = MagicMock()
        source.exists.return_value = True
        source.download_as_bytes.return_value = image_bytes(800, 600)

        def blob_for(name: str) -> MagicMock:
            if name == f"captures/{capture_id}/source":
                return source
            blob = MagicMock(name=name)
            if name == f"captures/{capture_id}/result.json":
                blob.exists.return_value = True
                blob.download_as_text.return_value = json.dumps({
                    "capture_id": capture_id, "tester_id": "a3",
                })
            else:
                blob.exists.return_value = False
            return blob

        storage_bucket.return_value.blob.side_effect = blob_for
        vision.return_value = {
            "stage": 2, "reader": "cloud_ocr", "latency_ms": 321, "words": [],
        }

        value = _process_stored_stage(capture_id, "a3", 1)

        forwarded = vision.call_args.args[0]
        self.assertTrue(forwarded.startswith(b"\xff\xd8"))
        self.assertEqual(vision.call_args.args[1:], (800, 600))
        self.assertEqual(value["tester_id"], "a3")
        cooling.assert_called_once_with(storage_bucket.return_value, capture_id, 1)
        store.assert_called_once_with(capture_id, 1, value)

    @patch("api.app._process_stored_stage", side_effect=RuntimeError("READER_COOLDOWN"))
    def test_stored_stage_cooldown_returns_without_retry(self, process: object) -> None:
        capture_id = "a" * 32
        response = self.client.post(
            f"/api/captures/{capture_id}/process/3",
            headers={"X-VillageLens-Tester-ID": "A3"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "READER_COOLDOWN")
        process.assert_called_once_with(capture_id, "a3", 3)

    @patch("api.app._openai_reader")
    @patch("api.app._vision_reader")
    @patch("api.app._storage_bucket")
    def test_stored_processing_reuses_all_existing_stages(
        self, storage_bucket: object, vision: object, openai: object,
    ) -> None:
        capture_id = "d" * 32
        values = {
            f"captures/{capture_id}/result.json": {
                "capture_id": capture_id, "tester_id": "a5",
            },
            f"captures/{capture_id}/stage-1.json": {
                "stage": 1, "reader": "cloud_ocr", "words": [],
            },
            f"captures/{capture_id}/stage-2.json": {
                "stage": 2, "reader": "vision_language", "model": "gpt-5.6-sol",
                "analysis_version": "instant-v2", "summary_kn": "ಪುಸ್ತಕ",
            },
            f"captures/{capture_id}/stage-3.json": {
                "stage": 3, "reader": "vision_language", "model": "gpt-5.6-sol",
                "analysis_version": "context-v2",
                "translations": [{"source": "book", "translation_kn": "ಪುಸ್ತಕ"}],
                "summary_kn": "ಪುಸ್ತಕ",
            },
            f"captures/{capture_id}/stage-4.json": {
                "stage": 4, "reader": "vision_language", "model": "gpt-6-astra",
                "analysis_version": "astra-review-v2", "summary_kn": "ಪುಸ್ತಕ",
                "consensus_validated": True,
            },
        }

        def blob_for(name: str) -> MagicMock:
            blob = MagicMock(name=name)
            blob.exists.return_value = name in values
            blob.download_as_text.return_value = json.dumps(values.get(name))
            return blob

        storage_bucket.return_value.blob.side_effect = blob_for

        stages, errors = _process_stored_capture(capture_id, "a3")

        self.assertEqual(set(stages), {1, 2, 3, 4})
        self.assertTrue(stages[3]["quality_validated"])
        self.assertEqual(errors, {})
        vision.assert_not_called()
        openai.assert_not_called()

        with self.assertRaises(FileNotFoundError):
            _process_stored_capture(capture_id, "a4")

    @patch("api.app.requests.post")
    def test_spoken_question_returns_scaled_evidence_without_storage(self, provider: object) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"output": [{"content": [{
            "type": "output_text", "text": json.dumps({
                "answer_kn": "ಇದು ಪುಸ್ತಕವಾಗಿದೆ.", "warning_kn": "", "uncertainty_kn": "",
                "evidence_box": [100, 200, 300, 400],
            }),
        }]}]}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            value = _openai_question(
                image_bytes(), "image/jpeg", 320, 120, "ಈ ಎಲೆಗೆ ರೋಗ ಇದೆಯೇ?",
                [{"question": "ಇದು ಏನು?", "answer_kn": "ಇದು ಒಂದು ಎಲೆ."}],
                {"x": 32, "y": 12, "width": 64, "height": 48, "label": "ಎಲೆ"},
                {"scene_type": "ಸಸ್ಯ", "brief_spoken_kn": "ಇದು ಒಂದು ಸಸ್ಯ."},
            )

        self.assertEqual(value["answer_kn"], "ಇದು ಪುಸ್ತಕವಾಗಿದೆ.")
        self.assertEqual(value["evidence"][0]["box"], {"x": 32, "y": 24, "width": 96, "height": 48})
        payload = provider.call_args.kwargs["json"]
        self.assertFalse(payload["store"])
        prompt = payload["input"][0]["content"][0]["text"]
        self.assertIn("ಈ ಎಲೆಗೆ ರೋಗ ಇದೆಯೇ?", prompt)
        self.assertIn("ಇದು ಒಂದು ಎಲೆ.", prompt)
        self.assertIn('"box_normalized_0_1000": [100, 100, 200, 400]', prompt)
        self.assertIn('"saved_semantic_scene": {"scene_type":', prompt)
        self.assertIn("Never answer with only a demonstrative word", prompt)
        self.assertIn("Kannada number words", prompt)

    def test_generic_identity_question_reuses_saved_semantic_answer(self) -> None:
        value = _saved_scene_identity_answer(
            "What is this?",
            {
                "brief_spoken_kn": "ಇದು ಎಫ್ ಎಸ್ ಹನ್ನೆರಡು ವೀಡಿಯೊ ಕ್ಯಾಮೆರಾ ಘಟಕ.",
                "detailed_spoken_kn": "ಇದು ಎಫ್ ಎಸ್ ಹನ್ನೆರಡು ವೀಡಿಯೊ ಕ್ಯಾಮೆರಾ ಘಟಕ. ಇದು ಚಿತ್ರವನ್ನು ದಾಖಲಿಸಲು ಬಳಸುತ್ತದೆ.",
                "objects": [{
                    "name_kn": "ವೀಡಿಯೊ ಕ್ಯಾಮೆರಾ ಘಟಕ",
                    "box": {"x": 10, "y": 20, "width": 200, "height": 80},
                }],
            },
            320, 120,
        )

        self.assertIsNotNone(value)
        self.assertEqual(value["answer_source"], "saved_semantic_scene")
        self.assertGreater(len(value["answer_kn"]), len("ಇದು"))
        self.assertIn("ಚಿತ್ರವನ್ನು ದಾಖಲಿಸಲು", value["answer_kn"])
        self.assertEqual(
            value["evidence"][0]["box"],
            {"x": 10.0, "y": 20.0, "width": 200.0, "height": 80.0},
        )

    @patch("api.app.requests.post")
    def test_openai_transcription_uses_audio_endpoint(self, provider: object) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"text": "ಈ ಚಿತ್ರದಲ್ಲಿ ಏನು ಇದೆ?"}

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            transcript = _openai_transcribe(b"audio", "question.m4a", "audio/mp4")

        self.assertEqual(transcript, "ಈ ಚಿತ್ರದಲ್ಲಿ ಏನು ಇದೆ?")
        self.assertEqual(provider.call_args.args[0], "https://api.openai.com/v1/audio/transcriptions")
        self.assertEqual(provider.call_args.kwargs["data"]["model"], "gpt-4o-mini-transcribe")
        self.assertEqual(provider.call_args.kwargs["files"]["file"], (
            "question.m4a", b"audio", "audio/mp4",
        ))

    @patch("api.app._openai_question", return_value={"answer_kn": "ಇದು ಒಂದು ಚಿತ್ರ."})
    @patch("api.app._openai_transcribe", return_value="ಇದು ಏನು?")
    @patch("api.app._stored_json", return_value={"tester_id": "a1"})
    @patch("api.app._storage_bucket")
    def test_recorded_question_endpoint_transcribes_then_answers(
        self, storage_bucket: object, stored_json: object,
        transcribe: object, question: object,
    ) -> None:
        source = storage_bucket.return_value.blob.return_value
        source.exists.return_value = True
        source.download_as_bytes.return_value = image_bytes()
        capture_id = "f" * 32

        response = self.client.post(
            f"/api/captures/{capture_id}/ask-audio",
            data={"audio": (io.BytesIO(b"recorded-audio"), "question.webm", "audio/webm")},
            headers={"X-VillageLens-Tester-ID": "a1"},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["answer_kn"], "ಇದು ಒಂದು ಚಿತ್ರ.")
        transcribe.assert_called_once_with(b"recorded-audio", "question.webm", "audio/webm")
        self.assertEqual(question.call_args.args[4], "ಇದು ಏನು?")
        self.assertEqual(response.get_json()["question"], "ಇದು ಏನು?")

    @patch("api.app._openai_question", return_value={"answer_kn": "ಇದು ಮಾದರಿ ಚಿತ್ರ."})
    @patch("api.app._openai_transcribe", return_value="ಇದು ಏನು?")
    def test_demo_recorded_question_is_supported(
        self, transcribe: object, question: object,
    ) -> None:
        response = self.client.post(
            "/api/demos/demo-i1/ask-audio",
            data={"audio": (io.BytesIO(b"recorded-audio"), "question.m4a", "audio/mp4")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["question"], "ಇದು ಏನು?")
        transcribe.assert_called_once()
        question.assert_called_once()

    def test_usage_events_accept_only_privacy_safe_aggregates(self) -> None:
        with self.assertLogs("api.app", level="INFO") as logs:
            response = self.client.post("/api/events", json={"events": [
                {"name": "infer", "capture_id": "e" * 32, "ok": True,
                 "elapsed_ms": "bad", "question": "private spoken words"},
                {"name": "not-allowed", "text": "private OCR"},
            ]})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()["accepted"], 1)
        joined = " ".join(logs.output)
        self.assertIn('"name":"infer"', joined)
        self.assertNotIn("private spoken words", joined)
        self.assertNotIn("private OCR", joined)

    def test_unknown_reader_stage_is_rejected(self) -> None:
        response = self.client.post("/api/read/5", data=image_bytes(), content_type="image/jpeg")
        self.assertEqual(response.status_code, 404)

        retained_only = self.client.post(
            "/api/read/4", data=image_bytes(), content_type="image/jpeg",
        )
        self.assertEqual(retained_only.status_code, 409)

    @patch("api.app._normalized_image")
    def test_unconfigured_stage_three_fails_before_image_work(self, normalize: object) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            response = self.client.post(
                "/api/read/3", data=image_bytes(), content_type="image/jpeg",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "OPENAI_READER_NOT_CONFIGURED")
        normalize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
