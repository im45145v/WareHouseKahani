# Data Dictionary

This project follows a strict data provenance approach. Every operational metric must be traceable to a source field in the raw dataset.

## Primary files

### Product.csv
- Reference: product identifier
- ABCCOD: ABC classification code supplied in the warehouse dataset
- Sector: warehouse sector, as recorded in the data

### Customer_Order.csv
- codCustomer: customer identifier
- orderNumber: unique order number
- orderToCollect: collection sequence within an order
- Reference: product reference in the customer order
- Size (US): item size
- quantity (units): unit count ordered
- creationDate: order creation timestamp
- waveNumber: associated picking wave identifier
- operator: operator assigned to the wave/order

### Picking_Wave.csv
- waveNumber: picking wave identifier
- reference: product reference in the wave
- Size (US): product size
- quantityToPick (units): picked quantity for the wave line
- locations: location code picked from the warehouse
- operator: worker assigned to pick the item

### Storage_Location.csv
- originalLocation: warehouse storage location identifier
- position: coordinate tuple string from the warehouse geometry
- x, y, z: axis coordinates for the storage position

### Support_Points_Navigation.csv
- points_specified: geometry point tuple for navigation support points
- labels: navigation labels

## Storage strategy files

These files encode each storage slot as 18 product-position cells, each stored as `reference;quantity`.

- Class_Based_Storage.csv
- Dedicated_Storage.csv
- Hybrid_Storage.csv
- Random_Storage.csv

These data files are treated as supply-side storage maps and are not assumed to be order or route data.

## Data type notes

- Real dataset fields are the source of truth.
- Derived fields are created only in the processing layer and are labeled as derived.
- Any simulation-only variables are clearly marked as simulated or assumed.
