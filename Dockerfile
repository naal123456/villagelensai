FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    VILLAGELENS_TESSDATA_DIR=/app/models/tessdata

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY web ./web
COPY models ./models

RUN useradd --create-home --uid 10001 villagelens \
    && chown -R villagelens:villagelens /app
USER villagelens

CMD exec gunicorn --bind :${PORT} --workers 1 --threads 8 --timeout 90 api.app:app
