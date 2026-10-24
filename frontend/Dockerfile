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
CMD ["/bin/sh", "-c", "sed \"s/listen 8080;/listen ${PORT:-8080};/\" /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]
