FROM nginx:1.30.3
COPY ./conf/nginx.proxy.conf /etc/nginx/nginx.conf

ENTRYPOINT ["nginx", "-g", "daemon off;"]