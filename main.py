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
    spreadsheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/1n5XAAZV6yejTTD1yV_wAfLLBsidArbsR4OhlU1SqzMQ/edit?usp=sharing"
    )
    sheet = spreadsheet.worksheet("Summary compliance")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# ---------------------------------------------------
# DATA PROCESSING
# ---------------------------------------------------
df = load_data()
df.columns = df.columns.str.strip()

# Clean Percentages: Strip '%' and convert to numeric
def clean_pct(val):
    return pd.to_numeric(str(val).replace("%", ""), errors="coerce")

df["Compliance %"] = df["Compliance %"].apply(clean_pct)
df["Non Compliance %"] = df["Non Compliance %"].apply(clean_pct)
df["Month_Date"] = pd.to_datetime(df["Month"], errors="coerce")

# Sort chronologically (Jan 2025 -> Jan 2026) for the trend line to make sense
df = df.sort_values("Month_Date", ascending=True)

# ---------------------------------------------------
# DASHBOARD HEADER & KPIs
# ---------------------------------------------------
st.markdown("## 📊 Plug Statements - Performance Trend Analysis")

latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) > 1 else latest
avg_comp = df["Compliance %"].mean()

col1, col2, col3 = st.columns(3)

col1.metric(
    label=f"Current Compliance ({latest['Month']})",
    value=f"{latest['Compliance %']:.2f}%",
    delta=f"{latest['Compliance %'] - previous['Compliance %']:.2f}% vs Last Month"
)

col2.metric(
    label="Average Compliance (YTD)",
    value=f"{avg_comp:.2f}%"
)

col3.metric(
    label="Current Non-Compliance",
    value=f"{latest['Non Compliance %']:.2f}%",
    delta=f"{latest['Non Compliance %'] - previous['Non Compliance %']:.2f}%",
    delta_color="inverse" # Red if non-compliance increases
)

st.markdown("---")

# ---------------------------------------------------
# CHART: GROUPED BARS + COMPLIANCE TREND LINE
# ---------------------------------------------------
fig = go.Figure()

# 1. Trace for Compliance Bars
fig.add_trace(go.Bar(
    x=df["Month"],
    y=df["Compliance %"],
    name='Met Cases (Compliance)',
    marker_color='#2E8B57', # Forest Green
    opacity=0.7,
    text=df["Compliance %"].apply(lambda x: f"{x:.1f}%"),
    textposition='inside'
))

# 2. Trace for Non-Compliance Bars
fig.add_trace(go.Bar(
    x=df["Month"],
    y=df["Non Compliance %"],
    name='Non-Compliance',
    marker_color='#D62728', # Red
    text=df["Non Compliance %"].apply(lambda x: f"{x:.1f}%"),
    textposition='outside'
))

# 3. Trace for Trend Line (Met Cases)
fig.add_trace(go.Scatter(
    x=df["Month"],
    y=df["Compliance %"],
    name='Compliance Trend',
    mode='lines+markers',
    line=dict(color='#1B4D3E', width=4, shape='spline'), # Darker green, smooth curve
    marker=dict(size=8, symbol='diamond')
))

# Styling the layout
fig.update_layout(
    barmode='group',
    height=600,
    title="Monthly Compliance Growth & Error Rates",
    xaxis_title="Reporting Month",
    yaxis_title="Percentage (%)",
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    # Range set to show bars clearly; zoomed in slightly on the top
    yaxis=dict(range=[0, 110]) 
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# RAW DATA SUMMARY
# ---------------------------------------------------
st.markdown("### 📋 Data Summary")
st.dataframe(df[["Month", "Compliance %", "Non Compliance %"]].set_index("Month"), use_container_width=True)
