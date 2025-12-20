# Multi-stage Dockerfile for flac-detective
# Production-ready with minimal image size and security best practices

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Stage 2: Runtime
FROM python:3.11-slim

LABEL org.opencontainers.image.title="flac-detective"
LABEL org.opencontainers.image.description="Advanced FLAC audio file analysis and repair tool"
LABEL org.opencontainers.image.url="https://github.com/guillainm/flac-detective"
LABEL org.opencontainers.image.source="https://github.com/guillainm/flac-detective"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash flacuser

WORKDIR /app

# Install runtime dependencies (flac decoder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    flac \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Create directory for audio files with proper permissions
RUN mkdir -p /data && chown -R flacuser:flacuser /data

# Switch to non-root user
USER flacuser

# Set working directory to data volume
WORKDIR /data

# Default entrypoint
ENTRYPOINT ["flac-detective"]

# Default command: show help
CMD ["--help"]
