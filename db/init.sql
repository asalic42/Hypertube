-- Création des schémas
CREATE SCHEMA auth;
CREATE SCHEMA user_service;
CREATE SCHEMA movie;
CREATE SCHEMA torrent;
CREATE SCHEMA watch;


-- Création des utilisateurs des microservices

CREATE USER auth_service WITH PASSWORD 'auth_password';
CREATE USER user_service WITH PASSWORD 'user_password';
CREATE USER movie_service WITH PASSWORD 'movie_password';
CREATE USER torrent_service WITH PASSWORD 'torrent_password';
CREATE USER watch_service WITH PASSWORD 'watch_password';


-- Droits sur les schémas

GRANT USAGE, CREATE ON SCHEMA auth TO auth_service;

GRANT USAGE, CREATE ON SCHEMA user_service TO user_service;

GRANT USAGE, CREATE ON SCHEMA movie TO movie_service;

GRANT USAGE, CREATE ON SCHEMA torrent TO torrent_service;

GRANT USAGE, CREATE ON SCHEMA watch TO watch_service;


-- Chaque service utilise son propre schéma par défaut

ALTER USER auth_service
SET search_path TO auth;

ALTER USER user_service
SET search_path TO user_service;

ALTER USER movie_service
SET search_path TO movie;

ALTER USER torrent_service
SET search_path TO torrent;

ALTER USER watch_service
SET search_path TO watch;


-- Empêche les services de créer dans public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;