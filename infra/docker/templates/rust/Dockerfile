# Production Dockerfile for Rust Applications
# Optimized for Railway and GCP Cloud Run deployment
# Multi-stage build for minimal final image size

# ============================================
# Stage 1: Builder
# ============================================
FROM rust:1.75-alpine AS builder

# Install build dependencies
RUN apk add --no-cache musl-dev

WORKDIR /app

# Copy Cargo files first for better caching
COPY Cargo.toml Cargo.lock* ./

# Create dummy main.rs to cache dependencies
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# Copy actual source code
COPY . .

# Build the application
# This will use cached dependencies from above
ARG BIN_NAME=app
RUN cargo build --release --bin ${BIN_NAME}

# ============================================
# Stage 2: Production Runner
# ============================================
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates libgcc

# Create non-root user for security
RUN addgroup -g 1001 -S rustapp && \
    adduser -S rustapp -u 1001

WORKDIR /app

# Copy binary from builder
ARG BIN_NAME=app
COPY --from=builder --chown=rustapp:rustapp /app/target/release/${BIN_NAME} ./app

# Switch to non-root user
USER rustapp

# Set environment variables
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT}/health || exit 1

# Start the application
CMD ["./app"]
