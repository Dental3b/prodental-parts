import html
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st

CSV = Path(__file__).with_name("parts.csv")
COLUMNS = [
    "TECH",
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
    "TO ORDER": "#ef4444",
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
SUM_TH = (
    "background:#fff;color:#111;font-weight:700;text-align:center;"
    "border:1px solid #ccc;padding:0 4px;line-height:1.1;font-size:10px"
)
SUM_TD = (
    "text-align:center;background:#fff;color:#111;font-weight:700;"
    "border:1px solid #ccc;padding:0 4px;line-height:1.1;font-size:10px"
)
TECHS = ["DANIEL", "ELOY", "JOSE"]
SUMMARY_ROWS = ["TO ORDER", "ORDERED", "SHIPPED"]

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


def summary_html(frame: pd.DataFrame) -> str:
    tech = frame["TECH"].str.strip().str.upper()
    status = frame["STATUS"].str.strip().str.upper()

    def count(name: str, state: str) -> int:
        return int((tech.eq(name) & status.eq(state)).sum())

    head = "".join(f'<th style="{SUM_TH}">{html.escape(col)}</th>' for col in ["", *TECHS])
    body = []
    for state in SUMMARY_ROWS:
        cells = [f'<td style="{SUM_TD}">{html.escape(state)}</td>']
        cells += [f'<td style="{SUM_TD}">{count(name, state)}</td>' for name in TECHS]
        body.append("<tr>" + "".join(cells) + "</tr>")
    table = (
        '<table style="border-collapse:collapse;width:auto;margin:0">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"
    )
    return (
        '<div style="display:flex;justify-content:flex-end;margin-top:0.85rem;margin-bottom:-0.85rem">'
        f"{table}</div>"
    )


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
    [data-testid="stHorizontalBlock"] { align-items: flex-start; }
    [data-testid="stHorizontalBlock"] [data-testid="stElementContainer"] { margin: 0; }
    </style>
    """
)


@st.fragment(run_every=300)
def show_parts():
    frame = pd.read_csv(CSV, dtype=str, keep_default_na=False, encoding="utf-8")
    frame = frame[COLUMNS].apply(lambda col: col.str.strip().replace("", "-"))
    title_col, summary_col = st.columns([1.5, 1], vertical_alignment="top", gap="small")
    with title_col:
        st.subheader("Pro Dental Repair – Parts")
    with summary_col:
        st.html(summary_html(frame))
    query = st.text_input("Search", placeholder="Filter rows").strip()
    if query:
        needle = query.lower()
        frame = frame[
            frame.apply(lambda row: needle in " ".join(row.astype(str)).lower(), axis=1)
        ]
    status = frame["STATUS"].str.strip().str.upper()
    to_order = status.eq("TO ORDER")
    delivered = status.eq("DELIVERED")
    frame = pd.concat([
        frame.loc[to_order],
        frame.loc[~to_order & ~delivered],
        frame.loc[delivered],
    ])
    st.html(table_html(frame))
    st.caption(f"parts.csv last updated {last_updated(CSV)}")


show_parts()
