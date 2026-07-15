from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from database import get_production_summary

st.title("🏭 Production Dashboard")

st.caption(
    "Historical production information saved in the database."
)

try:
    production_data = get_production_summary()
except Exception as error:
    st.error(
        f"Production information could not be loaded: {error}"
    )
    st.stop()

if production_data.empty:
    st.info(
        "There is no saved production information yet. "
        "Open the Upload Reports page to upload the first report."
    )
    st.stop()

production_data["production_date"] = pd.to_datetime(
    production_data["production_date"],
    errors="coerce",
)

numeric_columns = [
    "expected_units",
    "actual_units",
    "avg_est_run_rate",
    "avg_actual_run_rate",
]

for column in numeric_columns:
    production_data[column] = pd.to_numeric(
        production_data[column],
        errors="coerce",
    )

production_data = production_data.dropna(
    subset=["production_date"]
)

st.sidebar.header("Report Filters")

minimum_date = (
    production_data["production_date"]
    .min()
    .date()
)
maximum_date = (
    production_data["production_date"]
    .max()
    .date()
)

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(
        minimum_date,
        maximum_date,
    ),
    min_value=minimum_date,
    max_value=maximum_date,
)

available_products = sorted(
    production_data["product"]
    .dropna()
    .unique()
    .tolist()
)

selected_products = st.sidebar.multiselect(
    "Select Products",
    options=available_products,
    default=available_products,
)

if len(date_range) == 2:
    start_date = pd.Timestamp(
        date_range[0]
    )
    end_date = pd.Timestamp(
        date_range[1]
    )
else:
    start_date = pd.Timestamp(
        date_range[0]
    )
    end_date = pd.Timestamp(
        date_range[0]
    )

if not selected_products:
    st.warning(
        "Select at least one product."
    )
    st.stop()

filtered = production_data[
    (
        production_data["production_date"]
        >= start_date
    )
    &
    (
        production_data["production_date"]
        <= end_date
    )
    &
    (
        production_data["product"]
        .isin(selected_products)
    )
].copy()

if filtered.empty:
    st.warning(
        "No production information matches the filters."
    )
    st.stop()

filtered["yield_percentage"] = (
    filtered["actual_units"]
    /
    filtered["expected_units"].replace(
        0,
        np.nan,
    )
) * 100

total_expected_units = (
    filtered["expected_units"]
    .fillna(0)
    .sum()
)
total_actual_units = (
    filtered["actual_units"]
    .fillna(0)
    .sum()
)

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

average_expected_rate = (
    filtered["avg_est_run_rate"]
    .mean()
)
average_actual_rate = (
    filtered["avg_actual_run_rate"]
    .mean()
)

st.subheader("Production Summary")

column_1, column_2, column_3, column_4 = st.columns(4)

column_1.metric(
    "Expected Units",
    f"{total_expected_units:,.0f}",
)
column_2.metric(
    "Actual Units",
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

rate_column_1, rate_column_2 = st.columns(2)

rate_column_1.metric(
    "Avg Expected Run Rate",
    (
        f"{average_expected_rate:.2f} /min"
        if pd.notna(average_expected_rate)
        else "N/A"
    ),
)
rate_column_2.metric(
    "Avg Actual Run Rate",
    (
        f"{average_actual_rate:.2f} /min"
        if pd.notna(average_actual_rate)
        else "N/A"
    ),
)

st.subheader("Production Report")

display_report = filtered[
    [
        "production_date",
        "product",
        "expected_units",
        "actual_units",
        "avg_est_run_rate",
        "avg_actual_run_rate",
        "yield_percentage",
        "source_report",
        "updated_at",
    ]
].copy()

display_report = display_report.sort_values(
    [
        "production_date",
        "product",
    ],
    ascending=[
        False,
        True,
    ],
)

display_report = display_report.rename(
    columns={
        "production_date": "Date",
        "product": "Product",
        "expected_units": "Expected Units",
        "actual_units": "Actual Units",
        "avg_est_run_rate": "Avg Expected Run Rate",
        "avg_actual_run_rate": "Avg Actual Run Rate",
        "yield_percentage": "Yield %",
        "source_report": "Source Report",
        "updated_at": "Last Updated",
    }
)

st.dataframe(
    display_report,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Date": st.column_config.DateColumn(
            "Date",
            format="DD/MM/YYYY",
        ),
        "Expected Units": st.column_config.NumberColumn(
            "Expected Units",
            format="%.0f",
        ),
        "Actual Units": st.column_config.NumberColumn(
            "Actual Units",
            format="%.0f",
        ),
        "Avg Expected Run Rate": st.column_config.NumberColumn(
            "Avg Expected Run Rate",
            format="%.2f",
        ),
        "Avg Actual Run Rate": st.column_config.NumberColumn(
            "Avg Actual Run Rate",
            format="%.2f",
        ),
        "Yield %": st.column_config.NumberColumn(
            "Yield %",
            format="%.2f%%",
        ),
        "Last Updated": st.column_config.DatetimeColumn(
            "Last Updated",
            format="DD/MM/YYYY HH:mm",
        ),
    },
)

download_report = display_report.copy()

download_report["Date"] = pd.to_datetime(
    download_report["Date"]
).dt.strftime("%d/%m/%Y")

csv_report = download_report.to_csv(
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
