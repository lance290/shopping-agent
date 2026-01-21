# Production Dockerfile for Next.js 15 Applications
# Optimized for Railway and GCP Cloud Run deployment
# Multi-stage build for minimal final image size

# ============================================
# Stage 1: Dependencies
# ============================================
FROM node:20-alpine AS deps

WORKDIR /app

# Install libc6-compat for Alpine compatibility
RUN apk add --no-cache libc6-compat

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm i --frozen-lockfile

# ============================================
# Stage 2: Builder
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy application code
COPY . .

# Build arguments for Next.js public env vars (must be available at build time)
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL=/login
ARG NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
ARG NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
ARG NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \
    NEXT_PUBLIC_CLERK_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_URL \
    NEXT_PUBLIC_CLERK_SIGN_UP_URL=$NEXT_PUBLIC_CLERK_SIGN_UP_URL \
    NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL \
    NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=$NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL

# Build Next.js application
# This creates the .next directory
RUN pnpm run build

# ============================================
# Stage 3: Production Runner
# ============================================
FROM node:20-alpine AS runner

WORKDIR /app

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Set production environment
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME="0.0.0.0" \
    PORT=8080

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Set correct permissions
RUN chown -R nextjs:nodejs /app

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 8080

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Start Next.js server
CMD ["node", "server.js"]
