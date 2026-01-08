# SvelteKit Production Dockerfile
# Optimized for security and compliance (CASA/SOC 2/HIPAA friendly)
FROM node:18-alpine AS base

# ============================================
# Stage 1: Builder (with ALL dependencies)
# ============================================
FROM node:18-alpine AS builder
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install ALL dependencies (including devDependencies for build)
# SvelteKit needs Vite, adapter, and other dev deps to build
RUN npm ci && npm cache clean --force

# Copy source code
COPY . .

# Build the application
# NOTE: This template assumes @sveltejs/adapter-node
# For other adapters (static, cloudflare, vercel), modify accordingly
RUN npm run build

# Prune dev dependencies after build
RUN npm prune --production

# Production image, copy all the files and run
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 svelte

# Copy built application
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./package.json

# Copy production node_modules from builder (already pruned)
COPY --from=builder /app/node_modules ./node_modules

# Set ownership to non-root user
RUN chown -R svelte:nodejs /app
USER svelte

# Health check for compliance monitoring
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node healthcheck.js

# Expose port (use PORT environment variable for cloud platforms)
EXPOSE 8080

# Security headers and secure defaults
ENV PORT=8080
ENV ORIGIN=https://yourdomain.com

# Start the application
CMD ["node", "build"]
