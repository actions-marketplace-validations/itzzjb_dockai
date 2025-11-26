"""
DockAI Agents Module.

This module contains the AI-powered agents for analyzing projects
and generating Dockerfiles:
- Code analyzer for project detection
- Dockerfile generator
- Security reviewer
- Specialized agent functions (planner, reflector, health detector, etc.)
"""

from .analyzer import analyze_repo_needs
from .generator import generate_dockerfile
from .reviewer import review_dockerfile
from .agent_functions import (
    create_plan,
    reflect_on_failure,
    detect_health_endpoints,
    detect_readiness_patterns,
    generate_iterative_dockerfile,
)

__all__ = [
    "analyze_repo_needs",
    "generate_dockerfile", 
    "review_dockerfile",
    "create_plan",
    "reflect_on_failure",
    "detect_health_endpoints",
    "detect_readiness_patterns",
    "generate_iterative_dockerfile",
]
