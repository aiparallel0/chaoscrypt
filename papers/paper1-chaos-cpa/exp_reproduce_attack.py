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
from matplotlib.colors import LogNorm
import numpy as np
from skimage import data

from chaoscrypt.targets import LLEOCipher, break_lleo, lorenz_keystream
from chaoscrypt.ciphers import logistic_keystream
from chaoscrypt.distinguishers import npcr, uaci, chi_square_uniformity

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
KEY = 0xC0FFEE
IMAGES = {"cam": data.camera(), "moon": data.moon(), "grv": data.gravel(), "brk": data.brick()}

# House figure style: restrained spines, consistent fonts, Okabe-Ito palette (colour-blind safe).
plt.rcParams.update({
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7,
})
OK_BLUE, OK_VERM, OK_GREEN = "#0072B2", "#D55E00", "#009E73"


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

    # Positive control: the recommended fix (seed the keystream from SHA-256 of the image) defeats
    # the very same attack. Key-only -> fully recovered; plaintext-hash-seeded -> chance level.
    from skimage.transform import resize as _resize
    pc = _resize(IMAGES["cam"], (256, 256), preserve_range=True).astype(np.uint8).reshape(-1)
    cko = LLEOCipher(KEY, (256, 256))
    dko, _ = break_lleo(cko.encrypt, (256, 256))
    cdef = LLEOCipher(KEY, (256, 256), plaintext_seeded=True)
    ddef, _ = break_lleo(cdef.encrypt, (256, 256))
    flat["keyonly_match_pct"] = round(100 * float(np.mean(dko(cko.encrypt(pc)) == pc)), 4)
    flat["defended_match_pct"] = round(100 * float(np.mean(ddef(cdef.encrypt(pc)) == pc)), 4)
    print(f"positive control: key-only recovered {flat['keyonly_match_pct']}% vs "
          f"hash-seeded {flat['defended_match_pct']}% (chance)")

    (RES / "repro_attack.json").write_text(json.dumps(flat, indent=2))

    # Figure 1: full-width montage -- rows {original, encrypted, recovered} x four images
    cols4 = ["cam", "moon", "grv", "brk"]
    labels = {"cam": "Cameraman", "moon": "Moon", "grv": "Gravel", "brk": "Brick"}
    rows = ["original", "encrypted", "recovered (no key)"]
    fig, ax = plt.subplots(3, 4, figsize=(8.6, 6.7))
    for c, nm in enumerate(cols4):
        for r, im in enumerate(store[nm]):  # (original, encrypted, recovered)
            ax[r, c].imshow(im, cmap="gray", vmin=0, vmax=255)
            ax[r, c].set_xticks([]); ax[r, c].set_yticks([])
            if r == 0:
                ax[r, c].set_title(labels[nm], fontsize=13)
    for r, lab in enumerate(rows):
        ax[r, 0].set_ylabel(lab, fontsize=13)
    plt.tight_layout(); plt.savefig(FIG / "break_grid.pdf"); plt.close()
    img, E2d, rec2d = store["cam"]  # Cameraman, for the histogram/correlation figures below

    # Figure 2: cipher histogram vs the uniform ideal (Cameraman)
    fig, a = plt.subplots(figsize=(3.3, 2.2))
    a.hist(E2d.ravel(), bins=256, range=(0, 256), color=OK_BLUE, alpha=0.9)
    a.axhline(E2d.size / 256, color=OK_VERM, ls="--", lw=1.0, label="uniform ideal")
    a.set_xlabel("pixel value"); a.set_ylabel("count"); a.set_xlim(0, 256); a.legend()
    plt.tight_layout(); plt.savefig(FIG / "cipher_hist.pdf"); plt.close()

    # Figure 3: adjacent-pixel correlation as a 2D density (every pair, log counts), plain vs cipher.
    # The plain image piles onto the diagonal (neighbours are alike); the cipher fills the square.
    fig, ax = plt.subplots(1, 2, figsize=(5.0, 2.5))
    for a, im, ttl in zip(ax, [img, E2d], ["plain image", "LLEO cipher"]):
        xs = im[:, :-1].ravel(); ys = im[:, 1:].ravel()
        a.hist2d(xs, ys, bins=128, range=[[0, 256], [0, 256]], cmap="magma", norm=LogNorm())
        a.set_title(ttl); a.set_aspect("equal")
        a.set_xlabel("pixel (x,y)"); a.set_ylabel("pixel (x+1,y)")
    plt.tight_layout(); plt.savefig(FIG / "correlation_scatter.pdf"); plt.close()

    # Figure 4: diffusion-failure difference images (same key throughout) -- the visual core of the NPCR
    # critique. Each panel is the absolute ciphertext difference |C_0 - C_1|: black where the ciphertext
    # is unchanged, bright where it differs. (A) a one-pixel plaintext change to LLEO leaves the cipher
    # black but for a single bright pixel; (B) the ~99.6% LLEO reports is really the gap between two
    # UNRELATED images; (C) a cipher that seeds its keystream from SHA-256(plaintext) diffuses the same
    # one-pixel change into full noise -- what (A) should have looked like.
    camf = img.reshape(-1).astype(np.uint8)
    cam1 = camf.copy(); cam1[camf.size // 2] ^= 1
    Ecam, Ecam1 = cc.encrypt(camf), cc.encrypt(cam1)               # cc: key-only LLEO on Cameraman's size
    Emoon = cc.encrypt(np.asarray(moon, np.uint8).reshape(-1))
    cD = LLEOCipher(KEY, img.shape, plaintext_seeded=True)
    Edef0, Edef1 = cD.encrypt(camf), cD.encrypt(cam1)
    panels = [("LLEO\n1-pixel change", Ecam, Ecam1),
              ("LLEO\nunrelated images", Ecam, Emoon),
              ("Diffused\n1-pixel change", Edef0, Edef1)]
    fig, ax = plt.subplots(1, 3, figsize=(3.4, 1.95))   # column-native: crisp fonts at \columnwidth
    for a, (ttl, e0, e1) in zip(ax, panels):
        d = np.abs(e0.astype(np.int16) - e1.astype(np.int16)).reshape(img.shape)
        a.imshow(d, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
        a.set_xticks([]); a.set_yticks([]); a.set_title(ttl, fontsize=7.5)
        val = npcr(e0, e1)
        a.set_xlabel(f"NPCR\n{val:.3g}%", fontsize=7, color=(OK_VERM if val < 1 else OK_GREEN))
        ys, xs = np.where(d > 0)
        if len(xs) <= 4:    # lone changed pixel: ring it and point, else invisible at print size
            a.add_patch(plt.Circle((xs.mean(), ys.mean()), 34, fill=False, color=OK_VERM, lw=1.2))
            a.annotate("1 px", xy=(float(xs.mean()), float(ys.mean())),
                       xytext=(0.36 * img.shape[1], 0.16 * img.shape[0]), color=OK_VERM, fontsize=7,
                       arrowprops=dict(arrowstyle="->", color=OK_VERM, lw=1.0))
    plt.tight_layout(pad=0.3); plt.savefig(FIG / "diffusion_diff.pdf"); plt.close()
    print("wrote results/repro_attack.json and 4 figures; "
          f"NPCR unrelated images = {flat['npcr_unrelated']}% vs 1-pixel = {flat['cam_npcr1px']}%")


if __name__ == "__main__":
    main()
