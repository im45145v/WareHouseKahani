# Assumptions

This project uses a strict assumption register.

## Real data
- Raw warehouse CSV files from the packaged dataset are treated as real data.

## Derived data
- Order KPIs, product summaries, and storage-slot flattening are derived data.

## Simulated data
- Scenario outputs such as projected volume changes are simulated and labeled as such.

## Assumed data
- Any missing business parameters not available in the dataset must be documented explicitly before use.

## Current project status
- The initial implementation focuses on the real primary warehouse dataset and derived analytics only.
- Advanced simulation and optimization are intentionally scoped to what can be supported by the actual warehouse tables.
