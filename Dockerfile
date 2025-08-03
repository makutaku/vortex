# Multi-stage build for efficient bc-utils image
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml setup.py README.md ./
COPY src/ ./src/

# Install dependencies using uv directly
RUN uv pip install --system -e .

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source code
COPY --from=builder /app/pyproject.toml /app/setup.py /app/
COPY --from=builder /app/src /app/src

# Create app user and ensure data directories exist
RUN useradd -m -r bcutils && \
    mkdir -p /app /data /config /app/data && \
    chown -R bcutils:bcutils /app /data /config

# Set working directory
WORKDIR /app

# Copy application files
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

# Stay as root for cron and permissions
# USER bcutils  # Keep as root for cron functionality

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]