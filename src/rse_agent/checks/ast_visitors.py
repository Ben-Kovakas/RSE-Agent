"""AST (Abstract Syntax Tree) visitors for code analysis.

These visitors traverse Python ASTs to detect code patterns and issues.
"""

from __future__ import annotations

import ast


class IOSeparationVisitor(ast.NodeVisitor):
    """AST visitor that detects top-level I/O calls.
    
    This visitor enforces separation of concerns by identifying I/O operations
    (like file reading) that occur at the module level rather than inside
    functions. Top-level I/O makes code harder to test and reuse.
    """

    def __init__(self) -> None:
        """Initialize the visitor with empty results."""
        self.top_level_io_calls: list[str] = []
        self._function_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track when entering/exiting a function definition.
        
        Args:
            node: The function definition AST node
        """
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track when entering/exiting an async function definition.
        
        Args:
            node: The async function definition AST node
        """
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        """Detect I/O calls at the top level (outside functions).
        
        Enforces separation of concerns: no top-level I/O calls that read data.
        This makes code more testable and reusable.
        
        Args:
            node: The function call AST node
        """
        # Only check calls at the top level (function_depth == 0)
        if self._function_depth == 0:
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            # Check for common I/O operations
            if name in {"open", "read_csv", "read_table", "read_excel", "load"}:
                self.top_level_io_calls.append(name)

        self.generic_visit(node)

