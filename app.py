# Install requirements:
# pip install streamlit pandas numpy openpyxl pillow
#
# Run the app:
# streamlit run Pedro/app.py

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image


# ============================================================
# APP FILES
# ============================================================
APP_FOLDER = Path(__file__).parent
FAVICON_FILE = APP_FOLDER / "favicon.png"


# Use favicon.png if it exists.
# Otherwise, use the factory emoji.
if FAVICON_FILE.exists():
    favicon = Image.open(FAVICON_FILE)
else:
    favicon = "🏭"


# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Production Dashboard",
    page_icon=favicon,
    layout="wide",
)


# ============================================================
# PAGE HEADER
# ============================================================
st.title("🏭 Production Dashboard")

st.caption(
    "Upload the latest production report to review production performance."
)


# ============================================================
# FUNCTIONS
# ============================================================
def load_uploaded_report(uploaded_file) -> pd.DataFrame:
    """
    Load a CSV or Excel report uploaded through the Streamlit interface.
    """

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        file_bytes = uploaded_file.getvalue()

        # Try common CSV encodings.
        for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                return pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                )
            except UnicodeDecodeError:
                continue

        raise ValueError(
            "The CSV encoding could not be recognised."
        )

    if file_name.endswith(".xlsx"):
        return pd.read_excel(
            uploaded_file,
            engine="openpyxl",
        )

    raise ValueError(
        "Unsupported file type. Upload a CSV or XLSX file."
    )


def clean_numeric_column(
    dataframe: pd.DataFrame,
    column_name: str,
) -> None:
    """
    Convert a report column into numeric values.
    """

    dataframe[column_name] = (
        dataframe[column_name]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" /min", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )

    dataframe[column_name] = pd.to_numeric(
        dataframe[column_name],
        errors="coerce",
    )


# ============================================================
# REPORT UPLOAD
# ============================================================
st.sidebar.header("Report")

uploaded_report = st.sidebar.file_uploader(
    "Upload Production Report",
    type=["csv", "xlsx"],
    accept_multiple_files=False,
    help="Upload the latest Pedro production report.",
)


if uploaded_report is None:
    st.info(
        "⬅️ Upload a CSV or Excel production report from the sidebar "
        "to open the dashboard."
    )

    st.stop()


# ============================================================
# LOAD DATA
# ============================================================
try:
    df = load_uploaded_report(uploaded_report)

except Exception as error:
    st.error(
        f"The report could not be opened: {error}"
    )
    st.stop()


# Clean spaces from column names.
df.columns = (
    df.columns
    .astype(str)
    .str.strip()
)


st.sidebar.success(
    f"Loaded: {uploaded_report.name}"
)

st.sidebar.caption(
    f"Original report rows: {len(df):,}"
)


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================
required_columns = [
    "Date",
    "Line",
    "Product",
    "Actual Units",
    "Expected Units",
    "Actual Run Rate (/min)",
    "Est. Run Rate (/min)",
]


missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_columns:
    st.error(
        "The uploaded report is missing the following columns:"
    )

    for column in missing_columns:
        st.write(f"- {column}")

    with st.expander(
        "Columns detected in the uploaded report"
    ):
        st.write(list(df.columns))

    st.stop()


# ============================================================
# FILTER PRODUCTION RECORDS
# ============================================================
df["Line"] = (
    df["Line"]
    .fillna("")
    .astype(str)
    .str.strip()
)

df["Product"] = (
    df["Product"]
    .fillna("")
    .astype(str)
    .str.strip()
)


production_mask = (
    df["Line"].str.contains(
        "Units Made",
        case=False,
        na=False,
    )
    &
    ~df["Product"].str.contains(
        r"Break|changeover|\[|cleaning",
        case=False,
        regex=True,
        na=False,
    )
)


df = df.loc[production_mask].copy()


if df.empty:
    st.warning(
        "No production records were found after filtering the report."
    )
    st.stop()


# ============================================================
# CLEAN DATA
# ============================================================
df["Date"] = pd.to_datetime(
    df["Date"],
    dayfirst=True,
    errors="coerce",
)


clean_numeric_column(
    df,
    "Actual Units",
)

clean_numeric_column(
    df,
    "Expected Units",
)

clean_numeric_column(
    df,
    "Actual Run Rate (/min)",
)

clean_numeric_column(
    df,
    "Est. Run Rate (/min)",
)


# Remove rows without a valid date.
df = df.dropna(
    subset=["Date"]
)


# Remove rows without a product name.
df = df[
    df["Product"] != ""
].copy()


if df.empty:
    st.warning(
        "No valid production records remained after cleaning the report."
    )
    st.stop()


# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.divider()
st.sidebar.header("Filters")


minimum_date = df["Date"].min().date()
maximum_date = df["Date"].max().date()


date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)


available_products = sorted(
    df["Product"]
    .dropna()
    .unique()
    .tolist()
)


selected_products = st.sidebar.multiselect(
    "Select Products",
    options=available_products,
    default=available_products,
)


# ============================================================
# VALIDATE FILTERS
# ============================================================
if len(date_range) == 2:
    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1])

else:
    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[0])


if not selected_products:
    st.warning(
        "Select at least one product from the sidebar."
    )
    st.stop()


# ============================================================
# APPLY FILTERS
# ============================================================
filtered = df[
    (df["Date"] >= start_date)
    & (df["Date"] <= end_date)
    & (df["Product"].isin(selected_products))
].copy()


if filtered.empty:
    st.warning(
        "No production records match the selected filters."
    )
    st.stop()


# ============================================================
# GROUP DATA
# ============================================================
result = (
    filtered
    .groupby(
        [
            filtered["Date"].dt.date,
            "Product",
        ],
        as_index=False,
    )
    .agg(
        Expected_Units=(
            "Expected Units",
            "sum",
        ),
        Actual_Units=(
            "Actual Units",
            "sum",
        ),
        Avg_Est_Run_Rate=(
            "Est. Run Rate (/min)",
            "mean",
        ),
        Avg_Actual_Run_Rate=(
            "Actual Run Rate (/min)",
            "mean",
        ),
    )
)


# ============================================================
# CALCULATE KPIs
# ============================================================
result["Yield %"] = (
    result["Actual_Units"]
    / result["Expected_Units"].replace(0, np.nan)
) * 100


result["Expected_Units"] = (
    result["Expected_Units"]
    .fillna(0)
    .round(0)
    .astype(int)
)

result["Actual_Units"] = (
    result["Actual_Units"]
    .fillna(0)
    .round(0)
    .astype(int)
)

result["Avg_Est_Run_Rate"] = (
    result["Avg_Est_Run_Rate"]
    .round(2)
)

result["Avg_Actual_Run_Rate"] = (
    result["Avg_Actual_Run_Rate"]
    .round(2)
)

result["Yield %"] = (
    result["Yield %"]
    .round(2)
)


total_expected_units = result["Expected_Units"].sum()
total_actual_units = result["Actual_Units"].sum()


if total_expected_units > 0:
    overall_yield = (
        total_actual_units
        / total_expected_units
    ) * 100

else:
    overall_yield = 0.0


unit_variance = (
    total_actual_units
    - total_expected_units
)


# ============================================================
# SUMMARY KPIs
# ============================================================
st.subheader("Production Summary")


column_1, column_2, column_3, column_4 = st.columns(4)


column_1.metric(
    "Total Expected Units",
    f"{total_expected_units:,.0f}",
)

column_2.metric(
    "Total Actual Units",
    f"{total_actual_units:,.0f}",
)

column_3.metric(
    "Unit Variance",
    f"{unit_variance:+,.0f}",
)

column_4.metric(
    "Overall Yield",
    f"{overall_yield:.2f}%",
)


# ============================================================
# PRODUCTION REPORT TABLE
# ============================================================
st.subheader("Production Report")


display_result = result.rename(
    columns={
        "Expected_Units": "Expected Units",
        "Actual_Units": "Actual Units",
        "Avg_Est_Run_Rate": "Avg Expected Run Rate",
        "Avg_Actual_Run_Rate": "Avg Actual Run Rate",
    }
)


st.dataframe(
    display_result,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Date": st.column_config.DateColumn(
            "Date",
            format="DD/MM/YYYY",
        ),
        "Expected Units": st.column_config.NumberColumn(
            "Expected Units",
            format="%d",
        ),
        "Actual Units": st.column_config.NumberColumn(
            "Actual Units",
            format="%d",
        ),
        "Avg Expected Run Rate": (
            st.column_config.NumberColumn(
                "Avg Expected Run Rate",
                format="%.2f",
            )
        ),
        "Avg Actual Run Rate": (
            st.column_config.NumberColumn(
                "Avg Actual Run Rate",
                format="%.2f",
            )
        ),
        "Yield %": st.column_config.NumberColumn(
            "Yield %",
            format="%.2f%%",
        ),
    },
)


# ============================================================
# DOWNLOAD REPORT
# ============================================================
csv_report = display_result.to_csv(
    index=False,
).encode("utf-8-sig")


st.download_button(
    label="📥 Download Filtered Report",
    data=csv_report,
    file_name=(
        f"production_report_"
        f"{start_date.strftime('%Y%m%d')}_"
        f"{end_date.strftime('%Y%m%d')}.csv"
    ),
    mime="text/csv",
)


# ============================================================
# CLEANED SOURCE DATA
# ============================================================
with st.expander(
    "View cleaned source data"
):
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
    )
