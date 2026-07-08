FROM nginx:1.30.3

COPY ./conf/nginx.proxy.conf /etc/nginx/nginx.conf

RUN mkdir -p /etc/nginx/certs
# COPY ./certs/* /etc/nginx/certs
RUN rm -rf /etc/nginx/sites-enabled/default


ENTRYPOINT ["nginx", "-g", "daemon off;"]