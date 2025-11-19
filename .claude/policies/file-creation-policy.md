# Claude Code File Creation Policy

**Version:** 1.0
**Purpose:** Prevent unwanted file generation and conversation artifacts in repositories

---

## 🚨 CRITICAL: File Creation Rules

**Do NOT create files unless explicitly requested by the user.**

### ❌ Prohibited File Types

**NEVER create these files under any circumstances:**

1. **Analysis/Audit Reports**
   - `*ANALYSIS*.md`, `*AUDIT*.md`, `*SUMMARY*.txt`
   - `COMPREHENSIVE_*.md`, `CONFIG_ANALYSIS.md`
   - Any file with "analysis", "audit", "summary", "report" in the name

2. **Conversation Artifacts**
   - Files documenting your work process or findings
   - Temporary tracking files for your internal use
   - "Work-in-progress" documentation files

3. **Unsolicited Documentation**
   - `README*.md` files (unless explicitly requested)
   - `ENHANCEMENTS_*.md`, `IMPROVEMENTS_*.md`
   - Design documents for unimplemented features
   - Architecture decision records without user approval

4. **Tracking/Planning Files**
   - TODO lists in markdown format
   - Progress tracking files
   - Issue logs or bug lists (use GitHub Issues instead)

### ✅ Allowed File Creation

**ONLY create files when:**

1. **User explicitly requests** a specific file by name or type
2. **Source code files** are needed for implementation (`.py`, `.js`, `.ts`, etc.)
3. **Test files** are required for testing features
4. **Configuration files** are needed for the project to function
5. **Build/deployment files** are explicitly requested

### 📋 Best Practices

**Instead of creating files, you should:**

1. **Report findings verbally** - Respond directly to the user in conversation
2. **Update existing documentation** - Prefer editing `README.md`, `CLAUDE.md`, or docs in `docs/` directory
3. **Use GitHub Issues** - For tracking bugs, features, or TODOs
4. **Ask first** - When in doubt, ask the user if they want a file created

**Examples of correct behavior:**

```
❌ WRONG: Creating "ANALYSIS_REPORT.md" to document your findings
✅ RIGHT: Reporting findings directly in conversation

❌ WRONG: Creating "ENHANCEMENTS_SUMMARY.md" to list improvements made
✅ RIGHT: Updating CHANGES.md or responding with the list

❌ WRONG: Creating "TODO.md" to track remaining tasks
✅ RIGHT: Using TodoWrite tool or asking user to create GitHub Issues
```

### 🎯 Exception Cases

**Files that ARE allowed without explicit request:**

- Test files when implementing features (e.g., `test_feature.py`)
- Source code modules when implementing features (e.g., `new_module.py`)
- Configuration snippets when configuring systems (e.g., `.env.example`)

**When unsure:** ASK THE USER before creating any documentation file.

---

## Why This Policy Exists

1. **Prevents repository pollution** - Keeps repos clean of conversation artifacts
2. **Reduces noise** - Users don't want to manage files they didn't request
3. **Better workflow** - Conversation is better for ad-hoc analysis than files
4. **Clear boundaries** - Code files are for implementation, not for AI work logs

---

## How to Use This Policy in Your Project

Add this line to your `CLAUDE.md` file:

```markdown
@.claude/policies/file-creation-policy.md
```

This will automatically load these rules into Claude's context when working on your project.

---

**Remember:** Your job is to help users write code and improve their projects, not to create documentation about your process. Let the user decide what files they need.
