from __future__ import annotations

from typing import Dict, Any

import pandas as pd


def summarize_missing_values(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Return column-level missing value stats for the warehouse tables."""
    summary = {}
    for column in df.columns:
        s = df[column]
        missing = int(s.isna().sum())
        summary[column] = {
            'missing_count': missing,
            'missing_percent': float((missing / len(df)) * 100) if len(df) else 0.0,
            'dtype': str(s.dtype),
        }
    return summary


def validate_table(df: pd.DataFrame, required_columns: list[str] | None = None) -> Dict[str, Any]:
    """Return deterministic quality findings without dropping source records."""
    required = required_columns or []
    missing_columns = [column for column in required if column not in df.columns]
    null_counts = {column: int(value) for column, value in df.isna().sum().items() if value}
    duplicate_rows = int(df.duplicated().sum())
    invalid_numeric = {
        column: int((pd.to_numeric(df[column], errors='coerce').isna() & df[column].notna()).sum())
        for column in df.columns
        if df[column].dtype == object
    }
    invalid_numeric = {column: value for column, value in invalid_numeric.items() if value}
    return {
        'rows': int(len(df)),
        'columns': int(len(df.columns)),
        'missing_columns': missing_columns,
        'null_counts': null_counts,
        'duplicate_rows': duplicate_rows,
        'invalid_numeric_values': invalid_numeric,
        'status': 'FAIL' if missing_columns else 'WARN' if null_counts or duplicate_rows else 'PASS',
    }


def build_data_quality_report(dataset: Dict[str, pd.DataFrame], schemas: Dict[str, list[str]] | None = None) -> pd.DataFrame:
    """Build a table suitable for dashboard display and audit documentation."""
    schemas = schemas or {}
    records = []
    for name, frame in dataset.items():
        result = validate_table(frame, schemas.get(name))
        records.append({'dataset': name, **result})
    return pd.DataFrame(records)
