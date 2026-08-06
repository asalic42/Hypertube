-- Création des schémas
CREATE SCHEMA users;
CREATE SCHEMA auth;
CREATE SCHEMA movies;


-- Création des utilisateurs des microservices

CREATE USER users_service WITH PASSWORD 'users_password';
CREATE USER auth_service WITH PASSWORD 'auth_password';
CREATE USER movies_service WITH PASSWORD 'movies_password';


-- Droits sur les schémas

GRANT USAGE, CREATE ON SCHEMA users TO users_service;
GRANT USAGE, CREATE ON SCHEMA auth TO auth_service;
GRANT USAGE, CREATE ON SCHEMA movies TO movies_service;


-- Chaque service utilise son propre schéma par défaut

ALTER USER users_service
SET search_path TO users;

ALTER USER auth_service
SET search_path TO auth;

ALTER USER movies_service
SET search_path TO movies;


-- Empêche les services de créer dans public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;