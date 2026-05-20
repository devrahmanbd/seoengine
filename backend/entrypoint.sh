#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."

# Wait for PostgreSQL
until python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.close()
" 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up!"
echo "Running Alembic migrations..."
cd /app
python -m alembic upgrade head 2>/dev/null || echo "Alembic migration skipped (tables may already exist)"

echo "Running seed..."
python seed.py

mkdir -p /app/data

echo "Starting backend server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
