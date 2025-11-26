"""
DockAI CLI Module.

This module contains the command-line interface components:
- Typer CLI commands and entry point
- Rich console UI components
"""

from .main import app, build
from .ui import (
    console,
    setup_logging,
    print_welcome,
    print_error,
    print_success,
    print_warning,
    display_summary,
    display_failure,
    get_status_spinner,
)
# Re-export callbacks from utils for backward compatibility
from ..utils.callbacks import TokenUsageCallback

__all__ = [
    "app",
    "build",
    "console",
    "setup_logging",
    "print_welcome",
    "print_error",
    "print_success",
    "print_warning",
    "display_summary",
    "display_failure",
    "get_status_spinner",
    "TokenUsageCallback",
]
