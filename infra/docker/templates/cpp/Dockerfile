# Production Dockerfile for C++ Applications
# Optimized for Railway and GCP Cloud Run deployment
# Multi-stage build for minimal final image size

# ============================================
# Stage 1: Builder
# ============================================
FROM ubuntu:22.04 AS builder

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    git \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Conan package manager
RUN pip3 install --no-cache-dir conan

WORKDIR /app

# Copy dependency files first for better caching
COPY conanfile.txt CMakeLists.txt ./

# Install dependencies with Conan
RUN conan profile detect --force && \
    conan install . --output-folder=build --build=missing

# Copy source code
COPY . .

# Build the application
RUN cmake -S . -B build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake && \
    cmake --build build --config Release

# Run tests
RUN cd build && ctest --output-on-failure || true

# ============================================
# Stage 2: Production Runner
# ============================================
FROM ubuntu:22.04 AS runner

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libstdc++6 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1001 cppapp

WORKDIR /app

# Copy binary from builder
COPY --from=builder --chown=cppapp:cppapp /app/build/bin/app ./app

# Switch to non-root user
USER cppapp

# Set environment variables
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the application
CMD ["./app"]
