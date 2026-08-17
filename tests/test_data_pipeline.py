import pandas as pd

from warehouse_ai.data_loader import load_dataset_registry
from warehouse_ai.analytics import (
    compute_order_kpis,
    compute_product_metrics,
    compute_zone_activity,
    generate_recommendations,
)
from warehouse_ai.storage_model import parse_storage_strategy_table
from warehouse_ai.storage_strategy import compare_storage_strategies
from warehouse_ai.data_quality import summarize_missing_values
from warehouse_ai.data_quality import validate_table


def test_load_dataset_registry_includes_expected_files():
    registry = load_dataset_registry()
    names = {item['name'] for item in registry}
    assert 'Customer_Order.csv' in names
    assert 'Picking_Wave.csv' in names
    assert 'Storage_Location.csv' in names
    assert 'Product.csv' in names


def test_compute_order_kpis_returns_valid_summary():
    orders = pd.DataFrame(
        {
            'orderNumber': [101, 101, 102],
            'Reference': ['A1', 'A2', 'A1'],
            'quantity (units)': [1, 2, 3],
            'waveNumber': [10, 10, 11],
            'creationDate': ['2023-10-19 07:18:00', '2023-10-19 07:20:00', '2023-10-19 08:00:00'],
        }
    )
    result = compute_order_kpis(orders)
    assert 'total_orders' in result
    assert 'total_order_lines' in result
    assert result['total_orders'] == 2
    assert result['total_order_lines'] == 3


def test_compute_product_metrics_returns_abc_summary():
    products = pd.DataFrame(
        {
            'Reference': ['A1', 'A2', 'A3'],
            'ABCCOD': ['A', 'B', 'C'],
            'Sector': ['PF', 'PF', 'PD'],
            'order_count': [10, 5, 1],
            'pick_frequency': [100, 50, 10],
        }
    )
    result = compute_product_metrics(products)
    assert 'abc_distribution' in result
    assert set(result['abc_distribution'].keys()) == {'A', 'B', 'C'}


def test_parse_storage_strategy_table_converts_slot_values():
    df = pd.DataFrame(
        {
            'Location': ['A-01', 'A-02'],
            'ABCCOD': ['C', 'C'],
            '1': ['SKU1;10.0', 'SKU2;7.0'],
            '2': ['SKU3;4.5', None],
        }
    )
    result = parse_storage_strategy_table(df, strategy_name='class_based')
    assert len(result) == 3
    assert {'location', 'reference', 'quantity', 'slot_index', 'strategy_name'} <= set(result.columns)
    assert result['quantity'].sum() == 21.5


def test_summarize_missing_values_returns_counts():
    df = pd.DataFrame({'a': [1, None, 3], 'b': ['x', 'y', None]})
    result = summarize_missing_values(df)
    assert result['a']['missing_count'] == 1
    assert result['b']['missing_count'] == 1


def test_compute_zone_activity_groups_by_zone():
    storage_locations = pd.DataFrame(
        {
            'originalLocation': ['A-14-11', 'A-14-12', 'H-10-13'],
            'x': [368, 352, 600],
            'y': [0, 0, 120],
            'z': [1, 1, 1],
        }
    )
    wave_activity = pd.DataFrame(
        {
            'locations': ['A-14-11', 'A-14-11', 'H-10-13'],
            'quantityToPick (units)': [4, 2, 6],
        }
    )
    result = compute_zone_activity(storage_locations, wave_activity)
    assert 'zone' in result.columns
    assert result['pick_total'].sum() == 12


def test_generate_recommendations_returns_priority_actions():
    orders = pd.DataFrame(
        {
            'Reference': ['A1', 'A1', 'B2', 'B2', 'C3'],
            'quantity (units)': [1, 1, 1, 1, 1],
        }
    )
    waves = pd.DataFrame(
        {
            'locations': ['RC-01', 'RC-01', 'H-10-22'],
            'quantityToPick (units)': [8, 2, 5],
        }
    )
    products = pd.DataFrame({'Reference': ['A1', 'B2', 'C3'], 'ABCCOD': ['A', 'B', 'C']})
    result = generate_recommendations(orders, waves, products)
    assert 'top_skus' in result
    assert 'top_locations' in result
    assert 'recommendation' in result


def test_compare_storage_strategies_returns_strategy_summary():
    strategy_inputs = {
        'class_based': pd.DataFrame({
            'Location': ['A-01', 'A-01'],
            'ABCCOD': ['C', 'C'],
            '1': ['SKU1;5', 'SKU2;7'],
            '2': [None, 'SKU3;2'],
        }),
        'dedicated': pd.DataFrame({
            'Location': ['H-01'],
            'XYZCOD': ['X'],
            '1': ['SKU1;10'],
            '2': ['SKU1;5'],
        }),
    }
    result = compare_storage_strategies(strategy_inputs)
    assert 'class_based' in result
    assert 'dedicated' in result
    assert result['class_based']['unique_skus'] >= 2
    assert result['dedicated']['total_slots'] >= 2


def test_validate_table_reports_missing_schema_without_dropping_rows():
    result = validate_table(pd.DataFrame({'id': [1, 1, None]}), required_columns=['id', 'name'])
    assert result['rows'] == 3
    assert result['missing_columns'] == ['name']
    assert result['duplicate_rows'] == 1
    assert result['status'] == 'FAIL'
