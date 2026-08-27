#!/usr/bin/env python3
"""Download a manageable, attack-diverse subset of CIC-IDS-2017 (flow-based IDS, 78 features) from a
public HuggingFace mirror. Three day files (DDoS, PortScan, Web attacks) give benign + three distinct
attack families across days -- enough for a second-dataset replication and a cross-day drift study,
without the full ~1.5 GB set. Usage: python -m ids_selective.fetch_cicids [dest_dir]
"""
from __future__ import annotations
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/datasets/c01dsnap/CIC-IDS2017/resolve/main/"
FILES = [
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
]


def fetch(dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    ok = 0
    for f in FILES:
        out = dest / f
        if out.exists() and out.stat().st_size > 1_000_000:
            print(f"  have {f} ({out.stat().st_size/1e6:.1f} MB)")
            ok += 1
            continue
        url = BASE + urllib.parse.quote(f)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as w:
                total = 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    w.write(chunk)
                    total += len(chunk)
            print(f"  got {f} ({total/1e6:.1f} MB)")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {f}: {e}")
    print(f"fetched {ok}/{len(FILES)} into {dest}")
    return 0 if ok == len(FILES) else 1


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("papers/paper2-ids-selective/data/cicids")
    raise SystemExit(fetch(dest))
