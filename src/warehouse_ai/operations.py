from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from warehouse_ai.analytics import classify_congestion, classify_location_type


def summarize_wave_activity(waves: pd.DataFrame) -> Dict[str, Any]:
    """Summarize the operational workload implied by the warehouse picking-wave table."""
    if waves.empty:
        return {'total_waves': 0, 'total_picks': 0, 'avg_picks_per_wave': 0.0, 'top_locations': []}

    total_waves = waves['waveNumber'].nunique() if 'waveNumber' in waves.columns else len(waves)
    total_picks = int(waves['quantityToPick (units)'].sum()) if 'quantityToPick (units)' in waves.columns else 0
    avg_picks = total_picks / total_waves if total_waves else 0.0
    top_locations = []
    if 'locations' in waves.columns:
        top_locations = waves['locations'].value_counts().head(10).to_dict()

    return {
        'total_waves': int(total_waves),
        'total_picks': int(total_picks),
        'avg_picks_per_wave': float(avg_picks),
        'top_locations': top_locations,
    }


def identify_bottleneck_locations(waves: pd.DataFrame) -> pd.DataFrame:
    """Identify locations with the highest pick burden using observed activity counts."""
    if waves.empty or 'locations' not in waves.columns:
        return pd.DataFrame(columns=['location', 'pick_count'])

    if 'quantityToPick (units)' in waves.columns:
        df = waves.groupby('locations', as_index=False)['quantityToPick (units)'].sum()
        df.rename(columns={'locations': 'location', 'quantityToPick (units)': 'pick_count'}, inplace=True)
    else:
        df = waves['locations'].value_counts().reset_index()
        df.columns = ['location', 'pick_count']

    df = df.sort_values('pick_count', ascending=False).reset_index(drop=True)
    total = df['pick_count'].sum()
    df['workload_share'] = df['pick_count'] / total if total else 0.0
    df['bottleneck_score'] = df['workload_share']
    df['evidence_basis'] = 'Observed picked units by location'
    return df


def build_operational_action_queue(waves: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    """Turn observed location workload into a manager-ready triage queue.

    The recommended action is deliberately different for storage bins and
    staging/corridor points; neither is presented as a proven capacity failure.
    """
    columns = [
        'priority', 'location', 'location_type', 'picked_units', 'workload_share',
        'status', 'recommended_action', 'owner',
    ]
    bottlenecks = identify_bottleneck_locations(waves)
    if bottlenecks.empty:
        return pd.DataFrame(columns=columns)

    queue = bottlenecks.head(limit).copy()
    queue.rename(columns={'pick_count': 'picked_units'}, inplace=True)
    queue['location_type'] = queue['location'].map(classify_location_type)
    queue['status'] = queue['workload_share'].map(classify_congestion)
    queue['priority'] = queue['status'].map({'Critical': 1, 'Watch': 2, 'Normal': 3}).fillna(3).astype(int)

    def action_for(row: pd.Series) -> str:
        if row['location_type'] == 'Staging / Corridor Point':
            return 'Observe queueing and rebalance staging or consolidation flow'
        if row['status'] == 'Critical':
            return 'Audit slot capacity, replenishment, and backup pick path before relocation'
        if row['status'] == 'Watch':
            return 'Review slotting and validate capacity during the next shift'
        return 'Include in routine workload and slotting review'

    queue['recommended_action'] = queue.apply(action_for, axis=1)
    queue['owner'] = queue['location_type'].map(
        {
            'Staging / Corridor Point': 'Shift supervisor',
            'Storage Bin': 'Warehouse planner',
        }
    ).fillna('Shift supervisor')
    return queue[columns].sort_values(['priority', 'picked_units'], ascending=[True, False]).reset_index(drop=True)


def analyze_wave_routes(waves: pd.DataFrame) -> Dict[str, Any]:
    """Describe observed wave stop sequences; distance is not claimed without route telemetry."""
    required = {'waveNumber', 'locations'}
    if waves.empty or not required.issubset(waves.columns):
        return {'waves_analyzed': 0, 'avg_stops': 0.0, 'avg_unique_stops': 0.0, 'repeat_stop_rate': 0.0, 'distance_available': False}
    locations = waves['locations'].astype(str).str.strip()
    by_wave = pd.DataFrame({'wave': waves['waveNumber'], 'location': locations}).groupby('wave')
    stops = by_wave.size()
    unique_stops = by_wave['location'].nunique()
    return {
        'waves_analyzed': int(len(stops)),
        'avg_stops': float(stops.mean()),
        'avg_unique_stops': float(unique_stops.mean()),
        'repeat_stop_rate': float(1 - unique_stops.sum() / stops.sum()) if stops.sum() else 0.0,
        'distance_available': False,
        'limitation': 'The dataset records locations but not ordered travel paths or travel distance.',
    }


def identify_wave_exceptions(waves: pd.DataFrame, quantile: float = 0.9) -> pd.DataFrame:
    """Flag unusually large or stop-heavy waves for supervisor review."""
    columns = ['wave', 'picked_units', 'unique_stops', 'line_count', 'exception', 'review_action']
    required = {'waveNumber', 'quantityToPick (units)', 'locations'}
    if waves.empty or not required.issubset(waves.columns):
        return pd.DataFrame(columns=columns)

    frame = waves.copy()
    frame['picked_units'] = pd.to_numeric(frame['quantityToPick (units)'], errors='coerce').fillna(0)
    frame['locations'] = frame['locations'].astype(str).str.strip()
    summary = frame.groupby('waveNumber', as_index=False).agg(
        picked_units=('picked_units', 'sum'),
        unique_stops=('locations', 'nunique'),
        line_count=('locations', 'size'),
    ).rename(columns={'waveNumber': 'wave'})
    unit_limit = summary['picked_units'].quantile(quantile)
    stop_limit = summary['unique_stops'].quantile(quantile)
    summary['exception'] = 'Normal'
    high_units = summary['picked_units'] >= unit_limit
    high_stops = summary['unique_stops'] >= stop_limit
    summary.loc[high_units & high_stops, 'exception'] = 'Units and stops high'
    summary.loc[high_units & ~high_stops, 'exception'] = 'Units high'
    summary.loc[~high_units & high_stops, 'exception'] = 'Stops high'
    summary['review_action'] = summary['exception'].map({
        'Units and stops high': 'Supervisor review before release; check staffing and batching',
        'Units high': 'Check unit volume and replenishment readiness',
        'Stops high': 'Check route sequence and wave consolidation opportunity',
        'Normal': 'No exception review required',
    })
    severity = {'Units and stops high': 1, 'Units high': 2, 'Stops high': 3}
    summary['severity'] = summary['exception'].map(severity).fillna(4)
    return summary[summary['exception'] != 'Normal'].sort_values(
        ['severity', 'picked_units'], ascending=[True, False]
    )[columns].reset_index(drop=True)


def simulate_volume_scenario(baseline_volume: float, volume_change_pct: float, staffing_change: int = 0) -> Dict[str, Any]:
    """Compute a simple operational scenario estimate based on observed demand and workforce change."""
    scenario_volume = baseline_volume * (1 + volume_change_pct / 100)
    throughput_index = scenario_volume / max(baseline_volume, 1)
    staffing_effect = max(0, staffing_change)
    adjusted_index = throughput_index * (1 + 0.05 * staffing_effect)
    return {
        'baseline_volume': float(baseline_volume),
        'volume_change_pct': float(volume_change_pct),
        'scenario_volume': float(scenario_volume),
        'staffing_change': int(staffing_change),
        'staffing_effect': int(staffing_effect),
        'expected_throughput_index': float(adjusted_index),
        'throughput_basis': 'Scenario index only; staffing response is an explicit assumption, not observed productivity.',
        'scenario_label': 'Demand increase' if volume_change_pct > 0 else 'Demand reduction',
    }
