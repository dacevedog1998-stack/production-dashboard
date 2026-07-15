from __future__ import annotations

import hashlib
import io
from typing import BinaryIO

import pandas as pd


REQUIRED_COLUMNS = [
    "Date",
    "Line",
    "Product",
    "Actual Units",
    "Expected Units",
    "Actual Run Rate (/min)",
    "Est. Run Rate (/min)",
]


def load_uploaded_report(
    uploaded_file: BinaryIO,
) -> tuple[pd.DataFrame, str]:
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    file_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    if file_name.endswith(".csv"):
        last_error = None

        for encoding in [
            "utf-8-sig",
            "utf-8",
            "latin-1",
        ]:
            try:
                dataframe = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                )

                if len(dataframe.columns) == 1:
                    dataframe = pd.read_csv(
                        io.BytesIO(file_bytes),
                        encoding=encoding,
                        sep=None,
                        engine="python",
                    )

                return dataframe, file_hash

            except UnicodeDecodeError as error:
                last_error = error

        raise ValueError(
            "The CSV encoding could not be recognised."
        ) from last_error

    if file_name.endswith(".xlsx"):
        dataframe = pd.read_excel(
            io.BytesIO(file_bytes),
            engine="openpyxl",
        )
        return dataframe, file_hash

    raise ValueError(
        "Unsupported file type. Upload a CSV or XLSX file."
    )


def clean_numeric_column(
    dataframe: pd.DataFrame,
    column_name: str,
) -> None:
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


def prepare_production_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    dataframe = dataframe.copy()

    dataframe.columns = (
        dataframe.columns
        .astype(str)
        .str.strip()
    )

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing columns: "
            + ", ".join(missing_columns)
        )

    dataframe["Line"] = (
        dataframe["Line"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["Product"] = (
        dataframe["Product"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    production_mask = (
        dataframe["Line"].str.contains(
            "Units Made",
            case=False,
            na=False,
        )
        &
        ~dataframe["Product"].str.contains(
            r"Break|changeover|\[|cleaning",
            case=False,
            regex=True,
            na=False,
        )
    )

    dataframe = dataframe.loc[
        production_mask
    ].copy()

    if dataframe.empty:
        raise ValueError(
            "No production records were found after filtering."
        )

    dataframe["Date"] = pd.to_datetime(
        dataframe["Date"],
        dayfirst=True,
        errors="coerce",
    )

    clean_numeric_column(
        dataframe,
        "Actual Units",
    )
    clean_numeric_column(
        dataframe,
        "Expected Units",
    )
    clean_numeric_column(
        dataframe,
        "Actual Run Rate (/min)",
    )
    clean_numeric_column(
        dataframe,
        "Est. Run Rate (/min)",
    )

    dataframe = dataframe.dropna(
        subset=["Date"]
    )

    dataframe = dataframe[
        dataframe["Product"] != ""
    ].copy()

    if dataframe.empty:
        raise ValueError(
            "No valid records remained after cleaning."
        )

    summary = (
        dataframe
        .groupby(
            [
                dataframe["Date"].dt.date,
                "Product",
            ],
            as_index=False,
        )
        .agg(
            expected_units=(
                "Expected Units",
                "sum",
            ),
            actual_units=(
                "Actual Units",
                "sum",
            ),
            avg_est_run_rate=(
                "Est. Run Rate (/min)",
                "mean",
            ),
            avg_actual_run_rate=(
                "Actual Run Rate (/min)",
                "mean",
            ),
        )
    )

    summary = summary.rename(
        columns={
            "Date": "production_date",
            "Product": "product",
        }
    )

    summary["expected_units"] = (
        summary["expected_units"]
        .round(0)
    )
    summary["actual_units"] = (
        summary["actual_units"]
        .round(0)
    )
    summary["avg_est_run_rate"] = (
        summary["avg_est_run_rate"]
        .round(2)
    )
    summary["avg_actual_run_rate"] = (
        summary["avg_actual_run_rate"]
        .round(2)
    )

    return summary
