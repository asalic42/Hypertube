FROM docker.io/library/postgres:16

RUN mkdir -p /docker-entrypoint-initdb
RUN mkdir -p /etc/psql.conf
RUN mkdir -p /certs

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql
# COPY ./conf/pg_hba.conf /etc/psql.conf/pg_hba.conf
# COPY ./conf/postgresql.conf /etc/psql.conf/postgresql.conf
# COPY ./conf/pg_hba.conf /var/lib/postgresql/data/pg_hba.conf
# COPY ./conf/postgresql.conf /var/lib/postgresql/data/postgresql.conf

# COPY ./certs/* /certs


# RUN chown -R postgres:postgres /etc/psql.conf
RUN chown -R postgres:postgres /var/lib/postgresql/data
RUN rm -rf /var/lib/prostresql/data
# RUN chown -R postgres:postgres /certs/

ENV POSTGRES_DB=hypertube
ENV POSTGRES_USER=hypertube
ENV POSTGRES_PASSWORD=hypertube