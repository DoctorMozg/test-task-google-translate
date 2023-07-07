#!/bin/bash
set -e

MAX_REQUESTS=${MAX_REQUESTS:-200}
MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-40}

GUNICORN_ARGS=(
    -b 0.0.0.0:5000
    --preload
    --workers ${WEB_WORKERS:-4}
    --max-requests ${MAX_REQUESTS}
    --max-requests-jitter ${MAX_REQUESTS_JITTER}
    --timeout 120
    --worker-class uvicorn.workers.UvicornWorker
    -c app/utils/gunicorn.conf.py
    wsgi:app
)


server() {
  alembic upgrade head
  exec /usr/local/bin/gunicorn "${GUNICORN_ARGS[@]}"
}


tests() {
  sed -i s/DB_HOST=.*/DB_HOST=postgres/g pytest.ini
  sed -i s/DB_PORT=.*/DB_PORT=5432/g pytest.ini
  sed -i s/REDIS_HOST=.*/REDIS_HOST=redis/g pytest.ini
  sed -i s/REDIS_PORT=.*/REDIS_PORT=6379/g pytest.ini
  poetry install --no-interaction --no-ansi --with test
  pytest -x
}


case "$1" in
  server)
    shift
    server
    ;;
  tests)
    shift
    tests
    ;;
  *)
    exec "$@"
    ;;
esac
