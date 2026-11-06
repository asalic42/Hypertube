#!/bin/bash
# Runs once, when the data directory is empty, from the postgres entrypoint.
# The service accounts and their passwords come from the .env file (the db
# service loads it): nothing secret is written here.
set -euo pipefail

for name in USERS_USER USERS_PASSWORD AUTH_USER AUTH_PASSWORD MOVIES_USER MOVIES_PASSWORD; do
    if [ -z "${!name:-}" ]; then
        echo "init: $name is not set. Add it to the .env file at the root of the project." >&2
        exit 1
    fi
done

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v users_user="$USERS_USER" -v users_password="$USERS_PASSWORD" \
    -v auth_user="$AUTH_USER" -v auth_password="$AUTH_PASSWORD" \
    -v movies_user="$MOVIES_USER" -v movies_password="$MOVIES_PASSWORD" <<'EOSQL'
-- Création des schémas
CREATE SCHEMA users;
CREATE SCHEMA auth;
CREATE SCHEMA movies;


-- Création des utilisateurs des microservices

CREATE USER :"users_user" WITH PASSWORD :'users_password';
CREATE USER :"auth_user" WITH PASSWORD :'auth_password';
CREATE USER :"movies_user" WITH PASSWORD :'movies_password';


-- Droits sur les schémas

GRANT USAGE, CREATE ON SCHEMA users TO :"users_user";
GRANT USAGE, CREATE ON SCHEMA auth TO :"auth_user";
GRANT USAGE, CREATE ON SCHEMA movies TO :"movies_user";


-- Chaque service utilise son propre schéma par défaut

ALTER USER :"users_user" SET search_path TO users;
ALTER USER :"auth_user" SET search_path TO auth;
ALTER USER :"movies_user" SET search_path TO movies;


-- Empêche les services de créer dans public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
EOSQL
