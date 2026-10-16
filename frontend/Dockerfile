# syntax=docker/dockerfile:1

# ---- build stage: Node only exists here ----
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- runtime stage: unprivileged nginx (uid 101, listens on 8080) ----
FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime
LABEL org.opencontainers.image.title="gearloop-frontend" \
      org.opencontainers.image.description="GearLoop lab equipment desk (React, served by nginx)"
USER root
RUN apk upgrade --no-cache
USER 101
# Where /api is proxied to. Compose: the `backend` service. Helm overrides it with the release's Service name.
ENV API_UPSTREAM=http://backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
