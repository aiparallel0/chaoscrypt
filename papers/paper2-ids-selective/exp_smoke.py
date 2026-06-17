"""Smoke test: end-to-end NSL-KDD -> calibration + selective-prediction signal chain.

Confirms the paper's thesis is real before we build the full experiment grid:
overconfidence (ECE), risk reduction under abstention (AURC, risk@80% coverage), and
lower confidence / accuracy on the 17 unknown (novel) attack types absent from training.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ids_selective.data import NslKdd
from ids_selective.pipeline import encode
from ids_selective.metrics import ece, risk_coverage, risk_at_coverage

ds = NslKdd.load()
Xtr, ytr, Xte, yte, _ = encode(ds.train, ds.test)
novel = set(ds.novel_attack_labels())
is_novel_attack = ds.test["label"].isin(novel).to_numpy()
is_known_attack = ((ds.test["y"] == 1).to_numpy()) & (~is_novel_attack)

results = {}
for name, clf in [
    ("logreg", LogisticRegression(max_iter=200, n_jobs=-1)),
    ("rf", RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=0)),
]:
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)
    pred = proba.argmax(1)
    conf = proba.max(1)
    correct = (pred == yte).astype(float)
    acc = correct.mean()
    e = ece(conf, correct)
    _, _, aurc = risk_coverage(conf, correct)
    r80 = risk_at_coverage(conf, correct, 0.80)
    # behavior on unknown vs known attacks: detection rate = P(pred=attack) on attack rows
    det_novel = (pred[is_novel_attack] == 1).mean()
    det_known = (pred[is_known_attack] == 1).mean()
    conf_novel = conf[is_novel_attack].mean()
    conf_known = conf[is_known_attack].mean()
    results[name] = dict(
        acc=round(float(acc), 4), ece=round(float(e), 4), aurc=round(float(aurc), 4),
        full_risk=round(float(1 - acc), 4), risk_at_80=round(float(r80), 4),
        detect_known=round(float(det_known), 4), detect_novel=round(float(det_novel), 4),
        conf_known=round(float(conf_known), 4), conf_novel=round(float(conf_novel), 4),
    )
    print(f"\n[{name}] acc={acc:.4f} ECE={e:.4f} AURC={aurc:.4f}")
    print(f"   full risk={1-acc:.4f} -> risk@80%coverage={r80:.4f}  (abstention helps if lower)")
    print(f"   detection rate: known={det_known:.3f} novel={det_novel:.3f}  "
          f"(unknown attacks missed more)")
    print(f"   mean confidence: known-attack={conf_known:.3f} novel-attack={conf_novel:.3f}")

out = Path(__file__).parent / "results" / "smoke.json"
out.write_text(json.dumps(results, indent=2))
print(f"\nwrote {out}")
