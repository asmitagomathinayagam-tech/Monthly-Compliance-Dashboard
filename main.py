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
    # Spreadsheet URL
    spreadsheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1n5XAAZV6yejTTD1yV_wAfLLBsidArbsR4OhlU1SqzMQ/edit?usp=sharing"
    )
    # Target Worksheet
    sheet = spreadsheet.worksheet("Summary compliance")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# ---------------------------------------------------
# DATA PROCESSING
# ---------------------------------------------------
df_raw = load_data()
df = df_raw.copy()
df.columns = df.columns.str.strip()

# Check for required columns
required_cols = ["Month", "Compliance %", "Non Compliance %"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Column '{col}' not found. Please check your Google Sheet headers.")
        st.stop()

# Clean Percentages: Remove '%' and convert to float
def clean_pct(val):
    return pd.to_numeric(str(val).replace("%", ""), errors="coerce")

df["Compliance %"] = df["Compliance %"].apply(clean_pct)
df["Non Compliance %"] = df["Non Compliance %"].apply(clean_pct)
df["Month_Date"] = pd.to_datetime(df["Month"], errors="coerce")

# Sort by Date (Oldest to Newest for Charting)
df = df.sort_values("Month_Date", ascending=True)

# ---------------------------------------------------
# DASHBOARD HEADER & KPIs
# ---------------------------------------------------
st.markdown("## 📊 Plug Statements - Monthly Compliance Overview")

# Get latest and previous for KPI calculation
latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) > 1 else latest
delta = latest["Compliance %"] - previous["Compliance %"]

col1, col2, col3 = st.columns(3)

col1.metric(
    label=f"Latest Compliance ({latest['Month']})",
    value=f"{latest['Compliance %']:.2f}%",
    delta=f"{delta:.2f}% vs Prev Month"
)

col2.metric(
    label="Average Compliance (YTD)",
    value=f"{df['Compliance %'].mean():.2f}%"
)

# Define SLA Target
TARGET = 97.0 

col3.metric(label="SLA Target", value=f"{TARGET}%")

st.markdown("---")

# ---------------------------------------------------
# STACKED BAR CHART WITH SLA LOGIC
# ---------------------------------------------------
# If Compliance < Target, Non-Compliance bar turns RED (#D62728). Otherwise GREY (#D3D3D3).
non_comp_colors = [
    "#D62728" if row["Compliance %"] < TARGET else "#D3D3D3" 
    for _, row in df.iterrows()
]

fig = go.Figure()

# Trace 1: Compliance (Always Green)
fig.add_trace(go.Bar(
    name='Compliance',
    x=df["Month"],
    y=df["Compliance %"],
    marker_color='#2E8B57',
    text=df["Compliance %"].apply(lambda x: f"{x:.1f}%"),
    textposition="inside",
    hovertemplate="Month: %{x}<br>Compliance: %{y}%<extra></extra>"
))

# Trace 2: Non-Compliance (Conditional Color)
fig.add_trace(go.Bar(
    name='Non Compliance',
    x=df["Month"],
    y=df["Non Compliance %"],
    marker_color=non_comp_colors,
    text=df["Non Compliance %"].apply(lambda x: f"{x:.1f}%"),
    textposition="inside",
    hovertemplate="Month: %{x}<br>Non-Compliance: %{y}%<extra></extra>"
))

# Add the SLA Threshold Line
fig.add_hline(
    y=TARGET, 
    line_dash="dash", 
    line_color="black",
    line_width=2,
    annotation_text=f"SLA Target {TARGET}%", 
    annotation_position="top left"
)

fig.update_layout(
    barmode='stack',
    height=550,
    yaxis=dict(title="Percentage (%)", range=[0, 105]),
    xaxis_title="Reporting Month",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=80, b=40)
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# EXECUTIVE INSIGHTS
# ---------------------------------------------------
st.markdown("---")
if latest["Compliance %"] >= TARGET:
    st.success(f"### ✅ Meeting SLA Target\nCompliance is currently **{latest['Compliance %']:.2f}%**.")
else:
    st.error(f"### ⚠️ Below SLA Target\nAttention Required: **{latest['Month']}** performance is **{latest['Compliance %']:.2f}%**.")

# Optional: List specifically which months failed the SLA
failed_months = df[df["Compliance %"] < TARGET]["Month"].tolist()
if failed_months:
    with st.expander("View Months Below Target"):
        st.write(f"The following months did not meet the {TARGET}% target: {', '.join(failed_months)}")
