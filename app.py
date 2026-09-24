"""
app.py — Combeez Monitor (Streamlit edition)

A gold/black-themed dashboard for watching the RAGer and Cloudes modules:
real file explorer + real code viewer, a log stream, and settings.

Deploy on Streamlit Community Cloud: point it at this file. Run locally with:
    pip install -r requirements.txt
    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from logger import get_logger, set_level, read_recent_logs, print_banner

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.json"
LOGO_FILE = BASE_DIR / "Combeez.png"

MODULES = {
    "RAGer": BASE_DIR / "RAGer",
    "Cloudes": BASE_DIR / "Cloudes",
}
IGNORE_NAMES = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".DS_Store"}
LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".sql": "sql", ".sh": "bash", ".rs": "rust",
    ".html": "html", ".css": "css",
}

DEFAULT_SETTINGS = {"log_level": "INFO", "refresh_interval_sec": 5}

log = get_logger("app")


# --------------------------------------------------------------------------- #
# Settings persistence
# --------------------------------------------------------------------------- #

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return {**DEFAULT_SETTINGS, **json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Module scanning
# --------------------------------------------------------------------------- #

def module_stats(root: Path) -> dict:
    root.mkdir(exist_ok=True)
    file_count, total_size = 0, 0
    for p in root.rglob("*"):
        if any(part in IGNORE_NAMES for part in p.parts):
            continue
        if p.is_file():
            file_count += 1
            total_size += p.stat().st_size
    return {"file_count": file_count, "total_size": total_size,
            "status": "RUNNING" if file_count else "EMPTY"}


def build_tree(path: Path, root: Path) -> dict:
    node = {"name": path.name, "path": "" if path == root else str(path.relative_to(root)),
            "type": "dir", "children": []}
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except OSError:
        return node
    for entry in entries:
        if entry.name in IGNORE_NAMES:
            continue
        if entry.is_dir():
            node["children"].append(build_tree(entry, root))
        else:
            node["children"].append({"name": entry.name,
                                      "path": str(entry.relative_to(root)),
                                      "type": "file"})
    return node


def flatten(node: dict, depth: int = -1) -> list[tuple[int, dict]]:
    """Depth-first flat list so we can render without nested expanders
    (Streamlit doesn't allow those)."""
    rows = []
    if node["type"] == "dir":
        if depth >= 0:
            rows.append((depth, node))
        for child in node["children"]:
            rows.extend(flatten(child, depth + 1))
    else:
        rows.append((depth, node))
    return rows


# --------------------------------------------------------------------------- #
# Page chrome / theme helpers
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="Combeez Monitor", page_icon="🐝", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }
.lolcat-title {
  background: linear-gradient(90deg,#ffe066,#f2c94c,#f2a900,#b8860b,#f2a900,#f2c94c,#ffe066);
  background-size: 300% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  font-weight: 800; font-size: 2rem;
}
.status-pill { padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.status-running { background: rgba(242,169,0,0.15); color: #f2a900; }
.status-empty { background: rgba(138,122,92,0.15); color: #8a7a5c; }
.log-ERROR, .log-CRITICAL { color: #e0563f; }
.log-WARNING { color: #ffc107; }
.log-DEBUG { color: #8a7a5c; }
.log-INFO { color: #e8871e; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    if LOGO_FILE.exists():
        st.image(str(LOGO_FILE), width=120)
    else:
        st.markdown("🐝")
    st.markdown('<span class="lolcat-title" style="font-size:1.1rem;">COMBEEZ MONITOR</span>',
                unsafe_allow_html=True)
    st.caption("> $ combeez --live")
    st.divider()
    page = st.radio("Navigate", ["Dashboard", "RAGer", "Cloudes", "Logs", "Settings"],
                     label_visibility="collapsed")
    st.divider()
    st.caption("Python 3.12+ · Streamlit")

settings = load_settings()
set_level(settings["log_level"])


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #

def page_dashboard():
    st.markdown('<div class="lolcat-title">$ combeez status --all</div>', unsafe_allow_html=True)
    st.caption("Real-time file & log monitor for **RAGer** (retrieval engine) and **Cloudes** (sync service).")

    cols = st.columns(2)
    for col, (name, root) in zip(cols, MODULES.items()):
        stats = module_stats(root)
        with col:
            st.markdown(f"#### {name}")
            pill = "status-running" if stats["status"] == "RUNNING" else "status-empty"
            st.markdown(f'<span class="status-pill {pill}">[{stats["status"]}]</span>', unsafe_allow_html=True)
            st.metric("Files", stats["file_count"])
            st.caption(f"{stats['total_size'] / 1024:.1f} KB on disk")

    st.divider()
    st.markdown("##### Recent Log Activity")
    entries = read_recent_logs(limit=8)
    if not entries:
        st.caption("No log entries yet — use RAGer/Cloudes with `logger.py` to generate some.")
    for e in reversed(entries):
        st.markdown(
            f'<span class="log-{e["level"]}">[{e["level"]}]</span> '
            f'<span style="color:#c9bda0">{e["time"]} · {e["module"]}:</span> {e["message"]}',
            unsafe_allow_html=True,
        )


def page_module(name: str):
    root = MODULES[name]
    stats = module_stats(root)
    st.markdown(f'<div class="lolcat-title">{name} Explorer</div>', unsafe_allow_html=True)
    st.caption(f"{stats['file_count']} files · {stats['total_size'] / 1024:.1f} KB — reading live from `./{name}/`")

    tree_col, code_col = st.columns([1, 2])
    state_key = f"selected_file_{name}"

    with tree_col:
        st.markdown("**Explorer**")
        tree = build_tree(root, root)
        rows = flatten(tree)
        if len(rows) <= 1:  # just the readme, or truly empty
            pass
        for depth, node in rows:
            indent = "&nbsp;&nbsp;" * max(depth, 0)
            if node["type"] == "dir":
                st.markdown(f"{indent}📁 **{node['name']}**", unsafe_allow_html=True)
            else:
                label = f"{indent}📄 {node['name']}"
                if st.button(label.replace("&nbsp;", " "), key=f"btn_{name}_{node['path']}", use_container_width=True):
                    st.session_state[state_key] = node["path"]

    with code_col:
        selected = st.session_state.get(state_key)
        if selected:
            file_path = root / selected
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                lang = LANG_BY_EXT.get(file_path.suffix.lower(), "text")
                st.markdown(f"**{selected}** · {content.count(chr(10)) + 1} lines · {file_path.stat().st_size} bytes")
                st.code(content, language=lang, line_numbers=True)
            except OSError as exc:
                st.error(f"Could not read {selected}: {exc}")
        else:
            st.info(f"Select a file from the tree to view it. Drop {name}'s real source files "
                    f"into `./{name}/` and they'll show up here automatically.")


def page_logs():
    st.markdown('<div class="lolcat-title">$ tail -f combeez.log</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2, 1, 1])
    search = c1.text_input("grep logs...", label_visibility="collapsed", placeholder="grep logs...")
    level = c2.selectbox("Level", ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                          label_visibility="collapsed")
    if c3.button("🔄 Refresh", use_container_width=True):
        st.rerun()

    entries = read_recent_logs(limit=300, level=level, search=search or None)
    st.caption(f"{len(entries)} entries")
    box = st.container(height=480)
    with box:
        if not entries:
            st.caption("No matching log entries.")
        for e in entries:
            box.markdown(
                f'<span style="color:#8a7a5c">{e["time"]}</span> '
                f'<span class="log-{e["level"]}">[{e["level"]}]</span> '
                f'<span style="color:#c9bda0">{e["module"]}:</span> {e["message"]}',
                unsafe_allow_html=True,
            )


def page_settings():
    st.markdown('<div class="lolcat-title">$ combeez config --set</div>', unsafe_allow_html=True)
    with st.form("settings_form"):
        log_level = st.selectbox("Log level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                  index=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"].index(settings["log_level"]))
        refresh = st.number_input("Refresh reminder (seconds)", min_value=2, max_value=60,
                                   value=settings["refresh_interval_sec"])
        submitted = st.form_submit_button("Apply Config")
        if submitted:
            new_settings = {"log_level": log_level, "refresh_interval_sec": int(refresh)}
            save_settings(new_settings)
            set_level(log_level)
            log.info("Settings updated: %s", new_settings)
            st.success("Saved.")
            st.rerun()


PAGES = {
    "Dashboard": page_dashboard,
    "RAGer": lambda: page_module("RAGer"),
    "Cloudes": lambda: page_module("Cloudes"),
    "Logs": page_logs,
    "Settings": page_settings,
}
PAGES[page]()
