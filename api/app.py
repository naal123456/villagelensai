from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}
CAPTURE_BUCKET = os.environ.get("VILLAGELENS_CAPTURE_BUCKET", "")
ACCESS_COOKIE_NAME = "villagelens_access"
ACCESS_COOKIE_TTL_SECONDS = 30 * 24 * 60 * 60
MODEL_SHA256 = {
    "kan": "bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}
DEMO_ASSETS = {
    "i1.jpeg", "i1-scene.json", "i2.jpeg", "i2-scene.json", "i2-gold.json",
}

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CAPTURE_BYTES
app.config["VILLAGELENS_ACCESS_CODE"] = os.environ.get("VILLAGELENS_ACCESS_CODE", "").strip()
app.config["VILLAGELENS_SESSION_SECRET"] = os.environ.get("VILLAGELENS_SESSION_SECRET", "")


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


def _has_access() -> bool:
    if not _access_configured():
        return not (
            app.config.get("VILLAGELENS_ACCESS_CODE")
            or app.config.get("VILLAGELENS_SESSION_SECRET")
        )
    try:
        issued, signature = request.cookies.get(ACCESS_COOKIE_NAME, "").split(".", 1)
        age = int(time.time()) - int(issued)
    except (TypeError, ValueError):
        return False
    return (
        -60 <= age <= ACCESS_COOKIE_TTL_SECONDS
        and hmac.compare_digest(signature, _access_signature(issued))
    )


@app.before_request
def _require_access() -> Response | tuple[Response, int] | None:
    if request.path in {"/access", "/health", "/healthz"} or _has_access():
        return None
    if request.path.startswith("/api/"):
        return jsonify(error="ACCESS_REQUIRED"), 401
    return redirect("/access", code=302)


def _allowed_origins() -> set[str]:
    return {
        value.strip()
        for value in os.environ.get("VILLAGELENS_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    }


@app.after_request
def _response_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self)"
    if request.path.startswith("/api/") or request.path == "/access":
        response.headers["Cache-Control"] = "no-store"
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
    return redirect("/a/", code=302)


@app.route("/access", methods=["GET", "POST"])
def access() -> Response:
    if not _access_configured():
        return redirect("/a/", code=302)
    failed = False
    if request.method == "POST":
        submitted = request.form.get("code", "").strip()
        expected = _access_code()
        if submitted and hmac.compare_digest(submitted, expected):
            response = make_response(redirect("/a/", code=303))
            response.set_cookie(
                ACCESS_COOKIE_NAME,
                _access_token(),
                max_age=ACCESS_COOKIE_TTL_SECONDS,
                secure=True,
                httponly=True,
                samesite="Lax",
                path="/",
            )
            return response
        failed = True
    message = "ಕೋಡ್ ಸರಿಯಾಗಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ." if failed else "ಪ್ರವೇಶ ಕೋಡ್ ನಮೂದಿಸಿ"
    page = f"""<!doctype html>
<html lang="kn"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="theme-color" content="#101418"><title>VillageLensAI Access</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#101418;
color:#f5f7fa;font-family:system-ui,sans-serif}}main{{width:min(92vw,420px);text-align:center}}
label{{display:block;font-size:1.35rem;margin:1rem}}input,button{{width:100%;min-height:58px;
border-radius:12px;font-size:1.4rem}}input{{padding:0 14px;border:2px solid #64717d}}
button{{margin-top:14px;border:0;background:#168447;color:white;font-weight:700}}</style></head>
<body><main><h1>VillageLensAI</h1><form method="post" action="/access">
<label for="code">{message}<br><small>Access code</small></label>
<input id="code" name="code" type="password" autocomplete="one-time-code"
required autofocus aria-label="Access code"><button type="submit">🔓</button></form></main></body></html>"""
    return make_response(page, 401 if failed else 200)


@app.get("/a/")
def tester_page() -> Response:
    return send_from_directory(WEB_ROOT / "a", "index.html")


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
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t"):
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


def _tesseract(image_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [
                "tesseract", str(image_path), "stdout", "--tessdata-dir", str(TESSDATA_DIRECTORY),
                "-l", "kan+eng", "--oem", "1", "--psm", "11",
                "-c", "tessedit_create_tsv=1",
            ],
            check=False, capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("LOCAL_OCR_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise RuntimeError("LOCAL_OCR_FAILED")
    words, lines = _parse_tsv(completed.stdout)
    return words, lines, round((time.monotonic() - started) * 1000)


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


def _valid_capture_id(capture_id: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{32}", capture_id))


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
            for blob in bucket.list_blobs(prefix="captures/"):
                if not blob.name.endswith("/result.json"):
                    continue
                value = json.loads(blob.download_as_text(encoding="utf-8"))
                capture_id = value.get("capture_id", "")
                if not _valid_capture_id(capture_id):
                    continue
                stored.append({
                    "id": capture_id,
                    "label": value.get("label") or "Captured page",
                    "kind": "capture",
                    "captured_at": value.get("captured_at"),
                    "image_url": f"/api/captures/{capture_id}/image",
                    "result": value,
                })
            stored.sort(key=lambda item: item.get("captured_at") or "", reverse=True)
            items.extend(stored[:20])
    except Exception:
        app.logger.exception("Capture gallery is temporarily unavailable")
    return jsonify(schema="villagelens.gallery.v1", items=items), 200


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
            image.save(image_path, format="PNG", optimize=True)
            words, lines, latency_ms = _tesseract(image_path)
            words, lines = _select_regions(words, lines, width=image.width, height=image.height)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    capture_id = uuid.uuid4().hex
    result = {
        "schema": "villagelens.capture.v1", "capture_id": capture_id,
        "captured_at": datetime.now(timezone.utc).isoformat(), "label": "Captured page",
        "source_sha256": source_sha256,
        "image_size": {"width": image.width, "height": image.height},
        "image_normalized": normalized, "stage": 1, "stage_state": "initial_reading",
        "reader": {
            "kind": "local_ocr", "languages": ["kan", "eng"],
            "model_sha256": MODEL_SHA256, "latency_ms": latency_ms,
        },
        "words": words, "lines": lines, "retained": False,
        "image_url": f"/api/captures/{capture_id}/image",
    }
    try:
        result["retained"] = _store_capture(data, media_type, result)
    except Exception:
        app.logger.exception("Capture could not be retained")
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
