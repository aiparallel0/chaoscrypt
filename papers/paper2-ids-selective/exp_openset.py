"""Paper 2 open-set experiment: controlled unknown-attack evaluation via family holdout.

For each attack family F, train with F entirely removed from TRAIN (normal + other families kept),
then measure on the TEST rows of F (now genuinely unknown): detection rate and mean confidence,
versus a model that DID see F. Also: at a global confidence threshold giving 80% coverage, what
fraction of unknown-F samples does abstention reject? Demonstrates that (a) unknown families are
detected far less, (b) the model is less confident on them, so (c) selective prediction rejects them.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode, family_holdout_mask

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
FAMILIES = ["DoS", "Probe", "R2L", "U2R"]  # U2R is rare (train 52 / test 67): high-variance estimate


def fit_predict(train_df, test_df):
    Xtr, ytr, Xte, _, _ = encode(train_df, test_df)
    clf = HistGradientBoostingClassifier(random_state=0).fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)
    return proba.argmax(1), proba.max(1)


def main() -> None:
    ds = NslKdd.load()
    fam_test = ds.test["family"].to_numpy()

    # full model (every family seen) -> baseline detection + the 80%-coverage confidence threshold
    pred_full, conf_full = fit_predict(ds.train, ds.test)
    tau = np.quantile(conf_full, 0.20)  # accept top-80% most confident
    flat = {"coverage_tau": round(float(tau), 4)}

    det_seen, det_unseen, rej_unseen = {}, {}, {}
    for F in FAMILIES:
        fmask = fam_test == F
        det_seen[F] = float((pred_full[fmask] == 1).mean())
        # retrain with F removed from training
        tr = ds.train[family_holdout_mask(ds.train, F)]
        pred_h, conf_h = fit_predict(tr, ds.test)
        det_unseen[F] = float((pred_h[fmask] == 1).mean())
        rej_unseen[F] = float((conf_h[fmask] < tau).mean())  # abstention rejects these
        flat.update({
            f"det_seen_{F}": round(det_seen[F], 4),
            f"det_unseen_{F}": round(det_unseen[F], 4),
            f"conf_unseen_{F}": round(float(conf_h[fmask].mean()), 4),
            f"reject_unseen_{F}": round(rej_unseen[F], 4),
        })
        print(f"[{F}] detection seen={det_seen[F]:.3f} -> unseen={det_unseen[F]:.3f}  "
              f"| abstention rejects {rej_unseen[F]:.3f} of unknown-{F} at 80% coverage")

    RES.mkdir(exist_ok=True)
    (RES / "openset.json").write_text(json.dumps(flat, indent=2))

    # Figure: detection seen vs unseen per family
    FIG.mkdir(exist_ok=True)
    x = np.arange(len(FAMILIES))
    plt.figure(figsize=(3.4, 2.6))
    plt.bar(x - 0.2, [det_seen[f] for f in FAMILIES], 0.4, label="family seen in train")
    plt.bar(x + 0.2, [det_unseen[f] for f in FAMILIES], 0.4, label="family held out (unknown)")
    plt.xticks(x, FAMILIES); plt.ylabel("detection rate"); plt.ylim(0, 1)
    plt.legend(fontsize=7); plt.grid(axis="y", alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "openset_detection.pdf"); plt.close()
    print(f"wrote {RES/'openset.json'} and openset_detection.pdf")


if __name__ == "__main__":
    main()
