# Distributed Usage Quota Management System Design

## Problem Statement

We need to share a single Barchart subscription (250 daily downloads) across multiple environments (prod, test, dev, e2e) while:
- Preventing any environment from consuming all credits
- Prioritizing production usage (most credits)
- Allowing other environments to share the remainder
- Maintaining system reliability and monitoring

## Architecture Overview

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│    PROD     │    │  Quota Manager   │    │    TEST     │
│ (quota: 180)│◄──►│   (Redis/DB)     │◄──►│ (quota: 30) │
└─────────────┘    │                  │    └─────────────┘
                   │  Daily: 250      │    
┌─────────────┐    │  Used: X         │    ┌─────────────┐
│     DEV     │◄──►│  Available: Y    │◄──►│     E2E     │
│ (quota: 30) │    │                  │    │ (quota: 10) │
└─────────────┘    └──────────────────┘    └─────────────┘
```

## Quota Allocation Strategy

| Environment | Allocated Credits | Percentage | Priority |
|-------------|------------------|------------|----------|
| Production  | 180              | 72%        | 1 (Highest) |
| Test        | 30               | 12%        | 2 |
| Development | 30               | 12%        | 3 |
| E2E Tests   | 10               | 4%         | 4 (Lowest) |
| **Total**   | **250**          | **100%**   | |

### Spillover Rules
- Each environment has a guaranteed allocation
- If an environment exceeds its allocation, it can use unused quota from other environments
- Global limit of 250 downloads/day is never exceeded
- Higher priority environments get preference during spillover scenarios

## Core Components

### 1. Centralized Quota Manager Service

#### QuotaManager Interface
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class EnvironmentQuota:
    environment: str
    allocated_quota: int
    used_quota: int
    priority: int  # 1=highest (prod), 4=lowest (e2e)
    
@dataclass
class QuotaAllocation:
    total_daily_limit: int = 250
    allocations: Dict[str, int] = None
    
    def __post_init__(self):
        if self.allocations is None:
            self.allocations = {
                "prod": 180,  # 72% for production
                "test": 30,   # 12% for testing
                "dev": 30,    # 12% for development
                "e2e": 10     # 4% for e2e tests
            }

class QuotaManager(ABC):
    @abstractmethod
    def request_quota(self, environment: str, requested_amount: int = 1) -> bool:
        """Request quota allocation for downloads."""
        pass
    
    @abstractmethod
    def get_usage_status(self, environment: str) -> EnvironmentQuota:
        """Get current usage status for environment."""
        pass
    
    @abstractmethod
    def get_global_status(self) -> Dict[str, any]:
        """Get global quota status across all environments."""
        pass
```

#### Redis-Based Implementation
```python
class RedisQuotaManager(QuotaManager):
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 allocation: QuotaAllocation = None):
        self.redis_client = redis.from_url(redis_url)
        self.allocation = allocation or QuotaAllocation()
        self._initialize_daily_quotas()
    
    def request_quota(self, environment: str, requested_amount: int = 1) -> bool:
        """Request quota with environment-specific limits and spillover."""
        # Algorithm:
        # 1. Check if global limit would be exceeded
        # 2. If within environment allocation - always allow
        # 3. If exceeding environment allocation - check spillover capacity
        # 4. Atomically increment counters if approved
        pass
    
    def get_usage_status(self, environment: str) -> EnvironmentQuota:
        """Get usage status for specific environment."""
        pass
    
    def get_global_status(self) -> Dict[str, any]:
        """Get comprehensive quota status."""
        pass
```

### 2. Enhanced Barchart Provider Integration

#### Updated Provider Constructor
```python
class BarchartDataProvider(DataProvider):
    def __init__(self, username: str, password: str, 
                 environment: str = "prod",
                 quota_manager: QuotaManager = None,
                 daily_download_limit: int = None):
        
        self.environment = environment
        self.quota_manager = quota_manager or self._create_default_quota_manager()
        
        # Use environment-specific allocation if quota manager available
        if quota_manager and not daily_download_limit:
            env_status = quota_manager.get_usage_status(environment)
            daily_download_limit = env_status.allocated_quota
        
        self.daily_limit = daily_download_limit or ProviderConstants.Barchart.DEFAULT_DAILY_DOWNLOAD_LIMIT
```

#### Pre-Download Quota Checking
```python
def _check_quota_availability(self, requested_downloads: int = 1) -> bool:
    """Check if quota is available before making request."""
    if not self.quota_manager:
        return True  # Fallback to server-side enforcement
    
    return self.quota_manager.request_quota(self.environment, requested_downloads)

def _fetch_historical_data_(self, instrument: str, frequency_attributes: FrequencyAttributes,
                           start_date, end_date, url: str, tz: str) -> Optional[DataFrame]:
    """Enhanced with quota checking."""
    
    # Check quota before attempting download
    if not self._check_quota_availability(1):
        # Raise enhanced error with quota context
        status = self.quota_manager.get_usage_status(self.environment)
        global_status = self.quota_manager.get_global_status()
        
        raise AllowanceLimitExceededError(
            provider="barchart",
            current_usage=status.used_quota,
            daily_limit=status.allocated_quota,
            additional_context={
                "environment": self.environment,
                "global_used": global_status["global_used"],
                "global_limit": global_status["global_limit"]
            }
        )
    
    # Proceed with download...
```

### 3. Configuration Updates

#### Environment-Specific Config
```python
@dataclass
class BarchartProviderConfig:
    username: str = None
    password: str = None
    environment: str = "prod"  # New field
    quota_manager_enabled: bool = True  # New field
    daily_limit: int = None  # Override automatic allocation
    
@dataclass
class QuotaManagerConfig:
    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    custom_allocations: Dict[str, int] = None
    
@dataclass
class ProvidersConfig:
    barchart: BarchartProviderConfig = field(default_factory=BarchartProviderConfig)
    quota: QuotaManagerConfig = field(default_factory=QuotaManagerConfig)
```

#### TOML Configuration Files
```toml
# config/environments/prod.toml
[providers.barchart]
username = "shared_username"
password = "shared_password"
environment = "prod"
quota_manager_enabled = true

[providers.quota]
enabled = true
redis_url = "redis://shared-redis:6379"

# config/environments/test.toml
[providers.barchart]
environment = "test"
# ... same credentials

# config/environments/dev.toml
[providers.barchart]
environment = "dev"

# config/environments/e2e.toml
[providers.barchart]
environment = "e2e"
```

### 4. CLI Quota Management Commands

#### Quota Status Command
```bash
# Show global quota status
vortex quota status

# Show specific environment
vortex quota status --environment prod

# Watch in real-time
vortex quota status --watch
```

#### Implementation Structure
```python
@click.group()
def quota():
    """Manage distributed quota allocation across environments."""
    pass

@quota.command()
@click.option('--environment', '-e', help='Specific environment to check')
@click.option('--watch', '-w', is_flag=True, help='Watch quota usage in real-time')
def status(environment, watch):
    """Show current quota usage status."""
    # Create rich tables showing:
    # - Per-environment allocated/used/available
    # - Global usage summary
    # - Usage percentages
    # - Real-time updates if --watch

@quota.command()
@click.option('--environment', '-e', required=True)
@click.option('--amount', '-a', type=int, required=True)
def allocate(environment, amount):
    """Allocate additional quota to an environment."""
    # Dynamic quota reallocation

@quota.command()
def reset():
    """Reset daily quota counters (admin only)."""
    # Manual quota reset functionality
```

### 5. Monitoring and Alerting

#### Quota Health Monitoring
```python
class QuotaMonitor:
    def check_quota_health(self) -> Dict[str, any]:
        """Check quota health across environments."""
        # Return structure:
        # {
        #   "status": {...},
        #   "alerts": [
        #     {"level": "warning", "environment": "dev", "message": "75% used"},
        #     {"level": "critical", "environment": "global", "message": "85% used"}
        #   ],
        #   "health": "critical|warning|healthy"
        # }
```

#### Alert Thresholds
- **Warning**: Environment >75% of allocation used
- **Critical**: Environment >90% of allocation used
- **Critical**: Global usage >85% of daily limit

### 6. Data Storage Schema

#### Redis Key Structure
```
barchart:quota:YYYYMMDD:ENVIRONMENT:used     # Per-environment daily usage
barchart:quota:YYYYMMDD:global:used          # Global daily usage
barchart:quota:YYYYMMDD:allocations          # Daily allocation overrides
```

#### TTL Management
- All quota keys expire after 24 hours
- Automatic cleanup of old quota data
- Daily reset at midnight UTC

### 7. Fallback and Error Handling

#### Graceful Degradation
1. **Quota Manager Unavailable**: Fall back to server-side Barchart enforcement
2. **Redis Connection Issues**: Log warnings but allow downloads
3. **Configuration Errors**: Use default allocations
4. **Network Partitions**: Cache last known quota status locally

#### Error Scenarios
```python
# Enhanced error context
class AllowanceLimitExceededError(DataProviderError):
    def __init__(self, provider: str, current_usage: int, daily_limit: int,
                 additional_context: Dict = None):
        self.additional_context = additional_context or {}
        # Include environment, global status, spillover availability
```

### 8. Deployment Strategy

#### Phase 1: Infrastructure Setup
- Deploy Redis quota manager service
- Set up monitoring and alerting
- Create configuration files

#### Phase 2: Monitoring Mode
- Deploy updated providers in "monitoring mode"
- Quota checking enabled but doesn't block downloads
- Gather baseline usage patterns

#### Phase 3: Gradual Enforcement
- Enable quota enforcement environment by environment:
  1. E2E tests (lowest risk)
  2. Development
  3. Test
  4. Production (last, highest confidence)

#### Phase 4: Full Operation
- All environments using quota management
- Monitoring dashboards active
- Automated alerting configured

### 9. Benefits and Guarantees

#### Guarantees
✅ **No Environment Starvation**: Each environment has minimum guaranteed quota
✅ **Production Priority**: 72% allocation ensures prod gets majority of credits
✅ **Global Limit Enforcement**: Never exceed 250 downloads/day across all environments
✅ **Spillover Efficiency**: Unused quota automatically available to other environments

#### Operational Benefits
✅ **Real-time Visibility**: Live quota status across all environments
✅ **Proactive Alerting**: Early warning before quota exhaustion
✅ **Audit Trail**: Complete download tracking and attribution
✅ **Dynamic Management**: Ability to adjust allocations without code changes
✅ **Graceful Degradation**: System continues working if quota manager fails

### 10. Implementation Considerations

#### Performance
- Redis operations are atomic and fast (<1ms typically)
- Minimal latency added to download requests
- Connection pooling for Redis client

#### Security
- Redis authentication and TLS encryption
- Environment isolation in quota keys
- Audit logging for quota modifications

#### Scalability
- Redis can handle thousands of quota requests per second
- Horizontal scaling possible with Redis Cluster
- Stateless quota manager allows multiple instances

### 11. Alternative Implementations

#### File-Based Quota Manager
For environments without Redis:
```python
class FileQuotaManager(QuotaManager):
    """File-based quota manager using atomic file operations."""
    # Use file locking for atomic quota operations
    # JSON storage for quota state
    # Suitable for single-instance deployments
```

#### Database-Based Quota Manager
For enterprise environments:
```python
class DatabaseQuotaManager(QuotaManager):
    """Database-based quota manager with ACID guarantees."""
    # PostgreSQL/MySQL backend
    # Transactional quota operations
    # Enhanced reporting capabilities
```

## Conclusion

This distributed quota management system provides a robust solution for sharing Barchart subscription credits across multiple environments while ensuring production workloads get priority access and preventing any single environment from exhausting the shared quota pool.

The design emphasizes reliability, observability, and operational simplicity while providing the flexibility to adjust quota allocations based on changing business needs.