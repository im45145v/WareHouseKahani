# AI-Powered Warehouse Digital Twin

Academic logistics and warehouse management prototype for IIM Ranchi. The system loads the real Mendeley Footwear Manufacturing Warehouse dataset, validates it, derives operational evidence, and exposes cautious decision support through Streamlit.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
streamlit run app/streamlit_app.py
```

The expected dataset directory is `data/raw/Order Picking Dataset from a Warehouse of a Footwear Manufacturing Company/`. The repository currently contains `Product.csv`, `Customer_Order.csv`, `Picking_Wave.csv`, `Storage_Location.csv`, `Support_Points_Navigation.csv`, and four storage-strategy CSVs. The loader detects the source delimiter, including the comma-delimited Random storage file.

## Architecture

`data_loader` performs configurable raw CSV ingestion. `data_quality` reports schema, null, duplicate, and malformed-value findings without silently deleting rows. `analytics`, `operations`, `storage_model`, and `optimization` derive workload, demand, location, storage-slot, and candidate-prioritization evidence. `decision_engine` and `ai_tools` provide grounded management responses. The Streamlit app is the presentation layer.

## What is measured

Observed KPIs include orders, order lines, ordered units, picking waves, picked units, unique locations, unique SKUs, average locations per wave, workload share, and order-line ABC concentration. Storage comparisons report parsed slot counts, SKU counts, and quantities. The coordinate view joins observed picked-unit activity to real `Storage_Location.csv` coordinates.

## What is not claimed

The source data does not contain picker travel paths, travel times, capacity, labor productivity, cost, revenue, inventory flow, or replenishment events. Therefore the project does not fabricate route distance, cost savings, throughput gains, or an optimal storage layout. Demand scenarios are simulations; staffing response is an explicit assumption. See `docs/LIMITATIONS.md` and `docs/ASSUMPTIONS.md`.

## Optional AI narrative

Set `OPENAI_API_KEY` in a local `.env` only when an external narrative explanation is desired. Deterministic evidence tools remain the source of numerical truth, and the dashboard works without an API key. Never commit `.env` or credentials.

## Academic support

`docs/METHODOLOGY.md`, `docs/DATA_DICTIONARY.md`, and `docs/DATA_PROVENANCE.md` support report writing. No literature citations are fabricated; external references should be added by the research team.