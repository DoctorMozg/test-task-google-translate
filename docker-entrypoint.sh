#!/bin/bash
set -e

MAX_REQUESTS=${MAX_REQUESTS:-100}
MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-50}

GUNICORN_ARGS=(
    -b 0.0.0.0:5000
    --preload
    --workers ${WEB_WORKERS:-4}
    --max-requests ${MAX_REQUESTS}
    --max-requests-jitter ${MAX_REQUESTS_JITTER}
    --timeout 120
    --worker-class uvicorn.workers.UvicornWorker
    wsgi:app
)


server() {
  alembic upgrade head
  exec /usr/local/bin/gunicorn "${GUNICORN_ARGS[@]}"
}


case "$1" in
  server)
    shift
    server
    ;;
  *)
    exec "$@"
    ;;
esac
