from __future__ import annotations

import csv
import base64
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from flask import Flask, Response, jsonify, make_response, redirect, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPOSITORY_ROOT / "web"
DEMO_ROOT = WEB_ROOT / "a" / "demo"
TESSDATA_DIRECTORY = Path(
    os.environ.get("VILLAGELENS_TESSDATA_DIR", REPOSITORY_ROOT / "models" / "tessdata")
)
MAX_CAPTURE_BYTES = int(os.environ.get("VILLAGELENS_MAX_CAPTURE_BYTES", 15 * 1024 * 1024))
MAX_IMAGE_PIXELS = int(os.environ.get("VILLAGELENS_MAX_IMAGE_PIXELS", 25_000_000))
MAX_IMAGE_EDGE = int(os.environ.get("VILLAGELENS_MAX_IMAGE_EDGE", 4096))
LOCAL_OCR_MAX_EDGE = int(os.environ.get("VILLAGELENS_LOCAL_OCR_MAX_EDGE", 1600))
LOCAL_OCR_TIMEOUT_SECONDS = int(os.environ.get("VILLAGELENS_LOCAL_OCR_TIMEOUT_SECONDS", 20))
MAX_SPEECH_CHARACTERS = int(os.environ.get("VILLAGELENS_MAX_SPEECH_CHARACTERS", 500))
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}
CAPTURE_BUCKET = os.environ.get("VILLAGELENS_CAPTURE_BUCKET", "")
OPENAI_MODEL = os.environ.get("VILLAGELENS_OPENAI_MODEL", "gpt-5.6-sol")
OPENAI_TRANSLATION_MODEL = os.environ.get("VILLAGELENS_TRANSLATION_MODEL", "gpt-5-mini")
OPENAI_ANALYSIS_VERSION = "context-v2"
KANNADA_TTS_VOICE = os.environ.get("VILLAGELENS_KANNADA_TTS_VOICE", "kn-IN-Standard-A")
ACCESS_COOKIE_NAME = "villagelens_access_v2"
TESTER_COOKIE_NAME = "villagelens_tester_v1"
LEGACY_ACCESS_COOKIE_NAMES = ("villagelens_access",)
ACCESS_COOKIE_TTL_SECONDS = 30 * 24 * 60 * 60
MAX_QUESTION_CHARACTERS = 500
MAX_QUESTION_AUDIO_BYTES = 4 * 1024 * 1024
MAX_QUESTION_HISTORY_TURNS = 6
OPENAI_TRANSCRIPTION_MODEL = os.environ.get(
    "VILLAGELENS_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe"
)
MODEL_SHA256 = {
    "kan": "bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}
TESTER_ID_PATTERN = re.compile(r"a(?:10|[1-9])")
REVIEWER_TESTER_IDS = {"a3"}
TESTER_NAMES = {
    "a1": "Eeregowda",
    "a2": "Umesh",
    "a3": "Reviewer",
    "a4": "Selvan",
    "a5": "Kiran",
    "a6": "Rupa",
    "a7": "Akul",
}
USAGE_EVENTS = {
    "capture", "word", "line", "translate", "object", "infer", "question",
    "question_tap", "question_permission", "question_recording", "question_upload",
    "camera_open", "camera_fallback", "camera_cancel", "camera_auto", "camera_manual",
    "audio_ok", "audio_failed", "stage_1", "stage_2", "stage_3", "stage_4",
}
DEMO_ASSETS = {
    "i1.jpeg", "i1-scene.json", "i2.jpeg", "i2-scene.json", "i2-gold.json",
}
APP_ASSETS = {
    "manifest.webmanifest", "sw.js", "icon.svg", "icon-192.png", "icon-512.png",
}
VERIFIED_CAPTURE_REGIONS = {
    "fac3bcfd6b5d43d79fa1652e10159b95": [
        {
            "id": "rupa-menu-thursday-1", "label": "Puliyogare",
            "spoken_kn": "ಒಂದು. ಪುಳಿಯೋಗರೆ.",
            "meaning_kn": "ಹುಣಸೆಹಣ್ಣಿನ ಮಸಾಲೆ ಅನ್ನ.",
            "box": {"x": 87, "y": 593, "width": 455, "height": 116},
            "verified_by": "owner_feedback_20260909",
        },
        {
            "id": "rupa-menu-thursday-2", "label": "Kadle kai",
            "spoken_kn": "ಎರಡು. ಕಡಲೆಕಾಯಿ.", "meaning_kn": "ನೆಲಗಡಲೆ.",
            "box": {"x": 122, "y": 698, "width": 436, "height": 125},
            "verified_by": "owner_feedback_20260909",
        },
        {
            "id": "rupa-menu-thursday-3", "label": "Shavige",
            "spoken_kn": "ಮೂರು. ಶಾವಿಗೆ.",
            "meaning_kn": "ವರ್ಮಿಸೆಲ್ಲಿಯಿಂದ ಮಾಡುವ ತಿಂಡಿ.",
            "box": {"x": 143, "y": 835, "width": 486, "height": 80},
            "verified_by": "owner_feedback_20260909",
        },
        {
            "id": "rupa-menu-thursday-7", "label": "Ollige",
            "spoken_kn": "ಏಳು. ಒಳಿಗೆ.", "meaning_kn": "ಒಳಿಗೆ ಎಂಬ ತಿಂಡಿ.",
            "box": {"x": 109, "y": 1211, "width": 474, "height": 104},
            "verified_by": "owner_feedback_20260909",
        },
    ],
}

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CAPTURE_BYTES
app.config["VILLAGELENS_ACCESS_CODE"] = os.environ.get("VILLAGELENS_ACCESS_CODE", "").strip()
app.config["VILLAGELENS_SESSION_SECRET"] = os.environ.get("VILLAGELENS_SESSION_SECRET", "")
_capture_processing_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)


def _access_code() -> str:
    return str(app.config.get("VILLAGELENS_ACCESS_CODE", "")).strip()


def _access_configured() -> bool:
    return bool(
        _access_code()
        and app.config.get("VILLAGELENS_SESSION_SECRET")
    )


def _access_signature(issued: str) -> str:
    code_hash = hashlib.sha256(_access_code().encode("utf-8")).hexdigest()
    return hmac.new(
        str(app.config["VILLAGELENS_SESSION_SECRET"]).encode("utf-8"),
        f"{issued}:{code_hash}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _access_token() -> str:
    issued = str(int(time.time()))
    return f"{issued}.{_access_signature(issued)}"


def _tester_link_token(tester_id: str) -> str:
    if not TESTER_ID_PATTERN.fullmatch(tester_id):
        raise ValueError("TESTER_ID_INVALID")
    code_hash = hashlib.sha256(_access_code().encode("utf-8")).hexdigest()
    signature = hmac.new(
        str(app.config["VILLAGELENS_SESSION_SECRET"]).encode("utf-8"),
        f"tester-link-v1:{tester_id}:{code_hash}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{tester_id}.{encoded}"


def _tester_from_link(token: str) -> str:
    tester_id, separator, _ = token.partition(".")
    if not separator or not TESTER_ID_PATTERN.fullmatch(tester_id):
        return ""
    try:
        expected = _tester_link_token(tester_id)
    except ValueError:
        return ""
    return tester_id if hmac.compare_digest(token, expected) else ""


def _has_access() -> bool:
    if not _access_configured():
        return not (
            app.config.get("VILLAGELENS_ACCESS_CODE")
            or app.config.get("VILLAGELENS_SESSION_SECRET")
        )
    for name in (ACCESS_COOKIE_NAME, *LEGACY_ACCESS_COOKIE_NAMES):
        for token in request.cookies.getlist(name):
            try:
                issued, signature = token.split(".", 1)
                age = int(time.time()) - int(issued)
            except (TypeError, ValueError):
                continue
            if (
                -60 <= age <= ACCESS_COOKIE_TTL_SECONDS
                and hmac.compare_digest(signature, _access_signature(issued))
            ):
                return True
    return False


@app.before_request
def _require_access() -> Response | tuple[Response, int] | None:
    if request.path in {"/access", "/access/link", "/health", "/healthz"} or _has_access():
        return None
    if request.path.startswith("/api/"):
        return jsonify(error="ACCESS_REQUIRED"), 401
    tester_id = request.args.get("tester", "").strip().lower()
    destination = f"/access?tester={tester_id}" if TESTER_ID_PATTERN.fullmatch(tester_id) else "/access"
    return redirect(destination, code=302)


def _allowed_origins() -> set[str]:
    return {
        value.strip()
        for value in os.environ.get("VILLAGELENS_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    }


def _tester_id() -> str:
    candidate = request.headers.get("X-VillageLens-Tester-ID", "").strip().lower()
    return candidate if TESTER_ID_PATTERN.fullmatch(candidate) else ""


def _is_reviewer(tester_id: str) -> bool:
    return tester_id in REVIEWER_TESTER_IDS


@app.after_request
def _response_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self)"
    if request.path.startswith("/api/") or request.path.startswith("/access"):
        response.headers["Cache-Control"] = (
            "private, max-age=604800" if request.path == "/api/speech" and response.status_code == 200
            else "no-store"
        )
        origin = request.headers.get("Origin", "")
        if origin and origin in _allowed_origins():
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
    return response


@app.errorhandler(413)
def _capture_too_large(_: Exception) -> tuple[Response, int]:
    return jsonify(error="CAPTURE_TOO_LARGE"), 413


@app.get("/")
def root() -> Response:
    return redirect("/access" if _access_configured() else "/a/", code=302)


def _with_access_cookie(response: Response, tester_id: str = "") -> Response:
    for legacy_name in LEGACY_ACCESS_COOKIE_NAMES:
        response.delete_cookie(
            legacy_name,
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/",
        )
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        _access_token(),
        max_age=ACCESS_COOKIE_TTL_SECONDS,
        secure=True,
        httponly=True,
        samesite="Lax",
        path="/",
    )
    if TESTER_ID_PATTERN.fullmatch(tester_id):
        response.set_cookie(
            TESTER_COOKIE_NAME,
            tester_id,
            max_age=ACCESS_COOKIE_TTL_SECONDS,
            secure=True,
            httponly=True,
            samesite="Lax",
            path="/a/",
        )
    return response


@app.post("/access/link")
def access_link() -> Response | tuple[Response, int]:
    if not _access_configured():
        return jsonify(error="ACCESS_NOT_CONFIGURED"), 503
    tester_id = _tester_from_link(request.form.get("token", "").strip())
    if not tester_id:
        return jsonify(error="ACCESS_LINK_INVALID"), 401
    return _with_access_cookie(jsonify(destination=f"/a/?tester={tester_id}"), tester_id)


@app.route("/access", methods=["GET", "POST"])
def access() -> Response:
    if not _access_configured():
        return redirect("/a/", code=302)
    message = "ಬಳಕೆದಾರರನ್ನು ಆಯ್ಕೆಮಾಡಿ ಮತ್ತು ಪ್ರವೇಶ ಕೋಡ್ ನಮೂದಿಸಿ"
    tester_id = request.values.get("tester", "").strip().lower()
    if not TESTER_ID_PATTERN.fullmatch(tester_id):
        tester_id = ""
    if request.method == "POST":
        submitted = request.form.get("code", "").strip()
        expected = _access_code()
        if tester_id and submitted and hmac.compare_digest(submitted, expected):
            destination = f"/a/?tester={tester_id}"
            return _with_access_cookie(make_response(redirect(destination, code=303)), tester_id)
        message = (
            "ಬಳಕೆದಾರರನ್ನು ಆಯ್ಕೆಮಾಡಿ. Choose a user."
            if not tester_id else "ಕೋಡ್ ಸರಿಯಾಗಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."
        )
    options = ['<option value="">User — A1 to A10</option>']
    for number in range(1, 11):
        value = f"a{number}"
        selected = " selected" if value == tester_id else ""
        options.append(f'<option value="{value}"{selected}>A{number}</option>')
    user_options = "".join(options)
    page = f"""<!doctype html>
<html lang="kn"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="theme-color" content="#101418"><title>VillageLensAI Access</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#101418;
color:#f5f7fa;font-family:system-ui,sans-serif}}main{{width:min(92vw,420px);text-align:center}}
label{{display:block;font-size:1.1rem;margin:1rem 0 .4rem;text-align:left}}input,select,button{{width:100%;min-height:58px;
border-radius:12px;font-size:1.3rem}}input,select{{padding:0 14px;border:2px solid #64717d;background:#fff;color:#111}}
button{{margin-top:14px;border:0;background:#168447;color:white;font-weight:700}}</style></head>
<body><main><h1>VillageLensAI</h1><form method="post" action="/access">
<p>{message}</p>
<label for="tester">User</label><select id="tester" name="tester" required autofocus>{user_options}</select>
<label for="code">Code</label>
<input id="code" name="code" type="password" autocomplete="one-time-code"
required aria-label="Access code"><button type="submit">🔓</button></form>
<script>(async()=>{{
  const token=new URLSearchParams(location.hash.slice(1)).get('enroll');
  if (!token) return;
  history.replaceState(null,'','/access');
  const form=document.querySelector('form'),message=document.querySelector('p');
  form.hidden=true; message.textContent='ತೆರೆಯಲಾಗುತ್ತಿದೆ…';
  try {{
    const response=await fetch('/access/link',{{method:'POST',credentials:'same-origin',
      headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
      body:new URLSearchParams({{token}})}});
    const value=await response.json();
    if (!response.ok) throw new Error('LINK_FAILED');
    location.replace(value.destination);
  }} catch (_) {{
    form.hidden=false; message.textContent='ಲಿಂಕ್ ಕೆಲಸ ಮಾಡಲಿಲ್ಲ. ಮತ್ತೆ ಲಿಂಕ್ ಒತ್ತಿರಿ.';
  }}
}})();</script></main></body></html>"""
    return make_response(page, 401 if request.method == "POST" else 200)


@app.get("/a/")
def tester_page() -> Response:
    tester_id = request.args.get("tester", "").strip().lower()
    if _access_configured() and not TESTER_ID_PATTERN.fullmatch(tester_id):
        installed_tester = request.cookies.get(TESTER_COOKIE_NAME, "").strip().lower()
        if TESTER_ID_PATTERN.fullmatch(installed_tester):
            shared = "&shared=1" if request.args.get("shared") == "1" else ""
            return redirect(f"/a/?tester={installed_tester}{shared}", code=302)
        return redirect("/access", code=302)
    return send_from_directory(WEB_ROOT / "a", "index.html")


@app.get("/a/<path:filename>")
def app_asset(filename: str) -> Response | tuple[Response, int]:
    if filename not in APP_ASSETS:
        return jsonify(error="APP_ASSET_NOT_FOUND"), 404
    response = make_response(send_from_directory(WEB_ROOT / "a", filename))
    if filename == "sw.js":
        response.headers["Service-Worker-Allowed"] = "/a/"
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/a/demo/<path:filename>")
def demo_asset(filename: str) -> Response | tuple[Response, int]:
    if filename not in DEMO_ASSETS:
        return jsonify(error="DEMO_ASSET_NOT_FOUND"), 404
    return send_from_directory(DEMO_ROOT, filename)


@app.get("/health")
@app.get("/healthz")
def health() -> tuple[Response, int]:
    missing = [
        language
        for language in MODEL_SHA256
        if not (TESSDATA_DIRECTORY / f"{language}.traineddata").is_file()
    ]
    access_misconfigured = bool(
        app.config.get("VILLAGELENS_ACCESS_CODE")
        or app.config.get("VILLAGELENS_SESSION_SECRET")
    ) and not _access_configured()
    status = 200 if not missing and not access_misconfigured else 503
    return jsonify(
        status="ok" if status == 200 else "not_ready",
        missing_models=missing,
        access_gate="enabled" if _access_configured() else "disabled",
    ), status


def _normalized_image(data: bytes) -> tuple[Image.Image, bool]:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            opened.load()
            original_size = opened.size
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("CAPTURE_IMAGE_INVALID") from exc
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("CAPTURE_PIXELS_EXCEEDED")
    resized = max(image.size) > MAX_IMAGE_EDGE
    if resized:
        image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
    return image, resized or image.size != original_size


def _parse_tsv(tsv: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    words: list[dict[str, Any]] = []
    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    # Tesseract text is not CSV-quoted. A stray recognised quote must not consume
    # every following TSV row as one enormous word.
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        if row.get("level") != "5" or not (text := (row.get("text") or "").strip()):
            continue
        try:
            confidence = float(row.get("conf") or -1)
            box = {
                "x": int(row["left"]), "y": int(row["top"]),
                "width": int(row["width"]), "height": int(row["height"]),
            }
            key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
        except (KeyError, TypeError, ValueError):
            continue
        word = {
            "id": f"word-{len(words) + 1:04d}", "text": text,
            "confidence": round(confidence, 3), "box": box, "line_key": key,
        }
        words.append(word)
        grouped[key].append(word)

    lines: list[dict[str, Any]] = []
    for line_words in grouped.values():
        left = min(word["box"]["x"] for word in line_words)
        top = min(word["box"]["y"] for word in line_words)
        right = max(word["box"]["x"] + word["box"]["width"] for word in line_words)
        bottom = max(word["box"]["y"] + word["box"]["height"] for word in line_words)
        confidences = [word["confidence"] for word in line_words if word["confidence"] >= 0]
        line_id = f"line-{len(lines) + 1:03d}"
        for word in line_words:
            word["line_id"] = line_id
            word.pop("line_key", None)
        lines.append({
            "id": line_id,
            "text": " ".join(word["text"] for word in line_words),
            "confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
            "box": {"x": left, "y": top, "width": right - left, "height": bottom - top},
            "word_ids": [word["id"] for word in line_words],
        })
    return words, lines


def _scale_regions(
    words: list[dict[str, Any]], lines: list[dict[str, Any]], *,
    source_width: int, source_height: int, target_width: int, target_height: int,
) -> None:
    scale_x = target_width / source_width
    scale_y = target_height / source_height
    for region in [*words, *lines]:
        box = region["box"]
        box.update(
            x=round(box["x"] * scale_x),
            y=round(box["y"] * scale_y),
            width=max(1, round(box["width"] * scale_x)),
            height=max(1, round(box["height"] * scale_y)),
        )


def _filter_local_regions(
    words: list[dict[str, Any]], lines: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept_words = []
    for word in words:
        text = str(word.get("text", ""))
        confidence = float(word.get("confidence", -1))
        kannada_letters = re.findall(r"[\u0c85-\u0cb9]", text)
        if confidence < 0 or "\n" in text or "\t" in text:
            continue
        if kannada_letters and (confidence < 35 or (len(kannada_letters) == 1 and confidence < 70)):
            continue
        kept_words.append(word)

    kept_ids = {word["id"] for word in kept_words}
    kept_lines = []
    words_by_id = {word["id"]: word for word in kept_words}
    for line in lines:
        line_words = [words_by_id[word_id] for word_id in line["word_ids"] if word_id in kept_ids]
        if not line_words:
            continue
        left = min(word["box"]["x"] for word in line_words)
        top = min(word["box"]["y"] for word in line_words)
        right = max(word["box"]["x"] + word["box"]["width"] for word in line_words)
        bottom = max(word["box"]["y"] + word["box"]["height"] for word in line_words)
        confidences = [word["confidence"] for word in line_words]
        normalized = dict(line)
        normalized.update(
            text=" ".join(word["text"] for word in line_words),
            confidence=round(sum(confidences) / len(confidences), 3),
            box={"x": left, "y": top, "width": right-left, "height": bottom-top},
            word_ids=[word["id"] for word in line_words],
        )
        kept_lines.append(normalized)
    return kept_words, kept_lines


def _select_regions(
    words: list[dict[str, Any]], lines: list[dict[str, Any]], *, width: int, height: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    words_by_id = {word["id"]: word for word in words}
    candidates: list[tuple[float, dict[str, Any]]] = []
    for line in lines:
        box = line["box"]
        if box["width"] < max(12, round(width * 0.008)) and box["height"] < max(10, round(height * 0.006)):
            continue
        confidences = [
            words_by_id[word_id]["confidence"]
            for word_id in line["word_ids"]
            if word_id in words_by_id and words_by_id[word_id]["confidence"] >= 0
        ]
        confidence = max(confidences, default=0)
        candidates.append((box["width"] * box["height"] * max(confidence, 10), line))
    chosen = [line for _, line in sorted(candidates, key=lambda item: item[0], reverse=True)[:32]]
    chosen.sort(key=lambda line: (line["box"]["y"], line["box"]["x"]))
    allowed = {line["id"] for line in chosen}
    return [word for word in words if word.get("line_id") in allowed], chosen


def _geometry_lines(words: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    rows: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda item: (item["box"]["y"], item["box"]["x"])):
        box = word["box"]
        center = box["y"] + box["height"] / 2
        row = next((candidate for candidate in rows if abs(center - sum(
            item["box"]["y"] + item["box"]["height"] / 2 for item in candidate
        ) / len(candidate)) <= max(box["height"], max(item["box"]["height"] for item in candidate)) * .65), None)
        if row is None:
            row = []
            rows.append(row)
        row.append(word)
    lines: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda items: min(item["box"]["y"] for item in items)):
        row.sort(key=lambda item: item["box"]["x"])
        line_id = f"{prefix}-line-{len(lines)+1:03d}"
        for word in row:
            word["line_id"] = line_id
        left=min(word["box"]["x"] for word in row); top=min(word["box"]["y"] for word in row)
        right=max(word["box"]["x"]+word["box"]["width"] for word in row)
        bottom=max(word["box"]["y"]+word["box"]["height"] for word in row)
        lines.append({"id": line_id, "text": " ".join(word["text"] for word in row),
                      "box": {"x": left, "y": top, "width": right-left, "height": bottom-top},
                      "word_ids": [word["id"] for word in row]})
    return lines


def _tesseract(image_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [
                "tesseract", str(image_path), "stdout", "--tessdata-dir", str(TESSDATA_DIRECTORY),
                # English first reduces false Kannada glyphs on branded Latin text
                # while retaining the repository-local Kannada model.
                "-l", "eng+kan", "--oem", "1", "--psm", "11",
                "-c", "tessedit_create_tsv=1",
            ],
            check=False, capture_output=True, text=True, timeout=LOCAL_OCR_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("LOCAL_OCR_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise RuntimeError("LOCAL_OCR_FAILED")
    words, lines = _parse_tsv(completed.stdout)
    words, lines = _filter_local_regions(words, lines)
    return words, lines, round((time.monotonic() - started) * 1000)


def _vision_reader(data: bytes, width: int, height: int) -> dict[str, Any]:
    from google.cloud import vision

    started = time.monotonic()
    response = vision.ImageAnnotatorClient().document_text_detection(
        image=vision.Image(content=data), timeout=70,
    )
    if response.error.message:
        raise RuntimeError("VISION_OCR_FAILED")
    words: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    paragraph_index = 0
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                paragraph_words: list[dict[str, Any]] = []
                for source_word in paragraph.words:
                    text = "".join(symbol.text for symbol in source_word.symbols).strip()
                    vertices = list(source_word.bounding_box.vertices)
                    if not text or not vertices:
                        continue
                    xs = [vertex.x for vertex in vertices]
                    ys = [vertex.y for vertex in vertices]
                    word = {
                        "id": f"vision-word-{len(words) + 1:04d}", "text": text,
                        "confidence": round(float(source_word.confidence) * 100, 3),
                        "box": {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs),
                                "height": max(ys) - min(ys)},
                    }
                    words.append(word)
                    paragraph_words.append(word)
                if paragraph_words:
                    paragraph_index += 1
                    lines.extend(_geometry_lines(paragraph_words, f"vision-p{paragraph_index:03d}"))
    # Vision paragraphs can span several physical rows. Rebuild touchable
    # sentence rows within each paragraph instead of merging the paragraph.
    lines.sort(key=lambda line: (line["box"]["y"], line["box"]["x"]))
    words, lines = _select_regions(words, lines, width=width, height=height)
    return {"schema": "villagelens.reader.v1", "stage": 2, "reader": "cloud_ocr",
            "latency_ms": round((time.monotonic()-started)*1000), "image_size": {"width": width, "height": height},
            "words": words, "lines": lines, "text": response.full_text_annotation.text}


def _openai_output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return str(content.get("text", ""))
    raise RuntimeError("OPENAI_READER_INVALID_RESPONSE")


def _valid_kannada_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or not re.search(r"[\u0c80-\u0cff]", text):
        return False
    # Provider output may preserve Latin names, but other writing systems are a
    # strong signal that the requested Kannada rendering is corrupt.
    return not re.search(
        r"[\u0370-\u052f\u0590-\u0c7f\u0d00-\u0dff\u0e00-\u109f"
        r"\u10a0-\u10ff\u1200-\u137f\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]",
        text,
    )


def _validated_kannada_output(parsed: dict[str, Any]) -> tuple[list[dict[str, str]], str, bool]:
    candidates = parsed.get("translations", [])
    translations = [
        {"source": str(item.get("source", "")).strip(),
         "translation_kn": str(item.get("translation_kn", "")).strip()}
        for item in candidates if isinstance(item, dict)
        and str(item.get("source", "")).strip()
        and _valid_kannada_text(item.get("translation_kn"))
    ] if isinstance(candidates, list) else []
    summary = str(parsed.get("brief_spoken_kn") or parsed.get("summary_kn", "")).strip()
    summary_valid = _valid_kannada_text(summary)
    expected = sum(
        1 for item in candidates if isinstance(item, dict)
        and re.search(r"[A-Za-z]", str(item.get("source", "")))
    ) if isinstance(candidates, list) else 0
    translations_valid = expected == len(translations)
    return translations, summary if summary_valid else "", summary_valid and translations_valid


def _normalize_stage_three(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)
    translations, summary, valid = _validated_kannada_output(normalized)
    context, context_valid = _validated_context(normalized)
    has_context = any(key in normalized for key in ("brief_spoken_kn", "objects", "what_is_it_kn"))
    normalized.update(
        translations=translations, summary_kn=summary,
        quality_validated=valid and (context_valid if has_context else True),
    )
    if has_context:
        normalized.update(context)
    return normalized


def _current_stage_three(value: dict[str, Any] | None) -> bool:
    return bool(value and value.get("analysis_version") == OPENAI_ANALYSIS_VERSION)


def _context_box(value: Any) -> list[float] | dict[str, float] | None:
    if isinstance(value, dict):
        try:
            box = {key: float(value[key]) for key in ("x", "y", "width", "height")}
        except (KeyError, TypeError, ValueError):
            return None
        return box if box["width"] > 0 and box["height"] > 0 else None
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        x, y, width, height = [max(0.0, min(1000.0, float(item))) for item in value]
    except (TypeError, ValueError):
        return None
    return [x, y, width, height] if width > 0 and height > 0 and x + width <= 1020 and y + height <= 1020 else None


def _selectable_object_box(value: Any, parsed: dict[str, Any]) -> list[float] | dict[str, float] | None:
    box = _context_box(value)
    if box is None:
        return None
    image_size = parsed.get("image_size", {})
    if isinstance(box, list):
        full_width = full_height = 1000.0
        _, _, width, height = box
    else:
        try:
            full_width = float(image_size.get("width", 0))
            full_height = float(image_size.get("height", 0))
            width, height = box["width"], box["height"]
        except (AttributeError, TypeError, ValueError):
            return box
    # A full-frame scene/background region overlaps every useful object and
    # steals its touch event. It belongs in global explanation, not object mode.
    if full_width > 0 and full_height > 0 and width >= full_width * .92 and height >= full_height * .92:
        return None
    return box


def _scale_context_boxes(context: dict[str, Any], width: int, height: int) -> None:
    def scaled(value: Any) -> dict[str, int] | None:
        box = _context_box(value)
        if not isinstance(box, list):
            return box
        x, y, box_width, box_height = box
        return {
            "x": round(x * width / 1000), "y": round(y * height / 1000),
            "width": round(box_width * width / 1000),
            "height": round(box_height * height / 1000),
        }

    for key in ("objects", "transcription_kn", "spoken_sections"):
        for item in context.get(key, []):
            if box := scaled(item.get("box")):
                item["box"] = box
            else:
                item.pop("box", None)


def _validated_context(parsed: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    required_text = ("what_is_it_kn", "what_it_does_kn", "brief_spoken_kn", "detailed_spoken_kn")
    context = {
        "scene_type": str(parsed.get("scene_type", "unknown")).strip() or "unknown",
        **{key: str(parsed.get(key, "")).strip() for key in required_text},
        "action_needed_kn": str(parsed.get("action_needed_kn", "")).strip(),
        "warning_kn": str(parsed.get("warning_kn", "")).strip(),
        "uncertainty_kn": str(parsed.get("uncertainty_kn", "")).strip(),
        "confidence": str(parsed.get("confidence", "low")).strip().lower(),
        "needs_independent_review": bool(parsed.get("needs_independent_review", True)),
    }
    points = parsed.get("important_points_kn", [])
    context["important_points_kn"] = [
        str(point).strip() for point in points if _valid_kannada_text(point)
    ] if isinstance(points, list) else []
    objects = parsed.get("objects", [])
    context["objects"] = [
        {
            "name": str(item.get("name", "")).strip(),
            "name_kn": str(item.get("name_kn", "")).strip(),
            "purpose_kn": str(item.get("purpose_kn", "")).strip(),
            "evidence": str(item.get("evidence", "")).strip(),
            "uncertain": bool(item.get("uncertain", False)),
            "box": _selectable_object_box(item.get("box"), parsed),
        }
        for item in objects
        if isinstance(item, dict)
        and _valid_kannada_text(item.get("name_kn"))
        and _valid_kannada_text(item.get("purpose_kn"))
        and _selectable_object_box(item.get("box"), parsed) is not None
    ] if isinstance(objects, list) else []
    transcription = parsed.get("transcription_kn", [])
    context["transcription_kn"] = [
        {
            "text_kn": str(item.get("text_kn", "")).strip(),
            "box": _context_box(item.get("box")),
            "uncertain": bool(item.get("uncertain", False)),
        }
        for item in transcription
        if isinstance(item, dict) and _valid_kannada_text(item.get("text_kn"))
    ] if isinstance(transcription, list) else []
    sections = parsed.get("spoken_sections", [])
    context["spoken_sections"] = [
        {
            "text_kn": str(item.get("text_kn", "")).strip(),
            "box": _context_box(item.get("box")),
        }
        for item in sections
        if isinstance(item, dict) and _valid_kannada_text(item.get("text_kn"))
    ] if isinstance(sections, list) else []
    if context["confidence"] not in {"high", "medium", "low"}:
        context["confidence"] = "low"
    valid = all(_valid_kannada_text(context[key]) for key in required_text)
    return context, valid


def _openai_reader(data: bytes, media_type: str, width: int, height: int) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_READER_NOT_CONFIGURED")
    started = time.monotonic()
    box_schema = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}
    object_schema = {"type": "object", "additionalProperties": False,
                     "required": ["name", "name_kn", "purpose_kn", "evidence", "uncertain", "box"],
                     "properties": {"name": {"type": "string"}, "name_kn": {"type": "string"},
                                    "purpose_kn": {"type": "string"}, "evidence": {"type": "string"},
                                    "uncertain": {"type": "boolean"}, "box": box_schema}}
    transcription_schema = {"type": "object", "additionalProperties": False,
                            "required": ["text_kn", "box", "uncertain"],
                            "properties": {"text_kn": {"type": "string"}, "box": box_schema,
                                           "uncertain": {"type": "boolean"}}}
    section_schema = {"type": "object", "additionalProperties": False,
                      "required": ["text_kn", "box"],
                      "properties": {"text_kn": {"type": "string"}, "box": box_schema}}
    schema = {"type": "object", "additionalProperties": False,
              "required": ["translations", "scene_type", "objects",
                           "what_is_it_kn", "what_it_does_kn", "important_points_kn",
                           "action_needed_kn", "warning_kn", "uncertainty_kn",
                           "brief_spoken_kn", "detailed_spoken_kn", "transcription_kn",
                           "spoken_sections", "confidence", "needs_independent_review"],
              "properties": {
                  "translations": {"type": "array", "items": {"type": "object",
                      "additionalProperties": False, "required": ["source", "translation_kn"],
                      "properties": {"source": {"type": "string"},
                                     "translation_kn": {"type": "string"}}}},
                  "scene_type": {"type": "string"},
                  "objects": {"type": "array", "items": object_schema},
                  "what_is_it_kn": {"type": "string"},
                  "what_it_does_kn": {"type": "string"},
                  "important_points_kn": {"type": "array", "items": {"type": "string"}},
                  "action_needed_kn": {"type": "string"},
                  "warning_kn": {"type": "string"},
                  "uncertainty_kn": {"type": "string"},
                  "brief_spoken_kn": {"type": "string"},
                  "detailed_spoken_kn": {"type": "string"}}}
    schema["properties"].update({
        "transcription_kn": {"type": "array", "items": transcription_schema},
        "spoken_sections": {"type": "array", "items": section_schema},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "needs_independent_review": {"type": "boolean"},
    })
    encoded = base64.b64encode(data).decode("ascii")
    payload = {"model": OPENAI_MODEL, "store": False, "reasoning": {"effort": "none"},
               "max_output_tokens": 5000,
               "input": [{"role": "user", "content": [
                   {"type": "input_text", "text": """Help a low-literacy Kannada-speaking adult understand this image. Read clearly visible Kannada and English for comprehension. Do not recreate all OCR boxes. Translate each distinct clearly visible English word into simple Kannada. Identify up to six useful visible objects and give each one bounding box [left,top,width,height] normalized 0 to 1000. Object boxes must tightly localize a touchable object or useful sub-part; never return the whole image, page, background, ground, or soil as an object box. If this is handwriting or a handwritten list, first identify its likely purpose and organization, such as a menu, shopping list, homework, names, dates, or tasks. Transcribe every readable line exactly into transcription_kn with a line box and mark uncertain lines; for uncertain words give a plausible reading only when the visible letters and list context support it, otherwise abstain. Distinguish recognition failure from blur, distance, perspective, cropping, and low contrast, and give specific capture guidance. Never label readable Kannada as another script. Treat joined measurements such as 300V, 2.0 HP, 50Hz, 10A, kg, ml, and degrees C as semantic units: preserve the printed characters and explain the unit naturally in Kannada. Explain what the image is, its purpose, important details, action, safety, and uncertainty in short natural spoken Kannada. Divide the explanation into two to six spoken_sections, each with the image region it refers to, so the interface can highlight evidence while speaking. brief_spoken_kn is the most useful one- or two-sentence global answer; detailed_spoken_kn adds useful context without mechanically repeating OCR. For calendars, summarize month, year, highlighted date and notable events rather than reciting the grid. For electrical equipment or medicine, report only visible or strongly supported identity, purpose, and ratings; never advise wiring, energizing, repair, or medication. Set confidence high only when important identity, text, numbers, and purpose are clear; set needs_independent_review true for handwriting uncertainty, safety-critical content, ambiguous units, or any important doubt. Never invent hidden facts, intent, diagnosis, species, or disease."""},
                   {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}", "detail": "high"}]}],
               "text": {"verbosity": "low", "format": {"type": "json_schema", "name": "villagelens_reading", "strict": True, "schema": schema}}}
    response = requests.post("https://api.openai.com/v1/responses", json=payload,
                             headers={"Authorization": f"Bearer {api_key}"}, timeout=75)
    if response.status_code != 200:
        app.logger.warning("OpenAI reader failed with HTTP %s", response.status_code)
        raise RuntimeError("OPENAI_READER_FAILED")
    parsed = json.loads(_openai_output_text(response.json()))
    translations, summary_kn, quality_validated = _validated_kannada_output(parsed)
    context, context_validated = _validated_context(parsed)
    _scale_context_boxes(context, width, height)
    return {"schema": "villagelens.reader.v1", "stage": 3, "reader": "vision_language",
            "model": OPENAI_MODEL, "analysis_version": OPENAI_ANALYSIS_VERSION,
            "latency_ms": round((time.monotonic()-started)*1000),
            "image_size": {"width": width, "height": height}, "words": [], "lines": [], "text": "",
            "translations": translations, "summary_kn": summary_kn, **context,
            "quality_validated": quality_validated and context_validated}


def _openai_question(
    data: bytes, media_type: str, width: int, height: int, question: str,
    history: list[dict[str, str]] | None = None,
    focus_box: dict[str, Any] | None = None,
    scene_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_READER_NOT_CONFIGURED")
    box_schema = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}
    schema = {
        "type": "object", "additionalProperties": False,
        "required": ["answer_kn", "warning_kn", "uncertainty_kn", "evidence_box"],
        "properties": {
            "answer_kn": {"type": "string"}, "warning_kn": {"type": "string"},
            "uncertainty_kn": {"type": "string"}, "evidence_box": box_schema,
        },
    }
    prior = (history or [])[-MAX_QUESTION_HISTORY_TURNS:]
    normalized_focus = None
    if focus_box:
        normalized_focus = [
            round(1000 * focus_box[key] / (width if key in {"x", "width"} else height))
            for key in ("x", "y", "width", "height")
        ]
    context = json.dumps({
        "prior_turns": prior,
        "current_referent": {
            "label": str((focus_box or {}).get("label", ""))[:120],
            "box_normalized_0_1000": normalized_focus,
        } if normalized_focus else None,
        "saved_semantic_scene": scene_context or None,
        "current_question": question,
    }, ensure_ascii=False)
    payload = {
        "model": OPENAI_MODEL, "store": False, "reasoning": {"effort": "none"},
        "max_output_tokens": 1200,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": (
                "Answer the user's spoken question about this image in simple natural Kannada. "
                "This is one continuing conversation about the same unchanged image. Use prior turns and "
                "the current referent region to resolve words such as this, it, that leaf, or this part. "
                "When there is no current referent, a general question such as 'what is this?' refers to "
                "the whole image; use the saved semantic scene when supplied. Never answer with only a "
                "demonstrative word such as 'this' or its Kannada equivalent. "
                "Keep the subject consistent across follow-up questions, but correct an earlier answer if "
                "the image contradicts it. For plant health questions, describe visible signs and uncertainty; "
                "do not claim a disease diagnosis from an image alone. "
                "Use only visible or strongly supported facts, preserve numbers and units, and state uncertainty. "
                "When the user asks to read numbers in Kannada, say every relevant visible number using "
                "Kannada number words and explain its unit or calendar role; do not merely repeat digits. "
                "Include a safety warning when relevant. evidence_box is the single most relevant image "
                "region [left,top,width,height] normalized 0 to 1000. Conversation context JSON: " + context
            )},
            {"type": "input_image", "image_url": (
                f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"
            ), "detail": "high"},
        ]}],
        "text": {"verbosity": "low", "format": {
            "type": "json_schema", "name": "villagelens_answer", "strict": True, "schema": schema,
        }},
    }
    response = requests.post(
        "https://api.openai.com/v1/responses", json=payload,
        headers={"Authorization": f"Bearer {api_key}"}, timeout=75,
    )
    if response.status_code != 200:
        raise RuntimeError("OPENAI_QUESTION_FAILED")
    parsed = json.loads(_openai_output_text(response.json()))
    answer = str(parsed.get("answer_kn", "")).strip()
    if not _valid_kannada_text(answer):
        raise RuntimeError("OPENAI_QUESTION_INVALID_RESPONSE")
    result = {
        "answer_kn": answer,
        "warning_kn": str(parsed.get("warning_kn", "")).strip(),
        "uncertainty_kn": str(parsed.get("uncertainty_kn", "")).strip(),
        "evidence": [{"box": _context_box(parsed.get("evidence_box"))}],
        "image_size": {"width": width, "height": height},
    }
    _scale_context_boxes({"spoken_sections": result["evidence"]}, width, height)
    return result


def _question_scene_context(value: dict[str, Any] | None) -> dict[str, Any]:
    if not _current_stage_three(value):
        return {}
    normalized = _normalize_stage_three(value or {})
    objects = [
        {
            "name_kn": str(item.get("name_kn", ""))[:120],
            "purpose_kn": str(item.get("purpose_kn", ""))[:300],
            "box": item.get("box"),
        }
        for item in normalized.get("objects", [])[:6]
        if isinstance(item, dict)
    ]
    return {
        "scene_type": str(normalized.get("scene_type", ""))[:200],
        "brief_spoken_kn": str(normalized.get("brief_spoken_kn", ""))[:1000],
        "objects": objects,
    }


def _saved_scene_identity_answer(
    question: str, scene: dict[str, Any], width: int, height: int,
) -> dict[str, Any] | None:
    normalized = re.sub(r"[^a-z0-9\u0c80-\u0cff]+", " ", question.casefold()).strip()
    generic_questions = {
        "what is this", "what s this", "what is it", "tell me what this is",
        "ಇದು ಏನು", "ಇದೇನು", "ಇದು ಏನು ಹೇಳಿ", "ಇದು ಏನು ಅಂತ ಹೇಳಿ",
    }
    answer = str(scene.get("brief_spoken_kn", "")).strip()
    if normalized not in generic_questions or not _valid_kannada_text(answer):
        return None
    evidence_box = None
    objects = scene.get("objects", [])
    if isinstance(objects, list) and objects and isinstance(objects[0], dict):
        evidence_box = _context_box(objects[0].get("box"))
    return {
        "answer_kn": answer, "warning_kn": "", "uncertainty_kn": "",
        "evidence": [{"box": evidence_box}] if evidence_box else [],
        "image_size": {"width": width, "height": height},
        "answer_source": "saved_semantic_scene",
    }


def _question_history(value: Any) -> list[dict[str, str]]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    turns = []
    for item in parsed[-MAX_QUESTION_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        question = re.sub(r"\s+", " ", str(item.get("question", ""))).strip()
        answer = re.sub(r"\s+", " ", str(item.get("answer_kn", ""))).strip()
        if question and answer:
            turns.append({
                "question": question[:MAX_QUESTION_CHARACTERS],
                "answer_kn": answer[:2000],
            })
    return turns


def _question_focus(value: Any, width: int, height: int) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    try:
        x, y, box_width, box_height = (float(parsed[key]) for key in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError):
        return None
    x, y = max(0.0, min(float(width), x)), max(0.0, min(float(height), y))
    box_width = max(0.0, min(float(width) - x, box_width))
    box_height = max(0.0, min(float(height) - y, box_height))
    if box_width <= 0 or box_height <= 0:
        return None
    return {"x": x, "y": y, "width": box_width, "height": box_height,
            "label": str(parsed.get("label", ""))[:120]}


def _openai_transcribe(audio: bytes, filename: str, media_type: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_READER_NOT_CONFIGURED")
    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {api_key}"},
        data={
            "model": OPENAI_TRANSCRIPTION_MODEL,
            "response_format": "json",
            "prompt": "The speaker may use Kannada, English, or both while asking about an image.",
        },
        files={"file": (filename or "question.webm", audio, media_type or "audio/webm")},
        timeout=45,
    )
    if response.status_code != 200:
        app.logger.warning("OpenAI transcription failed with HTTP %s", response.status_code)
        raise RuntimeError("OPENAI_TRANSCRIPTION_FAILED")
    transcript = re.sub(r"\s+", " ", str(response.json().get("text", ""))).strip()
    if not transcript:
        raise RuntimeError("OPENAI_TRANSCRIPTION_EMPTY")
    return transcript[:MAX_QUESTION_CHARACTERS]


def _openai_translate(text: str) -> dict[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_READER_NOT_CONFIGURED")
    schema = {
        "type": "object", "additionalProperties": False,
        "required": ["translation_kn"],
        "properties": {"translation_kn": {"type": "string"}},
    }
    payload = {
        "model": OPENAI_TRANSLATION_MODEL, "store": False,
        "reasoning": {"effort": "minimal"}, "max_output_tokens": 160,
        "input": [{"role": "user", "content": [{
            "type": "input_text", "text": (
                "Translate the English word or short visible label below into simple, natural Kannada "
                "for a low-literacy adult. Preserve numbers and joined units such as 110V, 50Hz, and "
                "2.0 HP, and explain the unit briefly in Kannada. Return only the requested structured "
                "field.\n\nVisible text:\n" + text
            ),
        }]}],
        "text": {"verbosity": "low", "format": {
            "type": "json_schema", "name": "villagelens_translation",
            "strict": True, "schema": schema,
        }},
    }
    response = requests.post(
        "https://api.openai.com/v1/responses", json=payload,
        headers={"Authorization": f"Bearer {api_key}"}, timeout=30,
    )
    if response.status_code != 200:
        app.logger.warning("OpenAI translation failed with HTTP %s", response.status_code)
        raise RuntimeError("OPENAI_TRANSLATION_FAILED")
    parsed = json.loads(_openai_output_text(response.json()))
    translation = str(parsed.get("translation_kn", "")).strip()
    if not _valid_kannada_text(translation):
        raise RuntimeError("OPENAI_TRANSLATION_INVALID_RESPONSE")
    return {"translation_kn": translation, "model": OPENAI_TRANSLATION_MODEL}


def _storage_bucket() -> Any:
    if not CAPTURE_BUCKET:
        return None
    from google.cloud import storage

    return storage.Client().bucket(CAPTURE_BUCKET)


def _store_capture(data: bytes, media_type: str, result: dict[str, Any]) -> bool:
    bucket = _storage_bucket()
    if bucket is None:
        return False
    capture_id = result["capture_id"]
    image_name = f"captures/{capture_id}/source"
    stored = dict(result)
    stored["retained"] = True
    stored["image_url"] = f"/api/captures/{capture_id}/image"
    bucket.blob(image_name).upload_from_string(data, content_type=media_type)
    bucket.blob(f"captures/{capture_id}/result.json").upload_from_string(
        json.dumps(stored, ensure_ascii=False, separators=(",", ":")),
        content_type="application/json; charset=utf-8",
    )
    return True


def _store_reader_evidence(capture_id: str, stage: int, result: dict[str, Any]) -> None:
    if not _valid_capture_id(capture_id) or (bucket := _storage_bucket()) is None:
        return
    bucket.blob(f"captures/{capture_id}/stage-{stage}.json").upload_from_string(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        content_type="application/json; charset=utf-8",
    )


def _stored_json(bucket: Any, name: str) -> dict[str, Any] | None:
    blob = bucket.blob(name)
    if not blob.exists():
        return None
    try:
        value = json.loads(blob.download_as_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        app.logger.warning("Ignoring invalid stored JSON at %s", name)
        return None


def _process_stored_capture(capture_id: str, tester_id: str) -> tuple[dict[int, dict[str, Any]], dict[int, str]]:
    bucket = _storage_bucket()
    if bucket is None:
        raise FileNotFoundError
    with _capture_processing_locks[capture_id]:
        capture = _stored_json(bucket, f"captures/{capture_id}/result.json")
        if capture is None or (
            tester_id and not _is_reviewer(tester_id) and capture.get("tester_id") != tester_id
        ):
            raise FileNotFoundError

        stages = {
            stage: value for stage in (2, 3)
            if (value := _stored_json(bucket, f"captures/{capture_id}/stage-{stage}.json")) is not None
            and (stage != 3 or _current_stage_three(value))
        }
        if 3 in stages:
            stages[3] = _normalize_stage_three(stages[3])
        missing = [stage for stage in (2, 3) if stage not in stages]
        errors: dict[int, str] = {}
        if 3 in missing and not os.environ.get("OPENAI_API_KEY", "").strip():
            missing.remove(3)
            errors[3] = "OPENAI_READER_NOT_CONFIGURED"
        if not missing:
            return stages, errors

        source = bucket.blob(f"captures/{capture_id}/source")
        if not source.exists():
            raise FileNotFoundError
        image, _ = _normalized_image(source.download_as_bytes())
        normalized = io.BytesIO()
        image.save(normalized, format="PNG")
        data = normalized.getvalue()

        def run(stage: int) -> dict[str, Any]:
            value = (_vision_reader(data, image.width, image.height) if stage == 2
                     else _openai_reader(data, "image/png", image.width, image.height))
            owner_id = str(capture.get("tester_id", "")).strip().lower()
            value["tester_id"] = (
                owner_id if TESTER_ID_PATTERN.fullmatch(owner_id)
                else tester_id or "unassigned"
            )
            _store_reader_evidence(capture_id, stage, value)
            return value

        if missing:
            with ThreadPoolExecutor(max_workers=len(missing)) as executor:
                futures = {executor.submit(run, stage): stage for stage in missing}
                for future in as_completed(futures):
                    stage = futures[future]
                    try:
                        stages[stage] = future.result()
                    except Exception as exc:
                        app.logger.exception("Stored reader stage %s failed for capture %s", stage, capture_id)
                        errors[stage] = str(exc) if isinstance(exc, RuntimeError) else f"STAGE_{stage}_UNAVAILABLE"
        return stages, errors


def _valid_capture_id(capture_id: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{32}", capture_id))


def _capture_quality_header() -> dict[str, Any]:
    raw = request.headers.get("X-VillageLens-Capture-Quality", "")
    if not raw or len(raw) > 1000:
        return {}
    try:
        supplied = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(supplied, dict):
        return {}
    quality: dict[str, Any] = {}
    for key in ("brightness", "dark_percent", "glare_percent", "sharpness", "motion"):
        value = supplied.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
            quality[key] = round(max(0.0, min(1000.0, float(value))), 2)
    if isinstance(supplied.get("auto_captured"), bool):
        quality["auto_captured"] = supplied["auto_captured"]
    return quality


def _speech_cache_name(text: str) -> str:
    identity = f"v1\0{KANNADA_TTS_VOICE}\0{text}".encode("utf-8")
    return f"speech/v1/{hashlib.sha256(identity).hexdigest()}.mp3"


def _synthesize_kannada(text: str) -> bytes:
    from google.cloud import texttospeech

    response = texttospeech.TextToSpeechClient().synthesize_speech(
        request={
            "input": texttospeech.SynthesisInput(text=text),
            "voice": texttospeech.VoiceSelectionParams(
                language_code="kn-IN", name=KANNADA_TTS_VOICE,
            ),
            "audio_config": texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.82,
            ),
        },
        timeout=20,
    )
    return bytes(response.audio_content)


@app.post("/api/translate")
def translate() -> Response | tuple[Response, int]:
    payload = request.get_json(silent=True)
    text = re.sub(r"\s+", " ", str(payload.get("text", ""))).strip() if isinstance(payload, dict) else ""
    if not text:
        return jsonify(error="TRANSLATION_TEXT_REQUIRED"), 400
    if len(text) > 80:
        return jsonify(error="TRANSLATION_TEXT_TOO_LONG"), 400
    if not re.search(r"[A-Za-z]", text):
        return jsonify(error="TRANSLATION_LANGUAGE_UNSUPPORTED"), 400
    try:
        return jsonify(_openai_translate(text)), 200
    except RuntimeError as exc:
        app.logger.exception("English-to-Kannada translation failed")
        return jsonify(error=str(exc)), 503


@app.post("/api/speech")
def speech() -> Response | tuple[Response, int]:
    payload = request.get_json(silent=True)
    text = re.sub(r"\s+", " ", str(payload.get("text", ""))).strip() if isinstance(payload, dict) else ""
    if not text:
        return jsonify(error="SPEECH_TEXT_REQUIRED"), 400
    if len(text) > MAX_SPEECH_CHARACTERS:
        return jsonify(error="SPEECH_TEXT_TOO_LONG"), 400
    if not re.search(r"[\u0c80-\u0cff]", text):
        return jsonify(error="SPEECH_LANGUAGE_UNSUPPORTED"), 400

    cache_name = _speech_cache_name(text)
    bucket = None
    try:
        bucket = _storage_bucket()
        if bucket is not None:
            blob = bucket.blob(cache_name)
            if blob.exists():
                audio = blob.download_as_bytes()
                response = make_response(audio)
                response.headers["Content-Type"] = blob.content_type or "audio/mpeg"
                response.headers["X-VillageLens-Speech-Cache"] = "hit"
                return response
    except Exception:
        app.logger.warning("Kannada speech cache read failed")

    try:
        audio = _synthesize_kannada(text)
        if not audio:
            raise RuntimeError("KANNADA_SPEECH_EMPTY")
    except Exception:
        app.logger.exception("Kannada speech synthesis failed")
        return jsonify(error="KANNADA_SPEECH_UNAVAILABLE"), 503

    if bucket is not None:
        try:
            blob = bucket.blob(cache_name)
            blob.cache_control = "private, max-age=31536000"
            blob.upload_from_string(audio, content_type="audio/mpeg")
        except Exception:
            app.logger.warning("Kannada speech cache write failed")
    response = make_response(audio)
    response.headers["Content-Type"] = "audio/mpeg"
    response.headers["X-VillageLens-Speech-Cache"] = "miss"
    return response


@app.get("/api/gallery")
def gallery() -> tuple[Response, int]:
    items: list[dict[str, Any]] = [
        {
            "id": "demo-i2", "label": "I2", "kind": "demo",
            "image_url": "/a/demo/i2.jpeg", "result_url": "/a/demo/i2-gold.json",
        },
        {
            "id": "demo-i1", "label": "I1", "kind": "demo",
            "image_url": "/a/demo/i1.jpeg", "result_url": "/a/demo/i1-scene.json",
        },
    ]
    try:
        bucket = _storage_bucket()
        if bucket is not None:
            stored: list[dict[str, Any]] = []
            blobs = list(bucket.list_blobs(prefix="captures/"))
            evidence = {
                (parts[1], int(match.group(1))): blob
                for blob in blobs
                if len(parts := blob.name.split("/")) == 3
                and (match := re.fullmatch(r"stage-([23])\.json", parts[2]))
                and _valid_capture_id(parts[1])
            }
            requested_tester_id = _tester_id()
            for blob in blobs:
                if not blob.name.endswith("/result.json"):
                    continue
                value = json.loads(blob.download_as_text(encoding="utf-8"))
                capture_id = value.get("capture_id", "")
                if not _valid_capture_id(capture_id):
                    continue
                if (
                    requested_tester_id
                    and not _is_reviewer(requested_tester_id)
                    and value.get("tester_id") != requested_tester_id
                ):
                    continue
                owner_id = str(value.get("tester_id", "")).strip().lower()
                verified_regions = VERIFIED_CAPTURE_REGIONS.get(capture_id, [])
                displayed_result = dict(value)
                if verified_regions:
                    displayed_result["verified_regions"] = verified_regions
                item = {
                    "id": capture_id,
                    "label": value.get("label") or "Captured page",
                    "capture_code": f"{(owner_id or 'UN').upper()}-{capture_id[:6].upper()}",
                    "kind": "capture",
                    "retained": True,
                    "captured_at": value.get("captured_at"),
                    "image_url": f"/api/captures/{capture_id}/image",
                    "result": displayed_result,
                    "tester_id": owner_id or "unassigned",
                    "tester_name": TESTER_NAMES.get(owner_id, ""),
                }
                if verified_regions:
                    item["verified_regions"] = verified_regions
                for stage in (2, 3):
                    if evidence_blob := evidence.get((capture_id, stage)):
                        try:
                            stage_value = json.loads(
                                evidence_blob.download_as_text(encoding="utf-8")
                            )
                            if stage != 3 or _current_stage_three(stage_value):
                                normalized = _normalize_stage_three(stage_value) if stage == 3 else stage_value
                                item[f"stage{stage}"] = normalized
                                if stage == 3:
                                    scene_type = str(normalized.get("scene_type", "")).strip()
                                    if scene_type:
                                        item["label"] = scene_type[:60]
                        except (TypeError, ValueError, json.JSONDecodeError):
                            app.logger.warning(
                                "Ignoring invalid stage %s evidence for capture %s",
                                stage, capture_id,
                            )
                stored.append(item)
            stored.sort(key=lambda item: item.get("captured_at") or "", reverse=True)
            items.extend(stored if _is_reviewer(requested_tester_id) else stored[:20])
    except Exception:
        app.logger.exception("Capture gallery is temporarily unavailable")
    return jsonify(
        schema="villagelens.gallery.v1", items=items,
        review_mode=_is_reviewer(_tester_id()),
    ), 200


@app.get("/api/captures/<capture_id>/image")
def captured_image(capture_id: str) -> Response | tuple[Response, int]:
    if not _valid_capture_id(capture_id):
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    try:
        bucket = _storage_bucket()
        if bucket is None:
            raise FileNotFoundError
        blob = bucket.blob(f"captures/{capture_id}/source")
        if not blob.exists():
            raise FileNotFoundError
        response = make_response(blob.download_as_bytes())
        response.headers["Content-Type"] = blob.content_type or "application/octet-stream"
        response.headers["Cache-Control"] = "private, max-age=3600"
        return response
    except FileNotFoundError:
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    except Exception:
        app.logger.exception("Stored capture could not be read")
        return jsonify(error="CAPTURE_STORAGE_UNAVAILABLE"), 503


@app.post("/api/captures/<capture_id>/process")
def process_captured_image(capture_id: str) -> tuple[Response, int]:
    if not _valid_capture_id(capture_id):
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    try:
        stages, errors = _process_stored_capture(capture_id, _tester_id())
        return jsonify(
            schema="villagelens.processing.v1",
            capture_id=capture_id,
            stages={str(stage): value for stage, value in stages.items()},
            errors={str(stage): error for stage, error in errors.items()},
            complete=all(stage in stages for stage in (2, 3)),
        ), 200
    except FileNotFoundError:
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        app.logger.exception("Stored capture processing failed for %s", capture_id)
        return jsonify(error="CAPTURE_PROCESSING_UNAVAILABLE"), 503


@app.post("/api/captures/<capture_id>/ask")
def ask_about_capture(capture_id: str) -> tuple[Response, int]:
    if not _valid_capture_id(capture_id):
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    payload = request.get_json(silent=True)
    question = re.sub(r"\s+", " ", str(payload.get("question", ""))).strip() if isinstance(payload, dict) else ""
    if not question:
        return jsonify(error="QUESTION_REQUIRED"), 400
    if len(question) > MAX_QUESTION_CHARACTERS:
        return jsonify(error="QUESTION_TOO_LONG"), 400
    try:
        bucket = _storage_bucket()
        if bucket is None:
            raise FileNotFoundError
        capture = _stored_json(bucket, f"captures/{capture_id}/result.json")
        tester_id = _tester_id()
        if capture is None or (
            tester_id and not _is_reviewer(tester_id) and capture.get("tester_id") != tester_id
        ):
            raise FileNotFoundError
        source = bucket.blob(f"captures/{capture_id}/source")
        if not source.exists():
            raise FileNotFoundError
        image, _ = _normalized_image(source.download_as_bytes())
        normalized = io.BytesIO()
        image.save(normalized, format="PNG")
        focus = _question_focus(payload.get("focus_box"), image.width, image.height)
        scene = _question_scene_context(
            _stored_json(bucket, f"captures/{capture_id}/stage-3.json")
        )
        answer = (None if focus else _saved_scene_identity_answer(
            question, scene, image.width, image.height,
        )) or _openai_question(
            normalized.getvalue(), "image/png", image.width, image.height, question,
            _question_history(payload.get("history")), focus, scene,
        )
        answer["question"] = question
        return jsonify(answer), 200
    except FileNotFoundError:
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    except Exception as exc:
        app.logger.exception("Spoken image question failed for %s", capture_id)
        error = str(exc) if isinstance(exc, RuntimeError) else "QUESTION_UNAVAILABLE"
        return jsonify(error=error), 503


@app.post("/api/captures/<capture_id>/ask-audio")
def ask_about_capture_audio(capture_id: str) -> tuple[Response, int]:
    if not _valid_capture_id(capture_id):
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    uploaded = request.files.get("audio")
    if uploaded is None:
        return jsonify(error="QUESTION_AUDIO_REQUIRED"), 400
    audio = uploaded.read(MAX_QUESTION_AUDIO_BYTES + 1)
    if not audio:
        return jsonify(error="QUESTION_AUDIO_REQUIRED"), 400
    if len(audio) > MAX_QUESTION_AUDIO_BYTES:
        return jsonify(error="QUESTION_AUDIO_TOO_LARGE"), 413
    try:
        bucket = _storage_bucket()
        if bucket is None:
            raise FileNotFoundError
        capture = _stored_json(bucket, f"captures/{capture_id}/result.json")
        tester_id = _tester_id()
        if capture is None or (
            tester_id and not _is_reviewer(tester_id) and capture.get("tester_id") != tester_id
        ):
            raise FileNotFoundError
        source = bucket.blob(f"captures/{capture_id}/source")
        if not source.exists():
            raise FileNotFoundError
        question = _openai_transcribe(
            audio, uploaded.filename or "question.webm", uploaded.mimetype or "audio/webm",
        )
        image, _ = _normalized_image(source.download_as_bytes())
        normalized = io.BytesIO()
        image.save(normalized, format="PNG")
        focus = _question_focus(request.form.get("focus_box"), image.width, image.height)
        scene = _question_scene_context(
            _stored_json(bucket, f"captures/{capture_id}/stage-3.json")
        )
        answer = (None if focus else _saved_scene_identity_answer(
            question, scene, image.width, image.height,
        )) or _openai_question(
            normalized.getvalue(), "image/png", image.width, image.height, question,
            _question_history(request.form.get("history")), focus, scene,
        )
        answer["question"] = question
        return jsonify(answer), 200
    except FileNotFoundError:
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    except Exception as exc:
        app.logger.exception("Spoken audio question failed for %s", capture_id)
        error = str(exc) if isinstance(exc, RuntimeError) else "QUESTION_UNAVAILABLE"
        return jsonify(error=error), 503


@app.post("/api/demos/<demo_id>/ask-audio")
def ask_about_demo_audio(demo_id: str) -> tuple[Response, int]:
    demo_files = {"demo-i1": "i1.jpeg", "demo-i2": "i2.jpeg"}
    filename = demo_files.get(demo_id)
    if filename is None:
        return jsonify(error="CAPTURE_NOT_FOUND"), 404
    uploaded = request.files.get("audio")
    if uploaded is None:
        return jsonify(error="QUESTION_AUDIO_REQUIRED"), 400
    audio = uploaded.read(MAX_QUESTION_AUDIO_BYTES + 1)
    if not audio:
        return jsonify(error="QUESTION_AUDIO_REQUIRED"), 400
    if len(audio) > MAX_QUESTION_AUDIO_BYTES:
        return jsonify(error="QUESTION_AUDIO_TOO_LARGE"), 413
    try:
        question = _openai_transcribe(
            audio, uploaded.filename or "question.webm", uploaded.mimetype or "audio/webm",
        )
        image, _ = _normalized_image((DEMO_ROOT / filename).read_bytes())
        normalized = io.BytesIO()
        image.save(normalized, format="PNG")
        answer = _openai_question(
            normalized.getvalue(), "image/png", image.width, image.height, question,
            _question_history(request.form.get("history")),
            _question_focus(request.form.get("focus_box"), image.width, image.height),
        )
        answer["question"] = question
        return jsonify(answer), 200
    except Exception as exc:
        app.logger.exception("Spoken audio question failed for demo %s", demo_id)
        error = str(exc) if isinstance(exc, RuntimeError) else "QUESTION_UNAVAILABLE"
        return jsonify(error=error), 503


@app.post("/api/events")
def usage_events() -> tuple[Response, int]:
    payload = request.get_json(silent=True)
    events = payload.get("events", []) if isinstance(payload, dict) else []
    if not isinstance(events, list) or not events or len(events) > 20:
        return jsonify(error="EVENTS_INVALID"), 400
    accepted = []
    for item in events:
        if not isinstance(item, dict) or item.get("name") not in USAGE_EVENTS:
            continue
        try:
            elapsed_ms = int(item.get("elapsed_ms", 0) or 0)
        except (TypeError, ValueError):
            elapsed_ms = 0
        accepted.append({
            "name": item["name"],
            "capture_id": item.get("capture_id") if _valid_capture_id(str(item.get("capture_id", ""))) else "",
            "ok": bool(item.get("ok", True)),
            "elapsed_ms": max(0, min(300_000, elapsed_ms)),
        })
    if not accepted:
        return jsonify(error="EVENTS_INVALID"), 400
    usage = {
        "tester_id": _tester_id() or "unassigned", "events": accepted,
    }
    app.logger.info("villagelens_usage %s", json.dumps(usage, separators=(",", ":")))
    if any(item["name"].startswith("question") for item in accepted):
        app.logger.warning("villagelens_mic %s", json.dumps(usage, separators=(",", ":")))
    return jsonify(accepted=len(accepted)), 202


@app.post("/api/capture")
def capture() -> tuple[Response, int]:
    media_type = (request.content_type or "").split(";", 1)[0].lower()
    if media_type not in ALLOWED_MEDIA_TYPES:
        return jsonify(error="CAPTURE_MEDIA_TYPE_UNSUPPORTED"), 415
    data = request.get_data(cache=False)
    if not data:
        return jsonify(error="CAPTURE_EMPTY"), 400
    source_sha256 = hashlib.sha256(data).hexdigest()
    try:
        image, normalized = _normalized_image(data)
        with tempfile.TemporaryDirectory(prefix="villagelens-capture-") as temporary:
            image_path = Path(temporary) / "normalized.png"
            ocr_image = image.copy()
            ocr_image.thumbnail(
                (LOCAL_OCR_MAX_EDGE, LOCAL_OCR_MAX_EDGE), Image.Resampling.LANCZOS,
            )
            ocr_image.save(image_path, format="PNG")
            words, lines, latency_ms = _tesseract(image_path)
            _scale_regions(
                words, lines,
                source_width=ocr_image.width, source_height=ocr_image.height,
                target_width=image.width, target_height=image.height,
            )
            words, lines = _select_regions(words, lines, width=image.width, height=image.height)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    requested_id = request.headers.get("X-VillageLens-Capture-ID", "")
    capture_id = requested_id if _valid_capture_id(requested_id) else uuid.uuid4().hex
    tester_id = _tester_id()
    capture_source = request.headers.get("X-VillageLens-Capture-Source", "").strip().lower()
    if capture_source not in {"guided-camera-v1", "file-camera", "shared-image"}:
        capture_source = "file-camera"
    capture_quality = _capture_quality_header()
    capture_code = f"{(tester_id or 'UN').upper()}-{capture_id[:6].upper()}"
    result = {
        "schema": "villagelens.capture.v1", "capture_id": capture_id,
        "captured_at": datetime.now(timezone.utc).isoformat(), "label": "Captured photo",
        "capture_code": capture_code, "capture_source": capture_source,
        "capture_quality": capture_quality,
        "source_sha256": source_sha256,
        "image_size": {"width": image.width, "height": image.height},
        "image_normalized": normalized, "stage": 1, "stage_state": "initial_reading",
        "reader": {
            "kind": "local_ocr", "languages": ["kan", "eng"],
            "model_sha256": MODEL_SHA256, "latency_ms": latency_ms,
            "input_size": {"width": ocr_image.width, "height": ocr_image.height},
        },
        "tester_id": tester_id or "unassigned",
        "words": words, "lines": lines, "retained": False,
        "image_url": f"/api/captures/{capture_id}/image",
    }
    try:
        result["retained"] = _store_capture(data, media_type, result)
    except Exception:
        app.logger.exception("Capture could not be retained")
    return jsonify(result), 200


@app.post("/api/read/<int:stage>")
def cloud_read(stage: int) -> tuple[Response, int]:
    if stage not in {2, 3}:
        return jsonify(error="READER_NOT_FOUND"), 404
    media_type = (request.content_type or "").split(";", 1)[0].lower()
    if media_type not in ALLOWED_MEDIA_TYPES:
        return jsonify(error="CAPTURE_MEDIA_TYPE_UNSUPPORTED"), 415
    data = request.get_data(cache=False)
    if not data:
        return jsonify(error="CAPTURE_EMPTY"), 400
    if stage == 3 and not os.environ.get("OPENAI_API_KEY", "").strip():
        return jsonify(error="OPENAI_READER_NOT_CONFIGURED"), 503
    try:
        image, _ = _normalized_image(data)
        normalized = io.BytesIO()
        image.save(normalized, format="PNG")
        payload = (_vision_reader(normalized.getvalue(), image.width, image.height) if stage == 2
                   else _openai_reader(normalized.getvalue(), "image/png", image.width, image.height))
        payload["tester_id"] = _tester_id() or "unassigned"
        _store_reader_evidence(request.headers.get("X-VillageLens-Capture-ID", ""), stage, payload)
        return jsonify(payload), 200
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        error = str(exc) if isinstance(exc, RuntimeError) else f"STAGE_{stage}_UNAVAILABLE"
        app.logger.exception("Reader stage %s failed", stage)
        return jsonify(error=error), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
