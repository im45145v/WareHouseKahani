import pandas as pd

from warehouse_ai.operations import analyze_wave_routes, summarize_wave_activity, identify_bottleneck_locations, simulate_volume_scenario


def test_summarize_wave_activity_counts_workload():
    wave_df = pd.DataFrame(
        {
            'waveNumber': [1, 1, 2, 2, 2, 3],
            'quantityToPick (units)': [2, 1, 3, 1, 2, 4],
            'locations': ['A', 'B', 'A', 'A', 'C', 'B'],
            'operator': ['op1', 'op1', 'op2', 'op2', 'op2', 'op3'],
        }
    )
    summary = summarize_wave_activity(wave_df)
    assert summary['total_waves'] == 3
    assert summary['total_picks'] == 13
    assert summary['avg_picks_per_wave'] == 13 / 3


def test_identify_bottleneck_locations_ranks_locations_by_workload():
    wave_df = pd.DataFrame(
        {
            'locations': ['A', 'A', 'B', 'C', 'C', 'C'],
            'quantityToPick (units)': [5, 4, 2, 1, 1, 3],
        }
    )
    result = identify_bottleneck_locations(wave_df)
    assert list(result['location'].head(3)) == ['A', 'C', 'B']
    assert result.iloc[0]['pick_count'] == 9


def test_simulate_volume_scenario_estimates_impact():
    result = simulate_volume_scenario(baseline_volume=100, volume_change_pct=25, staffing_change=1)
    assert result['scenario_volume'] == 125
    assert result['expected_throughput_index'] > 1
    assert result['staffing_effect'] == 1


def test_analyze_wave_routes_labels_distance_as_unavailable():
    result = analyze_wave_routes(pd.DataFrame({'waveNumber': [1, 1, 1], 'locations': ['A ', 'B', 'A ']}))
    assert result['waves_analyzed'] == 1
    assert result['avg_unique_stops'] == 2
    assert result['distance_available'] is False
