from __future__ import annotations

import hashlib
import re
import secrets
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


CAPTURE_REQUEST_SCHEMA = "villagelens.pi-capture-request.v1"
UPLOAD_ACCEPTANCE_SCHEMA = "villagelens.pi-upload-acceptance.v1"
SESSION_SCHEMA = "villagelens.pi-browser-session.v1"
PAIRING_SCHEMA = "villagelens.pi-pairing.v1"
DEVICE_PROFILE_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}")
REQUEST_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
SOURCE_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
PAIRING_TTL = timedelta(minutes=5)
SESSION_TTL = timedelta(hours=8)
CAPTURE_REQUEST_TTL = timedelta(seconds=45)
UPLOAD_GRACE = timedelta(minutes=10)
PREVIEW_TTL = timedelta(seconds=30)
MAX_PREVIEW_BYTES = 300_000
PREVIEW_INTERVAL = timedelta(milliseconds=400)
MAX_EVENT_QUEUE = 32
CAPTURE_STATES = {
    "capture_active", "capture_inactive", "uploading", "complete", "failed",
}


class PiBridgeError(ValueError):
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
class CaptureJob:
    request: dict[str, str]
    upload_deadline: datetime
    uploaded: bool = False
    source_sha256: str = ""
    capture_id: str = ""


@dataclass
class PiBrowserSession:
    session_id: str
    tester_id: str
    output_language: str
    created_at: datetime
    expires_at: datetime
    pairing_hash: str
    paired: bool = False
    device_profile_id: str = ""
    device_token_hash: str = ""
    commands: deque[dict[str, Any]] = field(default_factory=deque)
    events: deque[dict[str, Any] | bytes] = field(
        default_factory=lambda: deque(maxlen=MAX_EVENT_QUEUE)
    )
    jobs: dict[str, CaptureJob] = field(default_factory=dict)
    preview_until: datetime | None = None
    last_preview_at: datetime | None = None


class PiSessionHub:
    """One-instance, expiring router for the isolated /c proof of concept."""

    def __init__(self, *, now: Callable[[], datetime] = _utc_now) -> None:
        self._now = now
        self._sessions: dict[str, PiBrowserSession] = {}
        self._pairings: dict[str, str] = {}
        self._tokens: dict[str, str] = {}
        self._persistent_tokens: dict[str, str] = {}
        self._connected_profiles: set[str] = set()
        self._active_profile_sessions: dict[str, str] = {}
        self._lock = threading.RLock()

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._pairings.clear()
            self._tokens.clear()
            self._persistent_tokens.clear()
            self._connected_profiles.clear()
            self._active_profile_sessions.clear()

    def _purge(self) -> None:
        now = self._now()
        expired = [key for key, value in self._sessions.items() if value.expires_at <= now]
        for session_id in expired:
            session = self._sessions.pop(session_id)
            self._pairings.pop(session.pairing_hash, None)
            if session.device_token_hash:
                self._tokens.pop(session.device_token_hash, None)
            if self._active_profile_sessions.get(session.device_profile_id) == session_id:
                self._active_profile_sessions.pop(session.device_profile_id, None)

    def _has_live_work(self, session: PiBrowserSession, now: datetime) -> bool:
        if session.preview_until is not None and session.preview_until > now:
            return True
        return any(not job.uploaded and job.upload_deadline > now for job in session.jobs.values())

    def _claim_profile(self, session: PiBrowserSession) -> None:
        profile_id = session.device_profile_id
        if not profile_id:
            return
        prior_id = self._active_profile_sessions.get(profile_id, "")
        prior = self._sessions.get(prior_id)
        if prior is not None and prior is not session and self._has_live_work(prior, self._now()):
            raise PiBridgeError("PI_DEVICE_BUSY", 409)
        self._active_profile_sessions[profile_id] = session.session_id

    def create_session(
        self, tester_id: str, output_language: str, device_profile_id: str = "",
    ) -> dict[str, Any]:
        if not re.fullmatch(r"a(?:10|[1-9])", tester_id):
            raise PiBridgeError("PI_TESTER_REQUIRED", 400)
        if output_language not in {"kn", "en"}:
            raise PiBridgeError("PI_LANGUAGE_INVALID", 400)
        if device_profile_id and not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise PiBridgeError("PI_DEVICE_PROFILE_INVALID", 400)
        now = self._now()
        session_id = secrets.token_hex(16)
        pairing_code = "" if device_profile_id else secrets.token_urlsafe(12)
        pairing_hash = _secret_hash(pairing_code) if pairing_code else ""
        session = PiBrowserSession(
            session_id=session_id,
            tester_id=tester_id,
            output_language=output_language,
            created_at=now,
            expires_at=now + SESSION_TTL,
            pairing_hash=pairing_hash,
            paired=bool(device_profile_id),
            device_profile_id=device_profile_id,
        )
        with self._lock:
            self._purge()
            self._sessions[session_id] = session
            try:
                self._claim_profile(session)
            except PiBridgeError:
                self._sessions.pop(session_id, None)
                raise
            if pairing_hash:
                self._pairings[pairing_hash] = session_id
            if device_profile_id in self._connected_profiles:
                session.events.append({
                    "type": "device_connection",
                    "state": "connected",
                    "device_profile_id": device_profile_id,
                })
        value: dict[str, Any] = {
            "schema": SESSION_SCHEMA,
            "session_id": session_id,
            "paired": session.paired,
            "device_profile_id": device_profile_id,
            "device_connected": device_profile_id in self._connected_profiles,
            "expires_at": _timestamp(session.expires_at),
        }
        if pairing_code:
            value["pairing_code"] = pairing_code
            value["pairing_expires_at"] = _timestamp(now + PAIRING_TTL)
        return value

    def session_for_browser(self, session_id: str, tester_id: str) -> PiBrowserSession:
        with self._lock:
            self._purge()
            session = self._sessions.get(session_id)
            if session is None or session.tester_id != tester_id:
                raise PiBridgeError("PI_SESSION_NOT_FOUND", 404)
            return session

    def describe_session(self, session_id: str, tester_id: str) -> dict[str, Any]:
        session = self.session_for_browser(session_id, tester_id)
        return {
            "schema": SESSION_SCHEMA,
            "session_id": session.session_id,
            "paired": session.paired,
            "device_profile_id": session.device_profile_id if session.paired else "",
            "device_connected": session.device_profile_id in self._connected_profiles,
            "expires_at": _timestamp(session.expires_at),
        }

    def revoke_session(self, session_id: str, tester_id: str) -> None:
        with self._lock:
            session = self.session_for_browser(session_id, tester_id)
            self._sessions.pop(session.session_id, None)
            self._pairings.pop(session.pairing_hash, None)
            if session.device_token_hash:
                self._tokens.pop(session.device_token_hash, None)
            if self._active_profile_sessions.get(session.device_profile_id) == session.session_id:
                self._active_profile_sessions.pop(session.device_profile_id, None)
            session.commands.clear()
            session.events.clear()

    def pair_device(self, pairing_code: str, device_profile_id: str) -> dict[str, str]:
        if not pairing_code or len(pairing_code) > 64:
            raise PiBridgeError("PI_PAIRING_CODE_INVALID", 400)
        if not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise PiBridgeError("PI_DEVICE_PROFILE_INVALID", 400)
        now = self._now()
        pairing_hash = _secret_hash(pairing_code)
        with self._lock:
            self._purge()
            session_id = self._pairings.pop(pairing_hash, "")
            session = self._sessions.get(session_id)
            if session is None or session.created_at + PAIRING_TTL <= now or session.paired:
                raise PiBridgeError("PI_PAIRING_CODE_INVALID", 401)
            token = secrets.token_urlsafe(32)
            token_hash = _secret_hash(token)
            session.paired = True
            session.device_profile_id = device_profile_id
            session.device_token_hash = token_hash
            self._tokens[token_hash] = session.session_id
            self._claim_profile(session)
            session.events.append({
                "type": "device_paired",
                "device_profile_id": device_profile_id,
            })
        return {
            "schema": PAIRING_SCHEMA,
            "session_id": session.session_id,
            "device_profile_id": device_profile_id,
            "device_token": token,
            "expires_at": _timestamp(session.expires_at),
        }

    def rollback_pairing(self, token: str) -> None:
        token_hash = _secret_hash(token)
        with self._lock:
            session_id = self._tokens.pop(token_hash, "")
            session = self._sessions.get(session_id)
            if session is None:
                return
            if self._active_profile_sessions.get(session.device_profile_id) == session_id:
                self._active_profile_sessions.pop(session.device_profile_id, None)
            session.paired = False
            session.device_profile_id = ""
            session.device_token_hash = ""
            session.commands.clear()
            session.events.clear()

    def register_persistent_token(self, token: str, device_profile_id: str) -> None:
        if not DEVICE_PROFILE_PATTERN.fullmatch(device_profile_id):
            raise PiBridgeError("PI_DEVICE_PROFILE_INVALID", 400)
        if not token or len(token) > 128:
            raise PiBridgeError("PI_DEVICE_AUTH_REQUIRED", 401)
        with self._lock:
            self._persistent_tokens[_secret_hash(token)] = device_profile_id

    def revoke_profile(self, device_profile_id: str) -> None:
        with self._lock:
            hashes = [
                token_hash for token_hash, profile_id in self._persistent_tokens.items()
                if profile_id == device_profile_id
            ]
            for token_hash in hashes:
                self._persistent_tokens.pop(token_hash, None)
            self._connected_profiles.discard(device_profile_id)
            self._active_profile_sessions.pop(device_profile_id, None)
            for session in self._sessions.values():
                if session.device_profile_id == device_profile_id:
                    if session.device_token_hash:
                        self._tokens.pop(session.device_token_hash, None)
                    session.device_token_hash = ""
                    session.paired = False
                    session.commands.clear()
                    session.events.append({"type": "device_revoked"})

    def _profile_for_token(self, token: str) -> str:
        if not token or len(token) > 128:
            raise PiBridgeError("PI_DEVICE_AUTH_REQUIRED", 401)
        token_hash = _secret_hash(token)
        session_id = self._tokens.get(token_hash, "")
        session = self._sessions.get(session_id)
        if session is not None:
            return session.device_profile_id
        profile_id = self._persistent_tokens.get(token_hash, "")
        if not profile_id:
            raise PiBridgeError("PI_DEVICE_AUTH_INVALID", 401)
        return profile_id

    def session_for_token(self, token: str) -> PiBrowserSession:
        if not token or len(token) > 128:
            raise PiBridgeError("PI_DEVICE_AUTH_REQUIRED", 401)
        with self._lock:
            self._purge()
            token_hash = _secret_hash(token)
            session_id = self._tokens.get(token_hash, "")
            if not session_id:
                profile_id = self._persistent_tokens.get(token_hash, "")
                session_id = self._active_profile_sessions.get(profile_id, "")
            session = self._sessions.get(session_id)
            if session is None:
                if token_hash in self._persistent_tokens:
                    raise PiBridgeError("PI_DEVICE_SESSION_WAITING", 409)
                raise PiBridgeError("PI_DEVICE_AUTH_INVALID", 401)
            return session

    def token_from_authorization(self, authorization: str) -> str:
        scheme, separator, token = authorization.strip().partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            raise PiBridgeError("PI_DEVICE_AUTH_REQUIRED", 401)
        return token.strip()

    def create_command(
        self, session_id: str, tester_id: str, action: str,
    ) -> dict[str, Any]:
        with self._lock:
            session = self.session_for_browser(session_id, tester_id)
            if not session.paired:
                raise PiBridgeError("PI_DEVICE_NOT_PAIRED", 409)
            self._claim_profile(session)
            now = self._now()
            if action == "capture":
                session.preview_until = None
                session.events = deque(
                    (event for event in session.events if not isinstance(event, bytes)),
                    maxlen=MAX_EVENT_QUEUE,
                )
                request_id = secrets.token_hex(16)
                request = {
                    "schema": CAPTURE_REQUEST_SCHEMA,
                    "request_id": request_id,
                    "device_profile_id": session.device_profile_id,
                    "requested_at": _timestamp(now),
                    "expires_at": _timestamp(now + CAPTURE_REQUEST_TTL),
                }
                session.jobs[request_id] = CaptureJob(
                    request=request,
                    upload_deadline=now + CAPTURE_REQUEST_TTL + UPLOAD_GRACE,
                )
                command = {"type": "capture_request", "request": request}
            elif action == "preview_start":
                preview_id = secrets.token_hex(16)
                session.preview_until = now + PREVIEW_TTL
                session.last_preview_at = None
                command = {
                    "type": "preview_start",
                    "preview_id": preview_id,
                    "expires_at": _timestamp(session.preview_until),
                    "max_width": 640,
                    "max_height": 480,
                    "max_frames_per_second": 2,
                    "media_type": "image/jpeg",
                }
            elif action == "preview_stop":
                session.preview_until = None
                session.events = deque(
                    (event for event in session.events if not isinstance(event, bytes)),
                    maxlen=MAX_EVENT_QUEUE,
                )
                command = {"type": "preview_stop"}
            else:
                raise PiBridgeError("PI_COMMAND_INVALID", 400)
            session.commands.append(command)
            session.events.append({"type": "command_queued", "action": action})
            return command

    def next_command(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            try:
                session = self.session_for_token(token)
            except PiBridgeError as error:
                if error.code == "PI_DEVICE_SESSION_WAITING":
                    return None
                raise
            return session.commands.popleft() if session.commands else None

    def publish_device_connection(self, token: str, connected: bool) -> None:
        with self._lock:
            profile_id = self._profile_for_token(token)
            if connected:
                self._connected_profiles.add(profile_id)
            else:
                self._connected_profiles.discard(profile_id)
            session_id = self._active_profile_sessions.get(profile_id, "")
            session = self._sessions.get(session_id)
            if session is not None:
                session.events.append({
                    "type": "device_connection",
                    "state": "connected" if connected else "disconnected",
                    "device_profile_id": profile_id,
                })

    def next_browser_event(
        self, session_id: str, tester_id: str,
    ) -> dict[str, Any] | bytes | None:
        with self._lock:
            session = self.session_for_browser(session_id, tester_id)
            return session.events.popleft() if session.events else None

    def publish_state(self, token: str, request_id: str, state: str) -> None:
        if state not in CAPTURE_STATES:
            raise PiBridgeError("PI_CAPTURE_STATE_INVALID", 400)
        with self._lock:
            session = self.session_for_token(token)
            if request_id not in session.jobs:
                raise PiBridgeError("PI_CAPTURE_REQUEST_NOT_FOUND", 404)
            session.events.append({
                "type": "capture_state", "request_id": request_id, "state": state,
            })

    def publish_preview(self, token: str, frame: bytes) -> bool:
        now = self._now()
        if len(frame) > MAX_PREVIEW_BYTES or not frame.startswith(b"\xff\xd8"):
            raise PiBridgeError("PI_PREVIEW_FRAME_INVALID", 400)
        with self._lock:
            session = self.session_for_token(token)
            if session.preview_until is None or session.preview_until <= now:
                raise PiBridgeError("PI_PREVIEW_INACTIVE", 409)
            if session.last_preview_at and now - session.last_preview_at < PREVIEW_INTERVAL:
                return False
            session.last_preview_at = now
            session.events.append(frame)
            return True

    def validate_upload(self, token: str, request_id: str, source_sha256: str) -> PiBrowserSession:
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise PiBridgeError("PI_CAPTURE_REQUEST_INVALID", 400)
        if not SOURCE_HASH_PATTERN.fullmatch(source_sha256):
            raise PiBridgeError("PI_SOURCE_HASH_INVALID", 400)
        with self._lock:
            session = self.session_for_token(token)
            job = session.jobs.get(request_id)
            if job is None:
                raise PiBridgeError("PI_CAPTURE_REQUEST_NOT_FOUND", 404)
            if job.upload_deadline <= self._now():
                raise PiBridgeError("PI_CAPTURE_UPLOAD_EXPIRED", 410)
            if job.uploaded and job.source_sha256 != source_sha256:
                raise PiBridgeError("PI_CAPTURE_SOURCE_CONFLICT", 409)
            return session

    def existing_acceptance(
        self, token: str, request_id: str, source_sha256: str,
    ) -> dict[str, str] | None:
        with self._lock:
            session = self.validate_upload(token, request_id, source_sha256)
            job = session.jobs[request_id]
            if not job.uploaded:
                return None
            return {
                "schema": UPLOAD_ACCEPTANCE_SCHEMA,
                "request_id": request_id,
                "device_profile_id": session.device_profile_id,
                "source_sha256": source_sha256,
                "status": "accepted",
                "gallery_capture_id": job.capture_id,
            }

    def complete_upload(
        self, token: str, request_id: str, source_sha256: str, capture_id: str,
    ) -> dict[str, str]:
        with self._lock:
            session = self.validate_upload(token, request_id, source_sha256)
            job = session.jobs[request_id]
            job.uploaded = True
            job.source_sha256 = source_sha256
            job.capture_id = capture_id
            session.preview_until = None
            session.events.append({
                "type": "capture_complete",
                "request_id": request_id,
                "capture_id": capture_id,
                "image_url": f"/api/captures/{capture_id}/image",
            })
            return {
                "schema": UPLOAD_ACCEPTANCE_SCHEMA,
                "request_id": request_id,
                "device_profile_id": session.device_profile_id,
                "source_sha256": source_sha256,
                "status": "accepted",
                "gallery_capture_id": capture_id,
            }
