# FROM nginx:1.30.3
# COPY ./conf/nginx.server.conf /etc/nginx/nginx.conf

# RUN mkdir -p /var/www/hypertube_frontend
# RUN chown -R www-data:www-data var/www/hypertube_frontend/ 

# ENTRYPOINT ["nginx", "-g", "daemon off;"]

FROM node:20-alpine
WORKDIR /app
COPY volumes/frontend/package*.json ./
RUN npm install
# COPY volumes/frontend/ .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]