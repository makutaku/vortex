# Release notes

## 0.1.4 (2025-08-18) - Major Enterprise Features

### 🚀 Major New Features

**Raw Data Storage & Audit Trail System:**
* Added comprehensive raw data storage for compliance and debugging (`RawDataStorage`)
* Automatically saves untampered provider responses as compressed CSV files
* Structured file organization with metadata and correlation IDs
* Configurable retention periods, compression, and metadata inclusion
* Full integration with all providers (Barchart, Yahoo Finance, IBKR)

**Prometheus Monitoring Infrastructure:**
* Complete monitoring stack with Prometheus, Grafana, and Node Exporter
* Professional Grafana dashboards for business and system metrics
* 17+ alert rules for provider performance, circuit breakers, and system health
* Thread-safe metrics collection with correlation tracking
* Docker Compose monitoring stack setup

**Enhanced CLI Interface:**
* New `vortex metrics` command group for monitoring management
* New `vortex resilience` command group for circuit breaker status
* Enhanced validation commands with improved formats and displays
* Improved error handling and dependency injection across all commands

### 🔧 Infrastructure Improvements

**Configuration System:**
* Enhanced TOML configuration with new sections for raw data and metrics
* Complete environment variable override support for all settings
* Improved validation with Pydantic models and type safety
* Interactive configuration setup for new features

**Provider Enhancements:**
* Dependency injection implementation across all providers
* Raw data storage integration for audit trails
* Metrics collection for request duration and success rates
* Enhanced error handling and correlation tracking

**Testing & Quality:**
* Increased unit test coverage from 23% to 78%
* Added comprehensive tests for raw data storage (23 test cases)
* Enhanced integration tests for monitoring components
* Improved Docker test protection and refactoring safety

### 🐛 Bug Fixes

* Fixed forex downloads by using provider codes instead of JSON keys
* Fixed Barchart forex symbol handling and invalid data validation
* Fixed asset classification bugs in job creation
* Fixed download summary calculation showing impossible success rates
* Fixed IBKR provider connectivity test mocking
* Resolved critical best practices violations

### 📚 Documentation

* Updated design documentation to reflect current implementation
* Added comprehensive monitoring setup guides
* Enhanced security design documentation
* Improved Docker troubleshooting and deployment guides

### 🔒 Security

* Enhanced credential management with secure storage
* Improved Docker security guidelines
* Added audit trail capabilities for compliance
* Enhanced input validation and error handling

### ⚡ Performance

* Optimized job creation logic with better counting accuracy
* Enhanced logging consistency and reduced redundant messages
* Improved correlation tracking for end-to-end request monitoring
* Circuit breaker implementation for provider resilience

---

## 0.1.3 (2023-01-24)
* newer and renamed instruments in config
* publish with token
* latest github action versions
* fixing lint warnings
* fixing deepsource warnings
