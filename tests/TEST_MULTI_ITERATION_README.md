# Multi-Iteration Test Script

## Purpose

The file `test_multi_iteration.py` is designed to **intentionally fail tests** on the first iteration, forcing the agent to go through multiple cycles to fix all the bugs. This allows you to see the full iteration flow in the Streamlit UI.

## Bugs in the Script

The script contains **4 intentional bugs** that will cause test failures:

1. **Division by Zero** (`divide_numbers` function)
   - Crashes with `ZeroDivisionError` when denominator is 0
   - Tests will fail when they try to test edge cases

2. **Logic Error** (`find_maximum` function)
   - Finds **minimum** instead of maximum (comparison is reversed)
   - Tests will fail assertions like `assert find_maximum([1, 5, 3]) == 5`

3. **Type Error** (`process_data` function)
   - Crashes with `TypeError` when given non-numeric inputs
   - Tests will fail when they test with strings or other types

4. **Edge Case Handling** (`calculate_average` function)
   - Returns `0` for empty list instead of `None` or raising an error
   - Tests may fail if they expect different behavior

## Expected Behavior

When you upload this script to Streamlit:

1. **First Iteration**: 
   - LLM generates code and tests
   - Tests will **fail** (due to the bugs)
   - You'll see test failures in the output

2. **Second Iteration**:
   - Agent sees the test failures and tries to fix the bugs
   - May fix some but not all bugs
   - Tests may still fail

3. **Third Iteration** (if needed):
   - Agent fixes remaining bugs
   - Tests should pass

## How to Use

1. Open the Streamlit app (http://localhost:8501)
2. Upload `test_multi_iteration.py` in the file uploader
3. Enter a task like: "Fix all bugs and ensure all functions work correctly"
4. Click "Generate & Validate"
5. Watch the iteration flow in the UI:
   - See multiple code iterations in tabs
   - See test results for each iteration
   - See how the code evolves to fix bugs

## What You'll See

- **Code Iterations**: Multiple tabs showing how code changes
- **Test Execution Results**: stdout/stderr showing which tests failed
- **Error Messages**: Specific error messages that guide the agent
- **Comparison**: Original vs refined script outputs

## Notes

- The exact number of iterations may vary (2-3 typically)
- The agent may fix bugs in different orders
- Some iterations may fix multiple bugs at once
- The final iteration should have all tests passing

