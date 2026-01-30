#!/usr/bin/env bash
set -e

echo "Starting server on PORT=$PORT"
gunicorn wsgi:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 180
