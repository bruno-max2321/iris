"""Write and read the per-frame table. Parquet when pyarrow is available, gzip-CSV otherwise.
The chosen format is recorded in coverage.json so a consumer never guesses."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Any, Iterable


def write_frames(rows: Iterable[dict[str, Any]], ref_dir: Path, columns: list[str]) -> tuple[Path, str]:
    rows = list(rows)
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore

        table = pa.Table.from_pylist([{c: (json.dumps(r[c]) if isinstance(r.get(c), list) else r.get(c)) for c in columns} for r in rows])
        out = ref_dir / "frames.parquet"
        pq.write_table(table, out, compression="zstd")
        return out, "parquet"
    except ImportError:
        out = ref_dir / "frames.csv.gz"
        with gzip.open(out, "wt", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=columns)
            w.writeheader()
            for r in rows:
                w.writerow({c: (json.dumps(r[c]) if isinstance(r.get(c), list) else r.get(c)) for c in columns})
        return out, "csv.gz"


def read_frames(ref_dir: Path) -> list[dict[str, Any]]:
    pq_path = ref_dir / "frames.parquet"
    if pq_path.exists():
        import pyarrow.parquet as pq  # type: ignore

        rows = pq.read_table(pq_path).to_pylist()
    else:
        with gzip.open(ref_dir / "frames.csv.gz", "rt", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            for k, v in list(r.items()):
                if v in ("", None):
                    r[k] = None
                elif k == "phash":
                    continue
                elif k == "L_hist16":
                    r[k] = json.loads(v)
                elif k == "frame_id":
                    r[k] = int(v)
                else:
                    try:
                        r[k] = float(v)
                    except ValueError:
                        pass
    for r in rows:
        if isinstance(r.get("L_hist16"), str):
            r["L_hist16"] = json.loads(r["L_hist16"])
    return rows
