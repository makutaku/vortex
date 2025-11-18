# Documentation vs Implementation Audit Report

## Summary
Found 8 major mismatches between CLAUDE.md/README.md documentation and the actual codebase implementation.

---

## CRITICAL ISSUES

### 1. VALIDATE COMMAND OPTIONS MISMATCH
**Severity: HIGH** - Users following documentation will get command errors

**CLAUDE.md Claims (Line 282-283):**
```bash
vortex validate --enhanced  # Advanced validation with new formats
vortex validate --summary   # Validation summary display
```

**Actual Implementation (src/vortex/cli/commands/validate.py):**
```python
@click.option("--path", "-p", ...)                    # Required
@click.option("--provider", ...)                       # Optional provider filter
@click.option("--fix", is_flag=True, ...)             # Fix issues flag
@click.option("--detailed", is_flag=True, ...)        # Detailed results (NOT --enhanced)
@click.option("--format", choices=["table", "json", "csv"], ...) # Output format (NOT --summary)
```

**Impact:** Direct contradiction. Users running documented commands will get:
```
Error: No such option: --enhanced
Error: No such option: --summary
```

**What Users Should Use:**
- `vortex validate --path ./data --detailed` (instead of --enhanced)
- No direct summary option; use `--format json` and pipe output instead

---

### 2. RESILIENCE COMMAND INCOMPLETE IMPLEMENTATION
**Severity: MEDIUM** - Feature exists but partially unimplemented

**Documented (CLAUDE.md Line 295):**
```bash
vortex resilience recovery   # Error recovery statistics
```

**Actual Implementation (src/vortex/cli/commands/resilience.py, Line 167-175):**
```python
@resilience.command()
def recovery(format: str):
    """Show error recovery statistics."""
    ux = get_ux()
    
    # Note: This would need to be integrated with a global recovery manager
    # For now, show placeholder information
    ux.print("📊 Error Recovery Statistics")
    ux.print("\nThis feature requires integration with active recovery managers.")
    ux.print("Recovery stats will be available when operations are running.")
```

**Impact:** Users calling this command get a "not implemented yet" message instead of recovery stats.

---

### 3. UNDOCUMENTED WIZARD COMMAND
**Severity: MEDIUM** - Feature exists but not documented

**Actual Implementation Exists (src/vortex/cli/main.py, Line 167-223):**
```python
@cli.command()
@click.pass_context
def wizard(ctx: click.Context):
    """Interactive setup and command wizard."""
```

**CLAUDE.md Status:** No mention of `vortex wizard` command anywhere in documentation.

**Impact:** Users don't know this helpful feature exists.

**Documented In Code But Not In CLAUDE.md:**
- `vortex wizard` - Interactive setup wizard
- Available in main CLI help, but not explained in CLAUDE.md

---

### 4. UNDOCUMENTED HELP COMMAND
**Severity: LOW** - Help system exists but not documented

**Actual Implementation (src/vortex/cli/help.py):**
```python
@click.group()
def help():  # Command group with subcommands
    pass

@help.command()
def examples(command: Optional[str]):
    """Show command examples"""

@help.command()
def tutorial(topic: str):
    """Interactive tutorials"""

@help.command()
def tips(count: int):
    """Show tips and tricks"""

@help.command()
def commands():
    """List all commands"""

@help.command()
def quickstart():
    """Quick start guide"""
```

**CLAUDE.md Status:** Zero documentation for this entire help system.

**What Users Could Do (But Don't Know):**
```bash
vortex help examples download      # Download examples
vortex help tutorial getting_started
vortex help tips --count 5
vortex help quickstart
```

---

### 5. ASSET FILE FORMAT INCONSISTENCY
**Severity: MEDIUM** - Actual files don't match documentation

**Documentation (CLAUDE.md "Assets File Format"):**
```json
{
  "stock": {
    "AAPL": {
      "code": "AAPL",
      "tick_date": "1980-12-12",
      "start_date": "1980-12-12",
      "periods": "1d"                    // Single period shown
    }
  }
}
```

**Actual Asset Files - Inconsistent Period Format:**

`config/assets/yahoo.json`:
```json
"SPY": {"code": "SPY", "periods": null}           // Null value
"CADUSD": {"code": "CADUSD=X", "periods": "1d"}  // Single period
"AUDUSD": {"code": "^AUDUSD", "periods": ""}     // Empty string
```

`config/assets/barchart.json`:
```json
"SPY": {"code": "SPY", "periods": "1d,1h"}       // COMMA-SEPARATED (NOT documented!)
"AEX": {"code": "AE", "periods": "1d"}           // Single value
"AUD": {"code": "A6", "periods": ""}             // Empty string
```

**Impact:** Documentation shows single period values, but:
1. Files use empty strings, null, and comma-separated values inconsistently
2. Users creating assets files might use wrong format
3. Documentation doesn't explain periods can be comma-separated or what empty/null mean

---

### 6. DOWNLOAD COMMAND --RAW-DIR OPTION UNDOCUMENTED
**Severity: LOW** - Feature exists but not documented

**Actual Implementation (src/vortex/cli/commands/download.py, Line 95-98):**
```python
@click.option(
    "--raw-dir",
    type=click.Path(path_type=Path),
    help="Raw data directory for audit trail. Default: ./raw"
)
```

**CLAUDE.md Documentation:** No mention of `--raw-dir` in download command examples.

**README.md Documentation:** Mentions raw data storage features but not the `--raw-dir` CLI option.

**Impact:** Users can't easily set custom raw data directory from CLI without knowing about this hidden option.

---

### 7. OLD IMPORT PATH IN DOCUMENTATION
**Severity: LOW** - Documentation uses outdated import paths

**CLAUDE.md (Claims about architecture):**
```python
# Old path shown in examples
from vortex.plugins import get_provider_registry

# Actual location
from vortex.infrastructure.plugins import get_provider_registry
```

**Location:** Appears in Infrastructure Layer documentation section discussing plugins.

**Impact:** Code examples in documentation won't work if copied directly.

---

### 8. IBKR ASSET FILE PROVIDER-SPECIFIC FIELDS NOT PRESENT
**Severity: MEDIUM** - Documentation documents fields that don't exist in actual files

**Documentation (CLAUDE.md - Assets Configuration):**
```
**Provider-specific fields**:
  - **IBKR**: `conId`, `localSymbol`, `multiplier`, `baseCurrency`, `quoteCurrency`
```

**Actual IBKR Asset File (config/assets/ibkr.json):**
```json
{
  "forex": {
    "AUDUSD": {"code": "^AUDUSD", "tick_date": "2000-01-01", "start_date": "2000-01-01", "periods": ""}
  },
  "future": {
    "AUD": {"code": "A6", "cycle": "HMUZ", "tick_date": "2009-11-24", "periods": ""}
  },
  "stock": {
    "SPY": {"code": "SPY", "tick_date": "1993-01-29", "start_date": "1993-01-29", "periods": "1d,1h,30m,15m,5m"}
  }
}
```

**Actual Fields Used:** Only `code`, `cycle`, `tick_date`, `start_date`, `periods`
**Missing From Docs:** `conId`, `localSymbol`, `multiplier`, `baseCurrency`, `quoteCurrency` don't appear in actual file.

**Impact:** Users thinking they can configure IBKR-specific fields won't find them in the asset format.

---

## WARNINGS & OBSERVATIONS

### Legacy Python API Still Documented
**README.md Line 52-74** shows legacy Python API example:
```python
from vortex import get_barchart_downloads, create_bc_session
```

**Status:** This is marked as "Legacy Python API" so this is acceptable as historical reference, but users should be warned it's deprecated in favor of modern CLI.

---

## SUMMARY TABLE

| Issue | Severity | Mismatch Type | Fixable |
|-------|----------|---------------|---------|
| validate --enhanced/--summary | HIGH | Wrong options | Easy |
| resilience recovery | MEDIUM | Incomplete impl | Easy |
| Wizard command | MEDIUM | Undocumented | Easy |
| Help command | LOW | Undocumented | Easy |
| Asset period format | MEDIUM | Format inconsistency | Medium |
| Download --raw-dir | LOW | Undocumented | Easy |
| Import paths | LOW | Old examples | Easy |
| IBKR asset fields | MEDIUM | Documented non-existent fields | Medium |

---

## RECOMMENDATIONS

### Immediate Actions (CRITICAL)
1. **Update CLAUDE.md Line 282-283:** Change `--enhanced` to `--detailed` and remove `--summary`
2. **Add validate command note:** Explain that `--detailed` provides enhanced output
3. **Fix resilience recovery:** Either implement the feature or update documentation to mark it as "coming soon"

### High Priority (IMPORTANT)
4. **Document wizard command:** Add section explaining `vortex wizard` interactive setup
5. **Document help command:** Add section for help system with examples
6. **Clarify periods format:** Document that periods can be:
   - Empty string (no specific period)
   - Single value: "1d"
   - Comma-separated: "1d,1h,15m"
   - Null/not specified

### Medium Priority
7. **Document IBKR fields:** Either add missing fields to IBKR asset file OR remove from documentation
8. **Document --raw-dir:** Add to download command examples in CLAUDE.md
9. **Update import paths:** Use correct `vortex.infrastructure.plugins` path in architecture docs

### Low Priority
10. **Legacy API:** Keep as-is but ensure marked clearly as deprecated

