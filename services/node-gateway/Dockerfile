# syntax=docker/dockerfile:1.7
# Multi-arch: amd64 + arm64 via node:22-slim (official)

FROM node:26-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json* ./
RUN npm ci --omit=optional

# ---- dev ----
FROM base AS dev
RUN npm i -D tsx typescript @types/node
COPY . .
RUN groupadd -r app --gid 1001 && useradd -r -g app --uid 1001 -m -d /home/app app \
    && chown -R app:app /app
USER app
EXPOSE 3001
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD curl -sf http://localhost:3001/ready || exit 1
CMD ["npm", "run", "dev"]

# ---- build ----
FROM base AS build
COPY . .
RUN npm run build

# ---- prod ----
FROM node:26-slim AS prod
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev --omit=optional
COPY --from=build /app/dist ./dist
RUN groupadd -r app --gid 1001 && useradd -r -g app --uid 1001 -m -d /home/app app \
    && chown -R app:app /app
USER app
EXPOSE 3001
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD curl -sf http://localhost:3001/ready || exit 1
CMD ["node", "dist/server.js"]
