import html
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

CSV = Path(__file__).with_name("parts.csv")
COLUMNS = [
    "VENDOR",
    "PART",
    "DESCRIP.",
    "JOB",
    "CUSTOMER",
    "ADDRESS",
    "CARRIER",
    "TRACKING",
    "ETA",
    "STATUS",
]
STATUS_BG = {
    "ORDERED": "#ffffff",
    "SHIPPED": "#fff3b0",
    "DELIVERED": "#22c55e",
    "DELAYED": "#fb923c",
}
TRACK_URL = {
    "UPS": "https://www.ups.com/track?tracknum={}",
    "USPS": "https://tools.usps.com/go/TrackConfirmAction?tLabels={}",
    "FEDEX": "https://www.fedex.com/fedextrack/?trknbr={}",
}
TH = (
    "background:#000;color:#fff;font-weight:700;text-align:center;"
    "border:1px solid #000;padding:6px 8px"
)
TD = (
    "text-align:center;border:1px solid #000;padding:6px 8px;"
    "vertical-align:middle;color:#111;background:{bg};font-weight:700"
)

st.set_page_config(
    page_title="Pro Dental Repair – Parts",
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


def customer_html(value: str) -> str:
    parts = pieces(value)
    if not parts:
        return ""
    name = (
        f'<span style="font-size:0.8em;white-space:nowrap">{html.escape(parts[0])}</span>'
    )
    return name + "".join(f"<br>{html.escape(part)}" for part in parts[1:])


def tracking_html(carrier: str, value: str) -> str:
    template = TRACK_URL.get(str(carrier).strip().upper())
    bits = []
    for number in pieces(value):
        if not number or number == "-":
            bits.append("-")
            continue
        label = html.escape(number)
        if template:
            href = template.format(quote(number, safe=""))
            bits.append(f'<a href="{href}" target="_blank">{label}</a>')
        else:
            bits.append(label)
    return "<br>".join(bits)


def table_html(frame: pd.DataFrame) -> str:
    head = "".join(f'<th style="{TH}">{html.escape(col)}</th>' for col in COLUMNS)
    rows = []
    for rec in frame.to_dict("records"):
        cells = []
        for col in COLUMNS:
            bg = "#ffffff"
            if col == "STATUS":
                bg = STATUS_BG.get(str(rec[col]).strip().upper(), "#ffffff")
                body = html.escape(str(rec[col]))
            elif col == "TRACKING":
                body = tracking_html(rec["CARRIER"], rec[col])
            elif col == "CUSTOMER":
                body = customer_html(rec[col])
            elif col == "PART":
                body = "<br>".join(html.escape(part) for part in pieces(rec[col]))
            else:
                body = html.escape(str(rec[col]))
            cells.append(f'<td style="{TD.format(bg=bg)}">{body}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table style="border-collapse:collapse;width:100%;font-size:14px">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


frame = pd.read_csv(CSV, dtype=str, keep_default_na=False, encoding="utf-8")
frame = frame[COLUMNS].apply(lambda col: col.str.strip().replace("", "-"))

st.html(
    """
    <style>
    header[data-testid="stHeader"] { height: 0; min-height: 0; background: transparent; }
    table th, table td, table th *, table td * { font-weight: 700; }
    .stMain,
    [data-testid="stMain"],
    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
      padding-left: 0.5rem;
      padding-right: 0.5rem;
      max-width: 100%;
    }
    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] { padding-top: 1rem; }
    [data-testid="stHeading"],
    [data-testid="stHeading"] :is(h1, h2, h3) { margin-top: 0; }
    </style>
    """
)
st.subheader("Pro Dental Repair – Parts")
query = st.text_input("Search", placeholder="Filter rows").strip()
if query:
    needle = query.lower()
    frame = frame[
        frame.apply(lambda row: needle in " ".join(row.astype(str)).lower(), axis=1)
    ]
delivered = frame["STATUS"].str.strip().str.upper().eq("DELIVERED")
frame = pd.concat([frame.loc[~delivered], frame.loc[delivered]])

st.html(table_html(frame))
st.caption(f"parts.csv last updated {last_updated(CSV)}")
