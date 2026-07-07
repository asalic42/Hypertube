-- Création des schémas
CREATE SCHEMA app_users;


-- Création des utilisateurs des microservices

CREATE USER app_users_service WITH PASSWORD 'app_users_password';


-- Droits sur les schémas

GRANT USAGE, CREATE ON SCHEMA app_users TO app_users_service;


-- Chaque service utilise son propre schéma par défaut

ALTER USER app_users_service
SET search_path TO app_users;


-- Empêche les services de créer dans public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;