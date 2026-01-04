"""
Monitoring and metrics collection for MoAgent.

Provides Prometheus-compatible metrics and health checks.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime

from ..config.constants import METRICS_BUCKETS

logger = logging.getLogger(__name__)


class MetricsRegistry:
    """
    Simple metrics registry (Prometheus-compatible).

    Note: For production, use prometheus_client directly.
    This is a lightweight implementation for basic monitoring.
    """

    def __init__(self):
        """Initialize metrics registry."""
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}

    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Increment counter."""
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value

    def set(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge value."""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def observe(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Observe histogram value."""
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create key with labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics."""
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {k: {
                "count": len(v),
                "sum": sum(v),
                "avg": sum(v) / len(v) if v else 0
            } for k, v in self.histograms.items()}
        }


# Global metrics registry
_registry: Optional[MetricsRegistry] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


# Predefined metric names
METRIC_CRAWL_TOTAL = "moagent_crawl_total"
METRIC_PARSE_TOTAL = "moagent_parse_total"
METRIC_STORAGE_TOTAL = "moagent_storage_total"
METRIC_NOTIFY_TOTAL = "moagent_notify_total"
METRIC_ERRORS_TOTAL = "moagent_errors_total"
METRIC_DURATION_SECONDS = "moagent_duration_seconds"


def track_duration(metric_name: str = METRIC_DURATION_SECONDS):
    """
    Decorator to track function duration.

    Args:
        metric_name: Name of metric to track

    Example:
        @track_duration("my_function_duration")
        def my_function():
            pass
    """
    registry = get_metrics_registry()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                registry.increment(f"{func.__name__}_success_total")
                return result
            except Exception as e:
                registry.increment(f"{func.__name__}_error_total")
                raise
            finally:
                duration = time.time() - start
                registry.observe(metric_name, duration)
        return wrapper
    return decorator


def HealthChecker:
    """Health check system."""

    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, Callable[[], bool]] = {}

    def register(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register health check."""
        self.checks[name] = check_func

    def check(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        overall_healthy = True

        for name, check_func in self.checks.items():
            try:
                healthy = check_func()
                results[name] = {"healthy": healthy}
                if not healthy:
                    overall_healthy = False
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
                overall_healthy = False

        results["overall"] = {"healthy": overall_healthy}
        return results

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        results = self.check()
        return results.get("overall", {}).get("healthy", False)


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
