# syntax=docker/dockerfile:1
# Standalone service — build context is this directory:
#   docker build -t aios-frontend .
FROM node:22-slim AS base
ENV NODE_ENV=production
RUN groupadd --system appuser && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser

FROM base AS builder
WORKDIR /build
# Full (non-production) install for the build step: next build needs
# devDependencies (typescript, tailwind, eslint types, etc.).
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM base AS runtime
WORKDIR /app
COPY --from=builder /build/package.json /build/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=builder /build/.next ./.next
COPY --from=builder /build/public ./public
COPY --from=builder /build/next.config.mjs ./next.config.mjs
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["npm", "start"]
