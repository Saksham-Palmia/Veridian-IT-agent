# Frontend Nginx Container
FROM nginx:alpine

# Copy custom Nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy frontend static files
COPY frontend/employee /usr/share/nginx/html/employee
COPY frontend/admin /usr/share/nginx/html/admin

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

