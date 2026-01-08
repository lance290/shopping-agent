# Production Dockerfile for Go Applications
# Optimized for Railway and GCP Cloud Run deployment
# Multi-stage build for minimal final image size

# ============================================
# Stage 1: Builder
# ============================================
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git ca-certificates

WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum* ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
# CGO_ENABLED=0 for static binary
# -ldflags="-w -s" to strip debug info and reduce size
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o main .

# ============================================
# Stage 2: Production Runner
# ============================================
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates

# Create non-root user for security
RUN addgroup -g 1001 -S goapp && \
    adduser -S goapp -u 1001

WORKDIR /app

# Copy binary from builder
COPY --from=builder --chown=goapp:goapp /app/main .

# Switch to non-root user
USER goapp

# Set environment variables
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT}/health || exit 1

# Start the application
CMD ["./main"]
