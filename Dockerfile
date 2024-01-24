# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory
WORKDIR /bc-utils

# Install apt-utils to address warning
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends apt-utils && \
    rm -rf /var/lib/apt/lists/*

# Copy source code, install dependencies, and clean up in one step
COPY . /bc-utils
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/* && \
    python -m venv bcutils_env && \
    . bcutils_env/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set default values for environment variables
ENV BARCHART_USERNAME="" \
    BARCHART_PASSWORD="" \
    BARCHART_OUTPUT_DIR="/bc-utils/data" \
    BARCHART_START_YEAR=2015 \
    BARCHART_END_YEAR=2022 \
    BARCHART_DRY_RUN=True

# Copy cron configuration and set permissions
COPY cronfile /etc/cron.d/mycron
RUN chmod 0644 /etc/cron.d/mycron && \
    crontab /etc/cron.d/mycron

# Run cron in the foreground
CMD . $HOME/.profile && \
    cd /bc-utils && \
    . bcutils_env/bin/activate && \
    python bcutils/bc_utils.py 2>&1 | tee -a ./barchart_download.txt && \
    cron -f
