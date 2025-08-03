# Multi-stage build for efficient vortex image
FROM python:3.11-slim AS builder

# Install build dependencies in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove curl

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files for dependency resolution
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/

# Install dependencies and application in single layer for better optimization
RUN uv pip install --system --no-cache-dir -e .

# Runtime stage - use minimal base image
FROM python:3.11-slim

# Install runtime dependencies and clean up in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed packages from builder (more selective copying)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/vortex /usr/local/bin/

# Set working directory early
WORKDIR /app

# Copy application source code from builder
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/setup.py /app/

# Copy static assets and scripts
COPY docker/entrypoint.sh docker/ping.sh /app/
COPY assets/ /app/assets/

# Create directories, user, and set permissions in single layer
RUN mkdir -p /data /config \
    && useradd -m -r vortex \
    && chown -R vortex:vortex /app /data /config \
    && chmod +x /app/entrypoint.sh /app/ping.sh

# Default environment variables (modern Vortex configuration)
ENV VORTEX_DEFAULT_PROVIDER=yahoo \
    VORTEX_OUTPUT_DIR=/data \
    VORTEX_SCHEDULE="0 8 * * *" \
    VORTEX_RUN_ON_STARTUP=true \
    VORTEX_DOWNLOAD_ARGS="--yes" \
    VORTEX_LOG_LEVEL=INFO

# Volume mounts
VOLUME ["/data", "/config"]

# Stay as root for cron and permissions
# USER vortex  # Keep as root for cron functionality

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]