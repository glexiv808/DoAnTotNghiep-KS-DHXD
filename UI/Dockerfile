# Build stage for Frontend
FROM nginx:alpine

# Remove default nginx config
RUN rm -rf /usr/share/nginx/html/*

# Copy frontend static files to nginx
COPY assets /usr/share/nginx/html/assets
COPY pages /usr/share/nginx/html/pages

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
