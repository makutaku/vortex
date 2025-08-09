# Vortex Data Flow Design

**Version:** 2.0  
**Date:** 2025-08-04  
**Related:** [Component Architecture](02-component-architecture.md) | [Provider Abstraction](04-provider-abstraction.md)

## 1. Data Flow Overview

### 1.1 Modern CLI-Driven Pipeline
Vortex implements a sophisticated data processing pipeline with modern CLI interface, plugin architecture, comprehensive error handling, and dual-format storage with validation checkpoints.

```mermaid
graph TB
    subgraph "CLI Layer"
        User[User Input]
        Click[Click CLI Framework]
        Rich[Rich Terminal Output]
        ConfigMgr[TOML Configuration Manager]
    end
    
    subgraph "Application Layer"
        DownloadCmd[Download Command]
        ConfigCmd[Config Command]
        ProvidersCmd[Providers Command]
        ValidateCmd[Validate Command]
    end
    
    subgraph "Core Processing"
        JobFactory[Download Job Factory]
        PluginRegistry[Provider Plugin Registry]
        Orchestrator[Download Orchestrator]
        RetryLogic[Retry with Exponential Backoff]
    end
    
    subgraph "Data Provider Layer"
        Strategy[Provider Strategy Pattern]
        BarchartPlugin[Barchart Provider Plugin]
        YahooPlugin[Yahoo Provider Plugin]
        IBKRPlugin[IBKR Provider Plugin]
    end
    
    subgraph "Data Processing"
        Fetcher[Data Fetcher with Retries]
        Parser[Response Parser]
        Validator[Data Quality Validator]
        Transformer[OHLCV Format Transformer]
    end
    
    subgraph "Storage Layer"
        StorageBridge[Storage Bridge Pattern]
        CSVStorage[CSV Primary Storage]
        ParquetStorage[Parquet Backup Storage]
        MetadataStore[Metadata & Status Store]
        Deduplicator[Smart Data Deduplication]
    end
    
    User --> Click
    Click --> Rich
    Click --> ConfigMgr
    Click --> DownloadCmd
    DownloadCmd --> JobFactory
    JobFactory --> PluginRegistry
    PluginRegistry --> Strategy
    Strategy --> Orchestrator
    Orchestrator --> RetryLogic
    RetryLogic --> Fetcher
    
    Strategy --> BarchartPlugin
    Strategy --> YahooPlugin
    Strategy --> IBKRPlugin
    
    Fetcher --> Parser
    Parser --> Validator
    Validator --> Transformer
    Transformer --> StorageBridge
    StorageBridge --> Deduplicator
    Deduplicator --> CSVStorage
    StorageBridge --> ParquetStorage
    StorageBridge --> MetadataStore
    
    style Click fill:#e1f5fe
    style Strategy fill:#fff3e0
    style StorageBridge fill:#e8f5e8
    style Validator fill:#ffecb3
    style MetadataStore fill:#f3e5f5
```

### 1.2 Data Flow Architecture Principles

**Plugin-Based Extensibility:** Modern plugin architecture using registry pattern enables adding new data providers without modifying core system components.

**CLI-First Design:** Rich Click-based CLI provides professional user experience with progress bars, colored output, and comprehensive help system.

**Configuration-Driven Operation:** TOML-based configuration with environment variable overrides and interactive setup wizards.

**Dual Storage Strategy:** Primary CSV storage for human readability and analytics, with Parquet backup for performance and compression.

**Comprehensive Error Handling:** Hierarchical exception system with provider-specific error handling and user-friendly error messages.

### 1.3 Data States and Transformations
| State | Format | Location | Purpose |
|-------|--------|----------|---------|
| **Raw** | Provider-specific | Memory buffer | Initial API response |
| **Parsed** | Python objects | Memory | Structured data objects |
| **Validated** | pandas DataFrame | Memory | Quality-assured data |
| **Standardized** | Standard OHLCV | Memory | Unified format |
| **Persisted** | CSV/Parquet | File system | Long-term storage |

## 2. Detailed Data Flow Stages

### 2.1 Configuration and Job Generation

#### Configuration Loading Flow
```mermaid
sequenceDiagram
    participant CLI
    participant Loader as Config Loader
    participant Env as Environment
    participant Files as Config Files
    participant Validator as Config Validator
    
    CLI->>Loader: Load configuration
    Loader->>Env: Read environment variables
    Loader->>Files: Read JSON config files
    Loader->>Loader: Merge configurations
    Loader->>Validator: Validate completeness
    Validator->>CLI: Return session config
```

#### Job Generation Architecture
The job generation process transforms high-level configuration into executable download tasks through a systematic decomposition strategy:

**Job Generation Design Patterns:**
- **Configuration Transformation:** Convert user-defined parameters into structured job definitions
- **Date Range Segmentation:** Break large date ranges into manageable chunks for processing
- **Instrument Mapping:** Transform configuration symbols into typed instrument objects
- **Path Generation:** Create standardized output file paths based on instrument and date patterns

**Job Generation Strategy:**
- **Batch Processing:** Generate all jobs upfront for scheduling optimization
- **Resource Planning:** Consider rate limits and provider constraints during job creation
- **Dependency Management:** Ensure job order respects data dependencies
- **Error Isolation:** Structure jobs to minimize failure impact scope

### 2.2 Provider Selection and Data Fetching

#### Provider Selection Logic
```mermaid
graph TB
    JobStart[Download Job] --> Check{Provider Available?}
    Check -->|Yes| Auth[Authenticate]
    Check -->|No| Fallback[Try Fallback Provider]
    
    Auth --> RateLimit{Rate Limit OK?}
    RateLimit -->|Yes| Fetch[Fetch Data]
    RateLimit -->|No| Wait[Wait & Retry]
    
    Fetch --> Success{Success?}
    Success -->|Yes| ParseData[Parse Response]
    Success -->|No| HandleError[Handle Error]
    
    Wait --> RateLimit
    HandleError --> Fallback
    Fallback --> Check
    
    ParseData --> NextStage[Validation Stage]
    
    style Auth fill:#fff3e0
    style Fetch fill:#e1f5fe
    style ParseData fill:#e8f5e8
```

#### Data Fetching Strategy
The data fetching process implements several resilience patterns:

**Rate Limit Management:**
- Check provider limits before requests
- Automatic retry with appropriate delays
- Daily and hourly quota tracking

**Authentication Handling:**
- Automatic re-authentication on failures
- Session management for session-based providers
- Token refresh for OAuth providers

**Error Recovery:**
- Exponential backoff for transient errors
- Provider fallback for critical failures
- Graceful degradation when possible

*Detailed data fetching implementation available in [Data Processing Implementation](../lld/02-data-processing-implementation.md)*

### 2.3 Data Parsing and Validation

#### Parsing Flow by Provider
```mermaid
graph LR
    subgraph "Barchart Parsing"
        CSRF[Extract CSRF Token]
        CSV[Parse CSV Response]
        Headers[Validate Headers]
    end
    
    subgraph "Yahoo Parsing"
        JSON[Parse JSON Response]
        Struct[Extract Data Structure]
        Fields[Map Field Names]
    end
    
    subgraph "IBKR Parsing"
        Binary[Parse Binary Stream]
        Contracts[Map Contract Data]
        Times[Convert Timestamps]
    end
    
    RawData[Raw Response] --> CSRF
    RawData --> JSON
    RawData --> Binary
    
    CSV --> StandardFormat[Standard OHLCV]
    Struct --> StandardFormat
    Contracts --> StandardFormat
    
    style StandardFormat fill:#e8f5e8
```

#### Data Validation Strategy
The validation pipeline applies multiple layers of data quality checks:

**Schema Validation:**
- Required column presence verification
- Data type consistency checking
- Format validation (timestamps, numeric ranges)

**Business Rule Validation:**
- OHLC price relationship consistency
- Volume non-negativity constraints
- Instrument-specific business rules
- Market hours and trading calendar validation

**Statistical Validation:**
- Outlier detection using statistical methods
- Price movement reasonableness checks
- Volume pattern analysis
- Data completeness assessment

**Temporal Validation:**
- Timestamp monotonicity verification
- Duplicate timestamp detection
- Market schedule compliance
- Data freshness validation

*Detailed validation implementation available in [Data Processing Implementation](../lld/02-data-processing-implementation.md)*

### 2.4 Data Transformation and Standardization

#### Format Standardization Process
```mermaid
graph TB
    subgraph "External Provider Formats"
        YahooExt[Yahoo: Date, Open, High, Low, Close, Volume, Adj Close]
        BarchartExt[Barchart: Time, Open, High, Low, Last, Volume, Open Interest]
        IBKRExt[IBKR: date, open, high, low, close, volume, wap, count]
    end
    
    subgraph "Column Mapping Layer"
        YahooMap[Date → DATETIME index only]
        BarchartMap[Time → DATETIME, Last → Close]
        IBKRMap[date → DATETIME, lowercase → title case]
    end
    
    subgraph "Internal Standard Format"
        StandardIndex[DATETIME Index: UTC pd.DatetimeIndex]
        StandardCols[OHLCV: Open, High, Low, Close, Volume]
        ProviderCols[Provider-Specific: Adj Close, Open Interest, wap, count]
    end
    
    subgraph "Validation & Quality"
        ColumnVal[Column Name Validation]
        CaseVal[Case Consistency Validation]
        IndexVal[Index vs Column Validation]
    end
    
    YahooExt --> YahooMap
    BarchartExt --> BarchartMap
    IBKRExt --> IBKRMap
    
    YahooMap --> StandardIndex
    BarchartMap --> StandardIndex
    IBKRMap --> StandardIndex
    
    YahooMap --> StandardCols
    BarchartMap --> StandardCols
    IBKRMap --> StandardCols
    
    YahooExt --> ProviderCols
    BarchartExt --> ProviderCols
    IBKRExt --> ProviderCols
    
    StandardIndex --> ColumnVal
    StandardCols --> CaseVal
    ProviderCols --> IndexVal
    
    style StandardIndex fill:#e1f5fe
    style StandardCols fill:#e8f5e8
    style ProviderCols fill:#fff3e0
    style ColumnVal fill:#ffcdd2
```

#### Data Transformation Architecture
The transformation layer converts provider-specific formats into the standard OHLCV schema through a comprehensive column mapping system:

**Column Standardization Process:**
- **External Format Preservation:** Provider-specific column names maintained during ingestion
- **Mapping Layer:** Each provider implements explicit column transformation rules
- **Internal Standard:** All providers output consistent DATETIME index + title-case OHLCV columns
- **Provider-Specific Preservation:** Additional columns (Adj Close, WAP, Open Interest) preserved as-is

**Column Transformation Rules by Provider:**

| Provider | External Format | Transformation | Internal Standard |
|----------|----------------|----------------|-------------------|
| **Yahoo** | `Date` (index), `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close` | `Date` → `DATETIME` (index only) | `DATETIME` (index), `Open`, `High`, `Low`, `Close`, `Volume`, `Adj Close` |
| **Barchart** | `Time`, `Open`, `High`, `Low`, `Last`, `Volume`, `Open Interest` | `Time` → `DATETIME`, `Last` → `Close` | `DATETIME` (index), `Open`, `High`, `Low`, `Close`, `Volume`, `Open Interest` |
| **IBKR** | `date`, `open`, `high`, `low`, `close`, `volume`, `wap`, `count` | All OHLCV: lowercase → title case, `date` → `DATETIME` | `DATETIME` (index), `Open`, `High`, `Low`, `Close`, `Volume`, `wap`, `count` |

**Data Type Standardization:**
- float64 for all price columns (Open, High, Low, Close)
- int64 for Volume column
- Provider-specific columns maintain original data types

**Timestamp Standardization:**
- All timestamps converted to UTC pandas DatetimeIndex
- Provider-specific timezone handling (Yahoo: Date, Barchart: Time, IBKR: date)
- ISO 8601 format enforcement with timezone awareness

**Metadata Enrichment:**
- Provider attribution for audit trails
- Symbol normalization across providers
- Data quality scoring and validation flags

**Final Output Schema:**
- **Index:** `DATETIME` (pd.DatetimeIndex, UTC timezone)
- **Standard Columns:** `Open`, `High`, `Low`, `Close`, `Volume` (title case)
- **Metadata Columns:** `symbol`, `provider`
- **Provider-Specific:** Preserved with original names and casing
- **Sorting:** Chronologically sorted by DATETIME index

*Detailed transformation implementation available in [Data Processing Implementation](../lld/02-data-processing-implementation.md)*

#### Column Standardization Challenges & Solutions

**Critical Architecture Issue Identified:**
Comprehensive analysis revealed severe column name inconsistencies throughout the system affecting maintainability and reliability.

**Problem Analysis:**
```mermaid
graph TB
    subgraph "Current Issues"
        Incomplete[Incomplete Constants: Only 3/8 defined]
        Hardcoded[20+ Files: Hardcoded column names]
        CaseIssue[Case Mismatch: Title vs lowercase]
        IndexIssue[Index Confusion: DATETIME as column vs index]
    end
    
    subgraph "Impact Areas"
        Validation[CLI Validation Logic]
        Testing[Test Expectations]
        Providers[Provider Implementations]
        Constants[Column Constants Module]
    end
    
    subgraph "Architectural Solutions"
        CompleteConstants[Complete Column Constants]
        StandardizeUsage[Standardize All Usage]
        CaseConsistency[Enforce Case Consistency]
        ProperValidation[Fix Index/Column Validation]
    end
    
    Incomplete --> Constants
    Hardcoded --> Testing
    CaseIssue --> Validation
    IndexIssue --> Providers
    
    Constants --> CompleteConstants
    Testing --> StandardizeUsage
    Validation --> CaseConsistency
    Providers --> ProperValidation
    
    style Incomplete fill:#ffcdd2
    style Hardcoded fill:#ffcdd2
    style CompleteConstants fill:#c8e6c9
    style StandardizeUsage fill:#c8e6c9
```

**Required Architecture Fixes:**
1. **Complete Column Constants Module** (`models/columns.py`):
   ```python
   # Missing constants that must be added:
   OPEN_COLUMN = "Open"
   HIGH_COLUMN = "High" 
   LOW_COLUMN = "Low"
   DATE_COLUMN = "Date"  # For Yahoo provider mapping
   ```

2. **Standardize Column Usage Across Codebase:**
   - Update 20+ files using hardcoded column names
   - Fix CLI validation logic case sensitivity
   - Correct test expectations (lowercase → title case)
   - Update provider mapping implementations

3. **Validation Logic Architecture:**
   - **Index Validation:** `df.index.name == 'DATETIME'` (not `'DATETIME' in df.columns`)
   - **Column Validation:** Exact case matching for `['Open', 'High', 'Low', 'Close', 'Volume']`
   - **Provider Column Preservation:** Flexible handling of additional columns

**Data Flow Impact:**
This standardization is critical for the transformation layer reliability. Without proper column constants and validation, the data pipeline becomes fragile and error-prone during provider integration and data quality validation phases.

*Detailed transformation implementation available in [Data Processing Implementation](../lld/02-data-processing-implementation.md)*

### 2.5 Deduplication and Storage

#### Deduplication Logic
```mermaid
graph TB
    NewData[New Data] --> Check{Existing File?}
    Check -->|No| DirectSave[Save Directly]
    Check -->|Yes| LoadExisting[Load Existing Data]
    
    LoadExisting --> Merge[Merge Datasets]
    Merge --> Dedup[Remove Duplicates]
    Dedup --> Sort[Sort by Timestamp]
    Sort --> Save[Save Merged Data]
    
    DirectSave --> UpdateMeta[Update Metadata]
    Save --> UpdateMeta
    
    style Merge fill:#fff3e0
    style Dedup fill:#e1f5fe
    style Save fill:#e8f5e8
```

#### Storage Operation Strategy
The storage layer implements several patterns for data integrity and performance:

**Deduplication Strategy:**
- Timestamp and symbol-based duplicate detection
- Conflict resolution using provider preference
- Last-update-wins for conflicting data points

**Atomic Operations:**
- Temporary file staging for atomic writes
- Rollback capability on storage failures
- Metadata consistency with data files

**Data Validation:**
- Minimum data threshold enforcement
- Pre-storage validation checks
- Quality gate before persistence

**Metadata Management:**
- Automatic metadata generation and updates
- Dataset statistics tracking
- Audit trail maintenance

*Detailed storage implementation available in [Storage Implementation](../lld/04-storage-implementation.md)*

## 3. Error Handling and Recovery

### 3.1 Error Classification
```mermaid
graph TB
    Error[Error Occurred] --> Classify{Error Type}
    
    Classify -->|Network| NetworkFlow[Network Error Flow]
    Classify -->|Rate Limit| RateFlow[Rate Limit Flow]
    Classify -->|Auth| AuthFlow[Authentication Flow]
    Classify -->|Data Quality| QualityFlow[Quality Error Flow]
    Classify -->|System| SystemFlow[System Error Flow]
    
    NetworkFlow --> Retry1[Exponential Backoff Retry]
    RateFlow --> Wait[Wait Rate Limit Period]
    AuthFlow --> Reauth[Re-authenticate]
    QualityFlow --> Quarantine[Quarantine Data]
    SystemFlow --> Alert[System Alert]
    
    Retry1 --> Success1{Success?}
    Wait --> Success1
    Reauth --> Success1
    
    Success1 -->|Yes| Continue[Continue Processing]
    Success1 -->|No| MaxRetries{Max Retries?}
    
    MaxRetries -->|No| Retry1
    MaxRetries -->|Yes| FailJob[Fail Job]
    
    Quarantine --> Continue
    Alert --> FailJob
    
    style Error fill:#ffcdd2
    style Continue fill:#c8e6c9
    style FailJob fill:#ffebee
```

### 3.2 Recovery Strategies
| Error Type | Strategy | Implementation |
|------------|----------|----------------|
| **Network Timeout** | Exponential backoff | Retry with 2^n second delays |
| **Rate Limit** | Wait and retry | Sleep for provider-specified duration |
| **Authentication** | Token refresh | Re-authenticate and retry request |
| **Data Quality** | Quarantine | Save to separate location for review |
| **Disk Full** | Cleanup and retry | Remove old temp files, then retry |

## 4. Performance Optimization

### 4.1 Performance Architecture Strategy
The data flow pipeline implements a multi-layered performance optimization approach that balances throughput, memory efficiency, and system stability:

**Performance Design Principles:**
- **Resource Efficiency:** Minimize memory footprint through streaming and chunked processing
- **Concurrent Execution:** Maximize throughput within provider rate limits
- **Intelligent Caching:** Strategic data caching to reduce redundant operations
- **I/O Optimization:** Efficient storage patterns and atomic operations

### 4.2 Performance Optimization Patterns
The system employs several architectural patterns to achieve optimal performance across different workload scenarios:

**Caching Architecture:**
- **Multi-Level Caching:** Memory and disk-based caching with intelligent eviction policies
- **Cache Coherency:** TTL-based invalidation and freshness validation
- **Adaptive Sizing:** Dynamic cache size management based on available resources

**Concurrency Architecture:**
- **Bounded Parallelism:** Controlled concurrent execution within provider constraints
- **Asynchronous Processing:** Non-blocking I/O operations for improved throughput
- **Load Balancing:** Even distribution of work across available resources

**Memory Management Architecture:**
- **Streaming Processing:** Process large datasets without loading entirely into memory
- **Resource Monitoring:** Active memory usage tracking and cleanup
- **Garbage Collection:** Proactive cleanup of intermediate processing artifacts

**Storage Optimization Architecture:**
- **Batch Operations:** Grouped storage operations to reduce I/O overhead
- **Format Selection:** Optimal file format choice based on usage patterns
- **Atomic Transactions:** Safe storage operations with rollback capabilities

*Detailed performance implementation available in [Data Processing Implementation](../lld/02-data-processing-implementation.md)*

## 5. Data Flow Monitoring

### 5.1 Monitoring Architecture Strategy
The data flow monitoring system provides comprehensive observability into system performance, data quality, and operational health through a multi-dimensional metrics framework:

**Monitoring Design Framework:**
- **Performance Observability:** Real-time visibility into processing throughput and bottlenecks
- **Quality Assurance:** Continuous monitoring of data integrity and validation success
- **Operational Intelligence:** System health tracking and predictive alerting
- **Provider Analytics:** External dependency performance and reliability tracking

**Monitoring Architecture Patterns:**
- **Metrics Collection:** Multi-layered metric aggregation from all system components
- **Real-Time Alerting:** Threshold-based notification system for operational issues
- **Historical Analysis:** Trend analysis and capacity planning through metric retention
- **Dashboard Visualization:** Executive and operational dashboards for different stakeholder needs

**Observability Categories:**
- **System Performance:** Processing speed, resource utilization, and capacity metrics
- **Data Quality:** Validation rates, error patterns, and data completeness tracking
- **Provider Reliability:** External service availability, response times, and error rates
- **Business Metrics:** Download success rates, data coverage, and user satisfaction

*Detailed monitoring implementation available in [Data Processing Implementation](../lld/02-data-processing-implementation.md)*

### 5.2 Flow Observability
```mermaid
graph LR
    subgraph "Data Flow Stages"
        Fetch[Data Fetch]
        Parse[Parse]
        Validate[Validate]
        Store[Store]
    end
    
    subgraph "Monitoring"
        Metrics[Metrics Collection]
        Logs[Structured Logging]
        Alerts[Alert Rules]
    end
    
    subgraph "Observability"
        Dashboards[Performance Dashboards]
        Reports[Quality Reports]
        Traces[Distributed Tracing]
    end
    
    Fetch --> Metrics
    Parse --> Metrics
    Validate --> Metrics
    Store --> Metrics
    
    Metrics --> Dashboards
    Logs --> Reports
    Alerts --> Traces
    
    style Metrics fill:#e1f5fe
    style Dashboards fill:#e8f5e8
```

## 6. Integration Points

### 6.1 Upstream Dependencies
- **Configuration System:** Provides job parameters and settings
- **Provider Authenticator:** Supplies valid credentials
- **Scheduler:** Triggers data flow execution

### 6.2 Downstream Consumers
- **Analytics Pipeline:** Consumes standardized data files
- **Backup System:** Replicates data to secondary storage
- **Monitoring System:** Tracks flow health and performance

## Related Documents

- **[Component Architecture](02-component-architecture.md)** - Implementation details for flow components
- **[Provider Abstraction](04-provider-abstraction.md)** - Data provider interface design
- **[Storage Architecture](05-storage-architecture.md)** - Storage layer implementation
- **[Data Requirements](../../requirements/prd/data-requirements.md)** - Data format specifications

---

**Next Review:** 2025-09-04  
**Reviewers:** Senior Developer, Data Engineer, QA Lead