from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from warehouse_ai.analytics import classify_congestion, classify_location_type
from warehouse_ai.data_loader import get_layout_svg_path

SEVERITY_COLORS = {'Critical': '#d62728', 'Watch': '#e6a817', 'Normal': '#2e7d32'}


def render_layout_png(z_level: int, output_width: int = 1200) -> Optional[bytes]:
    """Rasterize the official CAD floor-plan SVG for a rack level into PNG bytes.

    Returns None if the source drawing is missing or cannot be rendered, so callers
    can fall back gracefully instead of crashing the dashboard.
    """
    svg_path = get_layout_svg_path(z_level)
    if not svg_path.exists():
        return None
    try:
        import cairosvg
    except ImportError:
        return None
    try:
        return cairosvg.svg2png(url=str(svg_path), output_width=output_width)
    except Exception:
        return None


def build_location_activity(locations: pd.DataFrame, waves: pd.DataFrame, z_level: Optional[int] = None) -> pd.DataFrame:
    """Join storage bin coordinates with observed picking activity and add business context.

    Adds `location_type` (storage bin vs. staging/corridor point) and `congestion` severity
    so a factory manager can triage hotspots at a glance.
    """
    activity = (
        waves.assign(locations=waves['locations'].astype(str).str.strip())
        .groupby('locations', as_index=False)['quantityToPick (units)']
        .sum()
        .rename(columns={'locations': 'originalLocation', 'quantityToPick (units)': 'picked_units'})
    )
    total_picks = activity['picked_units'].sum()
    activity['workload_share'] = activity['picked_units'] / total_picks if total_picks else 0.0

    merged = locations.merge(activity, on='originalLocation', how='left').fillna({'picked_units': 0.0, 'workload_share': 0.0})
    if z_level is not None and 'z' in merged.columns:
        merged = merged[merged['z'] == z_level].reset_index(drop=True)
    merged['location_type'] = merged['originalLocation'].map(classify_location_type)
    merged['congestion'] = merged['workload_share'].map(classify_congestion)
    return merged


def build_unmatched_activity(locations: pd.DataFrame, waves: pd.DataFrame) -> pd.DataFrame:
    """Return picking activity recorded against staging/corridor points not present in Storage_Location.

    These are real operational hotspots (e.g. packing or consolidation points) that would
    otherwise silently disappear from a coordinate-based map.
    """
    known = set(locations['originalLocation'].astype(str).str.strip())
    activity = (
        waves.assign(locations=waves['locations'].astype(str).str.strip())
        .groupby('locations', as_index=False)['quantityToPick (units)']
        .sum()
        .rename(columns={'locations': 'location', 'quantityToPick (units)': 'picked_units'})
    )
    total_picks = activity['picked_units'].sum()
    activity['workload_share'] = activity['picked_units'] / total_picks if total_picks else 0.0
    unmatched = activity[~activity['location'].isin(known)].copy()
    unmatched['location_type'] = unmatched['location'].map(classify_location_type)
    unmatched['congestion'] = unmatched['workload_share'].map(classify_congestion)
    return unmatched.sort_values('picked_units', ascending=False).reset_index(drop=True)


def build_map_figure(location_activity: pd.DataFrame, title: str, highlight: Optional[pd.DataFrame] = None) -> go.Figure:
    """Build an interactive, to-scale heatmap of bin activity for one rack level.

    If `highlight` (a one-row DataFrame from `build_location_activity`) is given, it is
    drawn as a large gold star so a searched bin is easy to spot on a busy floor.
    """
    if location_activity.empty:
        return go.Figure()
    fig = go.Figure()
    for severity, color in SEVERITY_COLORS.items():
        subset = location_activity[location_activity['congestion'] == severity]
        if subset.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=subset['x'],
                y=subset['y'],
                mode='markers',
                name=severity,
                marker=dict(
                    size=12,
                    color=color,
                    symbol='square',
                    line=dict(width=0.5, color='white'),
                ),
                customdata=subset[['originalLocation', 'picked_units', 'workload_share']],
                hovertemplate=(
                    'Bin: %{customdata[0]}<br>'
                    'Picked units: %{customdata[1]:,.0f}<br>'
                    'Share of workload: %{customdata[2]:.2%}<br>'
                    f'Status: {severity}<extra></extra>'
                ),
            )
        )
    if highlight is not None and not highlight.empty:
        fig.add_trace(
            go.Scatter(
                x=highlight['x'],
                y=highlight['y'],
                mode='markers',
                name='Searched bin',
                marker=dict(size=26, color='#f7c948', symbol='star', line=dict(width=2, color='#101828')),
                customdata=highlight[['originalLocation', 'picked_units', 'workload_share']],
                hovertemplate='Bin: %{customdata[0]}<br>Picked units: %{customdata[1]:,.0f}<extra></extra>',
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title='X-Axis (m)',
        yaxis_title='Y-Axis (m)',
        legend_title='Congestion',
        height=560,
        plot_bgcolor='white',
        font=dict(color='#101828'),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    fig.update_yaxes(scaleanchor='x', scaleratio=1)
    return fig

