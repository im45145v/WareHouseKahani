from __future__ import annotations

from typing import Dict, Any

import pandas as pd


def compute_order_kpis(orders: pd.DataFrame) -> Dict[str, Any]:
    """Compute core order-level warehouse KPIs from real order data."""
    if orders.empty:
        return {
            'total_orders': 0,
            'total_order_lines': 0,
            'avg_lines_per_order': 0.0,
            'avg_units_per_order': 0.0,
            'avg_order_value_units': 0.0,
        }

    required = {'orderNumber', 'quantity (units)'}
    missing = required - set(orders.columns)
    if missing:
        raise ValueError(f"Customer_Order is missing required columns: {sorted(missing)}")
    order_counts = orders.groupby('orderNumber').size().reset_index(name='line_count')
    total_orders = order_counts['orderNumber'].nunique()
    total_order_lines = len(orders)
    avg_lines_per_order = order_counts['line_count'].mean()
    avg_units_per_order = orders.groupby('orderNumber')['quantity (units)'].sum().mean()

    return {
        'total_orders': int(total_orders),
        'total_order_lines': int(total_order_lines),
        'avg_lines_per_order': float(avg_lines_per_order),
        'avg_units_per_order': float(avg_units_per_order),
        'avg_order_value_units': float(avg_units_per_order),
        'total_units': float(orders['quantity (units)'].sum()),
        'orders_per_wave': float(orders.groupby('waveNumber').orderNumber.nunique().mean()) if 'waveNumber' in orders else 0.0,
    }


def compute_product_metrics(products: pd.DataFrame) -> Dict[str, Any]:
    """Summarize product frequency and ABC segmentation using operational demand proxies."""
    if products.empty:
        return {'abc_distribution': {'A': 0, 'B': 0, 'C': 0}, 'top_products': []}

    if 'Reference' not in products or 'ABCCOD' not in products:
        raise ValueError('Product is missing required columns: Reference and ABCCOD')
    abc_counts = products['ABCCOD'].fillna('Unknown').astype(str).str.strip().value_counts().to_dict()
    return {
        'abc_distribution': {k: int(v) for k, v in sorted(abc_counts.items())},
        'top_products': products.head(10).to_dict(orient='records'),
        'classification_basis': 'ABCCOD supplied by the dataset; not revenue-based',
    }


def compute_picking_kpis(waves: pd.DataFrame) -> Dict[str, Any]:
    """Compute observed workload KPIs from Picking_Wave only."""
    if waves.empty:
        return {'total_picks': 0.0, 'unique_waves': 0, 'unique_locations': 0, 'unique_skus': 0, 'avg_locations_per_wave': 0.0}
    quantities = pd.to_numeric(waves['quantityToPick (units)'], errors='coerce').fillna(0)
    locations_per_wave = waves.groupby('waveNumber')['locations'].nunique() if 'waveNumber' in waves else pd.Series(dtype=float)
    return {
        'total_picks': float(quantities.sum()),
        'unique_waves': int(waves['waveNumber'].nunique()) if 'waveNumber' in waves else len(waves),
        'unique_locations': int(waves['locations'].astype(str).str.strip().nunique()) if 'locations' in waves else 0,
        'unique_skus': int(waves['reference'].nunique()) if 'reference' in waves else 0,
        'avg_locations_per_wave': float(locations_per_wave.mean()) if len(locations_per_wave) else 0.0,
    }


def compute_abc_from_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Rank SKUs by observed order-line frequency; no revenue is assumed."""
    if orders.empty or not {'Reference', 'quantity (units)'}.issubset(orders.columns):
        return pd.DataFrame(columns=['Reference', 'order_lines', 'units', 'cumulative_share', 'abc_class'])
    ranked = orders.groupby('Reference', as_index=False).agg(order_lines=('Reference', 'size'), units=('quantity (units)', 'sum'))
    ranked = ranked.sort_values(['order_lines', 'units'], ascending=False).reset_index(drop=True)
    ranked['cumulative_share'] = ranked['order_lines'].cumsum() / ranked['order_lines'].sum()
    ranked['abc_class'] = ranked['cumulative_share'].map(lambda share: 'A' if share <= 0.8 else 'B' if share <= 0.95 else 'C')
    return ranked


def compute_zone_activity(storage_locations: pd.DataFrame, wave_activity: pd.DataFrame) -> pd.DataFrame:
    """Summarize pick activity by warehouse zone using location coordinates and wave activity."""
    if storage_locations.empty or wave_activity.empty:
        return pd.DataFrame(columns=['zone', 'location_count', 'pick_total'])

    location_lookup = storage_locations[['originalLocation', 'x', 'y', 'z']].copy()
    location_lookup['originalLocation'] = location_lookup['originalLocation'].astype(str).str.strip()
    location_lookup['zone'] = location_lookup['originalLocation'].str.split('-').str[:2].str.join('-')
    activity = wave_activity[['locations', 'quantityToPick (units)']].copy()
    activity['locations'] = activity['locations'].astype(str).str.strip()
    merged = activity.rename(columns={'locations': 'originalLocation'}).merge(
        location_lookup[['originalLocation', 'zone']], on='originalLocation', how='left'
    )
    summary = merged.groupby('zone', as_index=False).agg(
        location_count=('originalLocation', 'nunique'),
        pick_total=('quantityToPick (units)', 'sum'),
    )
    return summary.sort_values('pick_total', ascending=False).reset_index(drop=True)


def compute_recommendation_score(orders: pd.DataFrame, waves: pd.DataFrame, products: pd.DataFrame) -> Dict[str, Any]:
    """Generate a simple evidence-based operational score for management recommendations."""
    top_skus = orders['Reference'].value_counts().head(5).to_dict() if not orders.empty else {}
    top_locations = waves['locations'].value_counts().head(5).to_dict() if not waves.empty else {}
    abc_dist = products['ABCCOD'].value_counts().to_dict() if not products.empty else {}

    return {
        'top_skus': top_skus,
        'top_locations': top_locations,
        'abc_distribution': abc_dist,
    }


def generate_recommendations(orders: pd.DataFrame, waves: pd.DataFrame, products: pd.DataFrame) -> Dict[str, Any]:
    """Map observed hotspot patterns into practical management recommendations with traceable evidence."""
    evidence = compute_recommendation_score(orders, waves, products)
    top_skus = list(evidence['top_skus'].keys())[:3]
    top_locations = list(evidence['top_locations'].keys())[:3]
    if not top_locations:
        recommendation = 'Review the current storage layout and validate high-traffic locations using the warehouse activity table.'
    else:
        recommendation = (
            f'Prioritize relocation or zone balancing for the most frequent SKUs ({top_skus or "available SKUs"}) '
            f'and review the busiest locations: {top_locations}. '
            'This reduces travel concentration and prevents a single zone from becoming the main bottleneck.'
        )

    return {
        'top_skus': top_skus,
        'top_locations': top_locations,
        'recommendation': recommendation,
        'evidence': evidence,
    }
