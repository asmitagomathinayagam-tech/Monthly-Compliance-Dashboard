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

# Clean Percentages
def clean_pct(val):
    return pd.to_numeric(str(val).replace("%", ""), errors="coerce")

df["Compliance %"] = df["Compliance %"].apply(clean_pct)
df["Non Compliance %"] = df["Non Compliance %"].apply(clean_pct)
df["Month_Date"] = pd.to_datetime(df["Month"], errors="coerce")

# Sort Newest to Oldest (Jan 2026 -> Jan 2025)
df = df.sort_values("Month_Date", ascending=False)

# ---------------------------------------------------
# DASHBOARD HEADER & KPIs
# ---------------------------------------------------
st.markdown("## 📊 Plug Statements - Performance Trend Analysis")

latest = df.iloc[0]
previous = df.iloc[1] if len(df) > 1 else latest

col1, col2, col3 = st.columns(3)

col1.metric(
    label=f"Latest Compliance ({latest['Month']})",
    value=f"{latest['Compliance %']:.2f}%",
    delta=f"{latest['Compliance %'] - previous['Compliance %']:.2f}% vs Prev Month"
)

col2.metric(
    label="Average Compliance",
    value=f"{df['Compliance %'].mean():.2f}%"
)

col3.metric(
    label="Latest Non-Compliance",
    value=f"{latest['Non Compliance %']:.2f}%",
    delta=f"{latest['Non Compliance %'] - previous['Non Compliance %']:.2f}%",
    delta_color="inverse"
)

st.markdown("---")

# ---------------------------------------------------
# CHART: REVERSED GROUPED BARS + CONTRAST TREND
# ---------------------------------------------------
# Define the colors
COMPLIANCE_COLOR = "#006400"  # Dark Green
TREND_COLOR = "#FF8C00"       # Dark Orange
NON_COMP_COLOR = "#D62728"    # Red

fig = go.Figure()

# 1. Compliance Bars (Dark Green)
fig.add_trace(go.Bar(
    x=df["Month"],
    y=df["Compliance %"],
    name='Met Cases (Compliance)',
    marker_color=COMPLIANCE_COLOR,
    opacity=0.8,
    text=df["Compliance %"].apply(lambda x: f"{x:.1f}%"),
    textposition='inside'
))

# 2. Non-Compliance Bars (Red)
fig.add_trace(go.Bar(
    x=df["Month"],
    y=df["Non Compliance %"],
    name='Non-Compliance',
    marker_color=NON_COMP_COLOR,
    text=df["Non Compliance %"].apply(lambda x: f"{x:.1f}%"),
    textposition='outside'
))

# 3. Trend Line (Orange - High Definition)
fig.add_trace(go.Scatter(
    x=df["Month"],
    y=df["Compliance %"],
    name='Compliance Trend',
    mode='lines+markers',
    line=dict(color=TREND_COLOR, width=4, shape='spline'),
    marker=dict(size=10, symbol='circle', color='white', 
                line=dict(color=TREND_COLOR, width=2))
))

# Layout Styling
fig.update_layout(
    barmode='group',
    height=600,
    xaxis_title="Month (Jan 2026 → Jan 2025)",
    yaxis_title="Percentage (%)",
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(range=[0, 110])
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# DATA TABLE
# ---------------------------------------------------
with st.expander("View Data Records"):
    st.dataframe(df[["Month", "Compliance %", "Non Compliance %"]], use_container_width=True)
