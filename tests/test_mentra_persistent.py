from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from api.app import _persistent_mentra_hub, app
from api.mentra_bridge import MentraBridgeError
from api.mentra_enrollment import ENROLLMENT_OBJECT, ENROLLMENT_SCHEMA, MentraEnrollmentStore
from api.mentra_persistent import PersistentMentraHub


class FakeBlob:
    def __init__(self) -> None:
        self.value: str | None = None
        self.cache_control = ""

    def exists(self) -> bool:
        return self.value is not None

    def download_as_text(self, encoding: str = "utf-8") -> str:
        if self.value is None:
            raise FileNotFoundError
        return self.value

    def upload_from_string(self, value: str, content_type: str) -> None:
        self.value = value


class FakeBucket:
    def __init__(self) -> None:
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, name: str) -> FakeBlob:
        return self.blobs.setdefault(name, FakeBlob())


class MentraEnrollmentStoreTests(unittest.TestCase):
    instant = datetime(2026, 9, 25, 18, 0, tzinfo=timezone.utc)

    def test_persists_only_token_hash_and_supports_revocation(self) -> None:
        bucket = FakeBucket()
        store = MentraEnrollmentStore(lambda: bucket, now=lambda: self.instant)
        token = "private-mentra-device-token-with-entropy-0123456789"

        store.enroll("mentra-live-01", token)

        raw = bucket.blob(ENROLLMENT_OBJECT).value or ""
        self.assertNotIn(token, raw)
        self.assertEqual(json.loads(raw)["schema"], ENROLLMENT_SCHEMA)
        restarted = MentraEnrollmentStore(lambda: bucket, now=lambda: self.instant)
        self.assertEqual(restarted.authenticate(token), "mentra-live-01")
        self.assertEqual(restarted.revoke("mentra-live-01")["status"], "revoked")
        with self.assertRaisesRegex(MentraBridgeError, "MENTRA_DEVICE_AUTH_INVALID"):
            restarted.authenticate(token)


class PersistentMentraHubTests(unittest.TestCase):
    def test_idle_device_gets_no_job_and_one_browser_press_gets_one_job(self) -> None:
        hub = PersistentMentraHub()
        browser = hub.create_session("a1", "kn")
        device = hub.pair_device(browser["pairing_code"], "mentra-live-01")

        first = hub.next_job(device["device_token"])
        second = hub.next_job(device["device_token"])

        self.assertEqual(first["camera"]["fov"], 62)
        self.assertEqual(first["camera"]["mode"], "text")
        self.assertTrue(first["camera"]["sound"])
        self.assertFalse(first["camera"]["save_to_gallery"])
        self.assertIsNone(second)
        self.assertEqual(hub.describe_session(browser["session_id"], "a1")["state"], "capturing")

    def test_persistent_token_routes_a_later_browser_request(self) -> None:
        hub = PersistentMentraHub()
        initial = hub.create_session("a1", "kn")
        device = hub.pair_device(initial["pairing_code"], "mentra-live-01")
        hub.next_job(device["device_token"])
        hub.revoke_session(initial["session_id"], "a1")

        later = hub.create_session("a2", "en", "mentra-live-01")
        job = hub.next_job(device["device_token"])

        self.assertTrue(later["paired"])
        self.assertNotIn("pairing_code", later)
        self.assertEqual(job["request_id"], later["request_id"])


class FakeDownload:
    status_code = 200
    headers = {"Content-Type": "image/jpeg", "Content-Length": "23"}

    def iter_content(self, chunk_size: int):
        yield b"\xff\xd8immutable-mentra-v2"

    def close(self) -> None:
        pass


class PersistentMentraApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(
            TESTING=True,
            VILLAGELENS_ACCESS_CODE="",
            VILLAGELENS_SESSION_SECRET="",
        )
        _persistent_mentra_hub.reset()
        self.client = app.test_client()

    def enroll_and_get_job(self) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        browser = self.client.post(
            "/api/mentra/v2/sessions",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"output_language": "kn"},
        ).get_json()
        credential = self.client.post("/api/mentra/v2/device/enroll", json={
            "pairing_code": browser["pairing_code"],
            "device_profile_id": "mentra-live-01",
        }).get_json()
        job = self.client.get(
            "/api/mentra/v2/device/jobs",
            headers={"Authorization": f"Bearer {credential['device_token']}"},
        ).get_json()
        return browser, credential, job

    def test_enrollment_job_contract_excludes_tester_identity(self) -> None:
        browser, credential, job = self.enroll_and_get_job()

        self.assertEqual(credential["schema"], "villagelens.mentra-device-credential.v1")
        self.assertNotIn("tester_id", credential)
        self.assertNotIn("output_language", job)
        self.assertNotIn("tester_id", job)
        self.assertEqual(job["request_id"], browser["request_id"])
        self.assertTrue(job["upload_url"].startswith("http://localhost/"))
        idle = self.client.get(
            "/api/mentra/v2/device/jobs",
            headers={"Authorization": f"Bearer {credential['device_token']}"},
        )
        self.assertEqual(idle.status_code, 204)

    @patch("api.app._ingest_capture")
    @patch("api.app.requests.get", return_value=FakeDownload())
    def test_signed_photo_is_allowlisted_hash_bound_and_ingested_once(
        self, download: object, ingest: object,
    ) -> None:
        browser, _credential, job = self.enroll_and_get_job()
        source = b"\xff\xd8immutable-mentra-v2"
        digest = hashlib.sha256(source).hexdigest()
        ingest.return_value = ({"capture_id": browser["request_id"], "retained": True}, 200)
        payload = {
            "request_id": browser["request_id"],
            "photo_url": "https://photos.mentra.test/private-signed-value",
            "photo_request_id": "opaque-mentra-request",
            "media_type": "image/jpeg",
            "reported_bytes": len(source),
            "fov": 62,
            "roi_position": "center",
            "capture_mode": "text",
        }
        headers = {"Authorization": f"Bearer {job['upload_token']}"}

        with patch.dict("os.environ", {"VILLAGELENS_MENTRA_PHOTO_HOSTS": "photos.mentra.test"}):
            accepted = self.client.post(job["upload_url"], headers=headers, json=payload)

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.get_json()["source_sha256"], digest)
        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.kwargs["tester_id"], "a1")
        self.assertEqual(ingest.call_args.kwargs["capture_source"], "mentra-live-v1")
        provenance = ingest.call_args.kwargs["capture_provenance"]
        self.assertEqual(provenance["fov_degrees"], 62)
        self.assertNotIn("photo_url", provenance)
        download.assert_called_once()

    @patch("api.app.requests.get")
    def test_signed_photo_rejects_unconfigured_or_unapproved_host(self, download: object) -> None:
        browser, _credential, job = self.enroll_and_get_job()
        payload = {
            "request_id": browser["request_id"],
            "photo_url": "https://attacker.example/private",
            "photo_request_id": "opaque-mentra-request",
            "media_type": "image/jpeg",
            "reported_bytes": 10,
            "fov": 62,
            "roi_position": "center",
            "capture_mode": "text",
        }
        headers = {"Authorization": f"Bearer {job['upload_token']}"}
        with patch.dict("os.environ", {"VILLAGELENS_MENTRA_PHOTO_HOSTS": "photos.mentra.test"}):
            rejected = self.client.post(job["upload_url"], headers=headers, json=payload)
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.get_json()["error"], "MENTRA_PHOTO_URL_INVALID")
        download.assert_not_called()

    @patch("api.app._ingest_capture")
    @patch("api.app.requests.get", return_value=FakeDownload())
    def test_signed_photo_rejects_reported_size_mismatch_before_ingest(
        self, _download: object, ingest: object,
    ) -> None:
        browser, _credential, job = self.enroll_and_get_job()
        payload = {
            "request_id": browser["request_id"],
            "photo_url": "https://photos.mentra.test/private-signed-value",
            "photo_request_id": "opaque-mentra-request",
            "media_type": "image/jpeg",
            "reported_bytes": 999,
            "fov": 62,
            "roi_position": "center",
            "capture_mode": "text",
        }
        with patch.dict("os.environ", {"VILLAGELENS_MENTRA_PHOTO_HOSTS": "photos.mentra.test"}):
            rejected = self.client.post(
                job["upload_url"],
                headers={"Authorization": f"Bearer {job['upload_token']}"},
                json=payload,
            )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.get_json()["error"], "MENTRA_PHOTO_SIZE_MISMATCH")
        ingest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
