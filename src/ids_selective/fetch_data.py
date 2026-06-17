#!/usr/bin/env python3
"""Download the NSL-KDD intrusion-detection dataset (public) into a data dir.

NSL-KDD is the de-facto cleaned successor to KDD'99 (Tavallaee et al., 2009): no duplicate records,
sane train/test split, 41 features + label + difficulty. Small (~5 MB), CPU-trivial. We pull the
canonical KDDTrain+ / KDDTest+ text files from public mirrors, trying several in case one is blocked.

Usage: python -m ids_selective.fetch_data [dest_dir]
"""
from __future__ import annotations
import sys
import urllib.request
from pathlib import Path

# (filename -> list of mirror URLs, tried in order)
SOURCES = {
    "KDDTrain+.txt": [
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt",
        "https://raw.githubusercontent.com/jmnwong/NSL-KDD-Dataset/master/KDDTrain%2B.txt",
        "https://raw.githubusercontent.com/HoaNP/NSL-KDD-DataSet/master/KDDTrain%2B.txt",
    ],
    "KDDTest+.txt": [
        "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt",
        "https://raw.githubusercontent.com/jmnwong/NSL-KDD-Dataset/master/KDDTest%2B.txt",
        "https://raw.githubusercontent.com/HoaNP/NSL-KDD-DataSet/master/KDDTest%2B.txt",
    ],
}


def fetch(dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    ok = 0
    for fname, urls in SOURCES.items():
        out = dest / fname
        if out.exists() and out.stat().st_size > 1000:
            print(f"  have {fname} ({out.stat().st_size} bytes)")
            ok += 1
            continue
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                if len(data) < 1000:
                    raise ValueError(f"too small ({len(data)} bytes)")
                out.write_bytes(data)
                print(f"  got {fname} <- {url} ({len(data)} bytes)")
                ok += 1
                break
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {fname} <- {url}: {e}")
    print(f"fetched {ok}/{len(SOURCES)} files into {dest}")
    return 0 if ok == len(SOURCES) else 1


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("papers/paper2-ids-selective/data")
    raise SystemExit(fetch(dest))
