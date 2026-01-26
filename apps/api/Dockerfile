FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PaddleOCR, OCR preprocessing, and database clients
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

# Copy application code
COPY . .

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# In docker-compose.yml (infra/docker-compose.yml):
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    command: ollama serve

# API connects to: http://ollama:11434 (internal Docker network)