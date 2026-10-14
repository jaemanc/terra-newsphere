FROM node:22.16.0-bookworm-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=terra_ca,target=/tmp/terra_ca.crt \
    if [ -s /tmp/terra_ca.crt ]; then export NODE_EXTRA_CA_CERTS=/tmp/terra_ca.crt; fi \
    && npm ci
COPY frontend ./
ARG VITE_CESIUM_ION_TOKEN=""
ARG VITE_OSM_TILE_URL="https://tile.openstreetmap.org/"
RUN npm run build

FROM nginx:1.30.5-alpine
COPY frontend/nginx-main.conf /etc/nginx/nginx.conf
COPY frontend/nginx.conf /etc/nginx/terra-template.conf
COPY frontend/start.sh /app/frontend-start.sh
COPY --from=build /app/dist /usr/share/nginx/html
USER 101:101
ENTRYPOINT ["sh", "/app/frontend-start.sh"]
EXPOSE 8080
