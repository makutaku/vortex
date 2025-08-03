# High-Level Design Documents

## 🏗️ Architecture Documentation

### Core Design Documents
1. **[System Overview](01-system-overview.md)** - Big picture architecture and context
2. **[Component Architecture](02-component-architecture.md)** - Major components and relationships
3. **[Data Flow Design](03-data-flow-design.md)** - How data moves through the system
4. **[Provider Abstraction](04-provider-abstraction.md)** - Data provider interface design
5. **[Storage Architecture](05-storage-architecture.md)** - Data persistence and retrieval
6. **[Security Design](06-security-design.md)** - Authentication and data protection
7. **[Deployment Architecture](07-deployment-architecture.md)** - Container and scaling design
8. **[Integration Design](08-integration-design.md)** - External system interfaces

### Document Status
| Document | Status | Last Updated | Reviewers |
|----------|--------|--------------|-----------|
| [System Overview](01-system-overview.md) | ✅ **Updated** | 2025-08-03 | System Architect, Lead Developer, DevOps Lead |
| [Component Architecture](02-component-architecture.md) | ✅ **Updated** | 2025-08-03 | Lead Developer, Senior Engineer, QA Lead |
| [Data Flow Design](03-data-flow-design.md) | ⚠️ Needs Update | 2025-01-08 | Senior Developer, Data Engineer, QA Lead |
| [Provider Abstraction](04-provider-abstraction.md) | ⚠️ Needs Update | 2025-01-08 | Senior Developer, Integration Architect, QA Lead |
| [Storage Architecture](05-storage-architecture.md) | ⚠️ Needs Update | 2025-01-08 | Senior Developer, Data Engineer, Infrastructure Lead |
| [Security Design](06-security-design.md) | ⚠️ Needs Update | 2025-01-08 | Security Architect, Compliance Officer, DevOps Lead |
| [Deployment Architecture](07-deployment-architecture.md) | ⚠️ Needs Update | 2025-01-08 | DevOps Lead, Security Architect, Infrastructure Team |
| [Integration Design](08-integration-design.md) | ⚠️ Needs Update | 2025-01-08 | Integration Architect, Senior Developer, DevOps Lead |

### Reading Guide

**For Architects:** Start with [System Overview](01-system-overview.md) → [Component Architecture](02-component-architecture.md)

**For Backend Developers:** [Component Architecture](02-component-architecture.md) → [Data Flow Design](03-data-flow-design.md) → [Provider Abstraction](04-provider-abstraction.md)

**For DevOps Engineers:** [Deployment Architecture](07-deployment-architecture.md) → [System Overview](01-system-overview.md#deployment-overview) → [Security Design](06-security-design.md)

**For CLI Development:** [System Overview](01-system-overview.md) → [Component Architecture](02-component-architecture.md) → [Component Implementation](../lld/01-component-implementation.md#cli-implementation)

**For Security Review:** [Security Design](06-security-design.md) → [Integration Design](08-integration-design.md)

### Recent Updates (2025-08-03)

**✅ Completed:**
- **System Overview**: Updated with modern CLI architecture, Docker deployment, uv package management
- **Component Architecture**: Reflects actual Click CLI, TOML configuration, single dispatch patterns

**🔄 Priority Updates Needed:**
- **Provider Abstraction**: Update to reflect single dispatch methods and actual provider implementations
- **Storage Architecture**: Document dual CSV/Parquet storage with bridge pattern
- **Deployment Architecture**: Add comprehensive Docker Compose setup and container orchestration

## 📋 Document Standards

### HLD Content Guidelines

**✅ HLD Documents INCLUDE:**
- **System architecture** and component relationships
- **Design patterns** and architectural principles
- **Interface contracts** and abstractions
- **Quality attributes** (performance, security, scalability)
- **Cross-cutting concerns** and system-wide decisions
- **Mermaid diagrams** for architectural visualization
- **Technology choices** and rationale
- **Integration patterns** between major components

**❌ HLD Documents AVOID:**
- Detailed code implementations
- Specific library configurations
- Unit test specifications
- Database schemas and file formats
- Implementation algorithms
- Method-level details

### Architecture Documentation Best Practices

**Focus on "WHAT" and "WHY":**
- What components exist and how they relate
- Why specific architectural decisions were made
- What quality attributes are prioritized
- What patterns solve specific architectural problems

**Use Architectural Patterns:**
- Strategy Pattern for provider abstraction
- Factory Pattern for component creation
- Observer Pattern for event handling
- Repository Pattern for data access

**Diagram Standards:**
- Component diagrams show relationships, not implementations
- Sequence diagrams show high-level message flows
- Deployment diagrams show system topology
- Use consistent styling and notation

### Cross-References
- Use relative links: `[Component Architecture](02-component-architecture.md)`
- Include section anchors: `[Storage Layer](05-storage-architecture.md#storage-layer)`
- Reference PRD requirements: `See [REQ-001](../../requirements/prd/product-requirements.md#req-001)`
- Link to LLD for implementation details: `*Implementation details in [Component Implementation](../lld/01-component-implementation.md)*`

### Architecture Diagrams
- Use Mermaid for simple diagrams
- External tools (draw.io, Lucidchart) for complex diagrams
- Include both source and rendered versions
- Focus on component relationships, not internal structure

### Update Process
- Update HLD when making architectural changes
- Cross-reference related document updates
- Maintain version history and change rationale
- Review impact on dependent LLD documents