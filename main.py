import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Plug Statements Compliance Dashboard",
    layout="wide",
    page_icon="📊"
)

# ---------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300)
def load_data():
    client = connect()

    # 🔴 PASTE YOUR GOOGLE SHEET FULL URL BELOW
    spreadsheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1n5XAAZV6yejTTD1yV_wAfLLBsidArbsR4OhlU1SqzMQ/edit?usp=sharing"
    )

    # ✅ Correct Sheet Name
    sheet = spreadsheet.worksheet("Summary compliance")

    data = sheet.get_all_records()
    return pd.DataFrame(data)


# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
df = load_data()

df.columns = df.columns.str.strip()

# Ensure required columns exist
required_cols = ["Month", "Compliance %"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"Column '{col}' not found in 'Summary compliance' sheet.")
        st.stop()

# ---------------------------------------------------
# CLEAN DATA
# ---------------------------------------------------
df["Compliance %"] = (
    df["Compliance %"]
    .astype(str)
    .str.replace("%", "", regex=False)
)

df["Compliance %"] = pd.to_numeric(df["Compliance %"], errors="coerce")

df["Month_Date"] = pd.to_datetime(df["Month"], errors="coerce")

# Sort Latest → Oldest (Jan 2026 → Jan 2025)
df = df.sort_values("Month_Date", ascending=False)

# ---------------------------------------------------
# TITLE
# ---------------------------------------------------
st.markdown("## 📊 Plug Statements - Monthly Compliance Overview")

# ---------------------------------------------------
# KPI SECTION
# ---------------------------------------------------
latest = df.iloc[0]
previous = df.iloc[1] if len(df) > 1 else latest

delta = latest["Compliance %"] - previous["Compliance %"]

col1, col2 = st.columns(2)

col1.metric(
    label=f"Latest Compliance ({latest['Month']})",
    value=f"{latest['Compliance %']:.2f}%",
    delta=f"{delta:.2f}% vs Previous Month"
)

col2.metric(
    label="Average Compliance",
    value=f"{df['Compliance %'].mean():.2f}%"
)

st.markdown("---")

# ---------------------------------------------------
# TARGET CONFIG
# ---------------------------------------------------
TARGET = 97  # Change SLA target if needed

colors = [
    "#2E8B57" if val >= TARGET else "#D62728"
    for val in df["Compliance %"]
]

# ---------------------------------------------------
# CHART
# ---------------------------------------------------
fig = go.Figure()

# Bar Chart
fig.add_trace(go.Bar(
    x=df["Month"],
    y=df["Compliance %"],
    marker_color=colors,
    text=[f"{v:.2f}%" for v in df["Compliance %"]],
    textposition="outside",
))

# Trend Line
fig.add_trace(go.Scatter(
    x=df["Month"],
    y=df["Compliance %"],
    mode="lines+markers",
    line=dict(width=3),
))

# SLA Target Line
fig.add_hline(
    y=TARGET,
    line_dash="dash",
    annotation_text=f"SLA Target ({TARGET}%)",
    annotation_position="top right"
)

fig.update_layout(
    height=550,
    yaxis=dict(range=[90, 100], title="Compliance %"),
    xaxis_title="Month (Latest → Oldest)",
    template="plotly_white",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------
# EXECUTIVE INSIGHT
# ---------------------------------------------------
if latest["Compliance %"] >= TARGET:
    status = "🟢 Meeting SLA Target"
else:
    status = "🔴 Below SLA Target – Attention Required"

st.info(f"""
### 📌 Executive Insight
- Latest Month: **{latest['Month']}**
- Compliance: **{latest['Compliance %']:.2f}%**
- SLA Target: **{TARGET}%**
- Status: {status}
""")
