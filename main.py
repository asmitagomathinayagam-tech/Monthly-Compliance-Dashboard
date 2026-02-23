import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Monthly Compliance Dashboard",
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
    spreadsheet = client.open("Non compliance 2025_Jan to 2026_Jan")
    sheet = spreadsheet.worksheet("PlugStatements_2026_02_Consolidate")
    data = sheet.get_all_records()
    return pd.DataFrame(data)


df = load_data()

# ---------------------------------------------------
# CLEANING
# ---------------------------------------------------
df.columns = df.columns.str.strip()

df["Compliance %"] = (
    df["Compliance %"]
    .astype(str)
    .str.replace("%", "")
)

df["Compliance %"] = pd.to_numeric(df["Compliance %"], errors="coerce")

df["Month_Date"] = pd.to_datetime(df["Month"], errors="coerce")
df = df.sort_values("Month_Date")

# ---------------------------------------------------
# KPI SECTION
# ---------------------------------------------------
st.markdown("## 📊 Plug Statements - Monthly Compliance Overview")

latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) > 1 else latest

delta = latest["Compliance %"] - previous["Compliance %"]

col1, col2 = st.columns([2,1])

with col1:
    st.metric(
        label=f"Latest Compliance ({latest['Month']})",
        value=f"{latest['Compliance %']:.2f}%",
        delta=f"{delta:.2f}% vs Previous Month"
    )

with col2:
    avg_compliance = df["Compliance %"].mean()
    st.metric(
        label="Average Compliance",
        value=f"{avg_compliance:.2f}%"
    )

st.markdown("---")

# ---------------------------------------------------
# TARGET
# ---------------------------------------------------
TARGET = 97  # change if needed

# Color coding
colors = [
    "#2E8B57" if val >= TARGET else "#D62728"
    for val in df["Compliance %"]
]

# ---------------------------------------------------
# PROFESSIONAL CHART
# ---------------------------------------------------
fig = go.Figure()

# Bars
fig.add_trace(go.Bar(
    x=df["Month"],
    y=df["Compliance %"],
    marker_color=colors,
    text=[f"{v:.2f}%" for v in df["Compliance %"]],
    textposition="outside",
    name="Compliance %"
))

# Line overlay
fig.add_trace(go.Scatter(
    x=df["Month"],
    y=df["Compliance %"],
    mode="lines+markers",
    line=dict(color="#1f77b4", width=3),
    name="Trend"
))

# Target line
fig.add_hline(
    y=TARGET,
    line_dash="dash",
    line_color="orange",
    annotation_text=f"SLA Target ({TARGET}%)",
    annotation_position="top right"
)

fig.update_layout(
    height=550,
    title="Monthly Compliance Performance",
    yaxis=dict(range=[90, 100], title="Compliance %"),
    xaxis_title="Month",
    template="plotly_white",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------
# INSIGHT BOX
# ---------------------------------------------------
if latest["Compliance %"] >= TARGET:
    insight = "🟢 Compliance is meeting SLA target."
else:
    insight = "🔴 Compliance is below SLA target. Immediate focus required."

st.info(f"""
### 📌 Executive Insight
- Latest Month: **{latest['Month']}**
- Compliance: **{latest['Compliance %']:.2f}%**
- SLA Target: **{TARGET}%**
- Status: {insight}
""")
