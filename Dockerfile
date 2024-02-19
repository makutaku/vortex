# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set default values for environment variables
ENV BARCHART_USERNAME="provide-username"
ENV BARCHART_PASSWORD="provide-password"
ENV BARCHART_MARKET_FILES="/bc-utils/config/config.json"
ENV BARCHART_OUTPUT_DIR="/bc-utils/data"
ENV BARCHART_START_YEAR="2000"
ENV BARCHART_END_YEAR="2002"
ENV BARCHART_DAILY_DOWNLOAD_LIMIT="50"
ENV BARCHART_DRY_RUN="True"
ENV BARCHART_BACKUP_DATA="False"
ENV BARCHART_LOGGING_LEVEL="debug"
ENV BARCHART_RANDOM_SLEEP_IN_SEC="10"


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
#COPY . /bc-utils
COPY cronfile /etc/cron.d/mycron
RUN chmod 0644 /etc/cron.d/mycron && \
    crontab -u nobody /etc/cron.d/mycron && \
    chmod u+s /usr/sbin/cron && \
    chmod +x entrypoint.sh ping.sh run_bc_utils.sh

RUN chown -R nobody:users /bc-utils


# Install and upgrade dependencies within a virtual environment
RUN python -m venv bcutils_env && \
    . bcutils_env/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install yfinance

# Switch to the nobody user
USER nobody

ENTRYPOINT ["/bc-utils/entrypoint.sh"]
