# Multi-stage build for efficient bc-utils image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.cargo/bin/uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN uv pip install -e .

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Create app user
RUN useradd -m -r bcutils && \
    mkdir -p /app /data /config && \
    chown -R bcutils:bcutils /app /data /config

# Set working directory
WORKDIR /app

# Copy application files
COPY --from=builder /app/src /app/src
COPY docker/entrypoint.sh /app/
COPY docker/ping.sh /app/
COPY assets/ /app/assets/

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/ping.sh

# Default environment variables
ENV BCU_PROVIDER=barchart \
    BCU_OUTPUT_DIR=/data \
    BCU_CONFIG_DIR=/config \
    BCU_ASSETS_FILE=/config/assets.json \
    BCU_SCHEDULE="0 8 * * *" \
    BCU_RUN_ON_STARTUP=True \
    BCU_DOWNLOAD_ARGS=""

# Volume mounts
VOLUME ["/data", "/config"]

# Switch to app user
USER bcutils

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]