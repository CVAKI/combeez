"""
app.py
Combeez Monitor — web dashboard for the RAGer and Cloudes modules.

Serves the lolcat-themed dashboard (design based on the Stitch export) and
backs it with real data:
  - Dashboard: live file counts / sizes / status for RAGer & Cloudes.
  - Module explorer: real file tree + real file contents for each module.
  - Logs: reads logger.py's JSON-lines log file, filterable, polled live.
  - Settings: log level + refresh interval, persisted to settings.json.

Python 3.12, Flask only.
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request, abort, send_from_directory

from logger import get_logger, set_level, read_recent_logs, print_banner

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.json"

# The two colleague-owned modules from the architecture diagram.
MODULES = {
    "rager": {"label": "RAGer", "dir": BASE_DIR / "RAGer"},
    "cloudes": {"label": "Cloudes", "dir": BASE_DIR / "Cloudes"},
}

# Files/dirs we never want to expose or walk into.
IGNORE_NAMES = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".DS_Store"}
CODE_EXTENSIONS = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".sql": "sql", ".sh": "bash", ".rs": "rust",
    ".html": "xml", ".css": "css", ".txt": "plaintext",
}

# The Combeez logo lives in the project root (not static/) — served directly.
LOGO_FILENAME = "Combeez.png"

DEFAULT_SETTINGS = {
    "log_level": "INFO",
    "refresh_interval_sec": 5,
    "rainbow_intensity": "full",  # "subtle" | "full"
}

app = Flask(__name__)
log = get_logger("app")


@app.context_processor
def inject_sidebar_status():
    """Makes module RUNNING/EMPTY status available to base.html's sidebar
    on every page, not just the dashboard."""
    try:
        status = {key: module_stats(key)["status"] for key in MODULES}
    except Exception:
        status = {key: "UNKNOWN" for key in MODULES}
    return {"stats_status": status}


# --------------------------------------------------------------------------- #
# Settings persistence
# --------------------------------------------------------------------------- #

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except (json.JSONDecodeError, OSError):
            log.warning("settings.json unreadable, falling back to defaults")
    return dict(DEFAULT_SETTINGS)


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Module file-tree helpers (path-traversal safe)
# --------------------------------------------------------------------------- #

def module_dir(module_key: str) -> Path:
    if module_key not in MODULES:
        abort(404, f"Unknown module '{module_key}'")
    d = MODULES[module_key]["dir"]
    d.mkdir(exist_ok=True)
    return d


def safe_resolve(module_key: str, rel_path: str) -> Path:
    """Resolve rel_path inside the module's dir; refuse anything that escapes it."""
    root = module_dir(module_key).resolve()
    target = (root / rel_path).resolve()
    if root != target and root not in target.parents:
        abort(400, "Invalid path")
    return target


def build_tree(path: Path, root: Path) -> dict:
    """Recursively build a JSON-serializable file tree for the explorer UI."""
    node = {
        "name": path.name or str(path),
        "path": str(path.relative_to(root)) if path != root else "",
        "type": "dir",
        "children": [],
    }
    try:
        entries = sorted(
            path.iterdir(),
            key=lambda p: (p.is_file(), p.name.lower()),
        )
    except OSError:
        return node

    for entry in entries:
        if entry.name in IGNORE_NAMES:
            continue
        if entry.is_dir():
            node["children"].append(build_tree(entry, root))
        else:
            node["children"].append({
                "name": entry.name,
                "path": str(entry.relative_to(root)),
                "type": "file",
                "size": entry.stat().st_size,
            })
    return node


def module_stats(module_key: str) -> dict:
    root = module_dir(module_key)
    file_count = 0
    total_size = 0
    for p in root.rglob("*"):
        if any(part in IGNORE_NAMES for part in p.parts):
            continue
        if p.is_file():
            file_count += 1
            total_size += p.stat().st_size
    has_code = file_count > 0
    return {
        "file_count": file_count,
        "total_size": total_size,
        "status": "RUNNING" if has_code else "EMPTY",
    }


# --------------------------------------------------------------------------- #
# Routes — pages
# --------------------------------------------------------------------------- #

@app.route("/logo.png")
def logo():
    """Serves Combeez.png straight from the project root folder."""
    if not (BASE_DIR / LOGO_FILENAME).exists():
        abort(404, f"Put {LOGO_FILENAME} in the project root (next to app.py)")
    return send_from_directory(BASE_DIR, LOGO_FILENAME)


@app.route("/")
def dashboard():
    settings = load_settings()
    stats = {key: module_stats(key) for key in MODULES}
    log_entries = read_recent_logs(limit=6)
    return render_template(
        "dashboard.html",
        active_page="dashboard",
        modules=MODULES,
        stats=stats,
        recent_logs=log_entries,
        settings=settings,
    )


@app.route("/module/<module_key>")
def module_page(module_key: str):
    if module_key not in MODULES:
        abort(404)
    settings = load_settings()
    tree = build_tree(module_dir(module_key), module_dir(module_key))
    stats = module_stats(module_key)
    return render_template(
        "module.html",
        active_page=module_key,
        module_key=module_key,
        module_label=MODULES[module_key]["label"],
        tree=tree,
        stats=stats,
        modules=MODULES,
        settings=settings,
    )


@app.route("/logs")
def logs_page():
    settings = load_settings()
    entries = read_recent_logs(limit=200)
    return render_template(
        "logs.html",
        active_page="logs",
        modules=MODULES,
        entries=entries,
        settings=settings,
    )


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    settings = load_settings()
    if request.method == "POST":
        settings["log_level"] = request.form.get("log_level", settings["log_level"])
        try:
            settings["refresh_interval_sec"] = int(
                request.form.get("refresh_interval_sec", settings["refresh_interval_sec"])
            )
        except ValueError:
            pass
        settings["rainbow_intensity"] = request.form.get(
            "rainbow_intensity", settings["rainbow_intensity"]
        )
        save_settings(settings)
        set_level(settings["log_level"])
        log.info("Settings updated: %s", settings)
    return render_template(
        "settings.html", active_page="settings", modules=MODULES, settings=settings
    )


# --------------------------------------------------------------------------- #
# Routes — JSON API (used by the page JS for live data)
# --------------------------------------------------------------------------- #

@app.route("/api/modules/status")
def api_module_status():
    return jsonify({key: module_stats(key) for key in MODULES})


@app.route("/api/module/<module_key>/tree")
def api_module_tree(module_key: str):
    if module_key not in MODULES:
        abort(404)
    return jsonify(build_tree(module_dir(module_key), module_dir(module_key)))


@app.route("/api/module/<module_key>/file")
def api_module_file(module_key: str):
    rel_path = request.args.get("path", "")
    target = safe_resolve(module_key, rel_path)
    if not target.is_file():
        abort(404, "File not found")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        abort(500, str(exc))
    ext = target.suffix.lower()
    return jsonify({
        "path": rel_path,
        "language": CODE_EXTENSIONS.get(ext, "plaintext"),
        "size": target.stat().st_size,
        "lines": content.count("\n") + 1,
        "content": content,
    })


@app.route("/api/logs")
def api_logs():
    level = request.args.get("level", "ALL")
    search = request.args.get("q") or None
    limit = int(request.args.get("limit", 200))
    entries = read_recent_logs(limit=limit, level=level, search=search)
    return jsonify(entries)


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        settings = load_settings()
        settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        save_settings(settings)
        set_level(settings["log_level"])
        log.info("Settings updated via API: %s", settings)
        return jsonify(settings)
    return jsonify(load_settings())


if __name__ == "__main__":
    print_banner("COMBEEZ MONITOR")
    settings = load_settings()
    set_level(settings["log_level"])
    log.info("Combeez Monitor starting on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
