"""
Infrastructure layer for Vortex.

This package contains infrastructure concerns including external service
integrations, data persistence, and cross-cutting infrastructure patterns.

Following Clean Architecture principles, this layer:
- Implements interfaces defined in the core layer
- Handles external dependencies (databases, APIs, file systems)
- Provides infrastructure services (resilience, storage, providers)
- Contains no business logic - only infrastructure concerns

Packages:
- providers: External data provider integrations (Barchart, Yahoo, IBKR)
- storage: Data persistence and storage implementations
- resilience: Infrastructure resilience patterns (circuit breaker, retry, etc.)
"""
