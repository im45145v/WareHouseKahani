# Limitations

## Data limitations
- The provided dataset includes order, wave, product, and storage-location data but does not include full travel-time telemetry or real labor productivity logs.
- No explicit shipment cost or revenue field is available from the warehouse files.
- The storage strategy CSVs encode product slots in a non-normalized format and require transformation before analytics.
- Navigation support points appear as geometry strings and require parsing before spatial interpretation.

## Methodological limitations
- Any route optimization or picker travel metric requires a defensible travel model; the raw data does not directly record every travel path.
- The project avoids fabricating warehouse metrics that cannot be derived from the data.
- Advanced optimization outputs should be interpreted as scenario estimates rather than observed historical warehouse performance unless directly measured.
- The implemented optimization module ranks slotting-review candidates; it does not solve a constrained relocation problem because capacity, compatibility, and route-cost inputs are absent.
- The optional language-model integration receives derived evidence only. It is an explanation layer, not an analytical engine.
