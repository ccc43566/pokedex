#!/usr/bin/env sh
set -eu
alembic upgrade head
exec uvicorn pokedex_api.main:app --host 0.0.0.0 --port 8000
