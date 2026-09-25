from __future__ import annotations

import hashlib
import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from api.app import _mentra_hub, app
from api.mentra_bridge import MentraBridgeError, MentraSessionHub


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 24, 22, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value


class MentraSessionHubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.hub = MentraSessionHub(now=self.clock)

    def test_one_time_pairing_keeps_tester_identity_out_of_device_contract(self) -> None:
        browser = self.hub.create_session("a1", "kn")
        device = self.hub.pair_companion(browser["pairing_code"])

        self.assertEqual(device["schema"], "villagelens.mentra-photo-pairing.v1")
        self.assertEqual(device["request_id"], browser["request_id"])
        self.assertNotIn("tester_id", device)
        self.assertNotIn("output_language", device)
        with self.assertRaisesRegex(MentraBridgeError, "MENTRA_PAIRING_CODE_INVALID"):
            self.hub.pair_companion(browser["pairing_code"])

    def test_pairing_and_upload_are_expiring_and_hash_bound(self) -> None:
        expired = self.hub.create_session("a1", "kn")
        self.clock.value += timedelta(minutes=5)
        with self.assertRaisesRegex(MentraBridgeError, "MENTRA_PAIRING_CODE_INVALID"):
            self.hub.pair_companion(expired["pairing_code"])

        browser = self.hub.create_session("a2", "en")
        device = self.hub.pair_companion(browser["pairing_code"])
        digest = "a" * 64
        self.assertIsNone(
            self.hub.existing_acceptance(
                device["device_token"], browser["request_id"], digest,
            )
        )
        accepted = self.hub.complete_upload(
            device["device_token"], browser["request_id"], digest, browser["request_id"],
        )
        self.assertEqual(accepted["source_sha256"], digest)
        self.assertEqual(
            self.hub.describe_session(browser["session_id"], "a2")["state"],
            "complete",
        )
        with self.assertRaisesRegex(MentraBridgeError, "MENTRA_CAPTURE_SOURCE_CONFLICT"):
            self.hub.existing_acceptance(
                device["device_token"], browser["request_id"], "b" * 64,
            )

    def test_browser_session_is_private_to_its_tester(self) -> None:
        browser = self.hub.create_session("a1", "kn")
        with self.assertRaisesRegex(MentraBridgeError, "MENTRA_SESSION_NOT_FOUND"):
            self.hub.describe_session(browser["session_id"], "a2")


class MentraBridgeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(
            TESTING=True,
            VILLAGELENS_ACCESS_CODE="",
            VILLAGELENS_SESSION_SECRET="",
        )
        _mentra_hub.reset()
        self.client = app.test_client()

    def create_and_pair(self) -> tuple[dict[str, str], dict[str, object]]:
        browser_response = self.client.post(
            "/api/mentra/v1/sessions",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"output_language": "kn"},
        )
        browser = browser_response.get_json()
        device_response = self.client.post(
            "/api/mentra/v1/device/pair",
            json={"pairing_code": browser["pairing_code"]},
        )
        return browser, device_response.get_json()

    def test_session_requires_access_and_pairing_endpoint_does_not(self) -> None:
        app.config.update(
            VILLAGELENS_ACCESS_CODE="test-code",
            VILLAGELENS_SESSION_SECRET="test-session-secret",
        )

        session = self.client.post(
            "/api/mentra/v1/sessions",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"output_language": "kn"},
        )
        pairing = self.client.post(
            "/api/mentra/v1/device/pair", json={"pairing_code": "0" * 16},
        )

        self.assertEqual(session.status_code, 401)
        self.assertEqual(pairing.status_code, 401)
        self.assertEqual(pairing.get_json()["error"], "MENTRA_PAIRING_CODE_INVALID")

    def test_pairing_returns_one_photo_webhook_without_tester_identity(self) -> None:
        browser, device = self.create_and_pair()

        self.assertEqual(device["schema"], "villagelens.mentra-photo-pairing.v1")
        self.assertEqual(device["request_id"], browser["request_id"])
        self.assertNotIn("tester_id", device)
        photo_request = device["photo_request"]
        self.assertEqual(photo_request["request_id"], browser["request_id"])
        self.assertTrue(photo_request["webhook_url"].endswith(
            f"/api/mentra/v1/device/captures/{browser['request_id']}"
        ))
        self.assertGreater(len(photo_request["auth_token"]), 32)
        self.assertTrue(photo_request["sound"])
        self.assertEqual(photo_request["exposure"], "auto")

    @patch("api.app._ingest_capture")
    def test_photo_webhook_uses_existing_gallery_ingest_and_is_idempotent(
        self, ingest: object,
    ) -> None:
        browser, device = self.create_and_pair()
        photo_request = device["photo_request"]
        source = b"\xff\xd8immutable-mentra-source"
        digest = hashlib.sha256(source).hexdigest()
        ingest.return_value = ({"capture_id": browser["request_id"], "retained": True}, 200)
        headers = {"Authorization": f"Bearer {photo_request['auth_token']}"}
        path = f"/api/mentra/v1/device/captures/{browser['request_id']}"

        def upload() -> object:
            return self.client.post(
                path,
                headers=headers,
                data={
                    "requestId": browser["request_id"],
                    "photo": (io.BytesIO(source), "capture.jpg", "image/jpeg"),
                },
            )

        first = upload()
        second = upload()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["schema"], "villagelens.mentra-upload-acceptance.v1")
        self.assertEqual(first.get_json()["source_sha256"], digest)
        self.assertEqual(second.get_json(), first.get_json())
        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.kwargs["tester_id"], "a1")
        self.assertEqual(ingest.call_args.kwargs["capture_source"], "mentra-live-v1")
        provenance = ingest.call_args.kwargs["capture_provenance"]
        self.assertEqual(provenance["schema"], "villagelens.mentra-capture-provenance.v1")
        self.assertEqual(provenance["source_sha256"], digest)
        self.assertEqual(provenance["capture_mode"], "explicit-still-photo")

        status = self.client.get(
            f"/api/mentra/v1/sessions/{browser['session_id']}",
            headers={"X-VillageLens-Tester-ID": "a1"},
        ).get_json()
        self.assertEqual(status["state"], "complete")
        self.assertEqual(status["gallery_capture_id"], browser["request_id"])

    def test_photo_webhook_rejects_missing_auth_and_mismatched_request(self) -> None:
        browser, device = self.create_and_pair()
        photo_request = device["photo_request"]
        path = f"/api/mentra/v1/device/captures/{browser['request_id']}"

        missing_auth = self.client.post(path, data={
            "requestId": browser["request_id"],
            "photo": (io.BytesIO(b"\xff\xd8source"), "capture.jpg", "image/jpeg"),
        })
        mismatch = self.client.post(
            path,
            headers={"Authorization": f"Bearer {photo_request['auth_token']}"},
            data={
                "requestId": "f" * 32,
                "photo": (io.BytesIO(b"\xff\xd8source"), "capture.jpg", "image/jpeg"),
            },
        )

        self.assertEqual(missing_auth.status_code, 401)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.get_json()["error"], "MENTRA_CAPTURE_REQUEST_MISMATCH")


if __name__ == "__main__":
    unittest.main()
