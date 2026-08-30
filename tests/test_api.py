from __future__ import annotations

import io
import subprocess
import unittest
from unittest.mock import patch

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

    @patch("api.app.subprocess.run")
    def test_capture_returns_stage_one_geometry_without_retention(self, run: object) -> None:
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


if __name__ == "__main__":
    unittest.main()
