from __future__ import annotations

import os
from typing import Any

import pandas as pd
import psycopg
import streamlit as st
from psycopg.rows import dict_row


def get_database_url() -> str:
    database_url = None

    try:
        database_url = st.secrets.get("DATABASE_URL")
    except Exception:
        database_url = None

    database_url = database_url or os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Add your Supabase PostgreSQL "
            "connection string to Streamlit Secrets."
        )

    database_url = str(database_url).strip()

    if database_url.startswith("postgres://"):
        database_url = (
            "postgresql://"
            + database_url[len("postgres://"):]
        )

    return database_url


def get_connection() -> psycopg.Connection:
    return psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
        connect_timeout=15,
    )


def init_database() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS production_summary (
                    id BIGSERIAL PRIMARY KEY,
                    production_date DATE NOT NULL,
                    product TEXT NOT NULL,
                    expected_units DOUBLE PRECISION,
                    actual_units DOUBLE PRECISION,
                    avg_est_run_rate DOUBLE PRECISION,
                    avg_actual_run_rate DOUBLE PRECISION,
                    source_report TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT production_summary_date_product_unique
                    UNIQUE (production_date, product)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS production_report_uploads (
                    id BIGSERIAL PRIMARY KEY,
                    file_hash TEXT NOT NULL UNIQUE,
                    report_name TEXT NOT NULL,
                    summary_rows INTEGER NOT NULL DEFAULT 0,
                    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS production_summary_date_index
                ON production_summary (production_date)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS production_summary_product_index
                ON production_summary (product)
                """
            )


def database_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def save_production_summary(
    summary: pd.DataFrame,
    report_name: str,
    file_hash: str,
) -> dict[str, Any]:
    if summary.empty:
        return {
            "duplicate": False,
            "processed": 0,
        }

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM production_report_uploads
                WHERE file_hash = %s
                """,
                (file_hash,),
            )

            existing_upload = cursor.fetchone()

            if existing_upload:
                return {
                    "duplicate": True,
                    "processed": 0,
                }

            processed_rows = 0

            for row in summary.itertuples(index=False):
                cursor.execute(
                    """
                    INSERT INTO production_summary (
                        production_date,
                        product,
                        expected_units,
                        actual_units,
                        avg_est_run_rate,
                        avg_actual_run_rate,
                        source_report,
                        updated_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (production_date, product)
                    DO UPDATE SET
                        expected_units = EXCLUDED.expected_units,
                        actual_units = EXCLUDED.actual_units,
                        avg_est_run_rate = EXCLUDED.avg_est_run_rate,
                        avg_actual_run_rate = EXCLUDED.avg_actual_run_rate,
                        source_report = EXCLUDED.source_report,
                        updated_at = NOW()
                    """,
                    (
                        row.production_date,
                        str(row.product),
                        database_number(row.expected_units),
                        database_number(row.actual_units),
                        database_number(row.avg_est_run_rate),
                        database_number(row.avg_actual_run_rate),
                        report_name,
                    ),
                )

                processed_rows += 1

            cursor.execute(
                """
                INSERT INTO production_report_uploads (
                    file_hash,
                    report_name,
                    summary_rows
                )
                VALUES (%s, %s, %s)
                """,
                (
                    file_hash,
                    report_name,
                    processed_rows,
                ),
            )

    return {
        "duplicate": False,
        "processed": processed_rows,
    }


def get_production_summary() -> pd.DataFrame:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    production_date,
                    product,
                    expected_units,
                    actual_units,
                    avg_est_run_rate,
                    avg_actual_run_rate,
                    source_report,
                    updated_at
                FROM production_summary
                ORDER BY
                    production_date DESC,
                    product ASC
                """
            )
            rows = cursor.fetchall()

    return pd.DataFrame(rows)


def get_upload_history() -> pd.DataFrame:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    report_name,
                    summary_rows,
                    uploaded_at
                FROM production_report_uploads
                ORDER BY uploaded_at DESC
                """
            )
            rows = cursor.fetchall()

    return pd.DataFrame(rows)
