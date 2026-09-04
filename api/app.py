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
import time
import uuid
from collections import defaultdict
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
OPENAI_MODEL = os.environ.get("VILLAGELENS_OPENAI_MODEL", "gpt-5-mini")
KANNADA_TTS_VOICE = os.environ.get("VILLAGELENS_KANNADA_TTS_VOICE", "kn-IN-Standard-A")
ACCESS_COOKIE_NAME = "villagelens_access"
ACCESS_COOKIE_TTL_SECONDS = 30 * 24 * 60 * 60
MODEL_SHA256 = {
    "kan": "bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}
TESTER_ID_PATTERN = re.compile(r"a(?:10|[1-9])")
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


@app.after_request
def _response_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self)"
    if request.path.startswith("/api/") or request.path == "/access":
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
            response = make_response(redirect(destination, code=303))
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
required aria-label="Access code"><button type="submit">🔓</button></form></main></body></html>"""
    return make_response(page, 401 if request.method == "POST" else 200)


@app.get("/a/")
def tester_page() -> Response:
    tester_id = request.args.get("tester", "").strip().lower()
    if _access_configured() and not TESTER_ID_PATTERN.fullmatch(tester_id):
        return redirect("/access", code=302)
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
                "-l", "kan+eng", "--oem", "1", "--psm", "11",
                "-c", "tessedit_create_tsv=1",
            ],
            check=False, capture_output=True, text=True, timeout=LOCAL_OCR_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("LOCAL_OCR_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise RuntimeError("LOCAL_OCR_FAILED")
    words, lines = _parse_tsv(completed.stdout)
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
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                line_words: list[dict[str, Any]] = []
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
                    words.append(word); line_words.append(word)
                if not line_words:
                    continue
                line_id = f"vision-line-{len(lines) + 1:03d}"
                for word in line_words:
                    word["line_id"] = line_id
                left = min(word["box"]["x"] for word in line_words)
                top = min(word["box"]["y"] for word in line_words)
                right = max(word["box"]["x"] + word["box"]["width"] for word in line_words)
                bottom = max(word["box"]["y"] + word["box"]["height"] for word in line_words)
                lines.append({"id": line_id, "text": " ".join(word["text"] for word in line_words),
                              "box": {"x": left, "y": top, "width": right-left, "height": bottom-top},
                              "word_ids": [word["id"] for word in line_words]})
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


def _openai_reader(data: bytes, media_type: str, width: int, height: int) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_READER_NOT_CONFIGURED")
    started = time.monotonic()
    schema = {"type": "object", "additionalProperties": False,
              "required": ["words", "lines", "translations", "summary_kn"],
              "properties": {
                  "words": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                      "required": ["text", "box"], "properties": {"text": {"type": "string"},
                      "box": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}}}},
                  "lines": {"type": "array", "items": {"type": "string"}},
                  "translations": {"type": "array", "items": {"type": "object",
                      "additionalProperties": False, "required": ["source", "translation_kn"],
                      "properties": {"source": {"type": "string"},
                                     "translation_kn": {"type": "string"}}}},
                  "summary_kn": {"type": "string"}}}
    encoded = base64.b64encode(data).decode("ascii")
    payload = {"model": OPENAI_MODEL, "store": False, "reasoning": {"effort": "low"},
               "input": [{"role": "user", "content": [
                   {"type": "input_text", "text": "Read every clearly visible Kannada or English word exactly. Return words in reading order. For each word, box is [left,top,width,height] normalized from 0 to 1000. Do not guess unclear text. For each distinct clearly visible English word, return its source spelling exactly and a simple Kannada translation. summary_kn must be a faithful Kannada rendering of the visible content: preserve names, numbers, prices, and existing Kannada; do not infer facts, intent, or context beyond the image; say when text is unclear rather than guessing."},
                   {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}", "detail": "high"}]}],
               "text": {"format": {"type": "json_schema", "name": "villagelens_reading", "strict": True, "schema": schema}}}
    response = requests.post("https://api.openai.com/v1/responses", json=payload,
                             headers={"Authorization": f"Bearer {api_key}"}, timeout=75)
    if response.status_code != 200:
        app.logger.warning("OpenAI reader failed with HTTP %s", response.status_code)
        raise RuntimeError("OPENAI_READER_FAILED")
    parsed = json.loads(_openai_output_text(response.json()))
    words: list[dict[str, Any]] = []
    for candidate in parsed.get("words", []):
        box = candidate.get("box", [])
        if len(box) != 4 or not str(candidate.get("text", "")).strip():
            continue
        x, y, w, h = [max(0.0, min(1000.0, float(value))) for value in box]
        if w <= 0 or h <= 0 or x+w > 1020 or y+h > 1020:
            continue
        words.append({"id": f"openai-word-{len(words)+1:04d}", "text": candidate["text"].strip(),
                      "box": {"x": round(x*width/1000), "y": round(y*height/1000),
                              "width": round(w*width/1000), "height": round(h*height/1000)}})
    lines = _geometry_lines(words, "openai")
    model_lines = [str(text).strip() for text in parsed.get("lines", []) if str(text).strip()]
    if len(model_lines) == len(lines):
        for line, text in zip(lines, model_lines):
            line["text"] = text
    return {"schema": "villagelens.reader.v1", "stage": 3, "reader": "vision_language",
            "model": OPENAI_MODEL, "latency_ms": round((time.monotonic()-started)*1000),
            "image_size": {"width": width, "height": height}, "words": words, "lines": lines,
            "text": "\n".join(line["text"] for line in lines),
            "translations": parsed.get("translations", []),
            "summary_kn": parsed.get("summary_kn", "")}


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


def _valid_capture_id(capture_id: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{32}", capture_id))


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
                if requested_tester_id and value.get("tester_id") != requested_tester_id:
                    continue
                item = {
                    "id": capture_id,
                    "label": value.get("label") or "Captured page",
                    "kind": "capture",
                    "captured_at": value.get("captured_at"),
                    "image_url": f"/api/captures/{capture_id}/image",
                    "result": value,
                }
                for stage in (2, 3):
                    if evidence_blob := evidence.get((capture_id, stage)):
                        try:
                            item[f"stage{stage}"] = json.loads(
                                evidence_blob.download_as_text(encoding="utf-8")
                            )
                        except (TypeError, ValueError, json.JSONDecodeError):
                            app.logger.warning(
                                "Ignoring invalid stage %s evidence for capture %s",
                                stage, capture_id,
                            )
                stored.append(item)
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
    result = {
        "schema": "villagelens.capture.v1", "capture_id": capture_id,
        "captured_at": datetime.now(timezone.utc).isoformat(), "label": "Captured page",
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
