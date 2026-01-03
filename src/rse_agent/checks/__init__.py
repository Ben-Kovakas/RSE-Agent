"""Code compliance checking utilities.

This module provides functions for checking code quality and compliance
with research software engineering best practices.
"""

from .ast_visitors import IOSeparationVisitor
from .code_checks import (
    check_license,
    check_no_hardcoded_paths,
    check_separation_of_concerns,
    check_version_control_hygiene,
    safe_bool,
)

__all__ = [
    "IOSeparationVisitor",
    "check_license",
    "check_no_hardcoded_paths",
    "check_separation_of_concerns",
    "check_version_control_hygiene",
    "safe_bool",
]

