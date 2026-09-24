"""
logger.py
Combeez shared logging module — "lolcat" themed.

- Rainbow, per-character gradient console banners (real lolcat-style cycling).
- Severity-colored console output (DEBUG/INFO/WARNING/ERROR/CRITICAL).
- Rotating file handler writing structured JSON-lines so the web dashboard
  (app.py) can read, filter, and live-tail logs.

Python 3.12. Standard library only (no extra deps).

Usage:
    from logger import get_logger, rainbow

    log = get_logger("RAGer")
    log.info("Index rebuilt in %.2fms", 12.4)

    print(rainbow("COMBEEZ MONITOR"))
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths / constants
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "combeez.log"

# Classic lolcat rainbow spectrum, matches the Combeez UI's spectral gradient.
RAINBOW = [196, 202, 208, 214, 220, 226, 190, 154, 118, 82, 46, 47, 48, 49, 50,
           51, 45, 39, 33, 27, 21, 57, 93, 129, 165, 201, 200, 199, 198, 197]

# Level -> ANSI color (256-color codes) used for console output.
LEVEL_COLORS = {
    "DEBUG": 244,     # grey
    "INFO": 51,       # cyan
    "WARNING": 220,   # yellow
    "ERROR": 198,     # magenta/pink
    "CRITICAL": 196,  # red
}

RESET = "\x1b[0m"


def _fg(code: int) -> str:
    return f"\x1b[38;5;{code}m"


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty() or os.environ.get("COMBEEZ_FORCE_COLOR") == "1"


def rainbow(text: str) -> str:
    """Return `text` with each character cycling through the lolcat rainbow.
    Falls back to plain text when the terminal doesn't support color."""
    if not _supports_color():
        return text
    out = []
    i = 0
    for ch in text:
        if ch != " ":
            color = RAINBOW[i % len(RAINBOW)]
            out.append(f"{_fg(color)}{ch}{RESET}")
            i += 1
        else:
            out.append(ch)
    return "".join(out)


def print_banner(title: str = "COMBEEZ MONITOR") -> None:
    """Print a lolcat-style startup banner."""
    bar = rainbow("=" * (len(title) + 8))
    print(bar)
    print(f"    {rainbow(title)}")
    print(bar)


# --------------------------------------------------------------------------- #
# Formatters
# --------------------------------------------------------------------------- #

class LolcatConsoleFormatter(logging.Formatter):
    """Colors each log line by severity; module name gets the rainbow treatment."""

    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelname, 15)
        ts = time.strftime("%H:%M:%S", time.localtime(record.created))
        message = record.getMessage()

        if not _supports_color():
            return f"{ts} [{record.levelname:<8}] {record.name}: {message}"

        level_str = f"{_fg(color)}[{record.levelname:<8}]{RESET}"
        name_str = rainbow(record.name)
        ts_str = f"\x1b[38;5;244m{ts}{RESET}"
        return f"{ts_str} {level_str} {name_str}: {message}"


class JsonLinesFormatter(logging.Formatter):
    """One JSON object per line, for the web dashboard's log viewer/API."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

_configured_root = False


def _configure_root(level: str = "INFO") -> None:
    global _configured_root
    if _configured_root:
        return

    root = logging.getLogger("combeez")
    root.setLevel(level)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(LolcatConsoleFormatter())
    root.addHandler(console)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(JsonLinesFormatter())
    root.addHandler(file_handler)

    root.propagate = False
    _configured_root = True


def get_logger(module_name: str, level: str = "INFO") -> logging.Logger:
    """Get a Combeez logger for a given module (e.g. 'RAGer', 'Cloudes', 'app').

    All loggers share one rotating JSON-lines file (logs/combeez.log) that
    app.py reads for the live web log viewer, plus rainbow console output.
    """
    _configure_root(level)
    log = logging.getLogger(f"combeez.{module_name}")
    log.setLevel(level)
    return log


def set_level(level: str) -> None:
    """Change the log level for every Combeez logger (used by Settings page)."""
    logging.getLogger("combeez").setLevel(level)
    for name in logging.root.manager.loggerDict:
        if name.startswith("combeez."):
            logging.getLogger(name).setLevel(level)


def read_recent_logs(limit: int = 200, level: str | None = None, search: str | None = None):
    """Read the most recent parsed log entries from the JSON-lines log file.
    Used by app.py's /api/logs endpoint to power the live web log viewer."""
    if not LOG_FILE.exists():
        return []

    entries = []
    with LOG_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if level and level != "ALL":
        entries = [e for e in entries if e.get("level") == level]
    if search:
        needle = search.lower()
        entries = [e for e in entries if needle in json.dumps(e).lower()]

    return entries[-limit:]


if __name__ == "__main__":
    print_banner()
    log = get_logger("demo")
    log.debug("Debug probe fired")
    log.info("Combeez logger online")
    log.warning("Cache nearing capacity")
    log.error("Failed to reach vector store")
    log.critical("Daemon crashed")
