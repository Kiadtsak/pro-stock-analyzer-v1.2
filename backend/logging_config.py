"""
backend/logging_config.py — Centralized logging setup.

Usage:
    from backend.logging_config import setup_logging, log
    setup_logging(level="INFO")
    log.info("Application started")
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Literal

LOG_FORMAT = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
LOG_FORMAT_COLOR = "\033[90m%(asctime)s\033[0m [%(levelname)8s] \033[36m%(name)s\033[0m: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LEVEL_COLORS = {
    "DEBUG":    "\033[37m",   # gray
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    """Format log messages with ANSI colors for terminal."""

    def format(self, record):
        color = LEVEL_COLORS.get(record.levelname, "")
        record.levelname_colored = f"{color}{record.levelname:8s}{RESET}"
        return f"{color}{super().format(record)}{RESET}" if color else super().format(record)


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    log_file: Path | str | None = None,
    color: bool = True,
) -> logging.Logger:
    """
    Setup application-wide logging.

    Args:
        level:    Minimum level to log
        log_file: Path to write logs to (in addition to stdout)
        color:    Use ANSI colors on stdout

    Returns:
        Root logger
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers
    root.handlers.clear()

    # Stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    if color and sys.stdout.isatty():
        formatter = ColorFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    else:
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)

    # File handler (optional)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        )
        root.addHandler(file_handler)

    # Reduce noise from third-party libraries
    for noisy_logger in ["uvicorn.access", "httpx", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel("WARNING")

    return root


# Default application logger
log = logging.getLogger("pro_stock_analyzer")


# ═══════════════════════════════════════════════════════════════════════════
# Metrics tracking (in-memory)
# ═══════════════════════════════════════════════════════════════════════════

from collections import Counter, defaultdict
from time import perf_counter


class MetricsTracker:
    """
    Simple in-memory metrics tracking.
    Exposed via /api/metrics endpoint.
    """

    def __init__(self):
        self.request_count = Counter()
        self.error_count = Counter()
        self.duration_ms: dict[str, list[float]] = defaultdict(list)
        self.start_time = perf_counter()

    def record_request(self, endpoint: str):
        self.request_count[endpoint] += 1

    def record_error(self, endpoint: str, error_type: str):
        self.error_count[f"{endpoint}:{error_type}"] += 1

    def record_duration(self, endpoint: str, duration_ms: float):
        self.duration_ms[endpoint].append(duration_ms)
        # Keep only last 1000 samples to bound memory
        if len(self.duration_ms[endpoint]) > 1000:
            self.duration_ms[endpoint] = self.duration_ms[endpoint][-1000:]

    def get_metrics(self) -> dict:
        uptime = perf_counter() - self.start_time
        return {
            "uptime_seconds": round(uptime, 1),
            "total_requests": sum(self.request_count.values()),
            "requests_by_endpoint": dict(self.request_count),
            "errors_by_type": dict(self.error_count),
            "avg_duration_ms": {
                endpoint: round(sum(times) / len(times), 2)
                for endpoint, times in self.duration_ms.items()
                if times
            },
            "p95_duration_ms": {
                endpoint: round(sorted(times)[int(len(times) * 0.95)], 2)
                for endpoint, times in self.duration_ms.items()
                if len(times) >= 20
            },
        }


metrics = MetricsTracker()
