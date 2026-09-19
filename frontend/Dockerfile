FROM nginx:1.27-alpine
COPY softphone-test.html /usr/share/nginx/html/index.html
COPY dashboard.html /usr/share/nginx/html/dashboard.html
COPY sip.min.js /usr/share/nginx/html/sip.min.js
COPY nginx.spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
