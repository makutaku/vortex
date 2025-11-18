# Multi-stage build for secure root-less vortex image
FROM python:3.13-slim AS builder

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

# Runtime stage - use minimal base image with supervisord
FROM python:3.13-slim

# Install runtime dependencies (supervisord instead of cron)
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create vortex user and directories early (before copying files)
RUN groupadd -g 1000 vortex \
    && useradd -u 1000 -g 1000 -m -r vortex \
    && mkdir -p /data /config /home/vortex/.config/vortex /home/vortex/logs \
    && chown -R vortex:vortex /data /config /home/vortex

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/vortex /usr/local/bin/

# Set working directory and switch to vortex user
WORKDIR /app
USER vortex

# Copy application source code from builder (as vortex user)
COPY --from=builder --chown=vortex:vortex /app/src /app/src
COPY --from=builder --chown=vortex:vortex /app/pyproject.toml /app/setup.py /app/

# Copy static assets and scripts (as vortex user)
COPY --chown=vortex:vortex docker/entrypoint.sh docker/ping.sh /app/
COPY --chown=vortex:vortex config/assets/ /app/config/assets/

# Make scripts executable
USER root
RUN chmod +x /app/entrypoint.sh /app/ping.sh
USER vortex

# Default environment variables (modern Vortex configuration)
ENV VORTEX_DEFAULT_PROVIDER=yahoo \
    VORTEX_OUTPUT_DIR=/data \
    VORTEX_SCHEDULE="0 8 * * *" \
    VORTEX_RUN_ON_STARTUP=true \
    VORTEX_DOWNLOAD_ARGS="--yes" \
    VORTEX_LOG_LEVEL=INFO \
    HOME=/home/vortex

# Volume mounts
VOLUME ["/data", "/config"]

# Container runs as vortex user consistently
# Uses supervisord for process management instead of system cron

# Use tini as init system with custom entrypoint
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]