import html
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

CSV = Path(__file__).with_name("repairs.csv")
STATUS_BG = {
    "RECEIVED": "#ffffff",
    "IN REPAIR": "#fff3b0",
    "WAITING PARTS": "#fb923c",
    "READY": "#93c5fd",
    "RETURNED": "#22c55e",
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TH = (
    "background:#000;color:#fff;font-weight:700;text-align:center;"
    "border:1px solid #000;padding:6px 8px"
)
TD = (
    "text-align:center;border:1px solid #000;padding:6px 8px;"
    "vertical-align:middle;color:#111;background:{bg}"
)

st.set_page_config(
    page_title="Pro Dental Repair – Equipment in Repair",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def last_updated(path: Path) -> str:
    try:
        stamp = subprocess.check_output(
            ["git", "log", "-1", "--format=%cs", "--", path.name],
            cwd=path.parent,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if stamp:
            return stamp
    except (OSError, subprocess.CalledProcessError):
        pass
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def pieces(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(" / ")]


def picked_label(picked: str, status: str, today) -> str:
    text = str(picked).strip()
    if text in {"", "-"}:
        return "-"
    try:
        start = datetime.strptime(text, "%b %d, %Y").date()
    except ValueError:
        return html.escape(text)
    short = html.escape(f"{MONTHS[start.month - 1]} {start.day}")
    if str(status).strip().upper() == "RETURNED":
        return short
    return f"{short}<br>{(today - start).days} días"


def table_html(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    today = datetime.now(ZoneInfo("America/New_York")).date()
    head = "".join(f'<th style="{TH}">{html.escape(col)}</th>' for col in columns)
    rows = []
    for rec in frame.to_dict("records"):
        cells = []
        for col in columns:
            bg = "#ffffff"
            if col == "STATUS":
                bg = STATUS_BG.get(str(rec[col]).strip().upper(), "#ffffff")
            if col == "PICKED UP":
                body = picked_label(rec[col], rec.get("STATUS", ""), today)
            else:
                body = "<br>".join(html.escape(part) for part in pieces(rec[col]))
            cells.append(f'<td style="{TD.format(bg=bg)}">{body}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table style="border-collapse:collapse;width:100%;font-size:14px">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


frame = pd.read_csv(CSV, dtype=str, keep_default_na=False, encoding="utf-8")
frame = frame.apply(lambda col: col.str.strip().replace("", "-"))

st.html(
    """
    <style>
    header[data-testid="stHeader"] { height: 0; min-height: 0; background: transparent; }
    .block-container,
    [data-testid="stAppViewBlockContainer"] { padding-top: 1rem; }
    [data-testid="stHeading"],
    [data-testid="stHeading"] :is(h1, h2, h3) { margin-top: 0; }
    </style>
    """
)
st.subheader("Pro Dental Repair – Equipment in Repair")
query = st.text_input("Search", placeholder="Filter rows").strip()
if query:
    needle = query.lower()
    frame = frame[
        frame.apply(lambda row: needle in " ".join(row.astype(str)).lower(), axis=1)
    ]
returned = frame["STATUS"].str.strip().str.upper().eq("RETURNED")
frame = pd.concat([frame.loc[~returned], frame.loc[returned]])

st.html(table_html(frame))
st.caption(f"repairs.csv last updated {last_updated(CSV)}")
