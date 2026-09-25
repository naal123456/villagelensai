from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable

from .mentra_bridge import MentraBridgeError


ENROLLMENT_SCHEMA = "villagelens.mentra-device-enrollment.v1"
CREDENTIAL_SCHEMA = "villagelens.mentra-device-credential.v1"
ENROLLMENT_OBJECT = "mentra-enrollments/v1/default.json"
DEVICE_PROFILE_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class MentraEnrollmentStore:
    """Persistent single-Mentra registry in the existing private bucket."""

    def __init__(
        self, bucket_provider: Callable[[], Any], *, now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._bucket_provider = bucket_provider
        self._now = now

    def _blob(self) -> Any:
        bucket = self._bucket_provider()
        if bucket is None:
            raise MentraBridgeError("MENTRA_ENROLLMENT_STORAGE_UNAVAILABLE", 503)
        return bucket.blob(ENROLLMENT_OBJECT)

    def _read(self) -> dict[str, Any] | None:
        blob = self._blob()
        try:
            if not blob.exists():
                return None
            value = json.loads(blob.download_as_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except Exception as error:
            raise MentraBridgeError("MENTRA_ENROLLMENT_STORAGE_UNAVAILABLE", 503) from error
        required = {"schema", "device_profile_id", "token_sha256", "enrolled_at", "status"}
        if (
            not isinstance(value, dict)
            or not required.issubset(value)
            or value.get("schema") != ENROLLMENT_SCHEMA
            or not DEVICE_PROFILE_PATTERN.fullmatch(str(value.get("device_profile_id", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("token_sha256", "")))
            or value.get("status") not in {"active", "revoked"}
        ):
            raise MentraBridgeError("MENTRA_ENROLLMENT_RECORD_INVALID", 503)
        return value

    def _write(self, value: dict[str, Any]) -> None:
        try:
            blob = self._blob()
            blob.cache_control = "no-store"
            blob.upload_from_string(
                json.dumps(value, separators=(",", ":"), sort_keys=True),
                content_type="application/json",
            )
        except MentraBridgeError:
            raise
        except Exception as error:
            raise MentraBridgeError("MENTRA_ENROLLMENT_STORAGE_UNAVAILABLE", 503) from error

    def active_profile_id(self) -> str:
        value = self._read()
        return str(value["device_profile_id"]) if value and value["status"] == "active" else ""

    def enroll(self, device_profile_id: str, token: str) -> dict[str, str]:
        if not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise MentraBridgeError("MENTRA_DEVICE_PROFILE_INVALID", 400)
        if not token or len(token) > 128 or any(character.isspace() for character in token):
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        existing = self._read()
        if existing is not None and existing["status"] == "active":
            raise MentraBridgeError("MENTRA_DEVICE_ALREADY_ENROLLED", 409)
        value = {
            "schema": ENROLLMENT_SCHEMA,
            "device_profile_id": device_profile_id,
            "token_sha256": _token_hash(token),
            "enrolled_at": _timestamp(self._now()),
            "status": "active",
            "revoked_at": "",
        }
        self._write(value)
        return {
            "schema": ENROLLMENT_SCHEMA,
            "device_profile_id": device_profile_id,
            "enrolled_at": str(value["enrolled_at"]),
            "status": "active",
        }

    def authenticate(self, token: str) -> str:
        if not token or len(token) > 128 or any(character.isspace() for character in token):
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        value = self._read()
        supplied = _token_hash(token)
        expected = str(value.get("token_sha256", "")) if value else "0" * 64
        if value is None or value["status"] != "active" or not hmac.compare_digest(supplied, expected):
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_INVALID", 401)
        return str(value["device_profile_id"])

    def revoke(self, device_profile_id: str) -> dict[str, str]:
        value = self._read()
        if (
            value is None
            or value["status"] != "active"
            or value["device_profile_id"] != device_profile_id
        ):
            raise MentraBridgeError("MENTRA_DEVICE_ENROLLMENT_NOT_FOUND", 404)
        value["status"] = "revoked"
        value["revoked_at"] = _timestamp(self._now())
        self._write(value)
        return {
            "schema": ENROLLMENT_SCHEMA,
            "device_profile_id": device_profile_id,
            "status": "revoked",
            "revoked_at": str(value["revoked_at"]),
        }
