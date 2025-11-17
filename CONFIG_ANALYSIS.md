# Vortex Configuration Consistency Analysis

## Executive Summary
This analysis examined all configuration-related files in the Vortex project including:
- TOML configuration files (examples, environments, pyproject.toml)
- Environment variable naming and implementation (VORTEX_*)
- Docker compose configurations
- Assets file structure and format
- Configuration documentation vs implementation

**Major Issues Found: 3 | Minor Issues Found: 5 | Inconsistencies: 7**

---

## 1. ENVIRONMENT VARIABLES ISSUES

### Issue 1.1: VORTEX_METRICS_PATH Not Implemented (HIGH SEVERITY)
**Location:** CLAUDE.md line 446
**Documentation States:**
```bash
export VORTEX_METRICS_PATH="/metrics"
```

**Implementation Status:** ❌ NOT IMPLEMENTED
- The `VortexSettings` class (models.py) has NO `vortex_metrics_path` field with `VORTEX_METRICS_PATH` alias
- Current code shows `metrics.path` is a hardcoded field in `MetricsConfig` with default "/metrics"
- Cannot be overridden via environment variable
- The CLI code uses `config.general.metrics.path` but has no way to set it from environment

**Impact:** Users cannot customize metrics path via environment variables as documented
**File:** `/home/user/vortex/src/vortex/core/config/models.py` (missing from VortexSettings)

---

### Issue 1.2: VORTEX_LOG_LEVEL Duplicate/Ambiguous (MEDIUM SEVERITY)
**Documentation:** CLAUDE.md mentions both:
- `VORTEX_LOG_LEVEL` (line 434)
- `VORTEX_LOGGING_LEVEL` (line 436)

**Implementation Shows:**
```python
vortex_log_level: Optional[str] = Field(None, alias="VORTEX_LOG_LEVEL")
vortex_logging_level: Optional[str] = Field(None, alias="VORTEX_LOGGING_LEVEL")
```

**Issue:** TWO different environment variables both control logging level with unclear precedence/priority
- `VORTEX_LOG_LEVEL` mapped to `general.log_level` 
- `VORTEX_LOGGING_LEVEL` mapped to `general.logging.level`
- Code applies both, last one wins - undefined behavior

**Recommendation:** Standardize on ONE of these

---

### Issue 1.3: Missing Timeout Environment Variables
**Environment Config Files Reference:** (production.toml, development.toml, testing.toml)
- `timeout = 30` (Barchart, IBKR, Yahoo)

**Models Implementation:**
- ✅ Barchart timeout is in BarchartConfig
- ✅ IBKR timeout is in IBKRConfig  
- ❌ Yahoo timeout NOT in config models (no VORTEX_YAHOO_TIMEOUT)
- ❌ No VORTEX_BARCHART_TIMEOUT, VORTEX_IBKR_TIMEOUT environment variables

**Files Affected:**
- `/home/user/vortex/config/environments/production.toml:20,26,27`
- `/home/user/vortex/config/environments/development.toml:17,22,24`
- `/home/user/vortex/config/environments/testing.toml:17,23,24`
- `/home/user/vortex/src/vortex/core/config/models.py` (no timeout env vars)

---

### Issue 1.4: Obsolete Configuration Fields in Environment Files (MEDIUM SEVERITY)
**Location:** All environment config files

These fields are defined but NOT in the core VortexConfig models and cannot be set via environment:

```toml
# In production.toml, development.toml, testing.toml
retry_attempts = 5
rate_limit_delay = 2.0
```

**Status:** These are provider-level configs (in `BarchartProviderConfig`, `YahooProviderConfig`, etc.) but are NOT exposed as environment variables or TOML config options at the top level

**Files:**
- `production.toml` lines 21-22, 27-28
- `development.toml` lines 18, 22, 24
- `testing.toml` lines 16-17, 22-24

---

## 2. TOML CONFIGURATION FILES INCONSISTENCIES

### Issue 2.1: Two Different Example TOML Files (CONFUSING)
**Files:**
- `/home/user/vortex/config/config.toml.example` (comprehensive, 75 lines)
- `/home/user/vortex/config/examples/config.toml.example` (minimal, 19 lines)

**Problem:**
- Both exist at different paths
- Different content/examples
- Users might use wrong file
- Inconsistent defaults shown

**Content Comparison:**
| Feature | config.toml.example | examples/config.toml.example |
|---------|-------------------|--------------------------|
| Structure | `[general]` with detailed sections | Top-level keys |
| Logging | Detailed `[general.logging]` | Missing |
| Raw storage | Documented | Missing |
| Metrics | Documented | Missing |
| Yahoo settings | Has `enabled=true` | Missing |
| IBKR settings | Has `timeout=30` | Has `timeout=30` |

**Recommendation:** Keep ONE authoritative example, remove the other or clearly document which is current.

---

### Issue 2.2: Missing Raw Data Config in Main Example (MEDIUM SEVERITY)
**File:** `/home/user/vortex/config/config.toml.example` 

**Missing Section:** No `[general.raw]` configuration section example
**But Documentation Shows:** CLAUDE.md lines 422-427 documents:
```toml
[general.raw]
enabled = true
retention_days = 30
compress = true
include_metadata = true
```

**Impact:** Users won't know about raw data configuration option from main example

---

### Issue 2.3: Logging Config Format Inconsistency
**config.toml.example (lines 19-25):**
```toml
[general.logging]
level = "INFO"
format = "console"
output = ["console"]  # Array format
```

**production.toml (lines 10-12):**
```toml
format = "json"
output = "file"  # String format (should be array)
```

**Problem:** `output` should be an array per the schema, but production.toml uses string. This may cause validation errors.

---

### Issue 2.4: Environment Files Reference Non-Standard Fields
**Files:** `config/environments/*.toml`

**Example from production.toml, lines 37-42:**
```toml
[production]
performance_monitoring = true
metrics_enabled = true
health_checks_enabled = true
circuit_breaker_enabled = true

[monitoring]
enable_tracing = true
enable_metrics = true
metrics_port = 8080
health_check_port = 8081
```

**Problem:** These sections `[production]` and `[monitoring]` are NOT in VortexConfig models
- They'll be rejected with `"extra": "forbid"` setting in the model
- These configuration values cannot be used by the application

---

## 3. ASSETS FILES INCONSISTENCIES

### Issue 3.1: Duplicate Assets Directories (CONFUSING)
**Directories:**
- `/home/user/vortex/assets/`
- `/home/user/vortex/config/assets/`

**Content:** Both contain identical asset files:
- `barchart.json` (identical)
- `yahoo.json` (identical)
- `ibkr.json` (identical)
- `default.json` (identical)

**Problem:** Two copies of same files create confusion about which is "canonical"

**Code References Both:** 
- `symbol_resolver.py` checks both: `assets/{provider}.json` and `config/assets/{provider}.json`
- `download_utils.py` only checks: `config/assets/{provider}.json`

**Inconsistent Asset Path Loading:**
```python
# In symbol_resolver.py (line 177-180):
possible_paths = [
    Path(f"assets/{provider}.json"),           # Checks root assets/
    Path(f"config/assets/{provider}.json"),    # Checks config/assets/
    Path("assets/default.json"),               # Checks root assets/
    Path("config/assets/default.json")         # Checks config/assets/
]

# In download_utils.py (line 56-62):
provider_file = Path(f"config/assets/{provider}.json")  # Only checks config/assets/
default_file = Path("config/assets/default.json")
```

**Impact:** Different code paths may resolve to different asset files

---

### Issue 3.2: Inconsistent Asset File Formats (MINOR)
**barchart.json:**
```json
"periods": "1d,1h"  // String format
```

**yahoo.json:**
```json
"periods": null     // null instead of string
```

**ibkr.json:**
```json
"periods": ""       // Empty string instead of null
```

**Inconsistency:** Same field uses 3 different formats across files
- String: `"1d,1h"`
- Null: `null`
- Empty string: `""`

**Problem:** Code may not handle all three formats consistently

---

### Issue 3.3: Asset File Forex Code Inconsistency
**barchart.json:**
```json
"AUDUSD": {"code": "^AUDUSD", ...}
```

**yahoo.json and ibkr.json:**
```json
"AUDUSD": {"code": "^AUDUSD", ...}  // Same as barchart
"CADUSD": {"code": "CADUSD=X", ...} // Different format
```

**Problem:** Same instruments use different code formats depending on file
- barchart uses: `^AUDUSD`
- yahoo/ibkr use: `CADUSD=X`
- These are provider-specific codes but mixing in same asset file is confusing

---

## 4. DOCKER COMPOSE INCONSISTENCIES

### Issue 4.1: docker-compose.yml vs docker-compose.monitoring.yml Environment Variables
**docker-compose.yml (lines 61-66):**
```yaml
VORTEX_OUTPUT_DIR: /data
VORTEX_SCHEDULE: ...
VORTEX_RUN_ON_STARTUP: ...
VORTEX_DOWNLOAD_ARGS: ...
# VORTEX_DEFAULT_PROVIDER: ...  (commented)
```

**docker-compose.monitoring.yml (lines 30-36):**
```yaml
VORTEX_METRICS_ENABLED: "true"
VORTEX_METRICS_PORT: "8000"
VORTEX_OUTPUT_DIR: /data
VORTEX_SCHEDULE: ...
VORTEX_RUN_ON_STARTUP: ...
VORTEX_DOWNLOAD_ARGS: ...
VORTEX_LOG_LEVEL: ...  (DIFFERENT from main)
```

**Problem:** Inconsistent environment variables between the two files
- Monitoring version adds `VORTEX_LOG_LEVEL` but main doesn't
- Documentation references different sets

---

### Issue 4.2: Missing Container Metrics Path Configuration
**docker-compose.monitoring.yml line 30:**
```yaml
VORTEX_METRICS_ENABLED: "true"
VORTEX_METRICS_PORT: "8000"
# Missing: VORTEX_METRICS_PATH (but can't set it - see Issue 1.1)
```

**Related to:** Issue 1.1 - VORTEX_METRICS_PATH environment variable not implemented

---

## 5. DOCUMENTATION vs IMPLEMENTATION GAPS

### Issue 5.1: CLAUDE.md Documents Features Not in Config (MEDIUM SEVERITY)
**CLAUDE.md Claims Support For (Section: Environment Variables):**

```bash
# Raw data storage (NEW)
export VORTEX_RAW_ENABLED=true
export VORTEX_RAW_RETENTION_DAYS=30
export VORTEX_RAW_BASE_DIRECTORY=./raw
export VORTEX_RAW_COMPRESS=true
export VORTEX_RAW_INCLUDE_METADATA=true

# Monitoring and metrics (NEW)
export VORTEX_METRICS_ENABLED=true
export VORTEX_METRICS_PORT=8000
export VORTEX_METRICS_PATH="/metrics"  # ❌ Not implemented
```

**Implementation Status:**
- ✅ VORTEX_RAW_ENABLED - Implemented
- ✅ VORTEX_RAW_RETENTION_DAYS - Implemented
- ❌ VORTEX_RAW_BASE_DIRECTORY - Field named `VORTEX_RAW_DIR` (not `BASE_DIRECTORY`)
- ✅ VORTEX_RAW_COMPRESS - Implemented
- ✅ VORTEX_RAW_INCLUDE_METADATA - Implemented
- ✅ VORTEX_METRICS_ENABLED - Implemented
- ✅ VORTEX_METRICS_PORT - Implemented
- ❌ VORTEX_METRICS_PATH - Not implemented

**Field Name Mismatch:** 
- Doc says: `VORTEX_RAW_BASE_DIRECTORY`
- Code has: `VORTEX_RAW_DIR` and `raw_directory` in GeneralConfig

---

### Issue 5.2: TOML Configuration Documentation Example Mismatch
**CLAUDE.md Section: "TOML Configuration (Recommended):" shows:**

```toml
# Raw data storage configuration (NEW)
[general.raw]
enabled = true
retention_days = 30
compress = true
include_metadata = true
```

**But main example file (`config.toml.example`) LACKS THIS SECTION**

**Problem:** Users following CLAUDE.md won't find this config in the provided example file

---

## 6. CONFIGURATION PATH RESOLUTION ISSUES

### Issue 6.1: Inconsistent Config File Location Logic
**ConfigManager (manager.py lines 74-86):**
```python
# Uses standard XDG/user config path
config_dir = Path.home() / ".config" / "vortex"

# Falls back to
config_dir = Path.cwd() / ".vortex"

# Then no persistent config available
self.config_file = None
```

**But CLI documentation in CLAUDE.md refers to:**
```bash
cp config/config.toml.example config/config.toml
```

**Problem:** Documentation assumes `config/` relative path, but code looks for `~/.config/vortex/`

---

### Issue 6.2: Assets Path Resolution Has Duplicated Logic
**Symbol Resolver vs Download Utils:**
- `symbol_resolver.py` has `_get_default_assets_file()` method
- `download_utils.py` has `get_default_assets_file()` function  
- Both do similar work, duplicated code with different logic

**Duplication Points:**
- Symbol resolver checks 4 paths: `assets/`, `config/assets/` (both provider and default)
- Download utils only checks `config/assets/`
- Can lead to different behavior

---

## 7. SUMMARY OF INCONSISTENCIES TABLE

| # | Issue | Severity | Type | Component |
|---|-------|----------|------|-----------|
| 1.1 | VORTEX_METRICS_PATH not implemented | HIGH | Env Var Missing | models.py |
| 1.2 | VORTEX_LOG_LEVEL ambiguity | MEDIUM | Dual Env Vars | models.py |
| 1.3 | Missing timeout env variables | MEDIUM | Partial Implementation | models.py |
| 1.4 | Obsolete retry/rate-limit in env files | MEDIUM | Legacy Config | environments/*.toml |
| 2.1 | Two example TOML files | MEDIUM | Duplicate Files | config/*.toml |
| 2.2 | Missing raw data in main example | MEDIUM | Incomplete Docs | config.toml.example |
| 2.3 | Logging output format inconsistency | LOW | Type Mismatch | environments/production.toml |
| 2.4 | Non-standard sections in env files | HIGH | Invalid Config | environments/*.toml |
| 3.1 | Duplicate assets directories | MEDIUM | Confusing Structure | assets/ & config/assets/ |
| 3.2 | Inconsistent periods field format | LOW | Type Variation | *.json |
| 3.3 | Inconsistent forex codes | LOW | Data Variation | *.json |
| 4.1 | Docker compose env var mismatch | MEDIUM | Inconsistency | docker-compose.yml |
| 4.2 | Missing metrics path in docker | HIGH | Related to 1.1 | docker-compose.monitoring.yml |
| 5.1 | Env var name mismatch in docs | MEDIUM | Docs vs Code | CLAUDE.md vs models.py |
| 5.2 | Raw storage config not in example | MEDIUM | Missing Docs | config.toml.example |
| 6.1 | Config path location mismatch | MEDIUM | Docs vs Code | CLAUDE.md vs ConfigManager |
| 6.2 | Duplicated asset resolution logic | LOW | Code Duplication | symbol_resolver vs download_utils |

---

## RECOMMENDATIONS

### High Priority
1. **Implement VORTEX_METRICS_PATH** environment variable in VortexSettings
2. **Remove invalid sections** from environment TOML files (`[production]`, `[monitoring]`) or add them to VortexConfig
3. **Remove one assets directory** - keep only `/config/assets/` or consolidate duplication
4. **Fix environment variable naming** - standardize `VORTEX_RAW_BASE_DIRECTORY` vs `VORTEX_RAW_DIR`

### Medium Priority  
1. **Choose one example TOML** - remove `/config/examples/config.toml.example`
2. **Standardize log level** - use VORTEX_LOGGING_LEVEL consistently
3. **Add raw data config** to main example file
4. **Implement timeout environment variables** for all providers
5. **Add asset format validation** for `periods` field consistency

### Low Priority
1. **Consolidate asset resolution logic** - merge `symbol_resolver` and `download_utils` implementations
2. **Standardize forex codes** or document why they differ
3. **Fix logging output type** in production.toml (use array format)
4. **Document config path logic** clearly in CLAUDE.md

---

## FILES REQUIRING UPDATES

1. `/home/user/vortex/src/vortex/core/config/models.py` - Add missing environment variables
2. `/home/user/vortex/config/config.toml.example` - Add missing sections
3. `/home/user/vortex/config/examples/config.toml.example` - Remove or merge
4. `/home/user/vortex/config/environments/production.toml` - Remove invalid sections
5. `/home/user/vortex/config/environments/development.toml` - Remove invalid sections
6. `/home/user/vortex/config/environments/testing.toml` - Remove invalid sections
7. `/home/user/vortex/assets/` - Consider removing duplicate
8. `/home/user/vortex/docker/docker-compose.monitoring.yml` - Standardize env vars
9. `/home/user/vortex/CLAUDE.md` - Update env var docs to match implementation
10. `/home/user/vortex/src/vortex/cli/utils/download_utils.py` - Consolidate with symbol_resolver

