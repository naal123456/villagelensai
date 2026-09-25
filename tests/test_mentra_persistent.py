from __future__ import annotations

import hashlib
import io
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from api.app import _native_mentra_hub, _persistent_mentra_hub, app
from api.mentra_bridge import MentraBridgeError
from api.mentra_enrollment import (
    ENROLLMENT_OBJECT,
    ENROLLMENT_SCHEMA,
    NATIVE_ENROLLMENT_OBJECT,
    MentraEnrollmentStore,
)
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

    def test_native_enrollment_uses_an_independent_record(self) -> None:
        bucket = FakeBucket()
        miniapp = MentraEnrollmentStore(lambda: bucket, now=lambda: self.instant)
        native = MentraEnrollmentStore(
            lambda: bucket,
            now=lambda: self.instant,
            object_name=NATIVE_ENROLLMENT_OBJECT,
        )
        miniapp.enroll("mentra-live-01", "m" * 48)
        native.enroll("mentra-live-01", "n" * 48)

        self.assertNotEqual(
            bucket.blob(ENROLLMENT_OBJECT).value,
            bucket.blob(NATIVE_ENROLLMENT_OBJECT).value,
        )
        self.assertEqual(native.authenticate("n" * 48), "mentra-live-01")


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
        _native_mentra_hub.reset()
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


class NativeMentraApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(
            TESTING=True,
            VILLAGELENS_ACCESS_CODE="",
            VILLAGELENS_SESSION_SECRET="",
        )
        _persistent_mentra_hub.reset()
        _native_mentra_hub.reset()
        self.client = app.test_client()

    def enroll_and_get_job(self) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        browser = self.client.post(
            "/api/mentra/v3/sessions",
            headers={"X-VillageLens-Tester-ID": "a2"},
            json={"output_language": "en"},
        ).get_json()
        credential = self.client.post("/api/mentra/v3/device/enroll", json={
            "pairing_code": browser["pairing_code"],
            "device_profile_id": "mentra-live-01",
        }).get_json()
        job = self.client.get(
            "/api/mentra/v3/device/jobs",
            headers={"Authorization": f"Bearer {credential['device_token']}"},
        ).get_json()
        return browser, credential, job

    def test_native_job_is_bounded_and_excludes_browser_identity(self) -> None:
        browser, credential, job = self.enroll_and_get_job()

        self.assertEqual(job["schema"], "villagelens.mentra-native-photo-job.v1")
        self.assertEqual(job["request_id"], browser["request_id"])
        self.assertEqual(job["camera"], {
            "fov": 62,
            "roi_position": "center",
            "size": "max",
            "compress": "none",
            "sound": True,
            "save": False,
            "exposure": "auto",
        })
        self.assertNotIn("tester_id", job)
        self.assertNotIn("output_language", job)
        self.assertNotIn("device_token", job)
        self.assertEqual(
            job["webhook_url"],
            f"http://localhost/api/mentra/v3/device/captures/{browser['request_id']}",
        )
        idle = self.client.get(
            "/api/mentra/v3/device/jobs",
            headers={"Authorization": f"Bearer {credential['device_token']}"},
        )
        self.assertEqual(idle.status_code, 204)

    def test_miniapp_credential_cannot_consume_native_job(self) -> None:
        miniapp_browser = self.client.post(
            "/api/mentra/v2/sessions",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"output_language": "kn"},
        ).get_json()
        miniapp_credential = self.client.post("/api/mentra/v2/device/enroll", json={
            "pairing_code": miniapp_browser["pairing_code"],
            "device_profile_id": "mentra-live-01",
        }).get_json()
        native_browser = self.client.post(
            "/api/mentra/v3/sessions",
            headers={"X-VillageLens-Tester-ID": "a2"},
            json={"output_language": "en"},
        ).get_json()
        native_credential = self.client.post("/api/mentra/v3/device/enroll", json={
            "pairing_code": native_browser["pairing_code"],
            "device_profile_id": "mentra-live-01",
        }).get_json()

        rejected = self.client.get(
            "/api/mentra/v3/device/jobs",
            headers={"Authorization": f"Bearer {miniapp_credential['device_token']}"},
        )
        native_job = self.client.get(
            "/api/mentra/v3/device/jobs",
            headers={"Authorization": f"Bearer {native_credential['device_token']}"},
        ).get_json()

        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(native_job["request_id"], native_browser["request_id"])

    @patch("api.app._ingest_capture")
    def test_native_multipart_preserves_hash_and_ingests_once(self, ingest: object) -> None:
        browser, _credential, job = self.enroll_and_get_job()
        source = b"\xff\xd8immutable-native-mentra"
        digest = hashlib.sha256(source).hexdigest()
        ingest.return_value = ({"capture_id": browser["request_id"], "retained": True}, 200)
        headers = {"Authorization": f"Bearer {job['auth_token']}"}

        accepted = self.client.post(
            job["webhook_url"],
            headers=headers,
            data={
                "requestId": browser["request_id"],
                "photo": (io.BytesIO(source), "capture.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        repeated = self.client.post(
            job["webhook_url"],
            headers=headers,
            data={
                "requestId": browser["request_id"],
                "photo": (io.BytesIO(source), "capture.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.get_json()["source_sha256"], digest)
        self.assertEqual(repeated.status_code, 200)
        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.kwargs["tester_id"], "a2")
        provenance = ingest.call_args.kwargs["capture_provenance"]
        self.assertEqual(provenance["transport"], "mentra-bluetooth-sdk-webhook-v1")
        self.assertEqual(provenance["source_sha256"], digest)
        self.assertNotIn("auth_token", provenance)

    @patch("api.app._ingest_capture")
    def test_native_upload_rejects_wrong_request_id(self, ingest: object) -> None:
        browser, _credential, job = self.enroll_and_get_job()
        rejected = self.client.post(
            job["webhook_url"],
            headers={"Authorization": f"Bearer {job['auth_token']}"},
            data={
                "requestId": "0" * 32,
                "photo": (io.BytesIO(b"\xff\xd8photo"), "capture.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.get_json()["error"], "MENTRA_CAPTURE_REQUEST_MISMATCH")
        ingest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
