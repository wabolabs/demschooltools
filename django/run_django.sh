#!/bin/bash
set -e

. ../set_env.sh

export DJANGO_SETTINGS_MODULE="demschooltools.settings_prod"

PID_FILE="${PID_FILE:-../dst-django.pid}"
LOG_FILE="${LOG_FILE:-../dst-django.log}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_PORT="${GUNICORN_PORT:-8000}"

# Run migrations and collect static files
uv run manage.py migrate --noinput
uv run manage.py collectstatic --noinput

# Install Playwright browser for PDF generation
uv run playwright install chromium

# Graceful restart using USR2 signal (zero-downtime if using preload)
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Sending USR2 to existing gunicorn master (PID $OLD_PID)..."
        kill -USR2 "$OLD_PID" || true
        sleep 2
        # Kill old worker gracefully
        kill -WINCH "$OLD_PID" 2>/dev/null || true
        sleep 2
        kill -TERM "$OLD_PID" 2>/dev/null || true
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Start fresh
nohup uv run --group prod gunicorn \
    --workers "$GUNICORN_WORKERS" \
    --threads 4 \
    --bind "0.0.0.0:$GUNICORN_PORT" \
    --pid "$PID_FILE" \
    --access-logfile - \
    --error-logfile - \
    demschooltools.wsgi >> "$LOG_FILE" 2>&1 &

echo "Gunicorn started (PID $(cat "$PID_FILE" 2>/dev/null || echo '?'))"
