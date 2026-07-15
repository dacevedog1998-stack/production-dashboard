from __future__ import annotations

import pandas as pd
import streamlit as st

from database import (
    get_upload_history,
    save_production_summary,
)
from report_utils import (
    load_uploaded_report,
    prepare_production_summary,
)

st.title("⬆️ Upload Production Reports")

st.caption(
    "Upload CSV or Excel reports here. Saved information will "
    "remain available in the Production Report page."
)

uploaded_files = st.file_uploader(
    "Select production reports",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
    help=(
        "You can upload one or several reports. "
        "Existing dates and products will be updated."
    ),
)

if uploaded_files:
    st.divider()

    for uploaded_file in uploaded_files:
        with st.container(border=True):
            st.subheader(uploaded_file.name)

            try:
                raw_dataframe, file_hash = load_uploaded_report(
                    uploaded_file
                )

                summary = prepare_production_summary(
                    raw_dataframe
                )

                minimum_date = min(
                    summary["production_date"]
                )
                maximum_date = max(
                    summary["production_date"]
                )

                column_1, column_2, column_3 = st.columns(3)

                column_1.metric(
                    "Original Rows",
                    f"{len(raw_dataframe):,}",
                )
                column_2.metric(
                    "Summary Rows",
                    f"{len(summary):,}",
                )
                column_3.metric(
                    "Products",
                    f"{summary['product'].nunique():,}",
                )

                st.write(
                    f"**Date range:** "
                    f"{minimum_date.strftime('%d/%m/%Y')} – "
                    f"{maximum_date.strftime('%d/%m/%Y')}"
                )

                preview = summary.rename(
                    columns={
                        "production_date": "Date",
                        "product": "Product",
                        "expected_units": "Expected Units",
                        "actual_units": "Actual Units",
                        "avg_est_run_rate": "Avg Expected Run Rate",
                        "avg_actual_run_rate": "Avg Actual Run Rate",
                    }
                )

                with st.expander("Preview information"):
                    st.dataframe(
                        preview,
                        use_container_width=True,
                        hide_index=True,
                    )

                save_button = st.button(
                    f"💾 Save {uploaded_file.name}",
                    key=f"save_{file_hash}",
                    type="primary",
                )

                if save_button:
                    result = save_production_summary(
                        summary=summary,
                        report_name=uploaded_file.name,
                        file_hash=file_hash,
                    )

                    if result["duplicate"]:
                        st.warning(
                            "This exact report was already uploaded."
                        )
                    else:
                        st.success(
                            f"{result['processed']:,} date/product "
                            "records were saved or updated."
                        )

            except Exception as error:
                st.error(
                    f"The report could not be processed: {error}"
                )

st.divider()
st.subheader("Upload History")

try:
    upload_history = get_upload_history()
except Exception as error:
    st.error(
        f"Upload history could not be loaded: {error}"
    )
    upload_history = pd.DataFrame()

if upload_history.empty:
    st.info(
        "No production reports have been saved yet."
    )
else:
    upload_history["uploaded_at"] = pd.to_datetime(
        upload_history["uploaded_at"],
        errors="coerce",
    )

    upload_history = upload_history.rename(
        columns={
            "report_name": "Report",
            "summary_rows": "Saved Rows",
            "uploaded_at": "Uploaded At",
        }
    )

    st.dataframe(
        upload_history,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Uploaded At": st.column_config.DatetimeColumn(
                "Uploaded At",
                format="DD/MM/YYYY HH:mm",
            ),
            "Saved Rows": st.column_config.NumberColumn(
                "Saved Rows",
                format="%d",
            ),
        },
    )
