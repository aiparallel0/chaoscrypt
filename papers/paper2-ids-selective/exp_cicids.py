"""Paper 2, second dataset: replicate the calibration / selective-prediction findings on CIC-IDS-2017
(flow-based, 78 features) and run a cross-day drift study. Train on Friday (DDoS+PortScan+benign),
test on Thursday (Web attacks + benign): Web is an unknown family and the benign traffic has drifted,
so we measure the detection collapse, the calibration inflation, and what abstention recovers.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from ids_selective.cicids import load_day, FRIDAY, THURSDAY
from ids_selective.metrics import ece, risk_coverage, risk_at_coverage

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
RNG = 42


def main() -> None:
    flat: dict = {}

    # --- replication: combined CIC, stratified split ---
    comb, feats = load_day(FRIDAY + THURSDAY, subsample=200_000)
    Xtr, Xte, ytr, yte, famtr, famte = train_test_split(
        comb[feats].to_numpy(), comb["y"].to_numpy(), comb["family"].to_numpy(),
        test_size=0.3, random_state=RNG, stratify=comb["y"].to_numpy())
    sc = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
    flat["cic_n_train"], flat["cic_n_test"] = int(len(ytr)), int(len(yte))
    curves = {}
    histgb = None
    for name, clf in [("logreg", LogisticRegression(max_iter=300)),
                      ("rf", RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=0)),
                      ("histgb", HistGradientBoostingClassifier(random_state=0))]:
        clf.fit(Xtr_s, ytr)
        p = clf.predict_proba(Xte_s); conf, pred = p.max(1), p.argmax(1)
        correct = (pred == yte).astype(float)
        cov, risks, aurc = risk_coverage(conf, correct)
        flat.update({
            f"cic_{name}_acc": round(float(correct.mean()), 4),
            f"cic_{name}_ece": round(float(ece(conf, correct)), 4),
            f"cic_{name}_aurc": round(float(aurc), 4),
            f"cic_{name}_risk_full": round(float(1 - correct.mean()), 4),
            f"cic_{name}_risk80": round(float(risk_at_coverage(conf, correct, 0.8)), 4),
        })
        curves[name] = (cov, risks)
        if name == "histgb":
            histgb = clf
            flat["cic_web_seen"] = round(float((pred[famte == "Web"] == 1).mean()), 4)
        print(f"[cic {name}] acc={flat[f'cic_{name}_acc']} ECE={flat[f'cic_{name}_ece']} "
              f"AURC={flat[f'cic_{name}_aurc']} risk {flat[f'cic_{name}_risk_full']}->{flat[f'cic_{name}_risk80']}")

    # --- cross-day drift: train Friday (DDoS+PortScan), test Thursday (Web unknown) ---
    fri, _ = load_day(FRIDAY, subsample=150_000)
    thu, _ = load_day(THURSDAY, subsample=80_000)
    scd = StandardScaler().fit(fri[feats].to_numpy())
    clf = HistGradientBoostingClassifier(random_state=0).fit(scd.transform(fri[feats].to_numpy()), fri["y"].to_numpy())
    pthu = clf.predict_proba(scd.transform(thu[feats].to_numpy()))
    confd, predd = pthu.max(1), pthu.argmax(1)
    yd, famd = thu["y"].to_numpy(), thu["family"].to_numpy()
    web = famd == "Web"
    tau = np.quantile(confd, 0.20)  # 80% coverage on the cross-day test
    flat.update({
        "cic_n_web_thu": int(web.sum()),
        "cic_web_unseen": round(float((predd[web] == 1).mean()), 4),
        "cic_drift_ece": round(float(ece(confd, (predd == yd).astype(float))), 4),
        "cic_drift_reject_web": round(float((confd[web] < tau).mean()), 4),
    })
    print(f"cross-day: Web detection seen={flat['cic_web_seen']} unseen={flat['cic_web_unseen']} | "
          f"drift ECE={flat['cic_drift_ece']} | abstention rejects {flat['cic_drift_reject_web']} of unknown Web")

    RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
    (RES / "cicids.json").write_text(json.dumps(flat, indent=2))
    plt.figure(figsize=(3.4, 2.6))
    for name, (cov, risks) in curves.items():
        plt.plot(cov, risks, label=name, lw=1.4)
    plt.xlabel("coverage"); plt.ylabel("selective risk (error)")
    plt.title("CIC-IDS-2017", fontsize=8); plt.legend(fontsize=7); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "risk_coverage_cic.pdf"); plt.close()
    print("wrote results/cicids.json and risk_coverage_cic.pdf")


if __name__ == "__main__":
    main()
