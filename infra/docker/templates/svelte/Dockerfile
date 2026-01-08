# Production Dockerfile for Svelte Applications
# Multi-stage build optimized for Railway and GCP Cloud Run

FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --frozen-lockfile && npm cache clean --force

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=production
RUN npm run build

FROM node:20-alpine AS runner
RUN apk add --no-cache dumb-init
RUN addgroup -g 1001 -S nodejs && adduser -S svelte -u 1001
WORKDIR /app
ENV NODE_ENV=production PORT=3000
COPY --from=builder --chown=svelte:nodejs /app/package.json ./
COPY --from=builder --chown=svelte:nodejs /app/build ./build
COPY --from=builder --chown=svelte:nodejs /app/node_modules ./node_modules
USER svelte
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); })"
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "build/index.js"]
