# Combeez Monitor

A lolcat-themed web dashboard (Flask, Python 3.12) for watching the
**RAGer** and **Cloudes** modules: live file explorer + real code viewer,
a rainbow-tinted log stream, and a settings page — built from the Stitch
AI design export.

## Logo

Put `Combeez.png` (your logo) directly in the project **root** — next to
`app.py`. The app serves it at `/logo.png` and shows it in the sidebar.
No need to move it into `static/`.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Folder layout

```
combeez_monitor/
├── app.py            # Flask app: routes + JSON API
├── logger.py          # Shared lolcat/rainbow logger for the whole project
├── settings.json       # Created automatically on first save (Settings page)
├── requirements.txt
├── templates/          # Jinja pages (dashboard, module explorer, logs, settings)
├── static/js/           # Frontend JS (file tree, code viewer, log polling)
├── RAGer/               # <- your colleague drops RAGer's source code here
├── Cloudes/             # <- your colleague drops Cloudes's source code here
└── logs/
    └── combeez.log      # JSON-lines log file, written by logger.py, read by the Logs page
```

## Using logger.py in RAGer / Cloudes

Your colleagues can log from inside their own modules and it shows up in
the dashboard automatically:

```python
from logger import get_logger

log = get_logger("RAGer")          # or "Cloudes"
log.info("Index rebuilt in %.2fms", 12.4)
log.warning("Cache nearing capacity")
log.error("Failed to reach vector store")
```

Every call is rainbow-colored in the console **and** appended as JSON to
`logs/combeez.log`, which the web Logs page live-tails.

## Notes

- The file explorer and code viewer show **real files** from `RAGer/` and
  `Cloudes/` — there's no mock data. Empty folders just show an empty tree
  until your colleagues add their code.
- Everything runs locally; nothing is uploaded anywhere.
- Change log level / poll interval / rainbow intensity from the Settings
  page — saved to `settings.json`.
