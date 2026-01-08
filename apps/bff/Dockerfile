# Production Dockerfile for Fastify Applications
# Multi-stage build optimized for Railway and GCP Cloud Run

FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production --frozen-lockfile && npm cache clean --force

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json tsconfig.json ./
RUN npm ci --frozen-lockfile
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
RUN apk add --no-cache dumb-init
RUN addgroup -g 1001 -S nodejs && adduser -S fastify -u 1001
WORKDIR /app
ENV NODE_ENV=production PORT=8080
COPY --from=deps --chown=fastify:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=fastify:nodejs /app/dist ./dist
COPY --from=builder --chown=fastify:nodejs /app/package.json ./
USER fastify
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:8080/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); })"
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/index.js"]
