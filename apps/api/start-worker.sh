#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -r requirements-worker.txt

echo "Starting ARQ worker..."
# Set PYTHONPATH to project root so imports work
export PYTHONPATH=/app:$PYTHONPATH
python -m arq worker.jobs.WorkerSettings
