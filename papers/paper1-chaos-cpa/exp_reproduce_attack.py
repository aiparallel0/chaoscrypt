"""Paper 1: reproduce the LLEO cipher, measure its statistics, and break it.

For four standard grayscale images: cipher entropy and adjacent-pixel correlation (reproduction),
the TRUE one-pixel-differential NPCR/UACI (which exposes the no-diffusion flaw), and the equivalent-key
chosen-plaintext attack (chosen-plaintext count, runtime, pixel-exact recovery). Also contrasts the
one-pixel NPCR with the NPCR between two unrelated images, and the chi-square keystream distinguisher.
Writes results/*.json (for the paper) and three figures.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from skimage import data

from chaoscrypt.targets import LLEOCipher, break_lleo, lorenz_keystream
from chaoscrypt.ciphers import logistic_keystream
from chaoscrypt.distinguishers import npcr, uaci, chi_square_uniformity

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
KEY = 0xC0FFEE
IMAGES = {"cam": data.camera(), "moon": data.moon(), "grv": data.gravel(), "brk": data.brick()}


def entropy(x) -> float:
    p = np.bincount(np.asarray(x, np.uint8).ravel(), minlength=256) / np.asarray(x).size
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def adj_corr(img2d) -> float:
    a = img2d[:, :-1].ravel().astype(float)
    b = img2d[:, 1:].ravel().astype(float)
    return float(np.corrcoef(a, b)[0, 1])


def main() -> None:
    RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    flat: dict = {}
    store = {}
    for name, img in IMAGES.items():
        img = np.asarray(img, np.uint8)
        M, N = img.shape
        f = img.reshape(-1)
        c = LLEOCipher(KEY, (M, N))
        E = c.encrypt(f)
        f2 = f.copy(); f2[f.size // 2] ^= 1            # flip one plaintext pixel
        Ed = c.encrypt(f2)
        t = time.time(); dec, info = break_lleo(c.encrypt, (M, N)); rec = dec(E)
        attack_s = time.time() - t
        store[name] = (img, E.reshape(M, N), rec.reshape(M, N))
        flat.update({
            f"{name}_ent_plain": round(entropy(f), 4),
            f"{name}_ent_cipher": round(entropy(E), 4),
            f"{name}_corr_plain": round(adj_corr(img), 4),
            f"{name}_corr_cipher": round(adj_corr(E.reshape(M, N)), 4),
            f"{name}_npcr1px": round(npcr(E, Ed), 6),
            f"{name}_uaci1px": round(uaci(E, Ed), 6),
            f"{name}_cpt": int(info["chosen_plaintexts"]),
            f"{name}_attack_s": round(attack_s, 3),
            f"{name}_broken": int(np.array_equal(rec, f)),
        })
        print(f"{name}: ent {flat[f'{name}_ent_plain']}->{flat[f'{name}_ent_cipher']} | "
              f"corr {flat[f'{name}_corr_cipher']} | 1px-NPCR {flat[f'{name}_npcr1px']}% | "
              f"broken={bool(flat[f'{name}_broken'])} in {info['chosen_plaintexts']} CPs, {attack_s:.2f}s")

    # NPCR between two UNRELATED images' ciphers (same key) -- explains the ~99.6% they report
    cam, moon = IMAGES["cam"], IMAGES["moon"]
    cc = LLEOCipher(KEY, cam.shape)
    flat["npcr_unrelated"] = round(npcr(cc.encrypt(cam.reshape(-1)), cc.encrypt(moon.reshape(-1))), 4)
    flat["ideal_npcr"] = 99.6094
    flat["one_over_N_pct"] = round(100.0 / cam.size, 6)

    # chi-square keystream distinguisher (chaotic maps are non-uniform)
    chi_log, p_log = chi_square_uniformity(logistic_keystream(0.413, 1_000_000))
    chi_lor, p_lor = chi_square_uniformity(lorenz_keystream(200_000))
    flat["chi2_logistic"] = round(chi_log, 1); flat["p_logistic"] = float(f"{p_log:.1e}")
    flat["chi2_lorenz"] = round(chi_lor, 1); flat["p_lorenz"] = float(f"{p_lor:.1e}")
    (RES / "repro_attack.json").write_text(json.dumps(flat, indent=2))

    # Figure 1: original / encrypted / recovered (Cameraman)
    img, E2d, rec2d = store["cam"]
    fig, ax = plt.subplots(1, 3, figsize=(5.2, 1.95))
    for a, im, ttl in zip(ax, [img, E2d, rec2d],
                          ["original", "encrypted", "recovered (no key)"]):
        a.imshow(im, cmap="gray", vmin=0, vmax=255); a.set_title(ttl, fontsize=8); a.axis("off")
    plt.tight_layout(); plt.savefig(FIG / "break_cameraman.pdf"); plt.close()

    # Figure 2: cipher histogram vs uniform (Cameraman)
    plt.figure(figsize=(3.4, 2.4))
    plt.hist(E2d.ravel(), bins=256, range=(0, 256), color="steelblue")
    plt.axhline(E2d.size / 256, color="k", ls="--", lw=.8, label="uniform")
    plt.xlabel("pixel value"); plt.ylabel("count"); plt.legend(fontsize=7); plt.tight_layout()
    plt.savefig(FIG / "cipher_hist.pdf"); plt.close()

    # Figure 3: adjacent-pixel correlation scatter (plain vs cipher)
    fig, ax = plt.subplots(1, 2, figsize=(5.0, 2.5))
    for a, im, ttl in zip(ax, [img, E2d], ["plain", "cipher"]):
        xs = im[:, :-1].ravel()[::31]; ys = im[:, 1:].ravel()[::31]
        a.scatter(xs, ys, s=1, alpha=.3); a.set_title(f"{ttl}", fontsize=8)
        a.set_xlabel("pixel (x,y)", fontsize=7); a.set_ylabel("pixel (x+1,y)", fontsize=7)
    plt.tight_layout(); plt.savefig(FIG / "correlation_scatter.pdf"); plt.close()
    print("wrote results/repro_attack.json and 3 figures; "
          f"NPCR unrelated images = {flat['npcr_unrelated']}% vs 1-pixel = {flat['cam_npcr1px']}%")


if __name__ == "__main__":
    main()
