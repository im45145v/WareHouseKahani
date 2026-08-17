from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from warehouse_ai.analytics import compute_abc_from_orders, compute_order_kpis, compute_picking_kpis
from warehouse_ai.operations import analyze_wave_routes, identify_bottleneck_locations


def build_decision_snapshot(orders: pd.DataFrame, waves: pd.DataFrame, products: pd.DataFrame) -> Dict[str, Any]:
    """Create the evidence bundle used by the dashboard and copilot."""
    bottlenecks = identify_bottleneck_locations(waves)
    abc = compute_abc_from_orders(orders)
    top_locations = bottlenecks.head(10).to_dict(orient='records')
    top_skus = abc.head(10).to_dict(orient='records')
    recommendation = 'No location bottleneck can be identified from the available picking records.'
    if top_locations:
        first = top_locations[0]
        recommendation = f"Review {first['location']} first: it has the highest observed picked-unit workload share ({first['workload_share']:.1%})."
    return {
        'finding': recommendation,
        'evidence': {'orders': compute_order_kpis(orders), 'picking': compute_picking_kpis(waves), 'routes': analyze_wave_routes(waves)},
        'top_locations': top_locations,
        'top_skus_by_order_lines': top_skus,
        'data_basis': 'Customer_Order.csv, Picking_Wave.csv, Product.csv; all recommendations are derived from observed records.',
        'confidence': 'Moderate: workload concentration is observed, but travel time, capacity, and labor productivity are absent.',
    }


def answer_question(question: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Return a grounded response for common management questions without inventing metrics."""
    normalized = question.lower()
    if any(term in normalized for term in ('bottleneck', 'problem', 'constraint')):
        return {'Finding': snapshot['finding'], 'Evidence': snapshot['top_locations'][:5], 'Root Cause': 'Concentration of observed picked-unit workload at the busiest locations.', 'Recommendation': 'Review slotting and zone balancing for the listed locations; validate capacity before relocating stock.', 'Expected Impact': 'Not quantified: route distance and capacity data are unavailable.', 'Trade-offs': 'Relocation may increase handling effort or disrupt current storage rules.', 'Confidence': snapshot['confidence'], 'Data Basis': snapshot['data_basis']}
    if any(term in normalized for term in ('travel', 'distance', 'route')):
        return {'Finding': 'The data supports stop and repeat-location analysis, not travel distance.', 'Evidence': snapshot['evidence']['routes'], 'Root Cause': 'Picking_Wave.csv has location identifiers but no ordered path geometry or timestamps.', 'Recommendation': 'Collect route traces or validate a warehouse graph before claiming distance reductions.', 'Expected Impact': 'Cannot be determined from this dataset.', 'Trade-offs': 'Additional telemetry collection is required.', 'Confidence': 'High regarding the data limitation.', 'Data Basis': snapshot['data_basis']}
    if any(term in normalized for term in ('relocat', 'product', 'sku')):
        return {'Finding': 'The highest-frequency order-line SKUs are available for review.', 'Evidence': snapshot['top_skus_by_order_lines'][:5], 'Root Cause': 'Demand concentration can increase repeated visits, but exact travel is unobserved.', 'Recommendation': 'Prioritize a slotting review for the listed SKUs, subject to capacity and handling validation.', 'Expected Impact': 'Not quantified without a route and capacity model.', 'Trade-offs': 'Slotting changes may affect replenishment and storage compatibility.', 'Confidence': snapshot['confidence'], 'Data Basis': snapshot['data_basis']}
    return {'Finding': 'The available dataset does not contain enough information to determine this.', 'Evidence': [], 'Root Cause': 'The question does not map to a supported deterministic analysis.', 'Recommendation': 'Ask about orders, picking workload, locations, storage strategies, or data quality.', 'Expected Impact': 'Cannot be determined.', 'Trade-offs': 'None assessed.', 'Confidence': 'Low.', 'Data Basis': snapshot['data_basis']}