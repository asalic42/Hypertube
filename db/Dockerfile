FROM postgres:16-alpine

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql

ENV POSTGRES_USER=hypertube
ENV POSTGRES_PASSWORD=hypertube
ENV POSTGRES_DB=hypertube