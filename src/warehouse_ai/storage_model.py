from __future__ import annotations

from typing import Any

import pandas as pd


def parse_storage_strategy_table(df: pd.DataFrame, strategy_name: str = 'unknown') -> pd.DataFrame:
    """Flatten the warehouse storage tables into a normalized product-slot dataset.

    The raw storage CSVs encode each storage position as 18 columns containing strings like
    'SKU123;7.0'. We normalize each into rows of (location, slot_index, reference, quantity).
    """
    if df.empty:
        return pd.DataFrame(columns=['location', 'reference', 'quantity', 'slot_index', 'strategy_name'])

    rows = []
    for _, row in df.iterrows():
        loc = row.get('Location')
        if pd.isna(loc):
            loc = row.get('originalLocation')
        for slot_index in range(1, 19):
            cell = row.get(str(slot_index), row.get(f'col_{slot_index}'))
            if pd.isna(cell) or cell is None:
                continue
            value = str(cell).strip()
            if not value or value.lower() == 'nan':
                continue
            if ';' not in value:
                continue
            reference, quantity = value.split(';', 1)
            try:
                qty_value = float(quantity)
            except ValueError:
                continue
            rows.append(
                {
                    'location': loc,
                    'reference': reference.strip(),
                    'quantity': qty_value,
                    'slot_index': slot_index,
                    'strategy_name': strategy_name,
                }
            )

    return pd.DataFrame(rows)
