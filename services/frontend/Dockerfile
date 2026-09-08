# syntax=docker/dockerfile:1
# Multi-stage build for the OpenGrow frontend.
#   target: dev     — hot-reload dev server (used by docker-compose.lite.yml)
#   target: runner  — minimal production image (Next standalone output)

FROM node:22-bookworm-slim AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# ---- deps ----
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# ---- dev (hot reload) ----
FROM base AS dev
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npx", "next", "dev", "-H", "0.0.0.0", "-p", "3000", "--turbopack"]

# ---- build (production) ----
FROM base AS build
# NEXT_PUBLIC_* is inlined into the client bundle at build time; compose passes
# these as build args so the prod image bakes the right values.
ARG NEXT_PUBLIC_API_BASE=""
ARG NEXT_PUBLIC_SITE_URL=""
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV NODE_ENV=production
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runner (production, non-root, standalone) ----
FROM base AS runner
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
RUN groupadd -r nodejs && useradd -r -g nodejs nextjs
COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
