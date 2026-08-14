#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose-dev.yml}"
DB_NAME="${DB_NAME:-hypertube}"
DB_USER="${DB_USER:-hypertube}"
DB_PASSWORD="${DB_PASSWORD:-hypertube}"
TEST_DB_USER="${TEST_DB_USER:-users_test}"
TEST_DB_PASSWORD="${TEST_DB_PASSWORD:-users_password}"
TEST_TARGET="${TEST_TARGET:-users_app.tests}"

if ! docker compose -f "$COMPOSE_FILE" ps db >/dev/null 2>&1; then
  docker compose -f "$COMPOSE_FILE" up -d db
fi

# Ensure a dedicated PostgreSQL role exists for running Django tests and has access
# to the project database schema used by the migration tracker and the test DB.
docker compose -f "$COMPOSE_FILE" exec -T db \
  psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${TEST_DB_USER}') THEN
    CREATE ROLE ${TEST_DB_USER} WITH LOGIN PASSWORD '${TEST_DB_PASSWORD}' CREATEDB;
  ELSE
    ALTER ROLE ${TEST_DB_USER} WITH LOGIN PASSWORD '${TEST_DB_PASSWORD}' CREATEDB;
  END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${TEST_DB_USER};
GRANT USAGE, CREATE ON SCHEMA public TO ${TEST_DB_USER};
GRANT USAGE, CREATE ON SCHEMA users TO ${TEST_DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${TEST_DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${TEST_DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA users TO ${TEST_DB_USER};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA users TO ${TEST_DB_USER};
ALTER ROLE ${TEST_DB_USER} SET search_path TO public, users;
SQL

docker compose -f "$COMPOSE_FILE" run --rm \
  -e DB_NAME="$DB_NAME" \
  -e DB_HOST=db \
  -e DB_PORT=5432 \
  -e USERS_USER="${TEST_DB_USER}" \
  -e USERS_PASSWORD="${TEST_DB_PASSWORD}" \
  users python manage.py test "${TEST_TARGET}" "$@"
