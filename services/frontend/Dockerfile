FROM docker.io/library/nginx:1.30.3
COPY ./conf/nginx.server.conf /etc/nginx/nginx.conf

RUN mkdir -p /var/www/hypertube_frontend
RUN chown -R www-data:www-data var/www/hypertube_frontend/ 

ENTRYPOINT ["nginx", "-g", "daemon off;"]