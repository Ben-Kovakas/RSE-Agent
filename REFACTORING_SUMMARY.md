# Quick Summary: `nodes.py` Refactoring Plan

## Current Problem

**`nodes.py` is 593 lines** and contains everything:
- ✅ 4 node functions (what you need to see)
- ❌ 6 code checking utilities (hidden)
- ❌ 2 OpenAI API functions (hidden)  
- ❌ 1 AST visitor class (hidden)
- ❌ Complex E2B execution logic (150+ lines, hard to follow)

**Result**: Hard to find what you need, scary to modify anything.

---

## Proposed Solution

Break into **4 focused modules**:

### 1. `checks/` - Code Compliance (Low Risk)
**What**: All the `_check_*` functions and AST visitor
**Why**: These are pure functions, easy to extract and test
**Files**: 
- `checks/code_checks.py` - all check functions
- `checks/ast_visitors.py` - AST visitor class

### 2. `llm/` - OpenAI Integration (Medium Risk)  
**What**: LLM API calls and prompt templates
**Why**: Prompts are long strings that clutter the code
**Files**:
- `llm/prompts.py` - prompt template functions
- `llm/client.py` - OpenAI API calls

### 3. `execution/` - Code Execution (Medium-High Risk)
**What**: E2B sandbox and local pytest execution
**Why**: This is the most complex part (150+ lines), needs isolation
**Files**:
- `execution/runners.py` - E2B and local execution
- `execution/utils.py` - helper functions

### 4. `nodes.py` - Just the Nodes (Simplified)
**What**: Only the 4 LangGraph node functions
**Why**: This is what you actually need to see and modify
**Result**: ~180 lines (down from 593)

---

## Visual Comparison

### Before (Current)
```
nodes.py (593 lines)
├── _check_no_hardcoded_paths()          [utility]
├── _check_version_control_hygiene()      [utility]
├── _check_separation_of_concerns()       [utility]
├── _check_license()                      [utility]
├── _IOSeparationVisitor                  [utility class]
├── _call_openai_refactor()               [LLM - 91 lines]
├── _call_openai_generate_tests()         [LLM - 57 lines]
├── _strip_markdown_fences()              [utility]
├── coder_node()                          [node - 64 lines]
├── tester_node()                         [node - 25 lines]
├── reviewer_node()                       [node - 73 lines]
└── executor_node()                       [node - 154 lines!]
```

### After (Proposed)
```
nodes.py (~180 lines)
├── coder_node()                          [node - ~50 lines]
├── tester_node()                         [node - ~30 lines]
├── reviewer_node()                       [node - ~70 lines]
└── executor_node()                       [node - ~30 lines]

checks/
├── code_checks.py                        [all _check_* functions]
└── ast_visitors.py                       [IOSeparationVisitor]

llm/
├── prompts.py                            [prompt templates]
└── client.py                             [OpenAI API calls]

execution/
├── runners.py                            [E2B + local execution]
└── utils.py                              [strip_markdown_fences, etc.]
```

---

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Find code** | Search 593 lines | Know which file to open |
| **Modify safely** | Risk breaking unrelated code | Changes are isolated |
| **Test** | Hard to test utilities | Each module testable |
| **Understand** | Overwhelming | Clear purpose per file |
| **Extend** | Add to giant file | Add to specific module |

---

## Implementation Phases

1. **Phase 1: Extract Checks** (Start here - safest)
   - Move `_check_*` functions → `checks/`
   - Test: Run existing test, verify nodes still work
   
2. **Phase 2: Extract LLM** 
   - Move OpenAI calls → `llm/`
   - Extract prompts to separate file
   - Test: Verify LLM calls still work
   
3. **Phase 3: Extract Execution**
   - Move E2B/local logic → `execution/`
   - Test: Verify both execution paths work
   
4. **Phase 4: Cleanup**
   - Remove old code from `nodes.py`
   - Add docstrings
   - Final test suite run

---

## Risk Assessment

| Phase | Risk | Why |
|-------|------|-----|
| Phase 1 (Checks) | **Low** | Pure functions, no side effects |
| Phase 2 (LLM) | **Medium** | Need to preserve prompt formatting |
| Phase 3 (Execution) | **Medium-High** | Complex, critical path |
| Phase 4 (Cleanup) | **Low** | Just removing code |

**Recommendation**: Start with Phase 1 to build confidence, then proceed incrementally.

---

## Next Steps

1. Review this plan
2. Decide if you want to proceed
3. If yes, I can implement Phase 1 as a proof of concept
4. Test Phase 1 thoroughly
5. Continue with remaining phases

---

## Questions to Consider

- Do you want to keep backward compatibility (all imports from `nodes` still work)?
- Should I create unit tests for the extracted modules?
- Do you want to see example code for one phase before proceeding?

