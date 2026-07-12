FROM docker.io/library/postgres:16

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql

ENV POSTGRES_DB=hypertube
ENV POSTGRES_USER=hypertube
ENV POSTGRES_PASSWORD=hypertube