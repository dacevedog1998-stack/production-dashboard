from __future__ import annotations

from pathlib import Path

import streamlit as st
from PIL import Image

from database import init_database

APP_FOLDER = Path(__file__).parent
FAVICON_FILE = APP_FOLDER / "favicon.png"

if FAVICON_FILE.exists():
    favicon = Image.open(FAVICON_FILE)
else:
    favicon = "🏭"

st.set_page_config(
    page_title="Production Dashboard",
    page_icon=favicon,
    layout="wide",
)

try:
    init_database()
except Exception as error:
    st.error("The application could not connect to the database.")
    st.code(str(error))
    st.info(
        "Add DATABASE_URL in Streamlit App settings > Secrets."
    )
    st.stop()

production_page = st.Page(
    "views/production_report.py",
    title="Production Report",
    icon="📊",
    default=True,
)

upload_page = st.Page(
    "views/upload_reports.py",
    title="Upload Reports",
    icon="⬆️",
)

navigation = st.navigation(
    [
        production_page,
        upload_page,
    ],
    position="sidebar",
    expanded=True,
)

navigation.run()
