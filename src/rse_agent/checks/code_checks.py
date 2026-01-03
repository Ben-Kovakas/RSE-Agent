"""Code compliance checking functions.

These functions analyze Python code for compliance with research software
engineering best practices, following Dr. Jeffrey Carver's guidelines.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .ast_visitors import IOSeparationVisitor

# Regular expression to detect absolute path string literals
ABSOLUTE_PATH_LITERAL_RE = re.compile(
    r"(?P<q>['\"])(?P<path>(/[^'\"]+|[A-Za-z]:\\\\[^'\"]+))(?P=q)"
)


def safe_bool(value: object) -> bool:
    """Safely convert a value to boolean, ensuring it's explicitly True.
    
    Args:
        value: Any object to check
        
    Returns:
        True only if value is explicitly True, False otherwise
    """
    return bool(value) is True


def check_no_hardcoded_paths(code: str) -> tuple[bool, str]:
    """Check for absolute path string literals in code.
    
    Hardcoded absolute paths make code non-portable and should be avoided
    in favor of relative paths or configuration.
    
    Args:
        code: Python source code to check
        
    Returns:
        Tuple of (pass: bool, detail: str) indicating whether check passed
    """
    matches = list(ABSOLUTE_PATH_LITERAL_RE.finditer(code))
    if not matches:
        return True, "no absolute path string literals detected"

    sample = [m.group("path")[:120] for m in matches[:3]]
    return False, f"found absolute path literals (sample): {sample}"


def check_version_control_hygiene(code: str) -> tuple[bool, str]:
    """Check if code header mentions version/commit metadata.
    
    Research code should include version information for reproducibility.
    
    Args:
        code: Python source code to check
        
    Returns:
        Tuple of (pass: bool, detail: str) indicating whether check passed
    """
    header = "\n".join(code.splitlines()[:40]).lower()
    signals = [
        "__version__",
        "version",
        "commit",
        "git",
        "sha",
        "revision",
    ]
    ok = any(s in header for s in signals)
    return ok, "header mentions version/commit" if ok else "no obvious version/commit metadata in header"


def check_separation_of_concerns(code: str) -> tuple[bool, str]:
    """Check that I/O operations are not at the top level.
    
    Top-level I/O calls make code harder to test and reuse. They should
    be moved into functions or behind a main guard.
    
    Args:
        code: Python source code to check
        
    Returns:
        Tuple of (pass: bool, detail: str) indicating whether check passed
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"cannot parse code to analyze I/O separation: {exc}"

    visitor = IOSeparationVisitor()
    visitor.visit(tree)

    if visitor.top_level_io_calls:
        calls = ", ".join(sorted(set(visitor.top_level_io_calls)))
        return False, f"top-level I/O call(s) detected: {calls}; move into functions or main-guard"

    return True, "no top-level I/O calls detected"


def check_license(repo_root: Path) -> tuple[bool, str]:
    """Check if a LICENSE or COPYING file exists at the repository root.
    
    Research software should include license information for clarity
    on usage and distribution rights.
    
    Args:
        repo_root: Path to the repository root directory
        
    Returns:
        Tuple of (pass: bool, detail: str) indicating whether check passed
    """
    license_files = []
    for pattern in ("LICENSE", "LICENSE.*", "COPYING", "COPYING.*"):
        license_files.extend(repo_root.glob(pattern))
    if license_files:
        return True, f"license file present: {license_files[0].name}"
    return False, "no LICENSE/COPYING file found at repo root"

