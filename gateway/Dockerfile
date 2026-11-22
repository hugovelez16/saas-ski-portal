FROM nginx:1.25-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY docker-entrypoint.d/40-real-ip.sh /docker-entrypoint.d/40-real-ip.sh
RUN chmod +x /docker-entrypoint.d/40-real-ip.sh \
    && mkdir -p /etc/nginx/real-ip.d

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
