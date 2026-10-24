FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE_URL
ARG VITE_R2_DIRECT_UPLOADS=false
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_R2_DIRECT_UPLOADS=${VITE_R2_DIRECT_UPLOADS}
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
EXPOSE 8080
CMD ["/bin/sh", "-c", "test -n \"$API_PRIVATE_DOMAIN\" || { echo 'API_PRIVATE_DOMAIN is required' >&2; exit 1; }; DNS_RESOLVER=\"$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)\"; case \"$DNS_RESOLVER\" in *:*) DNS_RESOLVER=\"[$DNS_RESOLVER]\" ;; esac; test -n \"$DNS_RESOLVER\" || { echo 'No DNS resolver found in /etc/resolv.conf' >&2; exit 1; }; sed \"s|listen 8080;|listen ${PORT:-8080};|; s|__API_PRIVATE_DOMAIN__|${API_PRIVATE_DOMAIN}|g; s|__RAILWAY_DNS_RESOLVER__|${DNS_RESOLVER}|g\" /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
