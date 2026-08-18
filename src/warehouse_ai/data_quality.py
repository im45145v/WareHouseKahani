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


def build_operational_readiness(dataset: Dict[str, pd.DataFrame], schemas: Dict[str, list[str]] | None = None) -> Dict[str, Any]:
    """Summarize whether the loaded data is fit for operational review."""
    schemas = schemas or {}
    issues: list[str] = []
    blockers: list[str] = []

    for name, frame in dataset.items():
        result = validate_table(frame, schemas.get(name))
        if result['missing_columns']:
            blockers.append(f"{name}: missing required columns ({', '.join(result['missing_columns'])})")
        elif result['null_counts'] or result['duplicate_rows']:
            issues.append(f'{name}: contains nulls or duplicate rows; review before operational use')

    for name, column in [('Customer_Order', 'quantity (units)'), ('Picking_Wave', 'quantityToPick (units)')]:
        frame = dataset.get(name, pd.DataFrame())
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors='coerce')
            negative_count = int((values < 0).sum())
            if negative_count:
                issues.append(f'{name}: {negative_count:,} negative quantity value(s)')

    waves = dataset.get('Picking_Wave', pd.DataFrame())
    locations = dataset.get('Storage_Location', pd.DataFrame())
    if 'locations' in waves.columns and 'originalLocation' in locations.columns:
        known = set(locations['originalLocation'].astype(str).str.strip())
        unmatched = int((~waves['locations'].astype(str).str.strip().isin(known)).sum())
        if unmatched:
            issues.append(f'Picking_Wave: {unmatched:,} location records are staging/corridor points or unmatched bins')

    status = 'BLOCKED' if blockers else 'REVIEW' if issues else 'READY'
    return {
        'status': status,
        'blockers': blockers,
        'issues': issues,
        'basis': 'Schema, null/duplicate, quantity-sign, and cross-table location checks; no records are deleted.',
    }
