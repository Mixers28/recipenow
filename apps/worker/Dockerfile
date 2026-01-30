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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY . .

# Run ARQ worker
CMD ["arq", "worker.WorkerSettings"]
