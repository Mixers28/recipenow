#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -r requirements-worker.txt

echo "Starting ARQ worker..."
python -m arq worker.jobs.WorkerSettings
