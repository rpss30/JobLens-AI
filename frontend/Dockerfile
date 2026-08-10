# Production image for the Next.js frontend. Three stages keep the runtime
# image to the standalone server plus its static assets: no npm, no lockfile,
# and no build-time dependencies.

FROM node:24-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

FROM node:24-alpine AS builder

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Pages read the API through searchParams and force-dynamic, so nothing is
# prerendered and the build does not need a reachable backend.
RUN npm run build

FROM node:24-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
# server.js binds to this; without it the server listens on localhost only and
# Caddy cannot reach it across the Docker network.
ENV HOSTNAME=0.0.0.0

# .next/standalone carries its own trimmed node_modules and server.js. Static
# assets are not included in it and have to be copied alongside.
# If a public/ directory is ever added, copy it into ./public here too.
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

CMD ["node", "server.js"]
