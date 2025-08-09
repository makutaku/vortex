# Vortex Storage Architecture

**Version:** 2.0  
**Date:** 2025-08-04  
**Related:** [Component Architecture](02-component-architecture.md) | [Data Flow Design](03-data-flow-design.md)

## 1. Modern Dual-Format Storage Architecture

### 1.1 Storage Bridge Pattern Design
Vortex implements a sophisticated dual-format storage architecture using the Bridge pattern, enabling simultaneous persistence in multiple formats while maintaining a unified interface. This design optimizes for both human accessibility (CSV) and analytical performance (Parquet).

### 1.2 Architecture Objectives
- **Dual Storage Strategy:** Primary CSV storage for human readability + Parquet backup for performance
- **Bridge Pattern Implementation:** Clean separation between storage interface and format implementations
- **Atomic Operations:** ACID-compliant operations with comprehensive rollback capability
- **Intelligent Deduplication:** Smart data merging with conflict resolution strategies
- **Comprehensive Metadata:** Complete audit trail with data quality metrics
- **Format Extensibility:** Plugin architecture for adding new storage formats

### 1.3 Storage Bridge Architecture
```mermaid
graph TB
    subgraph "Storage Orchestration Layer"
        StorageBridge[Storage Bridge Controller]
        FormatRegistry[Storage Format Registry]
        OperationCoordinator[Atomic Operation Coordinator]
    end
    
    subgraph "Storage Interface Layer"
        DataStorage[DataStorage Abstract Interface]
        FileStorage[FileStorage Template Base]
        MetadataManager[Metadata Management Interface]
    end
    
    subgraph "Primary Storage Implementations"
        CSVStorage[CSV Primary Storage]
        CSVFormatter[CSV Data Formatter]
        CSVDeduplicator[CSV Smart Deduplication]
        CSVValidator[CSV Data Validation]
    end
    
    subgraph "Backup Storage Implementations"
        ParquetStorage[Parquet Backup Storage]
        ParquetCompressor[Snappy Compression Engine]
        ParquetOptimizer[Columnar Storage Optimizer]
        ParquetValidator[Parquet Schema Validation]
    end
    
    subgraph "Metadata & Audit Layer"
        MetadataStore[JSON Metadata Store]
        AuditTracker[Operation Audit Tracker]
        QualityScorer[Data Quality Scorer]
        StatusTracker[Download Status Tracker]
    end
    
    subgraph "File System Integration"
        LocalFS[Local File System]
        AtomicWriter[Atomic File Writer]
        TempManager[Temporary File Manager]
        PathResolver[Intelligent Path Resolution]
    end
    
    StorageBridge --> FormatRegistry
    StorageBridge --> OperationCoordinator
    OperationCoordinator --> DataStorage
    
    DataStorage --> FileStorage
    FileStorage --> CSVStorage
    FileStorage --> ParquetStorage
    FileStorage --> MetadataStore
    
    CSVStorage --> CSVFormatter
    CSVStorage --> CSVDeduplicator
    CSVStorage --> CSVValidator
    
    ParquetStorage --> ParquetCompressor
    ParquetStorage --> ParquetOptimizer
    ParquetStorage --> ParquetValidator
    
    MetadataStore --> AuditTracker
    MetadataStore --> QualityScorer
    MetadataStore --> StatusTracker
    
    FileStorage --> LocalFS
    LocalFS --> AtomicWriter
    LocalFS --> TempManager
    LocalFS --> PathResolver
    
    style StorageBridge fill:#e1f5fe
    style CSVStorage fill:#e8f5e8
    style ParquetStorage fill:#fff3e0
    style MetadataStore fill:#f3e5f5
    style OperationCoordinator fill:#ffecb3
```

## 2. Storage Bridge Pattern Implementation

### 2.1 Bridge Controller Architecture
The Storage Bridge Controller orchestrates dual-format persistence while maintaining a clean separation between the storage interface and format-specific implementations. This enables runtime format selection and simultaneous multi-format operations.

**Bridge Pattern Benefits:**
- **Format Independence:** Client code works with any storage format combination
- **Runtime Flexibility:** Enable/disable storage formats based on configuration
- **Atomic Coordination:** Ensure consistency across multiple storage formats
- **Rollback Capability:** Complete transaction rollback if any format operation fails

**Bridge Controller Responsibilities:**
- **Operation Orchestration:** Coordinate save/load operations across multiple formats
- **Transaction Management:** Ensure ACID properties for multi-format operations
- **Format Registry:** Maintain catalog of available storage format implementations
- **Error Coordination:** Handle partial failures and rollback scenarios

### 2.2 Dual Storage Implementation Strategy
The dual storage strategy implements primary CSV storage with Parquet backup, optimizing for both immediate usability and long-term analytical performance.

**Primary Storage (CSV):**
- **Human Readable:** Immediate accessibility for debugging and manual analysis
- **Universal Compatibility:** Works with spreadsheets, text editors, and simple scripts
- **Incremental Updates:** Efficient merging and deduplication for new data
- **Audit Trail:** Clear format for tracking data changes and sources

**Backup Storage (Parquet):**
- **Analytical Performance:** Columnar format optimized for query operations
- **Storage Efficiency:** Snappy compression reduces storage footprint by 60-80%
- **Schema Evolution:** Handle changing data structures over time
- **Fast Aggregation:** Optimized for time-series analysis and reporting

**Coordination Strategy:**
- **Synchronous Operations:** Both formats updated atomically in single transaction
- **Consistency Validation:** Verify data integrity across both formats
- **Recovery Support:** Use either format for data recovery scenarios
- **Performance Monitoring:** Track operation metrics for both storage paths

**File Storage Architecture Features:**
- **Atomic Save Operations:** Temporary file staging with atomic moves
- **Backup Management:** Automatic backup creation and cleanup
- **Path Preparation:** Directory creation and validation
- **Metadata Integration:** Automatic metadata tracking and updates
- **Error Recovery:** Rollback capabilities on operation failures

**Common File Operations:**
- **Preparation Phase:** Path validation and directory creation
- **Staging Phase:** Write to temporary files for atomicity
- **Commit Phase:** Atomic move to final location
- **Metadata Phase:** Update tracking information
- **Cleanup Phase:** Remove temporary and backup files

**Error Handling Strategy:**
- **Rollback:** Restore from backup on save failures
- **Cleanup:** Remove temporary files on errors
- **Exception Translation:** Convert low-level errors to storage-specific exceptions
- **State Consistency:** Ensure storage remains in valid state after failures

*Detailed file storage implementation available in [Storage Implementation](../lld/04-storage-implementation.md)*

## 3. Format-Specific Storage Architectures

### 3.1 CSV Storage Architecture
The CSV storage implementation prioritizes human readability and universal compatibility while maintaining data integrity through structured validation.

**CSV Design Characteristics:**
- **Human Readable:** Plain text format for easy inspection and debugging
- **Universal Compatibility:** Works with spreadsheet applications and text editors
- **Encoding Standardization:** UTF-8 encoding with proper escaping
- **Header Consistency:** Standardized internal column naming convention (`Datetime` index, `Open`, `High`, `Low`, `Close`, `Volume` columns)

**CSV Storage Features:**
- **Delimiter Handling:** Configurable delimiter with automatic escaping
- **Quote Management:** Proper quoting of text fields containing delimiters
- **Type Preservation:** Consistent data type handling across save/load cycles (float64 for OHLC, int64 for Volume)
- **Large File Support:** Streaming operations for datasets exceeding memory
- **Column Validation:** Ensures adherence to internal standard format before persistence

### 3.2 Parquet Storage Architecture
The Parquet storage implementation optimizes for analytical performance and storage efficiency through columnar compression and schema evolution.

**Parquet Design Characteristics:**
- **Columnar Format:** Column-oriented storage for analytical queries
- **Compression Efficiency:** Snappy compression for space optimization
- **Schema Evolution:** Forward and backward compatibility for changing data structures
- **Type Safety:** Strong typing with automatic type inference

**Parquet Storage Features:**
- **Predicate Pushdown:** Efficient filtering at the storage layer
- **Partition Support:** Date-based partitioning for query optimization
- **Metadata Caching:** Column statistics for query planning
- **Vectorized Operations:** Optimized reading for analytical workloads

### 3.3 Column Naming Convention Enforcement

**Storage-Level Validation:**
All storage implementations enforce the internal standard column naming convention before persistence:

```python
# Required Internal Standard Format
Index: "Datetime" (pandas DatetimeIndex)
Columns: ["Open", "High", "Low", "Close", "Volume"] (exact title case)
Provider-Specific: Original casing preserved (e.g., "Adj Close", "Open Interest")
```

**Validation Requirements:**
- **Pre-Storage Validation:** Verify column names match internal standard before saving
- **Post-Load Validation:** Confirm loaded data maintains naming convention
- **Error Handling:** Reject data that doesn't conform to naming requirements
- **Metadata Tracking:** Record any column transformations applied during storage

**Storage Format Examples:**
```csv
# CSV File Header (example)
Datetime,Open,High,Low,Close,Volume,symbol,provider,Adj Close
2024-01-15T14:30:00Z,1850.25,1852.75,1849.50,1851.00,12500,GC_202406,barchart,1850.00
```

*Detailed format implementations available in [Storage Implementation](../lld/04-storage-implementation.md)*

## 4. Data Deduplication Architecture

### 4.1 Deduplication Strategy
The deduplication system ensures data consistency by identifying and resolving duplicate records across different data sources and time periods.

**Deduplication Design Patterns:**
- **Composite Key Strategy:** Multi-column uniqueness based on timestamp and instrument
- **Conflict Resolution:** Provider priority-based resolution for conflicting data
- **Incremental Processing:** Efficient deduplication for new data additions
- **Memory Optimization:** Streaming deduplication for large datasets

**Deduplication Process Architecture:**
- **Detection Phase:** Identify duplicate records using composite keys
- **Analysis Phase:** Determine conflict resolution strategy
- **Resolution Phase:** Apply provider priority rules
- **Validation Phase:** Verify data integrity after deduplication

### 4.2 Conflict Resolution Framework
The conflict resolution framework handles data conflicts when multiple providers supply different values for the same instrument and timestamp.

**Resolution Strategy Hierarchy:**
- **Provider Priority:** Use configured provider preference order
- **Data Quality Metrics:** Select based on data completeness and validation scores
- **Timestamp Precision:** Prefer data with more precise timestamps
- **Source Reliability:** Consider historical provider reliability metrics

*Detailed deduplication implementation available in [Storage Implementation](../lld/04-storage-implementation.md)*

## 5. Storage Performance Architecture

### 5.1 Performance Optimization Strategy
The storage layer implements multiple optimization techniques to handle large datasets efficiently while maintaining data integrity guarantees.

**Performance Design Principles:**
- **Streaming Operations:** Process data in chunks to minimize memory usage
- **Asynchronous I/O:** Non-blocking operations for improved throughput
- **Compression Optimization:** Format-specific compression algorithms
- **Cache Management:** Intelligent caching with memory-aware eviction

**Performance Optimization Patterns:**
- **Batch Operations:** Group multiple operations for reduced overhead
- **Lazy Loading:** Load data on demand to minimize initial latency
- **Connection Pooling:** Reuse connections for network storage backends
- **Memory Mapping:** Use memory-mapped files for large dataset access

### 5.2 Scalability Architecture
The storage architecture supports horizontal and vertical scaling through modular design and configurable backends.

**Scalability Design Features:**
- **Pluggable Backends:** Support for local, network, and cloud storage
- **Partition Strategy:** Automatic data partitioning for large datasets
- **Load Distribution:** Distribute storage operations across multiple backends
- **Capacity Management:** Automatic capacity monitoring and alerting

*Detailed performance implementation available in [Storage Implementation](../lld/04-storage-implementation.md)*

## 6. Backup and Recovery Architecture

### 6.1 Backup Strategy Framework
The backup system ensures data durability through multiple backup strategies and automatic recovery capabilities.

**Backup Design Patterns:**
- **Incremental Backup:** Only backup changed data to minimize overhead
- **Multi-Format Backup:** Backup in different formats for redundancy
- **Automated Scheduling:** Regular backup operations without manual intervention
- **Remote Backup:** Support for offsite backup storage

**Backup Architecture Components:**
- **Backup Controller:** Coordinates backup operations across storage formats
- **Schedule Manager:** Manages backup timing and frequency
- **Integrity Checker:** Validates backup completeness and accuracy
- **Recovery Manager:** Handles restoration from backup sources

### 6.2 Recovery Architecture
The recovery system provides comprehensive data restoration capabilities with minimal downtime and data loss.

**Recovery Strategy Framework:**
- **Point-in-Time Recovery:** Restore data to specific timestamps
- **Partial Recovery:** Selective restoration of specific instruments or date ranges
- **Cross-Format Recovery:** Restore from alternative format backups
- **Automated Recovery:** Self-healing capabilities for common failure scenarios

*Detailed backup and recovery implementation available in [Storage Implementation](../lld/04-storage-implementation.md)*

## 7. Storage Testing Architecture

### 7.1 Testing Strategy Framework
The storage testing approach validates correctness, performance, and reliability across all storage implementations and scenarios.

**Testing Architecture Patterns:**
- **Mock Storage:** In-memory implementations for unit testing
- **Property-Based Testing:** Automated test generation for edge cases
- **Performance Testing:** Load testing for throughput and latency validation
- **Fault Injection:** Simulate failures for resilience testing

**Test Coverage Areas:**
- **Interface Compliance:** Verify all implementations follow the storage contract
- **Data Integrity:** Validate data consistency across save/load cycles
- **Error Handling:** Test failure scenarios and recovery mechanisms
- **Performance Benchmarks:** Measure and validate storage performance metrics

### 7.2 Validation Architecture
The validation system ensures storage implementations maintain data quality and system reliability under all operating conditions.

**Validation Framework:**
- **Automated Validation:** Continuous testing through CI/CD pipelines
- **Integration Testing:** End-to-end validation with real data workflows
- **Regression Testing:** Prevent performance and correctness regressions
- **Stress Testing:** Validate behavior under extreme load conditions

*Detailed testing implementation available in [Testing Implementation](../lld/06-testing-implementation.md)*

## Related Documents

- **[Component Architecture](02-component-architecture.md)** - Overall component design context
- **[Data Flow Design](03-data-flow-design.md)** - Data processing pipeline integration
- **[Provider Abstraction](04-provider-abstraction.md)** - Data source integration
- **[Security Design](06-security-design.md)** - Storage security considerations

---

**Next Review:** 2025-09-04  
**Reviewers:** Senior Developer, Storage Architect, QA Lead