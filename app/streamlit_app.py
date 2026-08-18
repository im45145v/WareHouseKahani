from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from warehouse_ai.analytics import (
    classify_congestion,
    compute_abc_from_orders,
    compute_daily_order_trend,
    compute_operator_productivity,
    compute_order_kpis,
    compute_picking_kpis,
    compute_zone_activity,
)
from warehouse_ai.data_loader import load_primary_dataset
from warehouse_ai.data_quality import build_data_quality_report, build_operational_readiness
from warehouse_ai.decision_engine import answer_question, build_decision_snapshot
from warehouse_ai.operations import analyze_wave_routes, build_operational_action_queue, identify_bottleneck_locations, identify_wave_exceptions, simulate_volume_scenario
from warehouse_ai.optimization import rank_slotting_candidates
from warehouse_ai.storage_model import parse_storage_strategy_table
from warehouse_ai.storage_strategy import compare_storage_strategies
from warehouse_ai.warehouse_map import build_location_activity, build_map_figure, build_unmatched_activity, render_layout_png

st.set_page_config(page_title='Warehouse Digital Twin', layout='wide', page_icon='🏭')

st.markdown(
    """
    <style>
    .kpi-card {background:#ffffff;border:1px solid #dfe4ea;border-left:5px solid #2f5fd6;border-radius:10px;
        padding:14px 18px;height:100%;box-shadow:0 1px 3px rgba(16,24,40,0.06);}
    .kpi-label {font-size:0.78rem;color:#475467 !important;text-transform:uppercase;letter-spacing:.04em;font-weight:600;margin-bottom:4px;}
    .kpi-value {font-size:1.7rem;font-weight:800;color:#101828 !important;line-height:1.2;}
    .kpi-sub {font-size:0.78rem;color:#667085 !important;margin-top:2px;}
    .badge {display:inline-block;padding:3px 12px;border-radius:999px;font-size:0.76rem;font-weight:700;color:#ffffff !important;}
    .badge-critical {background:#d92d20;}
    .badge-watch {background:#dc9017;}
    .badge-normal {background:#12805c;}
    .action-card {border-left:5px solid #2f5fd6;background:#ffffff;border:1px solid #dfe4ea;border-radius:8px;
        padding:12px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(16,24,40,0.06);color:#101828 !important;}
    .action-card b, .action-card span {color:#101828 !important;}
    .section-note {background:#f4f6fb;border:1px solid #dfe4ea;border-radius:8px;padding:10px 14px;color:#344054 !important;font-size:0.85rem;}
    .risk-card {border-left:5px solid #d92d20;background:#fef3f2;border:1px solid #fda29b;border-radius:8px;
        padding:12px 16px;margin-bottom:10px;color:#7a271a !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


def kpi_card(label: str, value: str, sub: str = '') -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ''
    return f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{sub_html}</div>'


def severity_badge(severity: str) -> str:
    css_class = {'Critical': 'badge-critical', 'Watch': 'badge-watch', 'Normal': 'badge-normal'}.get(severity, 'badge-normal')
    return f'<span class="badge {css_class}">{severity}</span>'



with st.sidebar:
    st.markdown('### 🏭 Footwear DC Digital Twin')
    st.caption('Evidence-based operational cockpit for the warehouse manager, built on the shipped Order Picking dataset.')
    st.markdown('**Congestion legend**')
    st.markdown(
        severity_badge('Critical') + ' &nbsp; workload share ≥ 0.5%<br>' + severity_badge('Watch') + ' &nbsp; workload share ≥ 0.15%<br>' + severity_badge('Normal') + ' &nbsp; below watch threshold',
        unsafe_allow_html=True,
    )
    st.divider()
    if st.button('🔄 Reload source data'):
        st.cache_data.clear()
        st.rerun()
    st.caption('All figures are derived from real Customer_Order, Picking_Wave, Product and Storage_Location records. No revenue or travel-distance data is available, so cost and route claims are explicitly flagged as assumptions.')


@st.cache_data(show_spinner='Loading source CSVs...')
def get_dataset():
    return load_primary_dataset()


@st.cache_data(show_spinner='Rendering official floor plan...')
def get_layout_png(z_level: int):
    return render_layout_png(z_level)


st.title('AI-Powered Warehouse Digital Twin')
st.caption('Data-driven operational twin based on the shipped Footwear Manufacturing Warehouse dataset — built for the warehouse/factory manager.')

try:
    dataset = get_dataset()
    orders = dataset['Customer_Order']
    waves = dataset['Picking_Wave']
    products = dataset['Product']
    locations = dataset['Storage_Location']

    order_kpis = compute_order_kpis(orders)
    picking_kpis = compute_picking_kpis(waves)
    snapshot = build_decision_snapshot(orders, waves, products)
    bottlenecks = identify_bottleneck_locations(waves)
    bottlenecks['congestion'] = bottlenecks['workload_share'].map(classify_congestion)
    operator_productivity = compute_operator_productivity(waves)
    daily_trend = compute_daily_order_trend(orders)
    active_operators = orders['operator'].nunique() if 'operator' in orders.columns else 0

    critical_locations = bottlenecks[bottlenecks['congestion'] == 'Critical']

    tabs = st.tabs(['🏭 Executive Overview', '🗺️ Warehouse Map', '📦 Picking Operations', '🧱 Storage Strategy', '🔮 What-If Simulator', '🤖 AI Copilot', '🔍 Data Quality'])

    # ---------------------------------------------------------------- Executive Overview
    with tabs[0]:
        st.subheader('Operational state at a glance')
        card_cols = st.columns(5)
        card_values = [
            ('Orders', f"{order_kpis['total_orders']:,}"),
            ('Order lines', f"{order_kpis['total_order_lines']:,}"),
            ('Units ordered', f"{order_kpis['total_units']:,.0f}"),
            ('Picking waves', f"{picking_kpis['unique_waves']:,}"),
            ('Active operators', f"{active_operators:,}"),
        ]
        for col, (label, value) in zip(card_cols, card_values):
            col.markdown(kpi_card(label, value), unsafe_allow_html=True)

        st.write('')
        if not critical_locations.empty:
            top_crit = critical_locations.iloc[0]
            st.error(
                f"🔴 **{len(critical_locations)} location(s) are at Critical congestion.** "
                f"Top risk: **{top_crit['location']}** carries {top_crit['workload_share']:.1%} of all picked units — "
                'a single-point failure or slowdown there will ripple across the whole shift. Review staffing/slotting first.'
            )
        else:
            st.success('🟢 No location is currently flagged Critical. Workload is reasonably distributed across the floor.')
        st.caption(snapshot['confidence'])

        st.markdown('**Shift action queue**')
        action_queue = build_operational_action_queue(waves)
        if not action_queue.empty:
            st.dataframe(
                action_queue.rename(columns={
                    'priority': 'Priority', 'location': 'Location', 'location_type': 'Type',
                    'picked_units': 'Picked units', 'workload_share': 'Workload share',
                    'status': 'Status', 'recommended_action': 'Recommended action', 'owner': 'Owner',
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Workload share': st.column_config.ProgressColumn(format='%.2f%%', min_value=0.0, max_value=1.0),
                },
            )
            st.caption('Priority is an evidence-based review order, not a confirmed capacity or safety incident.')

        left, right = st.columns([1.3, 1])
        with left:
            st.markdown('**Order volume trend**')
            if not daily_trend.empty:
                fig = px.line(daily_trend, x='date', y='units', markers=True, labels={'date': 'Date', 'units': 'Units ordered'})
                fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)
                st.caption('Use this to plan shift staffing ahead of demand peaks — spikes here should precede a staffing review.')
            else:
                st.info('No parseable order dates were found in the dataset.')
        with right:
            st.markdown('**Operator productivity (picked units)**')
            if not operator_productivity.empty:
                top_ops = operator_productivity.head(10)
                fig = px.bar(top_ops, x='picked_units', y='operator', orientation='h', color='picked_units', color_continuous_scale='Blues')
                fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), yaxis=dict(categoryorder='total ascending'), coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
                st.caption('Large gaps between top and bottom operators may indicate a coaching or task-assignment opportunity.')
            else:
                st.info('No operator field available in Picking_Wave.')

        if not operator_productivity.empty:
            top_share = operator_productivity['picked_units'].iloc[0] / operator_productivity['picked_units'].sum()
            if top_share >= 0.15:
                st.markdown(
                    f'<div class="risk-card">⚠️ <b>Key-person dependency risk:</b> '
                    f'{operator_productivity["operator"].iloc[0]} alone accounts for {top_share:.1%} of all picked units. '
                    'If this operator is absent, throughput on their zones is exposed. Consider cross-training a backup.</div>',
                    unsafe_allow_html=True,
                )

        action_header, action_download = st.columns([3, 1])
        action_header.markdown('**Evidence-based priority actions**')
        action_rows = pd.DataFrame(snapshot['top_locations']).head(10)
        if not action_rows.empty:
            action_rows['congestion'] = action_rows['workload_share'].map(classify_congestion)
            action_download.download_button(
                '⬇️ Export watchlist (CSV)',
                data=action_rows.to_csv(index=False).encode('utf-8'),
                file_name='priority_actions.csv',
                mime='text/csv',
                use_container_width=True,
            )
            for _, row in action_rows.head(5).iterrows():
                st.markdown(
                    f'<div class="action-card">{severity_badge(row["congestion"])} &nbsp; '
                    f'<b>{row["location"]}</b> — {row["workload_share"]:.1%} of observed workload '
                    f'({row["pick_count"]:,.0f} picked units). Validate capacity before relocating stock.</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.write('No bottleneck evidence available.')

    # ---------------------------------------------------------------- Warehouse Map
    with tabs[1]:
        st.subheader('Interactive warehouse map')
        st.caption('A to-scale, zoomable replica of the floor built from real bin coordinates, colour-coded by congestion — plus the official CAD drawing for reference.')

        z_options = sorted(locations['z'].dropna().unique().tolist()) if 'z' in locations.columns else [1]
        z_labels = {z: f'Level {int(z)}' for z in z_options}

        nav_col, search_col = st.columns([3, 2])
        with nav_col:
            z_level = st.radio('Rack level (Z)', options=z_options, format_func=lambda z: z_labels[z], horizontal=True)
        with search_col:
            search_term = st.text_input('🔎 Find a bin (e.g. H-08-22)', '').strip().upper()

        level_activity = build_location_activity(locations, waves, z_level=z_level)
        level_total_picks = level_activity['picked_units'].sum()
        overall_picks = waves['quantityToPick (units)'].sum() if 'quantityToPick (units)' in waves.columns else 0
        share_of_total = (level_total_picks / overall_picks) if overall_picks else 0

        metric_cols = st.columns(4)
        metric_cols[0].markdown(kpi_card('Bins on this level', f"{len(level_activity):,}"), unsafe_allow_html=True)
        metric_cols[1].markdown(kpi_card('Picked units (level)', f"{level_total_picks:,.0f}"), unsafe_allow_html=True)
        metric_cols[2].markdown(kpi_card('Share of total workload', f"{share_of_total:.1%}"), unsafe_allow_html=True)
        crit_count = int((level_activity['congestion'] == 'Critical').sum())
        metric_cols[3].markdown(kpi_card('Critical bins', f"{crit_count}"), unsafe_allow_html=True)

        highlight = None
        if search_term:
            match = level_activity[level_activity['originalLocation'].str.upper().str.contains(search_term, na=False)]
            if not match.empty:
                highlight = match.iloc[[0]]
                hit = highlight.iloc[0]
                st.markdown(
                    f'<div class="section-note">📍 <b>{hit["originalLocation"]}</b> ({hit["location_type"]}) — '
                    f'{hit["picked_units"]:,.0f} picked units, {hit["workload_share"]:.2%} of workload, status: {severity_badge(hit["congestion"])}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.warning(f'No bin on Level {int(z_level)} matches "{search_term}".')

        fig = build_map_figure(level_activity, title=f'Live pick-activity heatmap — Level {int(z_level)}', highlight=highlight)
        fig.update_layout(height=720)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('**Level-by-level workload comparison**')
        level_summary_rows = []
        for z in z_options:
            la = build_location_activity(locations, waves, z_level=z)
            level_summary_rows.append({'Level': f'Level {int(z)}', 'Picked units': la['picked_units'].sum(), 'Critical bins': int((la['congestion'] == 'Critical').sum())})
        level_summary = pd.DataFrame(level_summary_rows)
        fig_levels = px.bar(level_summary, x='Level', y='Picked units', color='Critical bins', color_continuous_scale='Reds', text='Picked units')
        fig_levels.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_levels.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_levels, use_container_width=True)
        st.caption('Use this to prioritize which rack level to physically walk first during a shift audit.')

        with st.expander(f'📐 Official CAD layout drawing — Layout_Z{int(z_level)}.0'):
            png_bytes = get_layout_png(int(z_level))
            if png_bytes:
                st.image(png_bytes, use_container_width=True)
            else:
                st.info('CAD drawing could not be rendered (cairosvg not available). The interactive heatmap above still reflects the exact same bin coordinates.')

        st.markdown('**Top hotspots on this level**')
        top_level = level_activity.sort_values('picked_units', ascending=False).head(15)[['originalLocation', 'location_type', 'picked_units', 'workload_share', 'congestion']]
        st.dataframe(
            top_level.rename(columns={'originalLocation': 'Bin', 'location_type': 'Type', 'picked_units': 'Picked units', 'workload_share': 'Workload share', 'congestion': 'Status'}),
            use_container_width=True,
            hide_index=True,
            column_config={'Workload share': st.column_config.ProgressColumn(format='%.2f%%', min_value=0.0, max_value=float(max(top_level['workload_share'].max(), 0.001)))},
        )

        unmatched = build_unmatched_activity(locations, waves)
        if not unmatched.empty:
            with st.expander(f'⚠️ {len(unmatched)} staging/corridor hotspot(s) not shown on the map above (e.g. RC-/LC- consolidation points)'):
                st.dataframe(unmatched.head(15).rename(columns={'location': 'Point', 'picked_units': 'Picked units', 'workload_share': 'Workload share', 'congestion': 'Status', 'location_type': 'Type'}), use_container_width=True, hide_index=True)
                st.caption('These points sit outside Storage_Location.csv (they are corridor/staging markers from Support_Points_Navigation.csv), so they cannot be plotted on the coordinate map, but they can still be a real bottleneck — the busiest one is often the pack/consolidation point.')

    # ---------------------------------------------------------------- Picking Operations
    with tabs[2]:
        st.subheader('Picking workload')
        kcols = st.columns(4)
        kcols[0].markdown(kpi_card('Total picked units', f"{picking_kpis['total_picks']:,.0f}"), unsafe_allow_html=True)
        kcols[1].markdown(kpi_card('Unique locations', f"{picking_kpis['unique_locations']:,}"), unsafe_allow_html=True)
        kcols[2].markdown(kpi_card('Unique SKUs picked', f"{picking_kpis['unique_skus']:,}"), unsafe_allow_html=True)
        kcols[3].markdown(kpi_card('Avg. locations / wave', f"{picking_kpis['avg_locations_per_wave']:.1f}"), unsafe_allow_html=True)

        st.markdown('**Busiest locations (congestion triage)**')
        top_bottlenecks = bottlenecks.head(15)
        fig = px.bar(top_bottlenecks, x='pick_count', y='location', orientation='h', color='congestion', color_discrete_map={'Critical': '#d92d20', 'Watch': '#dc9017', 'Normal': '#12805c'})
        fig.update_layout(height=420, yaxis=dict(categoryorder='total ascending'), margin=dict(l=10, r=10, t=20, b=10), font=dict(color='#101828'))
        st.plotly_chart(fig, use_container_width=True)
        table_col, export_col = st.columns([4, 1])
        table_col.dataframe(top_bottlenecks[['location', 'pick_count', 'workload_share', 'congestion']].rename(columns={'location': 'Location', 'pick_count': 'Picked units', 'workload_share': 'Workload share', 'congestion': 'Status'}), use_container_width=True, hide_index=True)
        export_col.download_button(
            '⬇️ Export CSV',
            data=bottlenecks.to_csv(index=False).encode('utf-8'),
            file_name='bottleneck_locations.csv',
            mime='text/csv',
            use_container_width=True,
        )

        route_info = analyze_wave_routes(waves)
        rcols = st.columns(3)
        rcols[0].markdown(kpi_card('Avg. stops / wave', f"{route_info['avg_stops']:.1f}"), unsafe_allow_html=True)
        rcols[1].markdown(kpi_card('Avg. unique stops / wave', f"{route_info['avg_unique_stops']:.1f}"), unsafe_allow_html=True)
        rcols[2].markdown(kpi_card('Repeat-stop rate', f"{route_info['repeat_stop_rate']:.1%}"), unsafe_allow_html=True)
        st.caption(route_info.get('limitation', ''))

        st.markdown('**Wave exceptions for supervisor review**')
        wave_exceptions = identify_wave_exceptions(waves)
        if wave_exceptions.empty:
            st.success('No wave is simultaneously high in observed units and unique stops at the current threshold.')
        else:
            st.dataframe(
                wave_exceptions.head(25).rename(columns={
                    'wave': 'Wave', 'picked_units': 'Picked units', 'unique_stops': 'Unique stops',
                    'line_count': 'Lines', 'exception': 'Exception', 'review_action': 'Review action',
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.caption('Exceptions are relative to the top 10% of observed wave unit and stop distributions; they are review triggers, not confirmed overloads.')

        st.markdown('**Operator productivity**')
        if not operator_productivity.empty:
            st.dataframe(
                operator_productivity.rename(columns={'operator': 'Operator', 'picked_units': 'Picked units', 'waves_handled': 'Waves handled', 'locations_covered': 'Locations covered', 'units_per_wave': 'Units / wave'}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info('No operator field available in Picking_Wave.')

        st.markdown('**Demand concentration (SKU Pareto)**')
        abc = compute_abc_from_orders(orders)
        top_abc = abc.head(25)
        pareto = go.Figure()
        pareto.add_trace(go.Bar(x=top_abc['Reference'], y=top_abc['order_lines'], name='Order lines', marker_color='#1f77b4'))
        pareto.add_trace(go.Scatter(x=top_abc['Reference'], y=top_abc['cumulative_share'] * top_abc['order_lines'].max(), name='Cumulative share (scaled)', yaxis='y', mode='lines+markers', line=dict(color='#d62728')))
        pareto.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10), xaxis_tickangle=-45)
        st.plotly_chart(pareto, use_container_width=True)
        st.dataframe(top_abc.rename(columns={'Reference': 'SKU', 'order_lines': 'Order lines', 'units': 'Units', 'cumulative_share': 'Cumulative share', 'abc_class': 'ABC class'}), use_container_width=True, hide_index=True)

    # ---------------------------------------------------------------- Storage Strategy
    with tabs[3]:
        st.subheader('Storage strategy evidence')
        tables = {name.lower().replace('_storage', ''): dataset.get(name) for name in ['Class_Based_Storage', 'Dedicated_Storage', 'Hybrid_Storage', 'Random_Storage']}
        summary = compare_storage_strategies(tables)
        summary_df = pd.DataFrame(summary.values())
        strategy_cols = st.columns(len(summary_df))
        for col, (_, row) in zip(strategy_cols, summary_df.iterrows()):
            col.markdown(kpi_card(row['strategy_name'].replace('_', ' ').title(), f"{row['unique_skus']:,} SKUs / {row['total_slots']:,} slots"), unsafe_allow_html=True)
        fig = px.bar(summary_df, x='strategy_name', y='avg_quantity', color='strategy_name', labels={'strategy_name': 'Strategy', 'avg_quantity': 'Avg. quantity per slot'})
        fig.update_layout(height=340, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption('These are storage-slot summaries. Travel and cost superiority cannot be inferred without a validated route and cost model.')

        st.markdown('**Zone activity**')
        zone_activity = compute_zone_activity(locations, waves)
        fig = px.bar(zone_activity.head(20), x='zone', y='pick_total', color='pick_total', color_continuous_scale='Oranges')
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(zone_activity.head(20), use_container_width=True, hide_index=True)

        st.markdown('**Slotting review candidates**')
        storage_slots = parse_storage_strategy_table(dataset.get('Dedicated_Storage', pd.DataFrame()), strategy_name='dedicated')
        candidates = rank_slotting_candidates(orders, products, storage_slots)
        if candidates.empty:
            st.info('No storage-slot candidates could be derived from the available tables.')
        else:
            st.dataframe(
                candidates.head(20).rename(columns={
                    'priority_rank': 'Priority', 'reference': 'SKU', 'order_lines': 'Order lines',
                    'current_slot_count': 'Current slots', 'basis': 'Decision basis',
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.caption('Review high-frequency SKUs with few current slots first; this is a review queue, not an automatic relocation plan.')

    # ---------------------------------------------------------------- What-If Simulator
    with tabs[4]:
        st.subheader('What-if demand scenario')
        st.caption('Model a demand swing and staffing response before committing to a shift-plan change.')
        c1, c2 = st.columns(2)
        volume_change = c1.slider('Demand change (%)', -30, 60, 25)
        staffing_change = c2.number_input('Staffing change (headcount)', -3, 5, 0)
        result = simulate_volume_scenario(order_kpis['total_units'], volume_change, staffing_change)

        scols = st.columns(3)
        scols[0].markdown(kpi_card('Baseline units', f"{result['baseline_volume']:,.0f}"), unsafe_allow_html=True)
        scols[1].markdown(kpi_card('Scenario units', f"{result['scenario_volume']:,.0f}"), unsafe_allow_html=True)
        scols[2].markdown(kpi_card('Throughput index', f"{result['expected_throughput_index']:.2f}x"), unsafe_allow_html=True)

        fig = go.Figure(data=[go.Bar(name='Baseline', x=['Ordered units'], y=[result['baseline_volume']]), go.Bar(name='Scenario', x=['Ordered units'], y=[result['scenario_volume']])])
        fig.update_layout(height=340, barmode='group', margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.warning(result['throughput_basis'])
        st.caption('Business framing: use the throughput index as a directional staffing signal only — validate with a time-and-motion study before changing headcount.')

    # ---------------------------------------------------------------- AI Copilot
    with tabs[5]:
        st.subheader('Management AI Copilot')
        st.caption('Ask about the observed warehouse state. Answers are grounded in the analytical evidence above — nothing is fabricated.')
        if 'copilot_history' not in st.session_state:
            st.session_state.copilot_history = []
        for entry in st.session_state.copilot_history:
            with st.chat_message(entry['role']):
                if entry['role'] == 'user':
                    st.write(entry['content'])
                else:
                    for heading, value in entry['content'].items():
                        st.markdown(f'**{heading}**')
                        st.write(value)
        question = st.chat_input('Ask about the observed warehouse state, e.g. "What are the biggest bottlenecks?"')
        if question:
            st.session_state.copilot_history.append({'role': 'user', 'content': question})
            response = answer_question(question, snapshot)
            st.session_state.copilot_history.append({'role': 'assistant', 'content': response})
            st.rerun()

    # ---------------------------------------------------------------- Data Quality
    with tabs[6]:
        st.subheader('Data quality and provenance')
        schemas = {'Product': ['Reference', 'ABCCOD', 'Sector'], 'Customer_Order': ['orderNumber', 'Reference', 'quantity (units)'], 'Picking_Wave': ['waveNumber', 'reference', 'quantityToPick (units)', 'locations'], 'Storage_Location': ['originalLocation', 'x', 'y', 'z']}
        readiness = build_operational_readiness(dataset, schemas)
        if readiness['status'] == 'READY':
            st.success('READY: source data passed the operational review checks.')
        elif readiness['status'] == 'BLOCKED':
            st.error('BLOCKED: fix the required data issues before using recommendations.')
        else:
            st.warning('REVIEW: the data can be analyzed, but the findings below need manager review.')
        for issue in readiness['blockers'] + readiness['issues']:
            st.write(f'- {issue}')
        st.caption(readiness['basis'])
        report = build_data_quality_report(dataset, schemas)
        st.dataframe(report, use_container_width=True, hide_index=True)
        st.markdown('Real inputs are the source CSVs. KPIs and tables are derived. Scenario projections are simulated and marked as assumptions where staffing response is used.')
except Exception as exc:  # pragma: no cover
    st.error(f'Unable to load the primary dataset: {exc}')
    st.code('data/raw/Order Picking Dataset from a Footwear Manufacturing Company/')
