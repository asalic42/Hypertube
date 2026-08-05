FROM docker.io/library/postgres:16

RUN mkdir -p /docker-entrypoint-initdb
RUN mkdir -p /etc/postgresql
RUN mkdir -p /certs

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql
COPY ./conf/postgresql.conf /etc/postgresql/postgresql.conf
COPY ./conf/pg_hba.conf /etc/postgresql/pg_hba.conf
COPY ./certs/* /certs
RUN chown postgres:postgres /certs/*
RUN chmod 600  /certs/*

CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]