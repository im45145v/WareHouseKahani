from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from warehouse_ai.storage_model import parse_storage_strategy_table


def compare_storage_strategies(strategy_tables: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """Summarize the actual storage strategies represented in the dataset.

    This is intentionally limited to real warehouse data and derived operational summaries.
    """
    summary: Dict[str, Dict[str, Any]] = {}
    for strategy_name, table in strategy_tables.items():
        if table is None or table.empty:
            summary[strategy_name] = {'strategy_name': strategy_name, 'unique_skus': 0, 'total_slots': 0, 'avg_quantity': 0.0}
            continue
        parsed = parse_storage_strategy_table(table, strategy_name=strategy_name)
        unique_skus = parsed['reference'].nunique() if not parsed.empty else 0
        total_slots = len(parsed)
        avg_quantity = float(parsed['quantity'].mean()) if not parsed.empty else 0.0
        summary[strategy_name] = {
            'strategy_name': strategy_name,
            'unique_skus': int(unique_skus),
            'total_slots': int(total_slots),
            'avg_quantity': avg_quantity,
        }
    return summary
