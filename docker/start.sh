#!/bin/sh
set -eu

python -m alembic upgrade head
python -m app.scripts.seed_admin

uvicorn app.main:app --host 127.0.0.1 --port 8000 &

exec nginx -g 'daemon off;'
