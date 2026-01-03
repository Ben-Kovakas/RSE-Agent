# Refactoring Plan for `nodes.py` - Readability Improvements

## Current State Analysis

**File**: `src/rse_agent/nodes.py` (593 lines)

### Issues Identified:
1. **Single Responsibility Violation**: File contains 4 distinct concerns:
   - Code compliance checking utilities
   - LLM/OpenAI integration
   - Code execution (E2B + local)
   - Node implementations (LangGraph workflow)

2. **Function Complexity**:
   - `executor_node`: 154 lines with deeply nested E2B logic
   - `_call_openai_refactor`: 91 lines with embedded prompt template
   - `_call_openai_generate_tests`: 57 lines with embedded prompt template

3. **Testing Challenges**:
   - Private functions (`_check_*`, `_call_*`) are hard to test in isolation
   - Tight coupling makes unit testing difficult

4. **Maintainability**:
   - Hard to find specific functionality
   - Changes to one concern risk breaking others
   - Long functions are intimidating to modify

---

## Proposed Refactoring Structure

### Phase 1: Extract Code Compliance Checks (Low Risk)
**New File**: `src/rse_agent/checks/__init__.py`
**New File**: `src/rse_agent/checks/code_checks.py`
**New File**: `src/rse_agent/checks/ast_visitors.py`

**Moves**:
- `_check_no_hardcoded_paths()` → `checks.code_checks.check_no_hardcoded_paths()`
- `_check_version_control_hygiene()` → `checks.code_checks.check_version_control_hygiene()`
- `_check_separation_of_concerns()` → `checks.code_checks.check_separation_of_concerns()`
- `_check_license()` → `checks.code_checks.check_license()`
- `_IOSeparationVisitor` → `checks.ast_visitors.IOSeparationVisitor`
- `_ABSOLUTE_PATH_LITERAL_RE` → `checks.code_checks.ABSOLUTE_PATH_LITERAL_RE`
- `_safe_bool()` → `checks.code_checks.safe_bool()` (or move to utils)

**Benefits**:
- Clear separation: compliance logic is isolated
- Easy to add new checks
- Can be tested independently

**Risk**: Low - these are pure functions with no external dependencies

---

### Phase 2: Extract LLM Integration (Medium Risk)
**New File**: `src/rse_agent/llm/__init__.py`
**New File**: `src/rse_agent/llm/prompts.py`
**New File**: `src/rse_agent/llm/client.py`

**Moves**:
- `_call_openai_refactor()` → `llm.client.call_openai_refactor()`
- `_call_openai_generate_tests()` → `llm.client.call_openai_generate_tests()`
- Prompt templates → `llm.prompts.build_refactor_prompt()`, `llm.prompts.build_test_prompt()`

**Benefits**:
- Prompt templates become reusable and easier to edit
- LLM client logic is isolated
- Can swap LLM providers without touching nodes

**Risk**: Medium - need to ensure prompt formatting is preserved exactly

---

### Phase 3: Extract Execution Logic (Medium-High Risk)
**New File**: `src/rse_agent/execution/__init__.py`
**New File**: `src/rse_agent/execution/runners.py`
**New File**: `src/rse_agent/execution/utils.py`

**Moves**:
- E2B execution logic → `execution.runners.run_e2b_execution()`
- Local execution logic → `execution.runners.run_local_execution()`
- `_strip_markdown_fences()` → `execution.utils.strip_markdown_fences()`

**New Function**: `execution.runners.execute_code()` (main entry point that chooses E2B vs local)

**Benefits**:
- `executor_node` becomes ~30 lines (just orchestration)
- Execution strategies are testable independently
- Easy to add new execution backends (Docker, etc.)

**Risk**: Medium-High - execution logic is critical and complex

---

### Phase 4: Simplify `nodes.py` (Low Risk)
**After Phases 1-3**, `nodes.py` will contain only:
- `coder_node()` - ~50 lines
- `tester_node()` - ~30 lines  
- `tester_node()` - ~70 lines
- `executor_node()` - ~30 lines

**Total**: ~180 lines (down from 593)

**Benefits**:
- Each node is easy to understand
- Clear imports show dependencies
- Easy to see the workflow at a glance

---

## Implementation Strategy

### Step-by-Step Approach (Safest)

1. **Create new directory structure** (no code changes yet)
2. **Extract Phase 1** (code checks) - test thoroughly
3. **Update imports in `nodes.py`** - verify tests pass
4. **Extract Phase 2** (LLM) - test thoroughly  
5. **Update imports in `nodes.py`** - verify tests pass
6. **Extract Phase 3** (execution) - test thoroughly
7. **Update imports in `nodes.py`** - verify tests pass
8. **Clean up `nodes.py`** - remove old code, add docstrings
9. **Update `graph.py` imports** (if needed - should still work)
10. **Run full test suite** - ensure nothing broke

### Backward Compatibility

- Keep all public functions (`*_node`) in `nodes.py` initially
- Update `__init__.py` to re-export if needed
- `graph.py` imports should continue working

---

## File Structure After Refactoring

```
src/rse_agent/
├── __init__.py
├── state.py
├── graph.py
├── nodes.py (simplified - 4 node functions only)
│
├── checks/
│   ├── __init__.py (exports: check_*, IOSeparationVisitor)
│   ├── code_checks.py (all _check_* functions)
│   └── ast_visitors.py (IOSeparationVisitor class)
│
├── llm/
│   ├── __init__.py (exports: call_openai_*)
│   ├── prompts.py (prompt template functions)
│   └── client.py (OpenAI API calls)
│
└── execution/
    ├── __init__.py (exports: execute_code)
    ├── runners.py (E2B and local execution)
    └── utils.py (strip_markdown_fences, etc.)
```

---

## Testing Strategy

For each phase:
1. **Unit tests** for extracted functions
2. **Integration tests** to ensure nodes still work
3. **Manual smoke test** with `dry_run.py` or Streamlit app

---

## Estimated Benefits

- **Readability**: Each file has a single, clear purpose
- **Maintainability**: Changes are localized to specific modules
- **Testability**: Utilities can be tested in isolation
- **Extensibility**: Easy to add new checks, LLM providers, or execution backends
- **Confidence**: Smaller files reduce fear of breaking things

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Incremental extraction with tests after each phase |
| Import errors | Keep backward-compatible exports in `__init__.py` |
| Missing dependencies | Update imports carefully, test imports |
| Execution logic bugs | Test E2B and local execution paths thoroughly |

---

## Recommendation

**Start with Phase 1** (code checks) - it's the lowest risk and will give you confidence. Then proceed incrementally, testing after each phase.

Would you like me to:
1. Create a detailed implementation for Phase 1?
2. Show example code for one of the extracted modules?
3. Create a test plan for validation?

