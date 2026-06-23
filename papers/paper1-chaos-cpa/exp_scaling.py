"""Attack cost vs image size: the chosen-plaintext count grows only as ceil(log_256 MN)+1,
and wall-clock stays sub-second. Dumps results/scaling.json for the paper's scaling table."""
from __future__ import annotations
import json
import time
from pathlib import Path
import numpy as np
from chaoscrypt.targets import LLEOCipher, break_lleo

HERE = Path(__file__).parent
RES = HERE / "results"
KEY = 0xC0FFEE


def main() -> None:
    flat: dict = {}
    for s in (128, 256, 512, 1024):
        img = np.random.default_rng(0).integers(0, 256, s * s, dtype=np.uint8)
        c = LLEOCipher(KEY, (s, s))
        t = time.time()
        dec, info = break_lleo(c.encrypt, (s, s))
        rec = dec(c.encrypt(img))
        dt = time.time() - t
        flat[f"scale{s}_cpt"] = int(info["chosen_plaintexts"])
        flat[f"scale{s}_s"] = round(dt, 3)
        flat[f"scale{s}_ok"] = int(np.array_equal(rec, img))
        print(f"{s}x{s}: {info['chosen_plaintexts']} chosen plaintexts, {dt:.3f}s, ok={flat[f'scale{s}_ok']}")
    RES.mkdir(exist_ok=True)
    (RES / "scaling.json").write_text(json.dumps(flat, indent=2))


if __name__ == "__main__":
    main()
