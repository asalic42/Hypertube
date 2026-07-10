-- Création des schémas
CREATE SCHEMA app_users;
CREATE SCHEMA auth;


-- Création des utilisateurs des microservices

CREATE USER app_users_service WITH PASSWORD 'app_users_password';
CREATE USER auth_service WITH PASSWORD 'auth_password';


-- Droits sur les schémas

GRANT USAGE, CREATE ON SCHEMA app_users TO app_users_service;
GRANT USAGE, CREATE ON SCHEMA auth TO auth_service;


-- Chaque service utilise son propre schéma par défaut

ALTER USER app_users_service
SET search_path TO app_users;

ALTER USER auth_service
SET search_path TO auth;


-- Empêche les services de créer dans public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;