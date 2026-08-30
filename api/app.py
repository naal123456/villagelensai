from __future__ import annotations

import csv
import hashlib
import io
import os
import subprocess
import tempfile
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, redirect, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPOSITORY_ROOT / "web"
TESSDATA_DIRECTORY = Path(
    os.environ.get("VILLAGELENS_TESSDATA_DIR", REPOSITORY_ROOT / "models" / "tessdata")
)
MAX_CAPTURE_BYTES = int(os.environ.get("VILLAGELENS_MAX_CAPTURE_BYTES", 15 * 1024 * 1024))
MAX_IMAGE_PIXELS = int(os.environ.get("VILLAGELENS_MAX_IMAGE_PIXELS", 25_000_000))
MAX_IMAGE_EDGE = int(os.environ.get("VILLAGELENS_MAX_IMAGE_EDGE", 4096))
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}
MODEL_SHA256 = {
    "kan": "bd31e6b6ae93271e3bcf5383d306d8eefbb91542937cd6d735a5930c970e61d8",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CAPTURE_BYTES


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
    if request.path.startswith("/api/"):
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


@app.get("/a/")
def tester_page() -> Response:
    return send_from_directory(WEB_ROOT / "a", "index.html")


@app.get("/healthz")
def health() -> tuple[Response, int]:
    missing = [
        language
        for language in MODEL_SHA256
        if not (TESSDATA_DIRECTORY / f"{language}.traineddata").is_file()
    ]
    status = 200 if not missing else 503
    return jsonify(status="ok" if not missing else "not_ready", missing_models=missing), status


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

    return jsonify({
        "schema": "villagelens.capture.v1", "capture_id": uuid.uuid4().hex,
        "source_sha256": source_sha256,
        "image_size": {"width": image.width, "height": image.height},
        "image_normalized": normalized, "stage": 1, "stage_state": "initial_reading",
        "reader": {
            "kind": "local_ocr", "languages": ["kan", "eng"],
            "model_sha256": MODEL_SHA256, "latency_ms": latency_ms,
        },
        "words": words, "lines": lines, "retained": False,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
