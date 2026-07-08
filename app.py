# pip install streamlit
# streamlit run Pedro/app.py *****USAR ESTE PARA CORRER LA APP****


import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Production Dashboard", layout="wide")

st.title("🏭 Production Dashboard")

# ----------------------------
# LOAD DATA
# ----------------------------
file = Path(__file__).parent / "data.csv"
df = pd.read_csv(file)

# ----------------------------
# FILTER DATA
# ----------------------------
mask = (
    df["Line"].str.contains("Units Made", case=False, na=False) &
    ~df["Product"].str.contains(r"Break|changeover|\[", case=False, na=False)
)

df = df.loc[mask].copy()

# ----------------------------
# CLEAN DATA
# ----------------------------
df["Date"] = pd.to_datetime(
    df["Date"],
    dayfirst=True,
    errors="coerce"
)

df["Actual Units"] = pd.to_numeric(
    df["Actual Units"],
    errors="coerce"
)

df["Expected Units"] = pd.to_numeric(
    df["Expected Units"],
    errors="coerce"
)


# Clean Actual Run Rate
df["Actual Run Rate (/min)"] = (
    df["Actual Run Rate (/min)"]
    .astype(str)
    .str.replace(" /min", "", regex=False)
    .str.strip()
)

df["Actual Run Rate (/min)"] = pd.to_numeric(
    df["Actual Run Rate (/min)"],
    errors="coerce"
)


# Clean Estimated Run Rate
df["Est. Run Rate (/min)"] = (
    df["Est. Run Rate (/min)"]
    .astype(str)
    .str.replace(" /min", "", regex=False)
    .str.strip()
)

df["Est. Run Rate (/min)"] = pd.to_numeric(
    df["Est. Run Rate (/min)"],
    errors="coerce"
)


# ----------------------------
# SIDEBAR FILTERS
# ----------------------------
st.sidebar.header("Filters")

min_date = df["Date"].min()
max_date = df["Date"].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date]
)


products = st.sidebar.multiselect(
    "Select Products",
    sorted(df["Product"].dropna().unique()),
    default=sorted(df["Product"].dropna().unique())
)


# ----------------------------
# APPLY FILTERS
# ----------------------------
filtered = df[
    (df["Date"] >= pd.to_datetime(date_range[0])) &
    (df["Date"] <= pd.to_datetime(date_range[1])) &
    (df["Product"].isin(products))
]


# ----------------------------
# GROUP DATA
# ----------------------------
result = filtered.groupby(
    [filtered["Date"].dt.date, "Product"],
    as_index=False
).agg(
    Expected_Units=("Expected Units", "sum"),
    Actual_Units=("Actual Units", "sum"),
    Avg_Est_Run_Rate=("Est. Run Rate (/min)", "mean"),
    Avg_Actual_Run_Rate=("Actual Run Rate (/min)", "mean")
)


# ----------------------------
# CALCULATE KPIs
# ----------------------------

result["Yield %"] = (
    result["Actual_Units"] /
    result["Expected_Units"].replace(0, np.nan)
) * 100


# Round numbers
result["Avg_Actual_Run_Rate"] = (
    result["Avg_Actual_Run_Rate"]
    .round(2)
)

result["Avg_Est_Run_Rate"] = (
    result["Avg_Est_Run_Rate"]
    .round(2)
)

result["Yield %"] = (
    result["Yield %"]
    .round(2)
)


# ----------------------------
# KPIs
# ----------------------------
col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Actual Units",
    f"{int(result['Actual_Units'].sum()):,}"
)

col2.metric(
    "Total Expected Units",
    f"{int(result['Expected_Units'].sum()):,}"
)

col3.metric(
    "Avg Yield %",
    f"{result['Yield %'].mean():.2f}%"
)


# ----------------------------
# TABLE
# ----------------------------
st.subheader("Production Report")

st.dataframe(
    result,
    use_container_width=True
)


# ----------------------------
# DOWNLOAD BUTTON
# ----------------------------
csv = result.to_csv(index=False).encode("utf-8")

st.download_button(
    "📥 Download Report",
    data=csv,
    file_name="production_report.csv",
    mime="text/csv"
)