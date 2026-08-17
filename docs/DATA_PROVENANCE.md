# Data Provenance

The project is designed to keep all analytical decisions traceable.

## Provenance chain

`Source dataset -> File -> Column -> Transformation -> Calculation -> Output`

## Example provenance lines

- Customer order records originate from `Customer_Order.csv` and map to order-level KPIs.
- Product segmentation is based on `Product.csv` and `ABCCOD` values.
- Storage strategy encoding is derived from the storage CSVs and flattened into normalized slots.
- KPI outputs in the dashboard are derived from the loaded warehouse tables and are not treated as direct observations.
- Picking workload share is `Picking_Wave.csv.locations` plus `quantityToPick (units)`, normalized for whitespace and aggregated by location.
- Coordinate activity is the previous aggregation joined to `Storage_Location.csv.originalLocation`, `x`, and `y`.
- Demand ABC candidates are ranked from `Customer_Order.csv.Reference` order-line counts; they are not revenue ABC.
- Scenario volume is baseline ordered units multiplied by the selected percentage. Staffing response is an explicit simulation assumption.

## Provenance rule

Any result displayed in the management dashboard must be traceable to an actual source file and a transform step in the processing pipeline.
