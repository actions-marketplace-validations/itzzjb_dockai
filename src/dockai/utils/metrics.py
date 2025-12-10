"""
DockAI Metrics Collection Module.

This module provides optional, anonymized metrics collection to track
success rates, error patterns, and performance across different project types.

Metrics are stored locally and never sent externally unless explicitly configured.
Enable with: DOCKAI_COLLECT_METRICS=true
"""

import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("dockai")


class MetricsCollector:
    """
    Collects and stores anonymized metrics about DockAI execution.
    
    Metrics include:
    - Success/failure outcomes
    - Retry count distributions
    - Error type frequencies
    - Project type detection
    - Execution time
    - Token usage
    
    All data is stored locally in .dockai/metrics/ and is opt-in only.
    """
    
    def __init__(self, project_path: str):
        """
        Initialize metrics collector.
        
        Args:
            project_path: Path to the project being analyzed
        """
        self.enabled = os.getenv("DOCKAI_COLLECT_METRICS", "false").lower() == "true"
        self.project_path = project_path
        self.session_id = self._generate_session_id()
        self.start_time = time.time()
        self.metrics_dir = Path.home() / ".dockai" / "metrics"
        
        if self.enabled:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Metrics collection enabled. Session ID: {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID for this run."""
        timestamp = datetime.utcnow().isoformat()
        random_component = os.urandom(8).hex()
        return hashlib.sha256(f"{timestamp}{random_component}".encode()).hexdigest()[:16]
    
    def _anonymize_path(self, path: str) -> str:
        """
        Anonymize project path to protect user privacy.
        
        Returns a hash of the path rather than the actual path.
        """
        return hashlib.sha256(path.encode()).hexdigest()[:16]
    
    def record_session(
        self,
        success: bool,
        project_type: str,
        stack: str,
        retry_count: int,
        error_types: list,
        total_tokens: int,
        final_state: Dict[str, Any]
    ):
        """
        Record metrics for a completed session.
        
        Args:
            success: Whether the Dockerfile was successfully generated
            project_type: Detected project type (e.g., "service", "script")
            stack: Technology stack (e.g., "python-fastapi", "node-express")
            retry_count: Number of retry attempts needed
            error_types: List of error types encountered
            total_tokens: Total LLM tokens used
            final_state: Final workflow state
        """
        if not self.enabled:
            return
        
        duration = time.time() - self.start_time
        
        # Extract relevant metrics from final state
        validation_result = final_state.get("validation_result", {})
        usage_stats = final_state.get("usage_stats", [])
        
        # Calculate token distribution by agent
        token_distribution = {}
        for stat in usage_stats:
            if isinstance(stat, dict):
                stage = stat.get("stage", "unknown")
                tokens = stat.get("total_tokens", 0)
                token_distribution[stage] = token_distribution.get(stage, 0) + tokens
        
        # Build metrics record
        metrics = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "project_path_hash": self._anonymize_path(self.project_path),
            "success": success,
            "project_type": project_type,
            "stack": stack,
            "retry_count": retry_count,
            "error_types": error_types,
            "duration_seconds": round(duration, 2),
            "total_tokens": total_tokens,
            "token_distribution": token_distribution,
            "image_size_mb": self._extract_image_size(validation_result),
            "validation_message": validation_result.get("message", "")[:200] if validation_result else "",
            "dockai_version": self._get_version(),
            "llm_provider": os.getenv("DOCKAI_LLM_PROVIDER", "openai"),
        }
        
        # Write to JSONL file (one record per line for easy streaming analysis)
        metrics_file = self.metrics_dir / "sessions.jsonl"
        try:
            with open(metrics_file, "a") as f:
                f.write(json.dumps(metrics) + "\n")
            logger.debug(f"Metrics recorded to {metrics_file}")
        except Exception as e:
            logger.warning(f"Failed to write metrics: {e}")
    
    def _extract_image_size(self, validation_result: Dict) -> Optional[float]:
        """Extract image size in MB from validation result."""
        message = validation_result.get("message", "")
        if "Image size:" in message:
            # Parse "Image size: 123.45MB"
            try:
                size_str = message.split("Image size:")[1].split("MB")[0].strip()
                return float(size_str)
            except (IndexError, ValueError):
                pass
        return None
    
    def _get_version(self) -> str:
        """Get DockAI version."""
        try:
            from .. import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    def record_error(self, error_type: str, error_message: str, retry_count: int):
        """
        Record an error occurrence for later analysis.
        
        Args:
            error_type: Type of error (e.g., "dockerfile_error", "rate_limit")
            error_message: Error message (truncated for privacy)
            retry_count: Current retry count when error occurred
        """
        if not self.enabled:
            return
        
        error_record = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message_snippet": error_message[:200],  # Truncate to avoid sensitive data
            "retry_count": retry_count,
        }
        
        errors_file = self.metrics_dir / "errors.jsonl"
        try:
            with open(errors_file, "a") as f:
                f.write(json.dumps(error_record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write error metrics: {e}")


def get_metrics_summary(days: int = 30) -> Dict[str, Any]:
    """
    Generate a summary of collected metrics.
    
    Args:
        days: Number of days to include in summary
        
    Returns:
        Dictionary with summary statistics
    """
    metrics_dir = Path.home() / ".dockai" / "metrics"
    sessions_file = metrics_dir / "sessions.jsonl"
    
    if not sessions_file.exists():
        return {"error": "No metrics data found. Enable with DOCKAI_COLLECT_METRICS=true"}
    
    # Load recent sessions
    cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
    sessions = []
    
    try:
        with open(sessions_file, "r") as f:
            for line in f:
                try:
                    session = json.loads(line.strip())
                    session_time = datetime.fromisoformat(session["timestamp"]).timestamp()
                    if session_time >= cutoff_date:
                        sessions.append(session)
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as e:
        return {"error": f"Failed to read metrics: {e}"}
    
    if not sessions:
        return {"error": f"No sessions found in last {days} days"}
    
    # Calculate statistics
    total_sessions = len(sessions)
    successful_sessions = sum(1 for s in sessions if s.get("success"))
    success_rate = (successful_sessions / total_sessions) * 100
    
    # Group by stack
    stack_stats = {}
    for session in sessions:
        stack = session.get("stack", "unknown")
        if stack not in stack_stats:
            stack_stats[stack] = {"total": 0, "successful": 0}
        stack_stats[stack]["total"] += 1
        if session.get("success"):
            stack_stats[stack]["successful"] += 1
    
    # Add success rates
    for stack, stats in stack_stats.items():
        stats["success_rate"] = (stats["successful"] / stats["total"]) * 100
    
    # Average retry count
    avg_retries = sum(s.get("retry_count", 0) for s in sessions) / total_sessions
    
    # Average execution time
    avg_duration = sum(s.get("duration_seconds", 0) for s in sessions) / total_sessions
    
    # Most common error types
    error_types = {}
    for session in sessions:
        for error_type in session.get("error_types", []):
            error_types[error_type] = error_types.get(error_type, 0) + 1
    
    return {
        "period_days": days,
        "total_sessions": total_sessions,
        "successful_sessions": successful_sessions,
        "success_rate_percent": round(success_rate, 2),
        "avg_retry_count": round(avg_retries, 2),
        "avg_duration_seconds": round(avg_duration, 2),
        "stack_breakdown": stack_stats,
        "top_error_types": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]),
    }


# Example usage in main.py:
# from ..utils.metrics import MetricsCollector
# 
# metrics = MetricsCollector(path)
# try:
#     final_state = workflow.invoke(initial_state)
#     metrics.record_session(
#         success=final_state["validation_result"]["success"],
#         project_type=final_state["analysis_result"].get("project_type"),
#         stack=final_state["analysis_result"].get("stack"),
#         retry_count=final_state["retry_count"],
#         error_types=[],
#         total_tokens=total_tokens,
#         final_state=final_state
#     )
# except Exception as e:
#     metrics.record_error("fatal_error", str(e), 0)
