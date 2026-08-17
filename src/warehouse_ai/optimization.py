from __future__ import annotations

import pandas as pd


def rank_slotting_candidates(orders: pd.DataFrame, products: pd.DataFrame, storage_slots: pd.DataFrame) -> pd.DataFrame:
    """Rank review candidates; this is prioritization, not a claimed optimal relocation."""
    if orders.empty or storage_slots.empty or 'Reference' not in orders or 'reference' not in storage_slots:
        return pd.DataFrame(columns=['reference', 'order_lines', 'current_slot_count', 'priority_rank'])
    demand = orders.groupby('Reference', as_index=False).size().rename(columns={'size': 'order_lines', 'Reference': 'reference'})
    occupancy = storage_slots.groupby('reference', as_index=False).size().rename(columns={'size': 'current_slot_count'})
    result = demand.merge(occupancy, on='reference', how='left').fillna({'current_slot_count': 0})
    if 'Reference' in products.columns:
        result = result.merge(products[['Reference']].rename(columns={'Reference': 'reference'}), on='reference', how='inner')
    result = result.sort_values(['order_lines', 'current_slot_count'], ascending=[False, True]).reset_index(drop=True)
    result['priority_rank'] = result.index + 1
    result['basis'] = 'Observed order-line frequency with current storage-slot count; no travel improvement is estimated.'
    return result