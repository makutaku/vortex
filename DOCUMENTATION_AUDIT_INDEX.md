# Documentation Audit - Detailed File Index

This document maps all audit findings to exact file locations and line numbers for easy reference and remediation.

## File Locations Quick Reference

### Documentation Files
- **Primary Doc:** `/home/user/vortex/CLAUDE.md` (30KB, checked extensively)
- **README:** `/home/user/vortex/README.md` (8.1KB)
- **This Audit:** `/home/user/vortex/DOCUMENTATION_AUDIT.md` (8.9KB)

### CLI Implementation Files
- **Main CLI:** `/home/user/vortex/src/vortex/cli/main.py` (13KB)
- **Download Cmd:** `/home/user/vortex/src/vortex/cli/commands/download.py` (8.9KB)
- **Validate Cmd:** `/home/user/vortex/src/vortex/cli/commands/validate.py` (12KB)
- **Resilience Cmd:** `/home/user/vortex/src/vortex/cli/commands/resilience.py` (9.7KB)
- **Help System:** `/home/user/vortex/src/vortex/cli/help.py` (20KB)

### Asset Configuration Files
- **Yahoo Assets:** `/home/user/vortex/config/assets/yahoo.json` (1.1KB)
- **Barchart Assets:** `/home/user/vortex/config/assets/barchart.json` (1KB)
- **IBKR Assets:** `/home/user/vortex/config/assets/ibkr.json` (1KB)
- **Default Assets:** `/home/user/vortex/config/assets/default.json` (1.1KB)

---

## Issue #1: VALIDATE COMMAND OPTIONS MISMATCH
**Severity: CRITICAL**

### Documentation Claims
- **File:** `/home/user/vortex/CLAUDE.md`
- **Lines:** 282-283
- **Text:**
  ```bash
  vortex validate --enhanced  # Advanced validation with new formats
  vortex validate --summary   # Validation summary display
  ```

### Actual Implementation
- **File:** `/home/user/vortex/src/vortex/cli/commands/validate.py`
- **Lines:** 50-78
- **Options defined:**
  ```python
  @click.option("--path", "-p", ...)                    # Line 51-56
  @click.option("--provider", ...)                       # Line 57-61
  @click.option("--fix", is_flag=True, ...)             # Line 62-66
  @click.option("--detailed", is_flag=True, ...)        # Line 67-71 (NOT --enhanced)
  @click.option("--format", choices=[...], ...)         # Line 72-78 (NOT --summary)
  ```

**Fix Required:**
- Change CLAUDE.md Line 282: `--enhanced` → `--detailed`
- Change CLAUDE.md Line 283: `--summary` → Remove or explain `--format json` alternative

---

## Issue #2: RESILIENCE RECOVERY INCOMPLETE
**Severity: MEDIUM**

### Documentation
- **File:** `/home/user/vortex/CLAUDE.md`
- **Line:** 295
- **Text:** `vortex resilience recovery   # Error recovery statistics`

### Actual Implementation
- **File:** `/home/user/vortex/src/vortex/cli/commands/resilience.py`
- **Lines:** 160-175
- **Code:**
  ```python
  @resilience.command()
  def recovery(format: str):
      """Show error recovery statistics."""
      # NOTE: This would need to be integrated with a global recovery manager
      # For now, show placeholder information
      ux.print("📊 Error Recovery Statistics")
      ux.print("\nThis feature requires integration with active recovery managers.")
      ux.print("Recovery stats will be available when operations are running.")
  ```

**Fix Required:**
- Either implement recovery statistics or update CLAUDE.md to mark as "(coming soon)"

---

## Issue #3: WIZARD COMMAND UNDOCUMENTED
**Severity: MEDIUM**

### Feature Implementation
- **File:** `/home/user/vortex/src/vortex/cli/main.py`
- **Lines:** 167-223
- **Command:** `@cli.command()` at line 167 defining `wizard()` function

### Documentation Status
- **File:** `/home/user/vortex/CLAUDE.md`
- **Status:** Zero mentions of "wizard" command anywhere
- **Help System Reference:** Line 346 mentions "Interactive configuration wizard" but doesn't explain how to access it

**Fix Required:**
- Add section to CLAUDE.md documenting `vortex wizard` command
- Explain interactive setup workflow
- Provide example use cases

---

## Issue #4: HELP COMMAND SYSTEM UNDOCUMENTED
**Severity: LOW**

### Feature Implementation
- **File:** `/home/user/vortex/src/vortex/cli/help.py`
- **Lines:** 611-650
- **Commands:**
  ```python
  def get_help_system() -> HelpSystem:     # Line 611
  @click.group()
  def help():                              # Line 617
  @help.command()
  def examples(command: Optional[str]):    # Line 624
  @help.command()
  def tutorial(topic: str):                # Line 630
  @help.command()
  def tips(count: int):                    # Line 638
  @help.command()
  def commands():                          # Line 644
  @help.command()
  def quickstart():                        # Line 650
  ```

### Documentation Status
- **File:** `/home/user/vortex/CLAUDE.md`
- **Status:** Zero mentions of help command subcommands

**Fix Required:**
- Document help command system with examples
- Explain each subcommand (examples, tutorial, tips, commands, quickstart)
- Add quick reference table

---

## Issue #5: ASSET FILE PERIOD FORMAT INCONSISTENCY
**Severity: MEDIUM**

### Documentation Example
- **File:** `/home/user/vortex/CLAUDE.md`
- **Lines:** 465-490 (Assets File Format section)
- **Example shows:** `"periods": "1d"` (single value only)

### Actual Asset Files

#### yahoo.json
- **File:** `/home/user/vortex/config/assets/yahoo.json`
- **Lines:** 1-19
- **Inconsistencies:**
  - Line 3: `"periods": ""` (empty string - AUDUSD)
  - Line 4: `"periods": "1d"` (single value - CADUSD)
  - Line 5: `"periods": ""` (empty string - CHFUSD)
  - Line 13: `"periods": null` (null value - SPY)

#### barchart.json
- **File:** `/home/user/vortex/config/assets/barchart.json`
- **Lines:** 1-18
- **Inconsistencies:**
  - Line 3: `"periods": "1d"` (single value - AUDUSD)
  - Line 7: `"periods": "1d"` (single value - AEX)
  - Line 12: `"periods": "1d,1h"` (COMMA-SEPARATED - SPY) **NOT DOCUMENTED!**
  - Line 13: `"periods": "1d,1h"` (COMMA-SEPARATED - DIA)

#### ibkr.json
- **File:** `/home/user/vortex/config/assets/ibkr.json`
- **Lines:** 1-18
- **Format:** Empty strings and comma-separated values

**Fix Required:**
- Update CLAUDE.md to document that periods can be:
  1. Empty string `""` (no specific period)
  2. Single value `"1d"` (one period)
  3. Comma-separated `"1d,1h,15m"` (multiple periods)
  4. Null/omitted (not specified)

---

## Issue #6: IBKR ASSET PROVIDER-SPECIFIC FIELDS MISMATCH
**Severity: MEDIUM**

### Documentation Claims
- **File:** `/home/user/vortex/CLAUDE.md`
- **Lines:** 512-513
- **Text:**
  ```
  **Provider-specific fields**:
    - **IBKR**: `conId`, `localSymbol`, `multiplier`, `baseCurrency`, `quoteCurrency`
  ```

### Actual IBKR Asset File
- **File:** `/home/user/vortex/config/assets/ibkr.json`
- **Lines:** 1-18
- **Fields Actually Used:**
  - `code` (symbol code)
  - `cycle` (for futures, e.g., "HMUZ")
  - `tick_date` (first trade date)
  - `start_date` (start date)
  - `periods` (trading periods)

**Missing Fields:** None of the documented fields (`conId`, `localSymbol`, `multiplier`, `baseCurrency`, `quoteCurrency`) appear in the actual IBKR asset file.

**Fix Required:**
- Either add these fields to `/home/user/vortex/config/assets/ibkr.json` OR
- Remove from CLAUDE.md documentation and use only actual fields

---

## Issue #7: DOWNLOAD --RAW-DIR OPTION UNDOCUMENTED
**Severity: LOW**

### Feature Implementation
- **File:** `/home/user/vortex/src/vortex/cli/commands/download.py`
- **Lines:** 94-98
- **Code:**
  ```python
  @click.option(
      "--raw-dir",
      type=click.Path(path_type=Path),
      help="Raw data directory for audit trail. Default: ./raw"
  )
  ```

### Documentation Status
- **File:** `/home/user/vortex/CLAUDE.md`
- **Status:** No mention in download command examples (Lines 139-164)
- **README.md:** Mentions raw data storage (Lines 180-205) but not the CLI option

**Fix Required:**
- Add `--raw-dir` example to CLAUDE.md download command examples
- Update README.md to include CLI example

---

## Issue #8: OLD IMPORT PATHS IN DOCUMENTATION
**Severity: LOW**

### Documentation Example
- **File:** `/home/user/vortex/CLAUDE.md`
- **Location:** Architecture section (referenced in plugin discussion)
- **Incorrect Path:** `from vortex.plugins import get_provider_registry`

### Actual Import Path
- **Correct:** `from vortex.infrastructure.plugins import get_provider_registry`
- **Location:** Used in `/home/user/vortex/src/vortex/cli/commands/providers.py` (Line 12)

**Fix Required:**
- Update any documentation mentioning old `vortex.plugins` path
- Use correct `vortex.infrastructure.plugins` path

---

## Summary Table with Line Numbers

| Issue | Doc File | Line(s) | Code File | Line(s) | Severity |
|-------|----------|---------|-----------|---------|----------|
| validate options | CLAUDE.md | 282-283 | validate.py | 50-78 | CRITICAL |
| resilience recovery | CLAUDE.md | 295 | resilience.py | 160-175 | MEDIUM |
| wizard command | CLAUDE.md | - | main.py | 167-223 | MEDIUM |
| help command | CLAUDE.md | - | help.py | 611-650 | LOW |
| periods format | CLAUDE.md | 465-490 | *.json | multiple | MEDIUM |
| IBKR fields | CLAUDE.md | 512-513 | ibkr.json | all | MEDIUM |
| --raw-dir | CLAUDE.md | 139-164 | download.py | 94-98 | LOW |
| import paths | CLAUDE.md | various | providers.py | 12 | LOW |

---

## Remediation Checklist

- [ ] Fix validate command options (CLAUDE.md 282-283)
- [ ] Update resilience recovery documentation or implement feature
- [ ] Add wizard command documentation to CLAUDE.md
- [ ] Add help command system documentation to CLAUDE.md
- [ ] Update asset period format documentation in CLAUDE.md
- [ ] Resolve IBKR asset fields (add or remove from docs)
- [ ] Document --raw-dir option in CLAUDE.md
- [ ] Update import paths in documentation
- [ ] Run full CLI tests to verify fixes
- [ ] Update help system examples to match new documentation

