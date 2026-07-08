FROM nginx:1.30.3

RUN mkdir -p /var/www/hypertube_frontend
RUN chown -R www-data:www-data var/www/hypertube_frontend/ 

RUN mkdir -p /etc/nginx/certs

COPY conf/nginx.server.conf /etc/nginx/nginx.conf
COPY certs/* /etc/nginx/certs

RUN rm -rf /etc/nginx/sites-enabled/default

ENTRYPOINT ["nginx", "-g", "daemon off;"]