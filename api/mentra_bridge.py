from __future__ import annotations

import hashlib
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


SESSION_SCHEMA = "villagelens.mentra-browser-session.v1"
PAIRING_SCHEMA = "villagelens.mentra-photo-pairing.v1"
UPLOAD_ACCEPTANCE_SCHEMA = "villagelens.mentra-upload-acceptance.v1"
REQUEST_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
SOURCE_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
PAIRING_CODE_PATTERN = re.compile(r"[0-9A-F]{16}")
PAIRING_TTL = timedelta(minutes=5)
UPLOAD_GRACE = timedelta(minutes=10)


class MentraBridgeError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class MentraPhotoSession:
    session_id: str
    request_id: str
    tester_id: str
    output_language: str
    created_at: datetime
    pairing_expires_at: datetime
    upload_expires_at: datetime
    pairing_hash: str
    device_token_hash: str = ""
    source_sha256: str = ""
    capture_id: str = ""


class MentraSessionHub:
    """One-instance router for one explicitly requested Mentra still photo."""

    def __init__(self, *, now: Callable[[], datetime] = _utc_now) -> None:
        self._now = now
        self._sessions: dict[str, MentraPhotoSession] = {}
        self._pairings: dict[str, str] = {}
        self._tokens: dict[str, str] = {}
        self._lock = threading.RLock()

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._pairings.clear()
            self._tokens.clear()

    def _purge(self) -> None:
        now = self._now()
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session.upload_expires_at <= now
        ]
        for session_id in expired:
            session = self._sessions.pop(session_id)
            self._pairings.pop(session.pairing_hash, None)
            if session.device_token_hash:
                self._tokens.pop(session.device_token_hash, None)

    def create_session(self, tester_id: str, output_language: str) -> dict[str, Any]:
        if not re.fullmatch(r"a(?:10|[1-9])", tester_id):
            raise MentraBridgeError("MENTRA_TESTER_REQUIRED", 400)
        if output_language not in {"kn", "en"}:
            raise MentraBridgeError("MENTRA_LANGUAGE_INVALID", 400)
        now = self._now()
        session_id = secrets.token_hex(16)
        request_id = secrets.token_hex(16)
        pairing_code = secrets.token_hex(8).upper()
        pairing_hash = _secret_hash(pairing_code)
        session = MentraPhotoSession(
            session_id=session_id,
            request_id=request_id,
            tester_id=tester_id,
            output_language=output_language,
            created_at=now,
            pairing_expires_at=now + PAIRING_TTL,
            upload_expires_at=now + PAIRING_TTL + UPLOAD_GRACE,
            pairing_hash=pairing_hash,
        )
        with self._lock:
            self._purge()
            self._sessions[session_id] = session
            self._pairings[pairing_hash] = session_id
        return {
            "schema": SESSION_SCHEMA,
            "session_id": session_id,
            "request_id": request_id,
            "state": "waiting_for_companion",
            "pairing_code": pairing_code,
            "pairing_expires_at": _timestamp(session.pairing_expires_at),
        }

    def session_for_browser(
        self, session_id: str, tester_id: str,
    ) -> MentraPhotoSession:
        with self._lock:
            self._purge()
            session = self._sessions.get(session_id)
            if session is None or session.tester_id != tester_id:
                raise MentraBridgeError("MENTRA_SESSION_NOT_FOUND", 404)
            return session

    def describe_session(self, session_id: str, tester_id: str) -> dict[str, Any]:
        session = self.session_for_browser(session_id, tester_id)
        state = (
            "complete" if session.capture_id
            else "waiting_for_photo" if session.device_token_hash
            else "waiting_for_companion"
        )
        value: dict[str, Any] = {
            "schema": SESSION_SCHEMA,
            "session_id": session.session_id,
            "request_id": session.request_id,
            "state": state,
            "expires_at": _timestamp(session.upload_expires_at),
        }
        if session.capture_id:
            value["gallery_capture_id"] = session.capture_id
        return value

    def revoke_session(self, session_id: str, tester_id: str) -> None:
        with self._lock:
            session = self.session_for_browser(session_id, tester_id)
            self._sessions.pop(session.session_id, None)
            self._pairings.pop(session.pairing_hash, None)
            if session.device_token_hash:
                self._tokens.pop(session.device_token_hash, None)

    def pair_companion(self, pairing_code: str) -> dict[str, str]:
        normalized = pairing_code.strip().upper()
        if not PAIRING_CODE_PATTERN.fullmatch(normalized):
            raise MentraBridgeError("MENTRA_PAIRING_CODE_INVALID", 401)
        pairing_hash = _secret_hash(normalized)
        now = self._now()
        with self._lock:
            self._purge()
            session_id = self._pairings.pop(pairing_hash, "")
            session = self._sessions.get(session_id)
            if (
                session is None
                or session.pairing_expires_at <= now
                or session.device_token_hash
            ):
                raise MentraBridgeError("MENTRA_PAIRING_CODE_INVALID", 401)
            device_token = secrets.token_urlsafe(32)
            session.device_token_hash = _secret_hash(device_token)
            self._tokens[session.device_token_hash] = session.session_id
        return {
            "schema": PAIRING_SCHEMA,
            "request_id": session.request_id,
            "device_token": device_token,
            "expires_at": _timestamp(session.upload_expires_at),
        }

    @staticmethod
    def token_from_authorization(authorization: str) -> str:
        scheme, separator, token = authorization.strip().partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        return token.strip()

    def validate_upload(
        self, token: str, request_id: str, source_sha256: str,
    ) -> MentraPhotoSession:
        if not SOURCE_HASH_PATTERN.fullmatch(source_sha256):
            raise MentraBridgeError("MENTRA_SOURCE_HASH_INVALID", 400)
        session = self.authorize_upload(token, request_id)
        if session.capture_id and session.source_sha256 != source_sha256:
            raise MentraBridgeError("MENTRA_CAPTURE_SOURCE_CONFLICT", 409)
        return session

    def authorize_upload(self, token: str, request_id: str) -> MentraPhotoSession:
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise MentraBridgeError("MENTRA_CAPTURE_REQUEST_INVALID", 400)
        if not token or len(token) > 128:
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        with self._lock:
            self._purge()
            session_id = self._tokens.get(_secret_hash(token), "")
            session = self._sessions.get(session_id)
            if session is None:
                raise MentraBridgeError("MENTRA_DEVICE_AUTH_INVALID", 401)
            if session.request_id != request_id:
                raise MentraBridgeError("MENTRA_CAPTURE_REQUEST_NOT_FOUND", 404)
            if session.upload_expires_at <= self._now():
                raise MentraBridgeError("MENTRA_CAPTURE_UPLOAD_EXPIRED", 410)
            return session

    def existing_acceptance(
        self, token: str, request_id: str, source_sha256: str,
    ) -> dict[str, str] | None:
        with self._lock:
            session = self.validate_upload(token, request_id, source_sha256)
            if not session.capture_id:
                return None
            return self._acceptance(session)

    def complete_upload(
        self, token: str, request_id: str, source_sha256: str, capture_id: str,
    ) -> dict[str, str]:
        with self._lock:
            session = self.validate_upload(token, request_id, source_sha256)
            session.source_sha256 = source_sha256
            session.capture_id = capture_id
            return self._acceptance(session)

    @staticmethod
    def _acceptance(session: MentraPhotoSession) -> dict[str, str]:
        return {
            "schema": UPLOAD_ACCEPTANCE_SCHEMA,
            "request_id": session.request_id,
            "source_sha256": session.source_sha256,
            "status": "accepted",
            "gallery_capture_id": session.capture_id,
        }
