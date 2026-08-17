from __future__ import annotations

from typing import Any, Callable, Dict

import pandas as pd

from warehouse_ai.analytics import compute_abc_from_orders, compute_order_kpis, compute_picking_kpis
from warehouse_ai.data_quality import build_data_quality_report
from warehouse_ai.decision_engine import build_decision_snapshot
from warehouse_ai.operations import analyze_wave_routes, identify_bottleneck_locations


def build_tool_registry(dataset: Dict[str, pd.DataFrame]) -> Dict[str, Callable[[], Any]]:
    """Expose deterministic analytical tools; no raw dataset is sent to a language model."""
    orders, waves, products = dataset['Customer_Order'], dataset['Picking_Wave'], dataset['Product']
    snapshot = build_decision_snapshot(orders, waves, products)
    return {
        'get_kpis': lambda: {'orders': compute_order_kpis(orders), 'picking': compute_picking_kpis(waves)},
        'get_top_products': lambda: compute_abc_from_orders(orders).head(10).to_dict(orient='records'),
        'get_bottlenecks': lambda: identify_bottleneck_locations(waves).head(10).to_dict(orient='records'),
        'get_route_analysis': lambda: analyze_wave_routes(waves),
        'get_data_provenance': lambda: snapshot['data_basis'],
        'get_decision_snapshot': lambda: snapshot,
        'get_data_quality': lambda: build_data_quality_report(dataset).to_dict(orient='records'),
    }