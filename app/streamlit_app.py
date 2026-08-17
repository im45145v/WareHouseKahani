from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from warehouse_ai.analytics import compute_abc_from_orders, compute_order_kpis, compute_picking_kpis, compute_zone_activity
from warehouse_ai.data_loader import load_primary_dataset
from warehouse_ai.data_quality import build_data_quality_report
from warehouse_ai.decision_engine import answer_question, build_decision_snapshot
from warehouse_ai.operations import analyze_wave_routes, identify_bottleneck_locations, simulate_volume_scenario
from warehouse_ai.storage_strategy import compare_storage_strategies

st.set_page_config(page_title='Warehouse Digital Twin', layout='wide')
st.title('AI-Powered Warehouse Digital Twin')
st.caption('Data-driven operational twin based on the shipped Footwear Manufacturing Warehouse dataset.')


@st.cache_data(show_spinner='Loading source CSVs...')
def get_dataset():
    return load_primary_dataset()


try:
    dataset = get_dataset()
    orders = dataset['Customer_Order']
    waves = dataset['Picking_Wave']
    products = dataset['Product']
    locations = dataset['Storage_Location']
    order_kpis = compute_order_kpis(orders)
    picking_kpis = compute_picking_kpis(waves)
    snapshot = build_decision_snapshot(orders, waves, products)

    pages = st.tabs(['Executive Overview', 'Warehouse Map', 'Picking Analytics', 'Storage Analytics', 'Simulation', 'AI Copilot', 'Data Quality'])
    with pages[0]:
        st.subheader('Observed operational state')
        columns = st.columns(5)
        for column, (label, value) in zip(columns, [('Orders', order_kpis['total_orders']), ('Order lines', order_kpis['total_order_lines']), ('Units ordered', f"{order_kpis['total_units']:,.0f}"), ('Picking waves', picking_kpis['unique_waves']), ('Picked units', f"{picking_kpis['total_picks']:,.0f}")]):
            column.metric(label, value)
        st.info(snapshot['finding'])
        st.subheader('Evidence-based priorities')
        st.dataframe(pd.DataFrame(snapshot['top_locations']).head(10), use_container_width=True, hide_index=True)
        st.caption(snapshot['confidence'])

    with pages[1]:
        st.subheader('Observed activity by storage coordinate')
        activity = waves.assign(locations=waves['locations'].astype(str).str.strip()).groupby('locations', as_index=False)['quantityToPick (units)'].sum().rename(columns={'locations': 'originalLocation', 'quantityToPick (units)': 'picked_units'})
        map_data = locations.merge(activity, on='originalLocation', how='left').fillna({'picked_units': 0})
        st.plotly_chart(px.scatter(map_data, x='x', y='y', color='picked_units', size='picked_units', hover_name='originalLocation', title='Observed picked-unit activity'), use_container_width=True)
        st.dataframe(map_data.sort_values('picked_units', ascending=False).head(20), use_container_width=True, hide_index=True)

    with pages[2]:
        st.subheader('Picking workload')
        st.json({'kpis': picking_kpis, 'route_analysis': analyze_wave_routes(waves)})
        bottlenecks = identify_bottleneck_locations(waves)
        st.dataframe(bottlenecks.head(25), use_container_width=True, hide_index=True)
        abc = compute_abc_from_orders(orders)
        st.subheader('Demand concentration by observed order-line frequency')
        st.dataframe(abc.head(25), use_container_width=True, hide_index=True)

    with pages[3]:
        st.subheader('Storage strategy evidence')
        tables = {name.lower().replace('_storage', ''): dataset.get(name) for name in ['Class_Based_Storage', 'Dedicated_Storage', 'Hybrid_Storage', 'Random_Storage']}
        summary = compare_storage_strategies(tables)
        st.dataframe(pd.DataFrame(summary.values()), use_container_width=True, hide_index=True)
        st.caption('These are storage-slot summaries. Travel and cost superiority cannot be inferred without a validated route and cost model.')
        zone_activity = compute_zone_activity(locations, waves)
        st.dataframe(zone_activity.head(20), use_container_width=True, hide_index=True)

    with pages[4]:
        st.subheader('What-if demand scenario')
        volume_change = st.slider('Demand change (%)', -30, 60, 25)
        staffing_change = st.number_input('Staffing change (scenario assumption)', -3, 5, 0)
        result = simulate_volume_scenario(order_kpis['total_units'], volume_change, staffing_change)
        st.dataframe(pd.DataFrame([{'Metric': 'Ordered units', 'Baseline': result['baseline_volume'], 'Scenario': result['scenario_volume'], 'Change': result['scenario_volume'] - result['baseline_volume']}, {'Metric': 'Throughput index', 'Baseline': 1.0, 'Scenario': result['expected_throughput_index'], 'Change': result['expected_throughput_index'] - 1.0}]), use_container_width=True, hide_index=True)
        st.warning(result['throughput_basis'])

    with pages[5]:
        st.subheader('Management AI Copilot')
        question = st.text_input('Ask about the observed warehouse state', 'What are the biggest warehouse bottlenecks?')
        if st.button('Answer from analytical evidence'):
            response = answer_question(question, snapshot)
            for heading, value in response.items():
                st.markdown(f'**{heading}**')
                st.write(value)

    with pages[6]:
        st.subheader('Data quality and provenance')
        schemas = {'Product': ['Reference', 'ABCCOD', 'Sector'], 'Customer_Order': ['orderNumber', 'Reference', 'quantity (units)'], 'Picking_Wave': ['waveNumber', 'reference', 'quantityToPick (units)', 'locations'], 'Storage_Location': ['originalLocation', 'x', 'y', 'z']}
        st.dataframe(build_data_quality_report(dataset, schemas), use_container_width=True, hide_index=True)
        st.markdown('Real inputs are the source CSVs. KPIs and tables are derived. Scenario projections are simulated and marked as assumptions where staffing response is used.')
except Exception as exc:  # pragma: no cover
    st.error(f'Unable to load the primary dataset: {exc}')
    st.code('data/raw/Order Picking Dataset from a Footwear Manufacturing Company/')
