# Vortex Production Monitoring Guide

This guide covers the comprehensive monitoring infrastructure available in Vortex for production deployments.

## 🎯 Overview

Vortex includes enterprise-grade monitoring capabilities with:
- **Prometheus metrics collection** for all operations
- **Grafana dashboards** with business and system metrics
- **Comprehensive alerting** with 17+ pre-configured rules
- **Docker monitoring stack** with Node Exporter
- **Real-time observability** across all providers and operations

## 🚀 Quick Setup

### 1. Start Monitoring Stack

```bash
# Start complete monitoring infrastructure
docker compose -f docker/docker-compose.monitoring.yml up -d

# Verify services are running
docker compose -f docker/docker-compose.monitoring.yml ps
```

### 2. Enable Metrics in Vortex

```bash
# Environment variable method
export VORTEX_METRICS_ENABLED=true
export VORTEX_METRICS_PORT=8000

# Or TOML configuration method
```toml
[general.metrics]
enabled = true
port = 8000
path = "/metrics"
```

### 3. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Vortex Metrics**: http://localhost:8000/metrics
- **Node Exporter**: http://localhost:9100/metrics

## 📊 Available Dashboards

### Vortex Business Metrics Dashboard

**Key Performance Indicators:**
- Provider success rates and error rates
- Download completion rates by symbol
- Circuit breaker status and failures
- Authentication success/failure rates
- Quota utilization and limits

**Provider Performance:**
- Request duration by provider (Barchart, Yahoo, IBKR)
- Row download rates and volumes
- Provider-specific error tracking
- Response time percentiles

**System Health:**
- Active operations and correlation tracking
- Storage performance (CSV, Parquet, Raw)
- Memory and CPU utilization
- Error recovery statistics

### Node Exporter System Dashboard

**Infrastructure Metrics:**
- CPU, memory, disk usage
- Network traffic and I/O
- File system statistics
- System load and processes

## 🔔 Alert Rules

### Provider Performance Alerts

**High Error Rate:**
```yaml
alert: VortexProviderHighErrorRate
expr: rate(vortex_provider_requests_total{status="error"}[5m]) > 0.1
for: 2m
labels:
  severity: warning
annotations:
  summary: "High error rate for provider {{ $labels.provider }}"
```

**Slow Provider Response:**
```yaml
alert: VortexProviderSlowResponse
expr: histogram_quantile(0.95, rate(vortex_provider_request_duration_seconds_bucket[5m])) > 30
for: 3m
labels:
  severity: warning
annotations:
  summary: "Slow response times for provider {{ $labels.provider }}"
```

### Circuit Breaker Alerts

**Circuit Breaker Open:**
```yaml
alert: VortexCircuitBreakerOpen
expr: vortex_circuit_breaker_state{state="open"} == 1
for: 0m
labels:
  severity: critical
annotations:
  summary: "Circuit breaker open for {{ $labels.provider }}"
```

### Download Performance Alerts

**Low Download Success Rate:**
```yaml
alert: VortexLowDownloadSuccessRate
expr: rate(vortex_downloads_total{status="success"}[10m]) / rate(vortex_downloads_total[10m]) < 0.8
for: 5m
labels:
  severity: warning
annotations:
  summary: "Low download success rate: {{ $value | humanizePercentage }}"
```

### System Resource Alerts

**High Memory Usage:**
```yaml
alert: VortexHighMemoryUsage
expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.85
for: 5m
labels:
  severity: warning
annotations:
  summary: "High memory usage: {{ $value | humanizePercentage }}"
```

## 📈 Metrics Reference

### Provider Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `vortex_provider_requests_total` | Counter | Total API requests by provider, operation, status |
| `vortex_provider_request_duration_seconds` | Histogram | Request duration by provider and operation |
| `vortex_provider_quota_remaining` | Gauge | Remaining quota for rate-limited providers |
| `vortex_provider_authentication_failures_total` | Counter | Authentication failures by provider |

### Download Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `vortex_downloads_total` | Counter | Total downloads by provider, status, symbol |
| `vortex_download_rows` | Histogram | Number of rows downloaded per request |
| `vortex_download_duration_seconds` | Histogram | Download duration by provider |
| `vortex_download_retries_total` | Counter | Download retry attempts |

### Circuit Breaker Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `vortex_circuit_breaker_state` | Gauge | Circuit breaker state (0=closed, 1=open, 2=half-open) |
| `vortex_circuit_breaker_failures_total` | Counter | Circuit breaker failure count |
| `vortex_circuit_breaker_successes_total` | Counter | Circuit breaker success count |
| `vortex_circuit_breaker_requests_total` | Counter | Total requests through circuit breaker |

### Storage Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `vortex_storage_operations_total` | Counter | Storage operations by type and status |
| `vortex_storage_duration_seconds` | Histogram | Storage operation duration |
| `vortex_raw_storage_files_total` | Counter | Raw data files created |
| `vortex_raw_storage_size_bytes` | Gauge | Raw data storage size |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `vortex_active_operations` | Gauge | Currently active operations |
| `vortex_correlation_active` | Gauge | Active correlation IDs |
| `vortex_configuration_loads_total` | Counter | Configuration reload count |
| `vortex_health_status` | Gauge | Overall system health (0=unhealthy, 1=healthy) |

## 🛠️ CLI Monitoring Commands

### Metrics Management

```bash
# Check metrics system status
vortex metrics status

# Show metrics endpoint URL
vortex metrics endpoint

# Generate test metrics for validation
vortex metrics test

# Show metrics activity summary
vortex metrics summary

# Show dashboard URLs and access information
vortex metrics dashboard
```

### System Resilience

```bash
# Check circuit breaker status
vortex resilience status

# Reset all circuit breakers
vortex resilience reset

# Show error recovery statistics
vortex resilience recovery

# Check overall system health
vortex resilience health
```

## 🐳 Docker Monitoring Stack

### Stack Components

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts:/etc/prometheus/alerts

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - ./monitoring/grafana:/etc/grafana/provisioning

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    command:
      - '--path.rootfs=/host'
    volumes:
      - '/:/host:ro,rslave'
```

### Prometheus Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "/etc/prometheus/alerts/*.yml"

scrape_configs:
  - job_name: 'vortex'
    static_configs:
      - targets: ['host.docker.internal:8000']
    scrape_interval: 5s
    metrics_path: '/metrics'

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

## 🔧 Troubleshooting

### Common Issues

**Metrics Not Appearing:**
1. Verify `VORTEX_METRICS_ENABLED=true`
2. Check metrics endpoint: `curl http://localhost:8000/metrics`
3. Verify Prometheus can scrape Vortex

**Grafana Dashboard Empty:**
1. Check Prometheus data source configuration
2. Verify queries in dashboard panels
3. Check time range selection

**Alerts Not Firing:**
1. Verify alert rule syntax in Prometheus
2. Check alert evaluation intervals
3. Verify alertmanager configuration

### Debugging Commands

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify Vortex metrics
curl http://localhost:8000/metrics | grep vortex

# Check Grafana datasource
curl -u admin:admin123 http://localhost:3000/api/datasources

# Monitor logs
docker compose -f docker/docker-compose.monitoring.yml logs -f
```

## 📝 Configuration Examples

### Production TOML Configuration

```toml
[general.metrics]
enabled = true
port = 8000
path = "/metrics"
# Optional: basic auth for metrics endpoint
auth_username = "metrics"
auth_password = "secure_password"

[general.logging]
level = "INFO"
output = ["console", "file"]
file_path = "/var/log/vortex/app.log"
file_rotation = "1d"
file_retention = "30d"

[general.raw]
enabled = true
retention_days = 90
compress = true
include_metadata = true
```

### Environment Variables for Production

```bash
# Metrics
export VORTEX_METRICS_ENABLED=true
export VORTEX_METRICS_PORT=8000

# Raw data storage
export VORTEX_RAW_ENABLED=true
export VORTEX_RAW_RETENTION_DAYS=90

# Logging
export VORTEX_LOGGING_LEVEL=INFO
export VORTEX_LOGGING_FILE_PATH=/var/log/vortex/app.log
```

## 🏗️ Production Deployment

### Monitoring Stack Deployment

```bash
# Create monitoring directory structure
mkdir -p monitoring/{prometheus,grafana,alerts}

# Deploy monitoring stack
docker compose -f docker/docker-compose.monitoring.yml up -d

# Deploy Vortex with metrics enabled
export VORTEX_METRICS_ENABLED=true
docker compose up -d

# Verify deployment
curl http://localhost:9090/targets
curl http://localhost:3000/api/health
curl http://localhost:8000/metrics
```

### Resource Requirements

**Minimum Resources:**
- Prometheus: 512MB RAM, 2GB storage
- Grafana: 256MB RAM, 1GB storage  
- Node Exporter: 64MB RAM
- Vortex: Additional 64MB RAM for metrics

**Recommended Resources:**
- Prometheus: 2GB RAM, 10GB storage
- Grafana: 512MB RAM, 2GB storage
- Node Exporter: 128MB RAM
- Vortex: Additional 128MB RAM for metrics

### Security Considerations

**Network Security:**
- Use internal Docker networks for monitoring communication
- Expose only necessary ports (3000, 9090)
- Configure firewall rules for production

**Authentication:**
- Change default Grafana password
- Enable authentication for Prometheus if exposed
- Use TLS for external access
- Rotate credentials regularly

**Data Security:**
- Configure retention policies for metrics
- Monitor storage usage and implement cleanup
- Secure backup procedures for dashboards and configurations

This monitoring infrastructure provides comprehensive observability for Vortex in production environments, enabling proactive monitoring and quick resolution of issues.