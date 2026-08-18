from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from zipfile import ZipFile

import pandas as pd


DATASET_PATH = Path(__file__).resolve().parents[2] / 'data' / 'raw'
DATASET_FOLDER_NAME = 'Order Picking Dataset from a Warehouse of a Footwear Manufacturing Company'


def _ensure_dataset_root() -> Path:
    """Return the extracted dataset folder, extracting the shipped ZIP if needed."""
    dataset_root = DATASET_PATH / DATASET_FOLDER_NAME
    if dataset_root.exists():
        return dataset_root

    repo_root = Path(__file__).resolve().parents[2]
    archives = [repo_root / f'{DATASET_FOLDER_NAME}.zip', *sorted(DATASET_PATH.glob('*.zip'))]
    archive = next((path for path in archives if path.exists()), None)
    if archive is None:
        return dataset_root

    DATASET_PATH.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as zip_file:
        base = DATASET_PATH.resolve()
        for member in zip_file.infolist():
            target = (DATASET_PATH / member.filename).resolve()
            if target != base and base not in target.parents:
                raise ValueError(f'Unsafe path in dataset archive: {member.filename}')
        zip_file.extractall(DATASET_PATH)
    return dataset_root


def list_dataset_files(base_dir: str | Path | None = None) -> List[str]:
    """List the raw dataset files for the warehouse project."""
    root = Path(base_dir) if base_dir is not None else DATASET_PATH
    folder = next(root.iterdir()) if root.exists() and root.is_dir() and any(root.iterdir()) else None
    if folder is None:
        return []
    return sorted(str(p.name) for p in folder.glob('*.csv'))


def load_dataset_registry(base_dir: str | Path | None = None) -> List[Dict[str, Any]]:
    """Return metadata for the warehouse CSVs that are present."""
    root = Path(base_dir) if base_dir is not None else DATASET_PATH
    folders = [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
    if not folders:
        return []
    dataset_root = folders[0]
    registry = []
    for csv_path in sorted(dataset_root.glob('*.csv')):
        df = load_csv_dataset(csv_path, nrows=1)
        registry.append(
            {
                'name': csv_path.name,
                'path': str(csv_path),
                'format': 'csv',
                'size_bytes': csv_path.stat().st_size,
                'n_columns': len(df.columns),
                'sample_columns': list(df.columns[:10]),
            }
        )
    return registry


def load_csv_dataset(path: str | Path, nrows: int | None = None) -> pd.DataFrame:
    """Load one CSV dataset, accounting for the warehouse file formats."""
    p = Path(path)
    with p.open('r', encoding='utf-8-sig') as handle:
        header = handle.readline()
    separator = ',' if header.count(',') > header.count(';') else ';'
    return pd.read_csv(p, sep=separator, encoding='utf-8-sig', nrows=nrows)


def load_primary_dataset() -> Dict[str, pd.DataFrame]:
    """Load the key warehouse tables from the repository's raw dataset."""
    dataset_root = _ensure_dataset_root()
    if not dataset_root.exists():
        raise FileNotFoundError('Primary dataset not found. Place the shipped ZIP at the repository root or extract it into data/raw first.')
    data = {}
    expected_files = [
        'Product.csv',
        'Customer_Order.csv',
        'Picking_Wave.csv',
        'Storage_Location.csv',
        'Support_Points_Navigation.csv',
        'Class_Based_Storage.csv',
        'Dedicated_Storage.csv',
        'Hybrid_Storage.csv',
        'Random_Storage.csv',
    ]
    for csv_name in expected_files:
        path = dataset_root / csv_name
        if path.exists():
            data[csv_name.replace('.csv', '')] = load_csv_dataset(path)
    missing = [name for name in expected_files if not (dataset_root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Required dataset files were not found: {', '.join(missing)}")
    return data


def get_dataset_root() -> Path:
    """Return the folder containing the shipped dataset files, including layout drawings."""
    return DATASET_PATH / 'Order Picking Dataset from a Warehouse of a Footwear Manufacturing Company'


def get_layout_svg_path(z_level: int) -> Path:
    """Return the path to the official CAD floor-plan SVG for a given rack level (Z)."""
    return get_dataset_root() / f'Layout_Z{int(z_level)}.0.svg'
