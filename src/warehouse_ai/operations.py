from __future__ import annotations

from typing import Any, Dict

import pandas as pd


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
