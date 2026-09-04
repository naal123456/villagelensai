from __future__ import annotations

import io
import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from api.app import _access_token, app


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
        self.assertIn(b"VillageLensAI", response.data)
        self.assertIn(b'id="mode-word"', response.data)
        self.assertIn(b'id="play-sentences"', response.data)
        self.assertIn(b'id="quality-4"', response.data)
        self.assertIn(b'navigationGeneration', response.data)
        self.assertIn(b'localStorage.setItem', response.data)
        self.assertIn(b'X-VillageLens-Tester-ID', response.data)
        self.assertIn(b'function speechSegments', response.data)
        self.assertIn(b'function voiceFor', response.data)
        self.assertIn(b"fetch('/api/speech'", response.data)
        self.assertIn(b'function playKannada', response.data)
        self.assertIn(b'speechAudioCache', response.data)
        self.assertNotIn(b'Speech Services', response.data)
        self.assertIn(b'function translatedWord', response.data)
        self.assertIn(b"?'saved':'local'", response.data)
        stage_three = response.data.split(b"if (stageNumber===3)", 1)[1].split(
            b"if (gallery[galleryIndex]===item)", 1,
        )[0]
        self.assertNotIn(b"item.result=value", stage_three)
        self.assertIn(b"item.result.translations=item.translations", stage_three)
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
        self.assertIn(b"Swipe the page", response.data)
        self.assertIn("ಅ ಆ ಇ".encode(), response.data)

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
        stage_blob.download_as_text.return_value = json.dumps({"stage": 2, "words": []})
        storage_bucket.return_value.list_blobs.return_value = [result_blob, stage_blob]

        items = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "A1"},
        ).get_json()["items"]

        self.assertEqual(items[2]["stage2"], {"stage": 2, "words": []})
        other_items = self.client.get(
            "/api/gallery", headers={"X-VillageLens-Tester-ID": "a2"},
        ).get_json()["items"]
        self.assertEqual(len(other_items), 2)

    def test_health_reports_pinned_models(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

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
        self.assertEqual(response.headers["Cache-Control"], "no-store")

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
    def test_stage_two_reader_contract(self, reader: object, store: object) -> None:
        reader.return_value = {
            "schema": "villagelens.reader.v1", "stage": 2,
            "image_size": {"width": 320, "height": 120}, "words": [], "lines": [],
        }
        capture_id = "a" * 32
        response = self.client.post(
            "/api/read/2", data=image_bytes(), content_type="image/jpeg",
            headers={"X-VillageLens-Capture-ID": capture_id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stage"], 2)
        store.assert_called_once_with(capture_id, 2, reader.return_value)

    @patch("api.app._store_reader_evidence")
    @patch("api.app.requests.post")
    def test_stage_three_returns_word_translations_without_inference(
        self, provider: object, store: object,
    ) -> None:
        provider.return_value.status_code = 200
        provider.return_value.json.return_value = {"output": [{"content": [{
            "type": "output_text",
            "text": json.dumps({
                "words": [], "lines": [],
                "translations": [{"source": "book", "translation_kn": "ಪುಸ್ತಕ"}],
                "summary_kn": "ಪುಸ್ತಕ",
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
        self.assertEqual(value["tester_id"], "a1")
        request_payload = provider.call_args.kwargs["json"]
        prompt = request_payload["input"][0]["content"][0]["text"]
        self.assertIn("do not infer", prompt)
        self.assertIn("translations", request_payload["text"]["format"]["schema"]["required"])
        store.assert_called_once_with(capture_id, 3, value)

    def test_unknown_reader_stage_is_rejected(self) -> None:
        response = self.client.post("/api/read/4", data=image_bytes(), content_type="image/jpeg")
        self.assertEqual(response.status_code, 404)

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
