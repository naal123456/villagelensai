from __future__ import annotations

import hashlib
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .mentra_bridge import MentraBridgeError


SESSION_SCHEMA = "villagelens.mentra-browser-session.v2"
JOB_SCHEMA = "villagelens.mentra-photo-job.v1"
UPLOAD_ACCEPTANCE_SCHEMA = "villagelens.mentra-upload-acceptance.v1"
PAIRING_TTL = timedelta(minutes=5)
SESSION_TTL = timedelta(minutes=15)
UPLOAD_GRACE = timedelta(minutes=10)
DEVICE_PROFILE_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}")
REQUEST_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
PAIRING_CODE_PATTERN = re.compile(r"[0-9A-F]{16}")
SOURCE_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class PersistentMentraSession:
    session_id: str
    request_id: str
    tester_id: str
    output_language: str
    created_at: datetime
    pairing_expires_at: datetime
    upload_expires_at: datetime
    pairing_hash: str
    device_profile_id: str = ""
    upload_token_hash: str = ""
    job_delivered: bool = False
    source_sha256: str = ""
    capture_id: str = ""


class PersistentMentraHub:
    """Single-instance router for persistent enrollment and explicit still jobs."""

    def __init__(self, *, now: Callable[[], datetime] = _utc_now) -> None:
        self._now = now
        self._sessions: dict[str, PersistentMentraSession] = {}
        self._pairings: dict[str, str] = {}
        self._persistent_tokens: dict[str, str] = {}
        self._active_profile_sessions: dict[str, str] = {}
        self._upload_tokens: dict[str, str] = {}
        self._lock = threading.RLock()

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._pairings.clear()
            self._persistent_tokens.clear()
            self._active_profile_sessions.clear()
            self._upload_tokens.clear()

    def _purge(self) -> None:
        now = self._now()
        expired = [key for key, value in self._sessions.items() if value.upload_expires_at <= now]
        for session_id in expired:
            session = self._sessions.pop(session_id)
            self._pairings.pop(session.pairing_hash, None)
            self._upload_tokens.pop(session.upload_token_hash, None)
            if self._active_profile_sessions.get(session.device_profile_id) == session_id:
                self._active_profile_sessions.pop(session.device_profile_id, None)

    def create_session(
        self, tester_id: str, output_language: str, device_profile_id: str = "",
    ) -> dict[str, Any]:
        if not re.fullmatch(r"a(?:10|[1-9])", tester_id):
            raise MentraBridgeError("MENTRA_TESTER_REQUIRED", 400)
        if output_language not in {"kn", "en"}:
            raise MentraBridgeError("MENTRA_LANGUAGE_INVALID", 400)
        if device_profile_id and not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise MentraBridgeError("MENTRA_DEVICE_PROFILE_INVALID", 400)
        now = self._now()
        pairing_code = "" if device_profile_id else secrets.token_hex(8).upper()
        session = PersistentMentraSession(
            session_id=secrets.token_hex(16),
            request_id=secrets.token_hex(16),
            tester_id=tester_id,
            output_language=output_language,
            created_at=now,
            pairing_expires_at=now + PAIRING_TTL,
            upload_expires_at=now + SESSION_TTL + UPLOAD_GRACE,
            pairing_hash=_secret_hash(pairing_code) if pairing_code else "",
            device_profile_id=device_profile_id,
        )
        with self._lock:
            self._purge()
            if device_profile_id:
                prior_id = self._active_profile_sessions.get(device_profile_id, "")
                prior = self._sessions.get(prior_id)
                if prior and not prior.capture_id:
                    raise MentraBridgeError("MENTRA_DEVICE_BUSY", 409)
                self._active_profile_sessions[device_profile_id] = session.session_id
            else:
                self._pairings[session.pairing_hash] = session.session_id
            self._sessions[session.session_id] = session
        value: dict[str, Any] = self.describe_session(session.session_id, tester_id)
        if pairing_code:
            value["pairing_code"] = pairing_code
            value["pairing_expires_at"] = _timestamp(session.pairing_expires_at)
        return value

    def session_for_browser(self, session_id: str, tester_id: str) -> PersistentMentraSession:
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
            else "capturing" if session.job_delivered
            else "waiting_for_device" if session.device_profile_id
            else "waiting_for_enrollment"
        )
        value: dict[str, Any] = {
            "schema": SESSION_SCHEMA,
            "session_id": session.session_id,
            "request_id": session.request_id,
            "paired": bool(session.device_profile_id),
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
            self._upload_tokens.pop(session.upload_token_hash, None)
            if self._active_profile_sessions.get(session.device_profile_id) == session_id:
                self._active_profile_sessions.pop(session.device_profile_id, None)

    def pair_device(self, pairing_code: str, device_profile_id: str) -> dict[str, str]:
        normalized = pairing_code.strip().upper()
        if not PAIRING_CODE_PATTERN.fullmatch(normalized):
            raise MentraBridgeError("MENTRA_PAIRING_CODE_INVALID", 401)
        if not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise MentraBridgeError("MENTRA_DEVICE_PROFILE_INVALID", 400)
        with self._lock:
            self._purge()
            session_id = self._pairings.pop(_secret_hash(normalized), "")
            session = self._sessions.get(session_id)
            if session is None or session.pairing_expires_at <= self._now() or session.device_profile_id:
                raise MentraBridgeError("MENTRA_PAIRING_CODE_INVALID", 401)
            token = secrets.token_urlsafe(32)
            session.device_profile_id = device_profile_id
            self._persistent_tokens[_secret_hash(token)] = device_profile_id
            self._active_profile_sessions[device_profile_id] = session.session_id
        return {"device_profile_id": device_profile_id, "device_token": token}

    def rollback_pairing(self, token: str) -> None:
        with self._lock:
            profile_id = self._persistent_tokens.pop(_secret_hash(token), "")
            session_id = self._active_profile_sessions.pop(profile_id, "")
            session = self._sessions.get(session_id)
            if session:
                session.device_profile_id = ""

    def register_persistent_token(self, token: str, device_profile_id: str) -> None:
        if not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise MentraBridgeError("MENTRA_DEVICE_PROFILE_INVALID", 400)
        if not token or len(token) > 128:
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        with self._lock:
            self._persistent_tokens[_secret_hash(token)] = device_profile_id

    def revoke_profile(self, device_profile_id: str) -> None:
        with self._lock:
            for token_hash, profile_id in list(self._persistent_tokens.items()):
                if profile_id == device_profile_id:
                    self._persistent_tokens.pop(token_hash, None)
            session_id = self._active_profile_sessions.pop(device_profile_id, "")
            if session_id in self._sessions:
                self._sessions[session_id].device_profile_id = ""

    def authenticate_device(self, token: str) -> str:
        if not token or len(token) > 128:
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        with self._lock:
            profile_id = self._persistent_tokens.get(_secret_hash(token), "")
            if not profile_id:
                raise MentraBridgeError("MENTRA_DEVICE_AUTH_INVALID", 401)
            return profile_id

    def next_job(self, token: str) -> dict[str, Any] | None:
        if not token or len(token) > 128:
            raise MentraBridgeError("MENTRA_DEVICE_AUTH_REQUIRED", 401)
        with self._lock:
            self._purge()
            profile_id = self.authenticate_device(token)
            session_id = self._active_profile_sessions.get(profile_id, "")
            session = self._sessions.get(session_id)
            if session is None or session.capture_id or session.job_delivered:
                return None
            upload_token = secrets.token_urlsafe(32)
            session.upload_token_hash = _secret_hash(upload_token)
            session.job_delivered = True
            self._upload_tokens[session.upload_token_hash] = session.session_id
            return {
                "schema": JOB_SCHEMA,
                "request_id": session.request_id,
                "upload_token": upload_token,
                "expires_at": _timestamp(session.upload_expires_at),
                "camera": {
                    "fov": 62,
                    "roi_position": "center",
                    "size": "max",
                    "mode": "text",
                    "sound": True,
                    "save_to_gallery": False,
                },
            }

    def authorize_upload(self, token: str, request_id: str) -> PersistentMentraSession:
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise MentraBridgeError("MENTRA_CAPTURE_REQUEST_INVALID", 400)
        if not token or len(token) > 128:
            raise MentraBridgeError("MENTRA_UPLOAD_AUTH_REQUIRED", 401)
        with self._lock:
            self._purge()
            session_id = self._upload_tokens.get(_secret_hash(token), "")
            session = self._sessions.get(session_id)
            if session is None:
                raise MentraBridgeError("MENTRA_UPLOAD_AUTH_INVALID", 401)
            if session.request_id != request_id:
                raise MentraBridgeError("MENTRA_CAPTURE_REQUEST_NOT_FOUND", 404)
            return session

    def existing_acceptance(
        self, token: str, request_id: str, source_sha256: str,
    ) -> dict[str, str] | None:
        session = self.authorize_upload(token, request_id)
        if session.capture_id and session.source_sha256 != source_sha256:
            raise MentraBridgeError("MENTRA_CAPTURE_SOURCE_CONFLICT", 409)
        return self._acceptance(session) if session.capture_id else None

    def complete_upload(
        self, token: str, request_id: str, source_sha256: str, capture_id: str,
    ) -> dict[str, str]:
        if not SOURCE_HASH_PATTERN.fullmatch(source_sha256):
            raise MentraBridgeError("MENTRA_SOURCE_HASH_INVALID", 400)
        with self._lock:
            session = self.authorize_upload(token, request_id)
            session.source_sha256 = source_sha256
            session.capture_id = capture_id
            return self._acceptance(session)

    @staticmethod
    def _acceptance(session: PersistentMentraSession) -> dict[str, str]:
        return {
            "schema": UPLOAD_ACCEPTANCE_SCHEMA,
            "request_id": session.request_id,
            "source_sha256": session.source_sha256,
            "status": "accepted",
            "gallery_capture_id": session.capture_id,
        }
