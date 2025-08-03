# Vortex Documentation Best Practices

**Version:** 1.0  
**Date:** 2025-01-08  

## 📋 Documentation Standards

### Document Structure

#### High-Level Design (HLD) Documents
HLD documents focus on **architectural decisions** and **design patterns**:

✅ **Include:**
- **System architecture** and component relationships  
- **Design patterns** and architectural principles (Strategy, Factory, Observer)
- **Interface contracts** and abstractions
- **Quality attributes** (performance, security, scalability)
- **Cross-cutting concerns** and system-wide decisions
- **Technology choices** and architectural rationale
- **Integration patterns** between major components
- **Mermaid diagrams** for architectural visualization
- **Component interaction flows** (sequence diagrams)
- **Deployment topology** and scaling considerations

❌ **Avoid:**
- Detailed code implementations (>30 lines)
- Specific library configurations and parameters
- Unit test specifications and mock implementations
- Database schemas and file formats
- Implementation algorithms and pseudo-code
- Method-level details and error handling
- Performance optimization techniques (belongs in LLD)

#### Low-Level Design (LLD) Documents  
LLD documents contain **implementation patterns** and **algorithmic specifications**:

✅ **Include:**
- **Algorithm descriptions** and pseudo-code workflows
- **Design pattern implementations** (how patterns are applied)
- **Data structures** and storage schemas
- **Error handling strategies** and recovery patterns
- **Performance optimization techniques** and benchmarks
- **Security implementation patterns** and validation rules
- **Testing strategies** and mock implementation patterns
- **Configuration examples** (5-10 lines maximum)
- **Interface definitions** (key methods only, 5-15 lines)
- **Source file references** for detailed implementations
- **Decision matrices** and conflict resolution strategies
- **State machines** and component lifecycle management

❌ **Avoid:**
- **Complete class implementations** (>30 lines total)
- **Full method implementations** (use pseudo-code instead)
- **Boilerplate code** (imports, logging, exception handling)
- **Repetitive code examples** (show pattern once with "...")
- **Copy-pasted source code** (use source references)
- **High-level architectural decisions** (belongs in HLD)
- **Business requirements** and user stories (belongs in PRD)
- **Deployment topology** and infrastructure (belongs in HLD)

### Cross-Reference Standards

#### Linking Between Document Types
- **HLD → LLD:** `*Implementation patterns available in [Component Implementation](../lld/01-component-implementation.md)*`
- **LLD → HLD:** `**Related:** [Component Architecture](../hld/02-component-architecture.md)`
- **Within same level:** `[Storage Architecture](05-storage-architecture.md)`
- **Source references:** `**Source Reference:** src/bcutils/component/file.py`
- **Algorithm references:** `**Algorithm:** See [Data Processing](02-data-processing-implementation.md#deduplication-algorithm)`

#### Section Anchors
Use descriptive anchors for section linking:
```markdown
[Storage Layer](05-storage-architecture.md#storage-interface-architecture)
```

#### External References
Reference PRD requirements with specific IDs:
```markdown
See [REQ-001](../../requirements/prd/product-requirements.md#req-001)
```

### Diagram Standards

#### Mermaid Diagrams
Use Mermaid for architectural diagrams:
```mermaid
graph TB
    subgraph "Layer Name"
        Component[Component Name]
    end
    
    style Component fill:#e1f5fe
```

#### Styling Conventions
- **Primary components:** `fill:#e1f5fe` (light blue)
- **Secondary components:** `fill:#e8f5e8` (light green)  
- **External systems:** `fill:#fff3e0` (light orange)
- **Error states:** `fill:#ffcdd2` (light red)

### Version Control

#### Document Headers
All documents must include:
```markdown
**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Link to related docs]
```

#### Document Status Tracking
Maintain status tables in README files:
```markdown
| Document | Status | Last Updated | Reviewers |
|----------|--------|--------------|-----------|
| [Doc Name](doc.md) | ✅ Complete | 2025-01-08 | Role1, Role2 |
```

#### Review Schedule
Include review information at document end:
```markdown
---

**Next Review:** 2025-02-08  
**Reviewers:** Senior Developer, System Architect
```

## 🏗️ Architecture Documentation Guidelines

### Component Documentation

#### Component Responsibilities
Clearly define what each component does:
```markdown
#### Purpose
Central orchestrator that coordinates the entire data acquisition workflow.

#### Responsibilities  
- **Job Creation:** Convert configuration into download jobs
- **Provider Selection:** Choose appropriate data provider
- **Workflow Orchestration:** Manage download → validation → storage pipeline
```

#### Interface Documentation
Document interfaces with design principles:
```markdown
**Interface Design Principles:**
- **Format Agnostic:** Common interface abstracts format details
- **CRUD Operations:** Complete Create, Read, Update, Delete functionality
- **Error Handling:** Consistent error reporting across implementations
```

### Design Pattern Documentation

#### Pattern Identification
Explicitly identify design patterns used:
```markdown
**Architecture Pattern:** Strategy Pattern enables runtime provider selection

**Design Patterns:**
- **Factory Pattern:** Dynamic provider creation and configuration
- **Template Method:** Common workflow with format-specific implementations
- **Observer Pattern:** Event-driven monitoring and alerting
```

#### Algorithm Documentation
Document algorithms with step-by-step workflows:
```markdown
**Algorithm: Rate Limiting**
```
1. CHECK all time windows for capacity
2. IF any window is full: CALCULATE wait time
3. IF capacity available: RECORD request timestamp
4. CLEAN expired entries from all windows
5. RETURN success/failure with wait time
```

**Decision Matrix Example:**
| Error Type | Recovery Action | Retry Strategy |
|------------|-----------------|----------------|
| Rate Limit | Wait specified time | Immediate retry |
| Auth Failure | Re-authenticate | Single retry |
| Connection | Exponential backoff | Max 3 retries |
```

#### Pattern Rationale
Explain why patterns were chosen:
```markdown
**Pattern Benefits:**
- **Extensibility:** Add new providers without modifying existing code
- **Reliability:** Graceful fallback when providers are unavailable
- **Testability:** Mock providers for comprehensive testing
```

## 🔧 Implementation Documentation Guidelines

### Code Documentation

#### Code Examples
Provide pattern-focused examples (5-20 lines max):
```python
class DataProvider(ABC):
    """Abstract base class for all data providers"""
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Provider-specific authentication"""
    
    @abstractmethod
    def get_data(self, instrument, date_range) -> pd.DataFrame:
        """Retrieve data for instrument and date range"""
```

**Algorithm Pseudo-code Example:**
```
FOR each provider in priority_list:
  TRY authenticate(provider)
  IF successful: RETURN provider
  ELSE: LOG failure, continue
RAISE AuthenticationError("All providers failed")
```

**State Machine Example:**
```
PENDING → IN_PROGRESS → COMPLETED
    ↓         ↓              ↓
  FAILED ←─ RETRY ←──────── FAILED
```

**Workflow Description Example:**
```
1. CREATE download job from configuration
2. CHECK for existing data → IF exists, incremental update
3. FETCH raw data from provider
4. VALIDATE data quality → IF invalid, reject
5. STORE data with deduplication
6. UPDATE metadata tracking
```

**Code Length Guidelines:**
- **Interface definitions:** Show key methods only (5-15 lines)
- **Algorithms:** Core logic only (10-30 lines)
- **Configuration examples:** Minimal working config (5-10 lines)
- **Test patterns:** Essential structure (10-20 lines)
- **NO complete implementations** in LLD documents

**Strictly Avoid in LLD:**
- Complete class implementations (use pseudo-code + source references)
- Full method implementations (show patterns/algorithms only)
- Boilerplate code (imports, logging setup, exception handling)
- Repetitive methods (show one example with "..." for others)
- Detailed error handling (show strategy only)
- Long code blocks (>30 lines indicates too much detail)

**Preferred LLD Content:**
- **Algorithms**: Step-by-step pseudo-code
- **Patterns**: Design pattern descriptions
- **Architecture**: Component interaction flows
- **Strategies**: Decision trees and rule matrices
- **References**: Source file locations for implementation details

#### Error Handling
Document comprehensive error handling:
```python
try:
    result = self.provider.get_data(instrument, date_range)
except RateLimitError as e:
    self.logger.warning(f"Rate limited, retry in {e.retry_after}s")
    self.scheduler.schedule_retry(job, delay=e.retry_after)
except AuthenticationError:
    self.logger.error("Authentication failed, manual intervention required")
    raise
```

#### Configuration Examples
Provide realistic configuration examples:
```python
config = {
    "provider": {
        "type": "barchart",
        "daily_limit": 150,
        "timeout_seconds": 60
    },
    "storage": {
        "primary_format": "csv",
        "backup_format": "parquet"
    }
}
```

### Testing Documentation

#### Test Structure
Document testing approach:
```python
class TestDataProviderInterface(BCUtilsTestCase):
    """Test data provider interface compliance"""
    
    def test_provider_interface_compliance(self):
        """Test that all providers implement required interface"""
        # Test implementation
```

#### Mock Implementation
Provide reusable mock implementations:
```python
class MockDataProvider:
    """Mock data provider for testing"""
    
    def __init__(self, return_data: pd.DataFrame = None):
        self.return_data = return_data
        self.call_history = []
```

## 📝 Writing Style Guidelines

### Technical Writing

#### Clarity and Concision
- Use active voice: "The system processes data" not "Data is processed"
- Be specific: "150 downloads/day" not "limited downloads"
- Use parallel structure in lists and procedures

#### Terminology Consistency  
- **Provider** (not data source, API, service)
- **Storage** (not persistence, database, repository)
- **Configuration** (not settings, parameters, options)
- **Instrument** (not symbol, asset, security)

#### Section Structure
Follow consistent section patterns:
1. **Purpose/Overview** - What and why
2. **Design Principles** - How and constraints  
3. **Implementation Details** - Specific technical details
4. **Examples** - Concrete usage scenarios

### Markdown Formatting

#### Headers
Use descriptive headers with consistent numbering:
```markdown
## 1. Storage Architecture Overview
### 1.1 Design Philosophy
### 1.2 Storage Objectives
```

#### Code Blocks
Always specify language for syntax highlighting:
```markdown
```python
def example_function():
    pass
```

#### Lists
Use consistent bullet formatting:
```markdown
**Design Principles:**
- **Extensibility:** Add new providers without code changes
- **Reliability:** Graceful fallback when providers fail
- **Testability:** Mock providers for unit testing
```

#### Tables
Include headers and maintain alignment:
```markdown
| Component | Responsibility | Dependencies |
|-----------|----------------|--------------|
| **Download Manager** | Orchestrate workflow | Storage, Providers |
| **Data Providers** | External data access | HTTP, Authentication |
```

## 🔍 Review Process

### Review Checklist

#### Architecture Review
- [ ] Design patterns clearly identified and justified
- [ ] Component responsibilities well-defined
- [ ] Interface contracts documented
- [ ] Cross-cutting concerns addressed
- [ ] Quality attributes considered

#### Implementation Review  
- [ ] Code examples complete and runnable
- [ ] Error handling comprehensive
- [ ] Performance considerations documented
- [ ] Security implications addressed
- [ ] Testing approach defined

#### Documentation Review
- [ ] Structure follows best practices
- [ ] Cross-references are accurate
- [ ] Diagrams are clear and consistent
- [ ] Writing is clear and concise
- [ ] Version information updated

### Change Management

#### Document Updates
When making changes:
1. Update version and date in document header
2. Update status table in relevant README
3. Review and update cross-references
4. Notify stakeholders of significant changes

#### Breaking Changes
For architectural changes:
1. Document rationale for change
2. Update all affected documents
3. Review impact on implementation
4. Plan migration strategy if needed

---

**Document Level:** Process Documentation  
**Last Updated:** 2025-01-08  
**Reviewers:** Documentation Lead, System Architect