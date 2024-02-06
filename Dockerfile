# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set default values for environment variables
ENV BARCHART_USERNAME="" \
    BARCHART_PASSWORD="" \
    BARCHART_OUTPUT_DIR="/bc-utils/data" \
    BARCHART_START_YEAR=2015 \
    BARCHART_END_YEAR=2022 \
    BARCHART_DRY_RUN=True

# Set the working directory
WORKDIR /bc-utils

# Install apt-utils and cron
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    apt-utils cron && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -u 99 -g 100 nobody

# Copy source code, install dependencies, and set permissions
COPY --chown=nobody . /bc-utils
COPY cronfile /etc/cron.d/mycron
RUN chmod 0644 /etc/cron.d/mycron && \
    crontab -u nobody /etc/cron.d/mycron && \
    chmod u+s /usr/sbin/cron && \
    chmod +x entrypoint.sh show_input.sh run_bc_utils.sh

# Install and upgrade dependencies within a virtual environment
RUN python -m venv bcutils_env && \
    . bcutils_env/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Switch to the nobody user
USER nobody

ENTRYPOINT ["/bc-utils/entrypoint.sh"]
