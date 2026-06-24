"""Strong-venue track (NOT in the 6pp UBMK paper): VALIDATE THE FIX.

The UBMK paper's contribution is the diagnosis -- the benign-mimicry "detection collapse" is largely an
operating-point artifact over a still-discriminable score. The obvious next demand from a strong venue:
show that the implied remedy actually BEATS the naive global threshold as a deployable policy, at matched
analyst cost, not just that a different threshold exists.

We compare two DEPLOYABLE policies (neither peeks at the family label at inference) on the recall vs
benign-review-load plane, for the benign-mimicking family of each corpus:
  * BASELINE: the classifier's attack score with a single global threshold, swept.
  * FIX: union of (classifier attack score) and a benign-only Isolation-Forest novelty score, each
    given half the benign-review budget -- the paper's per-family/novelty remedy in label-free form.
The novelty score is orthogonal signal, so the union can exceed the classifier's own ROC for families
that sit in the benign cloud. At matched benign-review budget b in {5,10,20}% we report family recall for
both policies and the paired Delta with a 95% CI; the fix "provably beats" the global threshold where the
Delta CI excludes 0. Multi-seed; NSL-KDD R2L is evaluated open-set (R2L held out of training).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode, family_holdout_mask
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES = HERE / "results"
BUDGETS = [0.05, 0.10, 0.20]
K = 6


def _recall_global(score, fam_mask, benign_mask, b):
    """Recall of the family at a single global threshold giving benign FPR = b."""
    thr = np.quantile(score[benign_mask], 1 - b)
    return float((score[fam_mask] >= thr).mean())


def _recall_union(s_clf, s_nov, fam_mask, benign_mask, b):
    """Recall of the family under the union gate, each branch at benign FPR = b/2 (union FPR <= b)."""
    tc = np.quantile(s_clf[benign_mask], 1 - b / 2)
    tn = np.quantile(s_nov[benign_mask], 1 - b / 2)
    flag = (s_clf >= tc) | (s_nov >= tn)
    union_fpr = float(flag[benign_mask].mean())
    return float(flag[fam_mask].mean()), union_fpr


def eval_nslkdd(seed):
    ds = NslKdd.load()
    fam_te = ds.test["family"].to_numpy()
    yte = ds.test["y"].to_numpy()
    tr = ds.train.sample(frac=0.8, random_state=seed)
    trh = tr[family_holdout_mask(tr, "R2L")]                 # R2L unknown at train time (open-set)
    Xh, yh, Xte, _, _ = encode(trh, ds.test)
    clf = HistGradientBoostingClassifier(random_state=seed).fit(Xh, yh)
    s_clf = clf.predict_proba(Xte)[:, 1]
    Xtr_all, ytr_all, _, _, _ = encode(tr, ds.test)
    iforest = IsolationForest(n_estimators=200, random_state=seed, n_jobs=-1).fit(Xtr_all[ytr_all == 0])
    s_nov = -iforest.score_samples(Xte)
    benign, fam = yte == 0, fam_te == "R2L"
    return s_clf, s_nov, fam, benign


def eval_cic2018(seed):
    from exp_thirdcorpus import load
    X, y = load()                                            # y==1 is Infiltration
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    sc = StandardScaler().fit(Xtr); Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
    clf = HistGradientBoostingClassifier(random_state=seed).fit(Xtr_s, ytr)
    s_clf = clf.predict_proba(Xte_s)[:, 1]
    iforest = IsolationForest(n_estimators=150, random_state=seed, n_jobs=-1).fit(Xtr_s[ytr == 0])
    s_nov = -iforest.score_samples(Xte_s)
    benign, fam = yte == 0, yte == 1
    return s_clf, s_nov, fam, benign


def main():
    flat = {}
    for corpus, fn, fam_name in (("nslkdd_r2l", eval_nslkdd, "R2L"),
                                 ("cic2018_infil", eval_cic2018, "Infiltration")):
        base = {b: [] for b in BUDGETS}; fix = {b: [] for b in BUDGETS}; ufpr = {b: [] for b in BUDGETS}
        for seed in range(K):
            s_clf, s_nov, fam, benign = fn(seed)
            for b in BUDGETS:
                base[b].append(_recall_global(s_clf, fam, benign, b))
                r, uf = _recall_union(s_clf, s_nov, fam, benign, b)
                fix[b].append(r); ufpr[b].append(uf)
            print(f"{corpus} seed {seed} done")
        for b in BUDGETS:
            mb, hb = ci(base[b]); mf, hf = ci(fix[b])
            delta = np.array(fix[b]) - np.array(base[b])
            md, hd = ci(list(delta))
            tag = f"vf_{corpus}_b{int(b*100)}"
            flat[f"{tag}_base"] = round(mb, 3); flat[f"{tag}_fix"] = round(mf, 3)
            flat[f"{tag}_delta"] = round(md, 3); flat[f"{tag}_delta_hw"] = round(hd, 3)
            flat[f"{tag}_unionfpr"] = round(float(np.mean(ufpr[b])), 3)
            beats = (md - hd) > 0
            flat[f"{tag}_beats"] = bool(beats)
            print(f"  {corpus} {fam_name} @b={b:.0%}: base {mb:.3f} -> fix {mf:.3f} "
                  f"(Delta {md:+.3f} +/- {hd:.3f}; union FPR {np.mean(ufpr[b]):.3f}) "
                  f"{'BEATS' if beats else 'ns'}")
    RES.mkdir(exist_ok=True)
    (RES / "validatefix.json").write_text(json.dumps(flat, indent=2))
    print("wrote results/validatefix.json")


if __name__ == "__main__":
    main()
