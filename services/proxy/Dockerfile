FROM docker.io/library/nginx:1.30.3

COPY ./conf/nginx.proxy.conf /etc/nginx/nginx.conf
COPY ./conf/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# RUN mkdir -p /etc/nginx/certs
# COPY ./certs/* /etc/nginx/certs
RUN rm -rf /etc/nginx/sites-enabled/default


ENTRYPOINT ["/docker-entrypoint.sh"]