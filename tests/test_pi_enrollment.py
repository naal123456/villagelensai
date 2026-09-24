from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from api.pi_bridge import PiBridgeError
from api.pi_enrollment import ENROLLMENT_OBJECT, ENROLLMENT_SCHEMA, PiEnrollmentStore


class FakeBlob:
    def __init__(self) -> None:
        self.value: str | None = None
        self.cache_control = ""
        self.content_type = ""

    def exists(self) -> bool:
        return self.value is not None

    def download_as_text(self, encoding: str = "utf-8") -> str:
        if self.value is None:
            raise FileNotFoundError
        return self.value

    def upload_from_string(self, value: str, content_type: str) -> None:
        self.value = value
        self.content_type = content_type


class FakeBucket:
    def __init__(self) -> None:
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, name: str) -> FakeBlob:
        return self.blobs.setdefault(name, FakeBlob())


class PiEnrollmentStoreTests(unittest.TestCase):
    instant = datetime(2026, 9, 24, 18, 0, tzinfo=timezone.utc)

    def setUp(self) -> None:
        self.bucket = FakeBucket()
        self.store = PiEnrollmentStore(lambda: self.bucket, now=lambda: self.instant)

    def test_persists_only_hash_and_authenticates_after_new_store_instance(self) -> None:
        token = "private-device-token-with-enough-entropy-0123456789"
        enrolled = self.store.enroll("rpi5-bench-01", token)

        raw = self.bucket.blob(ENROLLMENT_OBJECT).value or ""
        self.assertNotIn(token, raw)
        self.assertEqual(json.loads(raw)["schema"], ENROLLMENT_SCHEMA)
        restarted = PiEnrollmentStore(lambda: self.bucket, now=lambda: self.instant)
        self.assertEqual(restarted.active_profile_id(), "rpi5-bench-01")
        self.assertEqual(restarted.authenticate(token), "rpi5-bench-01")
        self.assertEqual(enrolled["status"], "active")

    def test_active_device_must_be_revoked_before_reenrollment(self) -> None:
        self.store.enroll("rpi5-bench-01", "a" * 40)

        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_ALREADY_ENROLLED"):
            self.store.enroll("replacement-pi", "b" * 40)

        revoked = self.store.revoke("rpi5-bench-01")
        self.assertEqual(revoked["status"], "revoked")
        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_AUTH_INVALID"):
            self.store.authenticate("a" * 40)
        self.store.enroll("replacement-pi", "b" * 40)
        self.assertEqual(self.store.authenticate("b" * 40), "replacement-pi")

    def test_wrong_token_and_unavailable_storage_fail_closed(self) -> None:
        self.store.enroll("rpi5-bench-01", "a" * 40)
        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_AUTH_INVALID"):
            self.store.authenticate("b" * 40)
        with self.assertRaisesRegex(PiBridgeError, "PI_ENROLLMENT_STORAGE_UNAVAILABLE"):
            PiEnrollmentStore(lambda: None).active_profile_id()
