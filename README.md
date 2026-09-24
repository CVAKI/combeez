# Combeez Monitor (Streamlit edition)

Gold/black-themed dashboard for the **RAGer** and **Cloudes** modules —
real file explorer, real code viewer (syntax highlighted), a log stream,
and settings. Built for **Streamlit Community Cloud** deployment.

## Deploy on Streamlit Cloud
Point your Streamlit Cloud app at this repo with **`app.py`** as the main
file (that's the default). No extra config needed — `.streamlit/config.toml`
already sets the gold/black theme.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Folder layout
```
combeez_streamlit/
├── app.py              # Streamlit app (dashboard, explorer, logs, settings)
├── logger.py             # Shared rainbow/lolcat logger — same as before
├── Combeez.png            # Your logo, shown in the sidebar
├── RAGer/                  # <- colleague drops RAGer source here
├── Cloudes/                 # <- colleague drops Cloudes source here
└── logs/combeez.log          # JSON-lines log file written by logger.py
```

## Using logger.py from RAGer / Cloudes
```python
from logger import get_logger
log = get_logger("RAGer")
log.info("Index rebuilt in %.2fms", 12.4)
```
Every call shows up on the Logs page automatically.

## Note
This replaces the earlier Flask version. Flask apps can't run on Streamlit
Cloud — only Streamlit apps (`import streamlit as st`) can. If you ever want
to run this locally as a full custom web app instead, the Flask version
still works fine with `python app.py`; just don't push that one to
Streamlit Cloud.
