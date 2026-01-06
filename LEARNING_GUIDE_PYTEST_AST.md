# Learning Guide: Pytest and AST in RSE-Agent

## Part 1: Pytest Basics & Usage in This Project

### What is Pytest?

**Pytest** is a Python testing framework that makes it easy to write and run tests. It automatically discovers test files and functions.

### Basic Pytest Concepts

1. **Test Functions**: Functions that start with `test_` are automatically discovered
2. **Assertions**: Use `assert` statements to check conditions
3. **Test Discovery**: Pytest finds all files matching `test_*.py` or `*_test.py`
4. **Exit Codes**: Returns 0 if all tests pass, non-zero if any fail

### Example Test File Structure

```python
# test_candidate.py
import pytest
from candidate import my_function

def test_basic_functionality():
    result = my_function(5)
    assert result == 10

def test_edge_case():
    result = my_function(0)
    assert result == 0
```

### How Pytest is Used in This Project

#### 1. **Test Generation** (Tester Node)
The LLM generates pytest test files that follow this pattern:
- Import the code under test as `candidate` module
- Write test functions with `test_` prefix
- Use assertions to validate behavior

#### 2. **Test Execution** (Executor Node)

**In E2B Sandbox** (`run_e2b_execution`):
```python
# Lines 47-48 in runners.py
"subprocess.run([sys.executable,'-m','pip','install','-q','pytest'], ...)\n"
"p = subprocess.run([sys.executable,'-m','pytest','-qq','--color=no'], ...)\n"
```

**Locally** (`run_local_execution`):
```python
# Lines 145-146 in runners.py
proc = subprocess.run(
    [sys.executable, "-m", "pytest", "-qq", "--color=no"],
    cwd=str(tmp_path),
    capture_output=True,
    text=True,
)
```

#### 3. **Pytest Flags Used**

- `-m pytest`: Run pytest as a module
- `-qq`: Extra quiet mode (minimal output)
- `--color=no`: Disable colored output (for parsing)

#### 4. **How Results Are Captured**

```python
# Exit code 0 = all tests passed
# Exit code != 0 = tests failed
passed = proc.returncode == 0

# stdout contains test output
# stderr contains errors
return {
    "stdout": proc.stdout,
    "stderr": proc.stderr,
    "passed": passed,
    "runner": "local" or "e2b"
}
```

### Pytest Workflow in This Project

1. **Tester Node** generates test code (pytest format)
2. **Executor Node** writes two files:
   - `candidate.py` (the code to test)
   - `test_candidate.py` (the pytest tests)
3. **Pytest runs** in sandbox/local environment
4. **Results captured**: stdout, stderr, exit code
5. **Decision made**: If `passed=False`, loop back to coder

---

## Part 2: AST (Abstract Syntax Tree) Basics & Usage

### What is an AST?

An **Abstract Syntax Tree** is a tree representation of the structure of source code. Python's `ast` module lets you parse code and analyze its structure without executing it.

### Basic AST Concepts

1. **Parsing**: Convert source code string → AST tree
2. **Nodes**: Each element (function, call, assignment) is a node
3. **Visitors**: Traverse the tree to find patterns
4. **Analysis**: Inspect code structure without running it

### Example: Understanding AST Structure

```python
import ast

code = """
def hello(name):
    print(f"Hello, {name}")
"""

# Parse code into AST
tree = ast.parse(code)

# tree is now an AST.Module node containing:
#   - AST.FunctionDef node (the function)
#       - AST.arguments node (parameters)
#       - AST.Expr node (the print statement)
#           - AST.Call node (the function call)
```

### How AST is Used in This Project

#### 1. **Separation of Concerns Check** (`check_separation_of_concerns`)

**Location**: `src/rse_agent/checks/code_checks.py` (lines 77-101)

**Purpose**: Detects I/O operations at the top level (outside functions)

**How it works**:
```python
# Step 1: Parse code into AST
tree = ast.parse(code)

# Step 2: Use visitor to traverse tree
visitor = IOSeparationVisitor()
visitor.visit(tree)

# Step 3: Check if any top-level I/O calls found
if visitor.top_level_io_calls:
    return False, "top-level I/O detected"
```

#### 2. **IOSeparationVisitor** (Custom AST Visitor)

**Location**: `src/rse_agent/checks/ast_visitors.py`

**How it works**:

```python
class IOSeparationVisitor(ast.NodeVisitor):
    def __init__(self):
        self.top_level_io_calls = []
        self._function_depth = 0  # Track nesting level
    
    def visit_FunctionDef(self, node):
        # When entering a function, increase depth
        self._function_depth += 1
        self.generic_visit(node)  # Visit children
        self._function_depth -= 1  # When leaving, decrease depth
    
    def visit_Call(self, node):
        # Only check calls at top level (depth == 0)
        if self._function_depth == 0:
            # Check if it's an I/O call like open(), read_csv(), etc.
            if name in {"open", "read_csv", "read_table"}:
                self.top_level_io_calls.append(name)
```

### AST Visitor Pattern Explained

**NodeVisitor** is a base class that provides:
- `visit()`: Entry point to traverse tree
- `generic_visit()`: Default traversal of child nodes
- Custom methods: Override `visit_NodeType()` to handle specific nodes

**Example Traversal**:
```python
# Code: open("file.txt")
# AST: Call(func=Name(id='open'), args=[Constant(value='file.txt')])

# Visitor calls:
# 1. visit_Call(node)  ← Custom handler
# 2. generic_visit(node)  ← Visits children
# 3. visit_Name(node.func)  ← Visits the 'open' name
# 4. visit_Constant(node.args[0])  ← Visits the string
```

### Why Use AST Instead of Regex?

**Regex approach** (used for hardcoded paths):
```python
# Simple pattern matching
ABSOLUTE_PATH_LITERAL_RE = re.compile(r"/([^'\"]+)")
matches = ABSOLUTE_PATH_LITERAL_RE.findall(code)
```

**AST approach** (used for I/O separation):
```python
# Understands code structure
tree = ast.parse(code)
visitor.visit(tree)
# Can distinguish between:
#   - open() inside a function (OK)
#   - open() at top level (BAD)
```

**Why AST is better here**:
- Understands context (inside funct@n vs top level)
- Handles nested structures correctly
- Not fooled by strings containing patterns
- More robust for complex code analysis

### Real Example from Project

**Bad Code** (fails check):
```python
# Top-level I/O - BAD
data = open("file.csv").read()
def process(data):
    return data.upper()
```

**Good Code** (passes check):
```python
# I/O inside function - GOOD
def process(filename):
    data = open(filename).read()
    return data.upper()
```

The AST visitor can tell the difference because it tracks `_function_depth`.

---

## Part 3: How They Work Together

### Complete Flow Example

1. **Coder generates code**:
```python
def analyze(data):
    return sum(data) / len(data)
```

2. **Tester generates pytest tests**:
```python
import pytest
from candidate import analyze

def test_analyze():
    assert analyze([1, 2, 3]) == 2.0
```

3. **Reviewer uses AST**:
```python
# AST check: No top-level I/O? ✓ Pass
# Regex check: No hardcoded paths? ✓ Pass
```

4. **Executor runs pytest**:
```bash
pytest test_candidate.py
# Exit code: 0 (passed)
```

5. **Result**: `passed=True` → END

### Key Takeaways

- **Pytest**: Executes tests to validate runtime behavior
- **AST**: Analyzes code structure to validate static properties
- **Together**: They provide both dynamic (pytest) and static (AST) validation

---

## Exercises to Try

### Exercise 1: Write a Simple Pytest Test

Create `test_example.py`:
```python
def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0
```

Run: `pytest test_example.py`

### Exercise 2: Explore AST Structure

```python
import ast

code = """
x = 5
y = x + 10
"""

tree = ast.parse(code)
print(ast.dump(tree, indent=2))
```

### Exercise 3: Write a Simple AST Visitor

```python
import ast

class FunctionCounter(ast.NodeVisitor):
    def __init__(self):
        self.count = 0
    
    def visit_FunctionDef(self, node):
        self.count += 1
        self.generic_visit(node)

code = """
def func1():
    pass
def func2():
    pass
"""

tree = ast.parse(code)
visitor = FunctionCounter()
visitor.visit(tree)
print(f"Found {visitor.count} functions")  # Should print: Found 2 functions
```

---

## Further Reading

- **Pytest Docs**: https://docs.pytest.org/
- **Python AST Module**: https://docs.python.org/3/library/ast.html
- **Green Tree Snakes** (AST tutorial): https://greentreesnakes.readthedocs.io/

