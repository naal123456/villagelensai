from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from simple_websocket.errors import ConnectionClosed

from api.app import (
    _authenticate_pi_device,
    _pi_hub,
    _serve_pi_browser_socket,
    _serve_pi_device_socket,
    app,
)
from api.pi_bridge import PiBridgeError, PiSessionHub


class PiRuntimeConfigurationTests(unittest.TestCase):
    def test_gunicorn_timeout_covers_bounded_pi_session(self) -> None:
        dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("--timeout 3600", dockerfile)
        self.assertNotIn("--timeout 90 ", dockerfile)


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 23, 18, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value


class PiSessionHubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.hub = PiSessionHub(now=self.clock)

    def pair(self, tester_id: str = "a1") -> tuple[dict[str, str], dict[str, str]]:
        browser = self.hub.create_session(tester_id, "kn")
        device = self.hub.pair_device(browser["pairing_code"], "rpi5-bench-01")
        return browser, device

    def test_pairing_is_one_time_expiring_and_credential_is_not_in_session(self) -> None:
        browser, device = self.pair()

        self.assertNotIn("device_token", browser)
        self.assertNotEqual(device["device_token"], browser["pairing_code"])
        with self.assertRaisesRegex(PiBridgeError, "PI_PAIRING_CODE_INVALID"):
            self.hub.pair_device(browser["pairing_code"], "rpi5-bench-01")

        expired = self.hub.create_session("a2", "en")
        self.clock.value += timedelta(minutes=6)
        with self.assertRaisesRegex(PiBridgeError, "PI_PAIRING_CODE_INVALID"):
            self.hub.pair_device(expired["pairing_code"], "rpi5-bench-02")

    def test_sessions_are_isolated_between_users(self) -> None:
        browser, _device = self.pair("a1")
        with self.assertRaisesRegex(PiBridgeError, "PI_SESSION_NOT_FOUND"):
            self.hub.session_for_browser(browser["session_id"], "a2")

    def test_capture_command_is_short_lived_and_bound_to_device(self) -> None:
        browser, device = self.pair()
        command = self.hub.create_command(browser["session_id"], "a1", "capture")
        delivered = self.hub.next_command(device["device_token"])

        self.assertEqual(delivered, command)
        request = command["request"]
        self.assertEqual(request["schema"], "villagelens.pi-capture-request.v1")
        self.assertEqual(request["device_profile_id"], "rpi5-bench-01")
        requested = datetime.fromisoformat(request["requested_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))
        self.assertEqual(expires - requested, timedelta(seconds=45))
        self.assertIsNone(self.hub.next_command(device["device_token"]))

    def test_preview_is_bounded_ephemeral_and_rate_limited(self) -> None:
        browser, device = self.pair()
        self.hub.create_command(browser["session_id"], "a1", "preview_start")
        token = device["device_token"]
        frame = b"\xff\xd8preview"

        self.assertTrue(self.hub.publish_preview(token, frame))
        self.assertFalse(self.hub.publish_preview(token, frame))
        self.assertEqual(self.hub.next_browser_event(browser["session_id"], "a1")["type"], "device_paired")
        self.assertEqual(self.hub.next_browser_event(browser["session_id"], "a1")["type"], "command_queued")
        self.assertEqual(self.hub.next_browser_event(browser["session_id"], "a1"), frame)

        self.clock.value += timedelta(seconds=31)
        with self.assertRaisesRegex(PiBridgeError, "PI_PREVIEW_INACTIVE"):
            self.hub.publish_preview(token, frame)

    def test_upload_acceptance_is_idempotent_and_hash_bound(self) -> None:
        browser, device = self.pair()
        command = self.hub.create_command(browser["session_id"], "a1", "capture")
        request_id = command["request"]["request_id"]
        digest = "a" * 64

        self.assertIsNone(self.hub.existing_acceptance(device["device_token"], request_id, digest))
        first = self.hub.complete_upload(
            device["device_token"], request_id, digest, request_id,
        )
        second = self.hub.existing_acceptance(device["device_token"], request_id, digest)

        self.assertEqual(first, second)
        self.assertEqual(first["source_sha256"], digest)
        with self.assertRaisesRegex(PiBridgeError, "PI_CAPTURE_SOURCE_CONFLICT"):
            self.hub.existing_acceptance(device["device_token"], request_id, "b" * 64)

    def test_persistent_device_waits_inactive_then_routes_after_browser_press(self) -> None:
        token = "persistent-device-token-with-enough-entropy-012345"
        self.hub.register_persistent_token(token, "rpi5-bench-01")
        self.hub.publish_device_connection(token, True)

        self.assertIsNone(self.hub.next_command(token))
        browser = self.hub.create_session("a1", "kn", "rpi5-bench-01")
        self.assertTrue(browser["paired"])
        self.assertTrue(browser["device_connected"])
        self.assertNotIn("pairing_code", browser)

        command = self.hub.create_command(browser["session_id"], "a1", "preview_start")
        self.assertEqual(self.hub.next_command(token), command)
        self.hub.revoke_profile("rpi5-bench-01")
        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_AUTH_INVALID"):
            self.hub.next_command(token)

    def test_revocation_removes_both_enrollment_and_original_pairing_token(self) -> None:
        _browser, device = self.pair()
        token = device["device_token"]
        self.hub.register_persistent_token(token, "rpi5-bench-01")

        self.hub.revoke_profile("rpi5-bench-01")

        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_AUTH_INVALID"):
            self.hub.session_for_token(token)

    def test_persistent_device_cannot_be_taken_over_during_live_work(self) -> None:
        token = "persistent-device-token-with-enough-entropy-012345"
        self.hub.register_persistent_token(token, "rpi5-bench-01")
        first = self.hub.create_session("a1", "kn", "rpi5-bench-01")
        self.hub.create_command(first["session_id"], "a1", "preview_start")

        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_BUSY"):
            self.hub.create_session("a2", "en", "rpi5-bench-01")

        self.clock.value += timedelta(seconds=31)
        second = self.hub.create_session("a2", "en", "rpi5-bench-01")
        self.assertTrue(second["paired"])


class PiBridgeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(
            TESTING=True,
            VILLAGELENS_ACCESS_CODE="",
            VILLAGELENS_SESSION_SECRET="",
        )
        _pi_hub.reset()
        self.client = app.test_client()

    def create_and_pair(self) -> tuple[dict[str, str], dict[str, str]]:
        session_response = self.client.post(
            "/api/pi/v1/sessions",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"output_language": "kn"},
        )
        session = session_response.get_json()
        pair_response = self.client.post("/api/pi/v1/device/pair", json={
            "pairing_code": session["pairing_code"],
            "device_profile_id": "rpi5-bench-01",
        })
        return session, pair_response.get_json()

    def test_c_is_separate_route_and_a_and_b_behavior_is_unchanged(self) -> None:
        pi_page = self.client.get("/c/?tester=a1")
        a_page = self.client.get("/a/?tester=a1")
        b_page = self.client.get("/b/?tester=a3")
        self.addCleanup(pi_page.close)
        self.addCleanup(a_page.close)
        self.addCleanup(b_page.close)

        self.assertEqual(pi_page.status_code, 200)
        self.assertEqual(pi_page.headers["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(a_page.status_code, 200)
        self.assertEqual(b_page.status_code, 302)
        self.assertEqual(b_page.headers["Location"], "/a/?tester=a3&lang=en")
        self.assertIn(b'id="pi-camera"', pi_page.data)
        self.assertIn(b'id="mentra-camera"', pi_page.data)
        self.assertIn(b'id="mentra-camera-guide"', pi_page.data)
        self.assertIn(b"/api/mentra/v1/sessions", pi_page.data)
        self.assertIn(b"One explicit still photograph only", pi_page.data)
        self.assertIn(b"const piLane=location.pathname==='/c/'", pi_page.data)
        self.assertIn(b"piCamera.hidden=!piLane", pi_page.data)
        self.assertIn(b"new WebSocket", pi_page.data)
        self.assertIn(b"if (!piLane) return", pi_page.data)
        self.assertIn(b"if (value.paired)", pi_page.data)
        self.assertIn(b"Pi enrolled. Waiting for it to connect", pi_page.data)
        self.assertIn(b"if (piSession&&piSession.paired) startPiPreview()", pi_page.data)
        self.assertIn(b"piSocket.readyState===WebSocket.OPEN", pi_page.data)
        self.assertIn(b"function beginPiCaptureTimer()", pi_page.data)
        self.assertIn(b"Picture saved. Gallery is still loading", pi_page.data)
        self.assertIn(b"await showGallery(index);", pi_page.data)

    def test_access_gate_protects_c_but_allows_one_time_device_pairing(self) -> None:
        app.config.update(
            VILLAGELENS_ACCESS_CODE="test-code",
            VILLAGELENS_SESSION_SECRET="test-session-secret",
        )

        page = self.client.get("/c/?tester=a1")
        session = self.client.post(
            "/api/pi/v1/sessions",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"output_language": "kn"},
        )
        pairing = self.client.post("/api/pi/v1/device/pair", json={
            "pairing_code": "not-a-real-code",
            "device_profile_id": "rpi5-bench-01",
        })

        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.headers["Location"], "/access?tester=a1&next=c")
        self.assertEqual(session.status_code, 401)
        self.assertEqual(pairing.status_code, 401)
        self.assertEqual(pairing.get_json()["error"], "PI_PAIRING_CODE_INVALID")

        access = self.client.post("/access", data={
            "tester": "a1", "code": "test-code", "next": "c",
        })
        self.assertEqual(access.status_code, 303)
        self.assertEqual(access.headers["Location"], "/c/?tester=a1")

    def test_browser_session_requires_tester_and_enforces_ownership(self) -> None:
        missing = self.client.post(
            "/api/pi/v1/sessions", json={"output_language": "kn"},
        )
        session, _device = self.create_and_pair()
        other = self.client.get(
            f"/api/pi/v1/sessions/{session['session_id']}",
            headers={"X-VillageLens-Tester-ID": "a2"},
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(other.status_code, 404)

    @patch("api.app.CAPTURE_BUCKET", "existing-private-bucket")
    @patch("api.app._pi_enrollment_store")
    def test_enrollment_survives_hub_restart_and_reviewer_can_revoke(self, store: object) -> None:
        state = {"profile": ""}

        def active_profile_id() -> str:
            return state["profile"]

        def enroll(profile_id: str, _token: str) -> dict[str, str]:
            state["profile"] = profile_id
            return {
                "schema": "villagelens.pi-device-enrollment.v1",
                "device_profile_id": profile_id,
                "enrolled_at": "2026-09-24T18:00:00Z",
                "status": "active",
            }

        store.return_value.active_profile_id.side_effect = active_profile_id
        store.return_value.enroll.side_effect = enroll
        store.return_value.revoke.return_value = {
            "schema": "villagelens.pi-device-enrollment.v1",
            "device_profile_id": "rpi5-bench-01",
            "status": "revoked",
            "revoked_at": "2026-09-24T18:01:00Z",
        }
        session, device = self.create_and_pair()
        self.assertEqual(device["schema"], "villagelens.pi-device-enrollment.v1")
        self.assertNotIn("session_id", device)
        self.assertNotIn("expires_at", device)

        _pi_hub.reset()
        restored = self.client.post(
            "/api/pi/v1/sessions",
            headers={"X-VillageLens-Tester-ID": "a2"},
            json={"output_language": "en"},
        ).get_json()
        self.assertTrue(restored["paired"])
        self.assertNotIn("pairing_code", restored)

        forbidden = self.client.delete(
            "/api/pi/v1/devices/rpi5-bench-01",
            headers={"X-VillageLens-Tester-ID": "a1"},
        )
        revoked = self.client.delete(
            "/api/pi/v1/devices/rpi5-bench-01",
            headers={"X-VillageLens-Tester-ID": "a3"},
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(revoked.status_code, 200)
        store.return_value.revoke.assert_called_once_with("rpi5-bench-01")

    def test_browser_can_revoke_its_device_session(self) -> None:
        session, device = self.create_and_pair()
        revoked = self.client.delete(
            f"/api/pi/v1/sessions/{session['session_id']}",
            headers={"X-VillageLens-Tester-ID": "a1"},
        )

        self.assertEqual(revoked.status_code, 200)
        with self.assertRaisesRegex(PiBridgeError, "PI_DEVICE_AUTH_INVALID"):
            _pi_hub.session_for_token(device["device_token"])

    def test_persistent_authentication_fails_closed_when_storage_fails(self) -> None:
        _session, device = self.create_and_pair()
        with (
            patch("api.app.CAPTURE_BUCKET", "existing-private-bucket"),
            patch("api.app._pi_enrollment_store") as store,
        ):
            store.return_value.authenticate.side_effect = PiBridgeError(
                "PI_ENROLLMENT_STORAGE_UNAVAILABLE", 503,
            )

            with self.assertRaisesRegex(PiBridgeError, "PI_ENROLLMENT_STORAGE_UNAVAILABLE"):
                _authenticate_pi_device(device["device_token"])

    def test_command_reaches_only_paired_device(self) -> None:
        session, device = self.create_and_pair()
        response = self.client.post(
            f"/api/pi/v1/sessions/{session['session_id']}/commands",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"action": "capture"},
        )
        command = _pi_hub.next_command(device["device_token"])

        self.assertEqual(response.status_code, 202)
        self.assertEqual(command["type"], "capture_request")

    def test_websocket_handlers_route_one_device_command_to_its_browser_session(self) -> None:
        session, device = self.create_and_pair()
        self.client.post(
            f"/api/pi/v1/sessions/{session['session_id']}/commands",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"action": "capture"},
        )

        class FakeSocket:
            def __init__(self, received: list[object]) -> None:
                self.received = received
                self.sent: list[object] = []

            def receive(self, timeout: float | None = None) -> object:
                if self.received:
                    return self.received.pop(0)
                raise ConnectionClosed()

            def send(self, value: object) -> None:
                self.sent.append(value)

        device_socket = FakeSocket([
            json.dumps({"type": "authenticate", "device_token": device["device_token"]}),
        ])
        with app.test_request_context("/api/pi/v1/device/socket"):
            _serve_pi_device_socket(device_socket)
        messages = [json.loads(value) for value in device_socket.sent]
        self.assertEqual(messages[0]["type"], "authenticated")
        self.assertEqual(messages[1]["type"], "capture_request")

        browser_socket = FakeSocket([])
        with app.test_request_context(
            f"/api/pi/v1/browser/socket/{session['session_id']}?tester=a1",
        ):
            _serve_pi_browser_socket(browser_socket, session["session_id"])
        browser_messages = [
            json.loads(value) for value in browser_socket.sent if isinstance(value, str)
        ]
        self.assertEqual(browser_messages[0]["type"], "device_paired")
        self.assertIn("device_connection", [value["type"] for value in browser_messages])

    @patch("api.app._ingest_capture")
    def test_pi_still_uses_existing_ingest_and_returns_hash_acceptance(self, ingest: object) -> None:
        session, device = self.create_and_pair()
        self.client.post(
            f"/api/pi/v1/sessions/{session['session_id']}/commands",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"action": "capture"},
        )
        command = _pi_hub.next_command(device["device_token"])
        request_id = command["request"]["request_id"]
        source = b"\xff\xd8immutable-pi-source"
        digest = hashlib.sha256(source).hexdigest()
        ingest.return_value = ({"capture_id": request_id, "retained": True}, 200)
        headers = {
            "Authorization": f"Bearer {device['device_token']}",
            "X-VillageLens-Source-SHA256": digest,
            "X-VillageLens-Device-Profile-ID": "rpi5-bench-01",
            "X-VillageLens-Capture-Schema": "villagelens.pi-capture-response.v1",
            "X-VillageLens-Burst-Capture-ID": "bench-burst-01",
            "X-VillageLens-Captured-At": "2026-09-23T18:00:00Z",
            "X-VillageLens-Selected-Frame": "2",
            "X-VillageLens-Burst-Frames": "4",
        }

        first = self.client.post(
            f"/api/pi/v1/device/captures/{request_id}",
            headers=headers,
            data=source,
            content_type="image/jpeg",
        )
        second = self.client.post(
            f"/api/pi/v1/device/captures/{request_id}",
            headers=headers,
            data=source,
            content_type="image/jpeg",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["schema"], "villagelens.pi-upload-acceptance.v1")
        self.assertEqual(first.get_json()["source_sha256"], digest)
        self.assertEqual(second.get_json(), first.get_json())
        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.kwargs["tester_id"], "a1")
        self.assertEqual(ingest.call_args.kwargs["capture_source"], "pi-camera-v1")
        provenance = ingest.call_args.kwargs["capture_provenance"]
        self.assertEqual(provenance["source_sha256"], digest)
        self.assertEqual(provenance["selected_frame_index"], 2)
        self.assertEqual(provenance["burst_frames"], 4)

    def test_pi_upload_rejects_wrong_hash_and_missing_device_auth(self) -> None:
        session, device = self.create_and_pair()
        self.client.post(
            f"/api/pi/v1/sessions/{session['session_id']}/commands",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"action": "capture"},
        )
        request_id = _pi_hub.next_command(device["device_token"])["request"]["request_id"]
        path = f"/api/pi/v1/device/captures/{request_id}"

        unauthenticated = self.client.post(path, data=b"source", content_type="image/jpeg")
        wrong_hash = self.client.post(path, headers={
            "Authorization": f"Bearer {device['device_token']}",
            "X-VillageLens-Source-SHA256": "0" * 64,
            "X-VillageLens-Device-Profile-ID": "rpi5-bench-01",
        }, data=b"source", content_type="image/jpeg")

        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(wrong_hash.status_code, 400)

    @patch("api.app._ingest_capture")
    def test_pi_upload_requires_bounded_burst_provenance(self, ingest: object) -> None:
        session, device = self.create_and_pair()
        self.client.post(
            f"/api/pi/v1/sessions/{session['session_id']}/commands",
            headers={"X-VillageLens-Tester-ID": "a1"},
            json={"action": "capture"},
        )
        request_id = _pi_hub.next_command(device["device_token"])["request"]["request_id"]
        source = b"\xff\xd8immutable-pi-source"
        response = self.client.post(
            f"/api/pi/v1/device/captures/{request_id}",
            headers={
                "Authorization": f"Bearer {device['device_token']}",
                "X-VillageLens-Source-SHA256": hashlib.sha256(source).hexdigest(),
                "X-VillageLens-Device-Profile-ID": "rpi5-bench-01",
            },
            data=source,
            content_type="image/jpeg",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "PI_CAPTURE_SCHEMA_INVALID")
        ingest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
