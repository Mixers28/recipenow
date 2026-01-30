FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PaddleOCR + rotation detection
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    tesseract-ocr \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY apps/worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy worker entrypoints
COPY apps/worker/worker.py /app/worker.py
COPY apps/worker/jobs.py /app/jobs.py

# Copy shared packages + API code used by jobs
COPY packages /app/packages
COPY apps/api /app/apps/api

# Run ARQ worker
CMD ["arq", "worker.WorkerSettings"]
