from __future__ import annotations

import io
import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from api.app import app


TSV = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
1\t1\t0\t0\t0\t0\t0\t0\t320\t120\t-1\t
5\t1\t1\t1\t1\t1\t10\t20\t100\t30\t91.5\tಕನ್ನಡ
5\t1\t1\t1\t1\t2\t120\t20\t80\t30\t88.0\ttext
"""


def image_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (320, 120), "white").save(output, format="JPEG")
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
        self.assertIn(b"?'saved':'local'", response.data)
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
            "label": "Captured page", "words": [], "lines": [],
        })
        stage_blob = MagicMock(name="stage_blob")
        stage_blob.name = f"captures/{capture_id}/stage-2.json"
        stage_blob.download_as_text.return_value = json.dumps({"stage": 2, "words": []})
        storage_bucket.return_value.list_blobs.return_value = [result_blob, stage_blob]

        items = self.client.get("/api/gallery").get_json()["items"]

        self.assertEqual(items[2]["stage2"], {"stage": 2, "words": []})

    def test_health_reports_pinned_models(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

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
        response = self.client.post("/access", data={"code": "test-code"})
        self.assertEqual(response.status_code, 303)
        cookie = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=Lax", cookie)
        token = cookie.split(";", 1)[0].split("=", 1)[1]
        self.client.set_cookie("villagelens_access", token, secure=True)
        allowed = self.client.get("/a/", base_url="https://localhost")
        self.addCleanup(allowed.close)
        self.assertEqual(allowed.status_code, 200)

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
        )
        self.assertEqual(response.status_code, 200)
        value = response.get_json()
        self.assertEqual(value["stage"], 1)
        self.assertEqual(value["lines"][0]["text"], "ಕನ್ನಡ text")
        self.assertEqual(
            value["words"][0]["box"], {"x": 10, "y": 20, "width": 100, "height": 30},
        )
        self.assertFalse(value["retained"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")

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
