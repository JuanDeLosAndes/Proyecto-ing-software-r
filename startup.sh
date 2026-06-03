#!/bin/bash
set -e

PORT=${PORT:-8000}
echo "=========================================="
echo "Iniciando FastAPI en el puerto $PORT"
echo "Archivo principal: main.py"
echo "Instancia de FastAPI: app"
echo "=========================================="

exec gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app \
    --bind 0.0.0.0:$PORT \
    --timeout 120