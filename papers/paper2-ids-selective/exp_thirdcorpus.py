"""Paper 2, third corpus (CIC-IDS-2018 Infiltration): does the operating-point blind spot generalize?

The dissociation rested on two corpora, each with one benign-mimicking family (NSL-KDD R2L, CIC-2017
Web). A near-universal claim from n=2 is fragile, so we add a third, independent corpus whose attack
class -- Infiltration -- is the textbook benign-mimicking family. We ask the SAME threshold-decomposed
question as for R2L:

  * is the attack score discriminative for Infiltration (AUROC well above chance)?
  * does a single global argmax threshold nonetheless miss it (low recall)?
  * does a per-family 10% benign-FPR operating point recover it?
  * is the task itself "easy" in calibration terms (low ECE), i.e. is over-confidence task-dependent?

If Infiltration repeats R2L's signature -- discriminative score, argmax miss, FPR-threshold recovery --
the blind spot is an operating-point failure that recurs across corpora, not an NSL-KDD quirk; and if
CIC-2018's ECE is low like CIC-2017, calibration failure stays task-dependent. Multi-seed CIs.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ids_selective.metrics import ece, risk_coverage, risk_at_coverage
from ids_selective.ci import ci

HERE = Path(__file__).parent
DATA = HERE / "data" / "cicids2018" / "Thursday-01-03-2018.csv"
RES = HERE / "results"
K = 5
SUBSAMPLE = 150_000
DROP = {"Label", "Timestamp", "Dst Port", "Protocol", "Flow ID", "Src IP", "Dst IP", "Src Port"}


def load() -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(DATA, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df = df[df["Label"] != "Label"].reset_index(drop=True)            # drop repeated header rows
    y = (df["Label"].str.upper().str.startswith("INFIL")).astype(int).to_numpy()
    feats = [c for c in df.columns if c not in DROP]
    X = df[feats].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    keep = X.notna().all(axis=1).to_numpy()
    X, y = X[keep].to_numpy(np.float32), y[keep]
    if len(y) > SUBSAMPLE:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(y), SUBSAMPLE, replace=False)
        X, y = X[idx], y[idx]
    return X, y


def main() -> None:
    X, y = load()
    acc, ece_, aurc, risk80 = [], [], [], []
    infil_auroc, infil_argmax, infil_fpr10 = [], [], []
    for seed in range(K):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
        sc = StandardScaler().fit(Xtr)
        clf = HistGradientBoostingClassifier(random_state=seed).fit(sc.transform(Xtr), ytr)
        p = clf.predict_proba(sc.transform(Xte))
        score, pred = p[:, 1], p.argmax(1)
        cor = (pred == yte).astype(float)
        acc.append(float(cor.mean())); ece_.append(float(ece(p.max(1), cor)))
        aurc.append(float(risk_coverage(p.max(1), cor)[2])); risk80.append(float(risk_at_coverage(p.max(1), cor, 0.8)))
        benign, infil = yte == 0, yte == 1
        infil_auroc.append(float(roc_auc_score(yte, score)))
        infil_argmax.append(float((pred[infil] == 1).mean()))
        thr = np.quantile(score[benign], 0.90)                        # 10% benign FPR
        infil_fpr10.append(float((score[infil] >= thr).mean()))
        print(f"seed {seed}: acc {acc[-1]:.3f} ece {ece_[-1]:.3f} infil AUROC {infil_auroc[-1]:.3f} "
              f"argmax {infil_argmax[-1]:.3f} fpr10 {infil_fpr10[-1]:.3f}")

    flat, hws = {"c18_n": int(len(y)), "c18_infil_rate": round(float(y.mean()), 3)}, []
    for key, store in (("c18_acc", acc), ("c18_ece", ece_), ("c18_aurc", aurc), ("c18_risk80", risk80),
                       ("c18_infil_auroc", infil_auroc), ("c18_infil_recall_argmax", infil_argmax),
                       ("c18_infil_recall_fpr10", infil_fpr10)):
        m, h = ci(store); flat[key] = round(m, 3); hws.append(h)
    flat["c18_maxhw"] = round(max(hws), 3)
    RES.mkdir(exist_ok=True)
    (RES / "thirdcorpus.json").write_text(json.dumps(flat, indent=2))
    print(f"\nCIC-2018 Infiltration: AUROC {flat['c18_infil_auroc']} | argmax recall "
          f"{flat['c18_infil_recall_argmax']} -> fpr10 {flat['c18_infil_recall_fpr10']} | "
          f"ECE {flat['c18_ece']} (acc {flat['c18_acc']}); maxhw {flat['c18_maxhw']}")


if __name__ == "__main__":
    main()
