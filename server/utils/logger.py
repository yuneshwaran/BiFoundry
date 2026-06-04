import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "transactions.log"

# ── Structured JSON formatter ─────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    # All attributes that exist on a default LogRecord — never treat these as
    # user-supplied extras.  Keeping this explicit avoids the KeyError that
    # Python's logging raises when extra= tries to overwrite a built-in attr.
    _LOGRECORD_BUILTINS: frozenset[str] = frozenset(
        vars(logging.makeLogRecord({})).keys()
        | {
            "message", "asctime", "exc_text", "stack_info",
            # Python 3.12+
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Collect only the keys that were injected via extra={}
        for key, value in record.__dict__.items():
            if key not in self._LOGRECORD_BUILTINS:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


# ── Logger factory ─────────────────────────────────────────────────────────────


def get_logger(name: str = "metadash") -> logging.Logger:
    """
    Return a named logger with:
      - JSON file handler  → logs/transactions.log
      - Human-readable console handler → stdout
    Calling this multiple times with the same name is safe (handlers added once).
    """
    logger = logging.getLogger(name)

    if logger.handlers:          # already configured — return as-is
        return logger

    logger.setLevel(logging.DEBUG)

    # ── File handler (JSON) ────────────────────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())

    # ── Console handler (readable) ─────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


# ── Convenience: structured event helper ──────────────────────────────────────


def log_event(event_type: str, payload: dict, logger_name: str = "metadash") -> None:
    """
    Log a named event with a structured payload dict.

    Payload keys are prefixed with ``data_`` before being passed to
    ``extra={}`` so they never collide with Python's reserved LogRecord
    attributes (filename, lineno, module, thread, process, …).

    Usage:
        log_event("import.complete", {"report": "SalesReport", "file_count": 42})

    JSON output:
        {"event": "import.complete", "data_report": "SalesReport", "data_file_count": 42, ...}
    """
    _logger = get_logger(logger_name)
    safe_extra = {"event": event_type}
    safe_extra.update({f"data_{k}": v for k, v in payload.items()})
    _logger.info(event_type, extra=safe_extra)