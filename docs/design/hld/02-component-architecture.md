# BC-Utils Component Architecture

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [System Overview](01-system-overview.md) | [Data Flow Design](03-data-flow-design.md)

## 1. Component Overview

### 1.1 System Decomposition
BC-Utils follows a layered architecture with clear separation of concerns. Each layer has specific responsibilities and well-defined interfaces.

```mermaid
graph TB
    subgraph "Presentation Layer"
        CLI[CLI Interface]
        Config[Configuration Loader]
    end
    
    subgraph "Application Layer"
        DM[Download Manager]
        Job[Job Orchestrator]
        Retry[Retry Controller]
    end
    
    subgraph "Domain Layer"
        Instruments[Instrument Models]
        Validation[Data Validation]
        Transform[Data Transformation]
    end
    
    subgraph "Infrastructure Layer"
        Providers[Data Providers]
        Storage[Storage Engines]
        Logging[Logging Framework]
    end
    
    CLI --> DM
    Config --> DM
    DM --> Job
    Job --> Retry
    Job --> Instruments
    Job --> Validation
    Validation --> Transform
    Transform --> Providers
    Transform --> Storage
    
    Providers --> Storage
    Storage --> Logging
    
    style DM fill:#e1f5fe
    style Providers fill:#fff3e0
    style Storage fill:#e8f5e8
```

### 1.2 Component Responsibilities
| Layer | Components | Responsibility |
|-------|------------|----------------|
| **Presentation** | CLI, Configuration | User interaction and system setup |
| **Application** | Download Manager, Job Control | Business workflow orchestration |
| **Domain** | Instruments, Validation | Core business logic and rules |
| **Infrastructure** | Providers, Storage, Logging | External integrations and persistence |

## 2. Core Components

### 2.1 Download Manager (`downloaders/updating_downloader.py`)

#### Purpose
Central orchestrator that coordinates the entire data acquisition workflow from configuration to storage.

#### Responsibilities
- **Job Creation:** Convert configuration into download jobs
- **Provider Selection:** Choose appropriate data provider for each instrument
- **Workflow Orchestration:** Manage download → validation → storage pipeline
- **Error Handling:** Coordinate retries and fallback strategies
- **Progress Tracking:** Monitor and report download progress

#### Key Interfaces
```python
class UpdatingDownloader:
    def __init__(self, data_storage, data_provider, backup_storage=None)
    
    def download_instrument_data(self, instrument_config: InstrumentConfig) -> bool
    def download_multiple_instruments(self, configs: Dict[str, InstrumentConfig])
    def get_download_stats(self) -> DownloadStats
```

#### Dependencies
- **Data Providers:** Abstract interface for data acquisition
- **Storage Engines:** Primary and backup data persistence
- **Validation Service:** Data quality assurance
- **Configuration:** Instrument and system settings

#### Workflow Overview
The Download Manager orchestrates a five-stage process:
1. **Job Creation** - Convert configuration to executable download jobs
2. **Data Acquisition** - Fetch data from appropriate provider
3. **Quality Validation** - Ensure data meets business rules
4. **Storage Operations** - Persist to primary and backup storage
5. **Metadata Management** - Track download history and status

*Detailed implementation specifications available in [Component Implementation](../lld/01-component-implementation.md)*

### 2.2 Data Provider Interface (`data_providers/data_provider.py`)

#### Purpose
Abstract interface that standardizes data acquisition across different external providers.

#### Architecture Pattern
**Strategy Pattern:** Enables runtime selection of data provider based on configuration.

```mermaid
classDiagram
    class DataProvider {
        <<abstract>>
        +get_data(instrument, date_range)*
        +authenticate(credentials)*
        +get_supported_instruments()*
        +get_rate_limits()*
    }
    
    class BarchartProvider {
        +get_data(instrument, date_range)
        +authenticate(username, password)
        +_handle_pagination()
        +_parse_csv_response()
    }
    
    class YahooProvider {
        +get_data(instrument, date_range)
        +authenticate(api_key)
        +_handle_redirects()
        +_parse_json_response()
    }
    
    class IBKRProvider {
        +get_data(instrument, date_range)
        +authenticate(gateway_host, port)
        +_establish_connection()
        +_handle_realtime_data()
    }
    
    DataProvider <|-- BarchartProvider
    DataProvider <|-- YahooProvider
    DataProvider <|-- IBKRProvider
```

#### Provider Implementation Requirements
Each provider must implement:
1. **Authentication:** Handle provider-specific credential types
2. **Rate Limiting:** Respect API limits and implement backoff
3. **Data Formatting:** Convert to standard OHLCV schema
4. **Error Handling:** Classify and handle provider-specific errors
5. **Metadata Extraction:** Capture provider-specific attributes

#### Provider Implementation Patterns
Each provider implements the common interface but handles provider-specific concerns:

**Barchart Provider:**
- Session-based authentication with CSRF protection
- Rate limiting (150 downloads/day default)
- CSV response parsing and standardization

**Yahoo Provider:**
- No authentication required for basic data
- JSON API with automatic retry logic
- Real-time and historical data support

**IBKR Provider:**
- TWS Gateway connection management
- Binary protocol handling
- Contract specification and market data

*Detailed provider implementations available in [Provider Implementation](../lld/03-provider-implementation.md)*

### 2.3 Storage Architecture (`data_storage/`)

#### Purpose
Provides pluggable storage backends with dual-format persistence for different use cases.

#### Component Structure
```mermaid
graph TB
    subgraph "Storage Interface"
        DS[DataStorage Abstract]
        FS[FileStorage Base]
    end
    
    subgraph "Storage Implementations"
        CSV[CSV Storage]
        Parquet[Parquet Storage]
        Meta[Metadata Storage]
    end
    
    subgraph "Storage Features"
        Dedup[Deduplication]
        Compress[Compression]
        Validate[Validation]
    end
    
    DS --> FS
    FS --> CSV
    FS --> Parquet
    FS --> Meta
    
    CSV --> Dedup
    CSV --> Validate
    Parquet --> Compress
    Parquet --> Validate
    
    style FS fill:#e8f5e8
    style CSV fill:#fff3e0
    style Parquet fill:#fff3e0
```

#### Storage Implementation Strategy
The storage layer uses a dual-format approach:

**CSV Storage:**
- Human-readable format for debugging and manual analysis
- Atomic write operations with temporary files
- Automatic data merging and deduplication
- UTF-8 encoding with proper escaping

**Parquet Storage:**
- Columnar format optimized for analytical workloads
- Snappy compression for space efficiency
- Date-based partitioning for query performance
- Schema evolution support

**Common Features:**
- Pluggable backend architecture
- Metadata tracking and integrity verification
- Backup and recovery capabilities
- Transaction-like semantics with rollback

*Detailed storage implementations available in [Storage Implementation](../lld/04-storage-implementation.md)*

### 2.4 Instrument Model (`instruments/`)

#### Purpose
Domain models that encapsulate business logic for different financial instrument types.

#### Class Hierarchy
```mermaid
classDiagram
    class Instrument {
        <<abstract>>
        +symbol: str
        +get_download_params()*
        +validate_data()*
        +get_file_path()*
    }
    
    class Future {
        +contract_month: str
        +exchange: str
        +get_contract_code()
        +calculate_expiry()
        +handle_rollover()
    }
    
    class Stock {
        +exchange: str
        +currency: str
        +handle_splits()
        +handle_dividends()
    }
    
    class Forex {
        +base_currency: str
        +quote_currency: str
        +get_pip_value()
        +handle_weekends()
    }
    
    Instrument <|-- Future
    Instrument <|-- Stock
    Instrument <|-- Forex
```

#### Instrument Model Hierarchy
The instrument models encapsulate business logic for different financial instrument types:

**Future Contracts:**
- Contract cycle management (GJMQVZ months)
- Expiry date calculation with exchange-specific rules
- Active contract generation for date ranges
- Rollover handling and chain construction

**Stock Instruments:**
- Corporate action handling (splits, dividends)
- Exchange-specific symbol mapping
- Currency conversion support
- Sector and industry classification

**Forex Pairs:**
- Base/quote currency management
- Pip value calculations
- Market hours and weekend gap handling
- Central bank intervention periods

*Detailed instrument implementations available in [Component Implementation](../lld/01-component-implementation.md)*

### 2.5 Configuration Management (`initialization/`)

#### Purpose
Centralized configuration loading and validation with support for multiple sources.

#### Configuration Sources
```mermaid
graph LR
    subgraph "Configuration Sources"
        JSON[JSON Files]
        ENV[Environment Variables]
        CLI[Command Line Args]
        Defaults[Default Values]
    end
    
    subgraph "Configuration Processor"
        Loader[Config Loader]
        Validator[Config Validator]
        Merger[Config Merger]
    end
    
    subgraph "Configuration Objects"
        Session[Session Config]
        Instrument[Instrument Config]
        Provider[Provider Config]
    end
    
    JSON --> Loader
    ENV --> Loader
    CLI --> Loader
    Defaults --> Loader
    
    Loader --> Validator
    Validator --> Merger
    Merger --> Session
    Merger --> Instrument
    Merger --> Provider
    
    style Loader fill:#e1f5fe
```

#### Configuration Architecture
The configuration system supports multiple input sources with a clear precedence hierarchy:

**Configuration Sources (in precedence order):**
1. Command-line arguments (highest priority)
2. Environment variables
3. Configuration files (JSON)
4. Default values (lowest priority)

**Configuration Categories:**
- **Provider Settings:** Authentication and connection parameters
- **Download Settings:** Date ranges, limits, and output locations
- **Operational Settings:** Logging, dry-run mode, backup preferences
- **Instrument Settings:** Symbol definitions and data requirements

**Validation and Defaults:**
- Schema validation for all configuration inputs
- Automatic directory creation for output paths
- Credential validation before data operations
- Comprehensive error reporting for invalid configurations

*Detailed configuration implementation available in [Component Implementation](../lld/01-component-implementation.md)*

## 3. Component Interactions

### 3.1 Download Workflow Sequence
```mermaid
sequenceDiagram
    participant CLI
    participant DM as Download Manager
    participant Config
    participant Provider
    participant Validator
    participant Storage
    participant Metadata
    
    CLI->>Config: Load configuration
    Config->>DM: Initialize with config
    DM->>DM: Create download jobs
    
    loop For each instrument
        DM->>Provider: Request data
        Provider->>DM: Return raw data
        DM->>Validator: Validate data quality
        Validator->>DM: Return validated data
        DM->>Storage: Save primary format
        DM->>Storage: Save backup format
        DM->>Metadata: Record success
    end
    
    DM->>CLI: Return completion status
```

### 3.2 Error Handling Flow
```mermaid
graph TB
    Error[Error Occurs] --> Classify{Classify Error}
    
    Classify -->|Network| NetworkRetry[Network Retry Logic]
    Classify -->|Rate Limit| RateWait[Wait & Retry]
    Classify -->|Auth| AuthRefresh[Refresh Authentication]
    Classify -->|Data Quality| QualityLog[Log Quality Issue]
    Classify -->|System| SystemAlert[System Alert]
    
    NetworkRetry --> Success{Success?}
    RateWait --> Success
    AuthRefresh --> Success
    
    Success -->|Yes| Continue[Continue Processing]
    Success -->|No| MaxRetries{Max Retries?}
    
    MaxRetries -->|No| NetworkRetry
    MaxRetries -->|Yes| FailJob[Fail Job]
    
    QualityLog --> Continue
    SystemAlert --> FailJob
    
    style Error fill:#ffcdd2
    style Success fill:#c8e6c9
    style Continue fill:#e8f5e8
```

## 4. Component Dependencies

### 4.1 Dependency Graph
```mermaid
graph TB
    subgraph "External Dependencies"
        Pandas[pandas]
        Requests[requests]
        BS4[beautifulsoup4]
        PyArrow[pyarrow]
        IBAPI[ib-insync]
    end
    
    subgraph "BC-Utils Components"
        CLI[CLI Module]
        DM[Download Manager]
        Providers[Data Providers]
        Storage[Storage Layer]
        Instruments[Instrument Models]
        Config[Configuration]
    end
    
    CLI --> Config
    CLI --> DM
    DM --> Providers
    DM --> Storage
    DM --> Instruments
    Providers --> Instruments
    Storage --> Instruments
    
    Providers --> Requests
    Providers --> BS4
    Providers --> IBAPI
    Storage --> Pandas
    Storage --> PyArrow
    Instruments --> Pandas
    
    style DM fill:#e1f5fe
    style Providers fill:#fff3e0
    style Storage fill:#e8f5e8
```

### 4.2 Package Dependencies
| Component | Internal Dependencies | External Dependencies |
|-----------|----------------------|----------------------|
| **Download Manager** | Storage, Providers, Instruments | pandas, logging |
| **Data Providers** | Instruments, Validation | requests, beautifulsoup4, ib-insync |
| **Storage Layer** | Instruments, Metadata | pandas, pyarrow |
| **Instruments** | Price Series, Periods | pandas, pytz |
| **Configuration** | Utilities | json, os |

### 4.3 Circular Dependency Prevention
- **Dependency Injection:** Components receive dependencies through constructors
- **Interface Segregation:** Small, focused interfaces prevent tight coupling
- **Event-Driven Communication:** Loose coupling through events where appropriate
- **Factory Pattern:** Central factories create component graphs

## 5. Component Configuration

### 5.1 Runtime Configuration
Each component supports configuration through multiple mechanisms:

```python
# Environment variables
BCU_PROVIDER_HOST=localhost
BCU_PROVIDER_PORT=7497
BCU_DOWNLOAD_DIRECTORY=/data/futures

# Configuration file
{
  "barchart": {
    "username": "${BCU_USERNAME}",
    "password": "${BCU_PASSWORD}",
    "daily_limit": 150
  },
  "storage": {
    "primary_format": "csv",
    "backup_format": "parquet",
    "compression": "snappy"
  }
}
```

### 5.2 Component Assembly
The system uses dependency injection and factory patterns for component assembly:

**Factory Responsibilities:**
- Create configured component instances
- Wire dependencies between components
- Apply configuration settings to components
- Handle provider-specific initialization

**Dependency Injection Pattern:**
- Components receive dependencies through constructors
- Interfaces used instead of concrete classes where possible
- Configuration drives component selection and setup
- Testable design with easy mock injection

**Component Lifecycle:**
1. Configuration loading and validation
2. Factory creates component instances
3. Dependencies injected during construction
4. Components initialized and ready for use
5. Cleanup and resource disposal on shutdown

*Detailed factory implementations available in [Component Implementation](../lld/01-component-implementation.md)*

## 6. Testing Strategy

### 6.1 Component Test Structure
```
tests/
├── unit/                    # Component isolation tests
│   ├── test_downloaders/
│   ├── test_providers/
│   ├── test_storage/
│   └── test_instruments/
├── integration/             # Component interaction tests
│   ├── test_download_workflow/
│   └── test_provider_storage/
└── fixtures/               # Test data and mocks
    ├── sample_data/
    └── mock_providers/
```

### 6.2 Component Testing Strategy
The testing approach emphasizes component isolation and integration validation:

**Unit Testing:**
- Component isolation through dependency injection
- Mock implementations for external dependencies
- Interface contract validation
- Error condition testing

**Integration Testing:**
- Component interaction validation
- End-to-end workflow testing
- Provider integration testing with test accounts
- Storage system integration testing

**Test Infrastructure:**
- Mock provider implementations for reliable testing
- Test data fixtures for various scenarios
- Automated test data generation
- Test environment isolation

*Detailed testing implementations available in [Testing Implementation](../lld/06-testing-implementation.md)*

## Related Documents

- **[Data Flow Design](03-data-flow-design.md)** - Detailed data processing pipeline
- **[Provider Abstraction](04-provider-abstraction.md)** - Data provider interface details
- **[Storage Architecture](05-storage-architecture.md)** - Storage implementation details
- **[System Overview](01-system-overview.md)** - High-level system context

---

**Next Review:** 2025-02-08  
**Reviewers:** Lead Developer, Senior Engineer, QA Lead