"""Paper 2, second dataset: CIC-IDS-2017 replication + cross-day drift, multi-seed.

Within a random split CIC-2017 is far easier than NSL-KDD (so over-confidence is task-dependent). The
cross-day study trains on Friday (DDoS+PortScan) and tests on Thursday (Web = unknown). Over K seeds we
resample the split/subsample and model seed; tables report means and the caption a max 95% CI half-width.
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
from ids_selective.ci import ci

HERE = Path(__file__).parent
RES, FIG = HERE / "results", HERE / "figures"
K = 5


def main() -> None:
    comb, feats = load_day(FRIDAY + THURSDAY, subsample=200_000)
    fri, _ = load_day(FRIDAY, subsample=150_000)
    thu, _ = load_day(THURSDAY, subsample=80_000)
    Xc, yc, famc = comb[feats].to_numpy(), comb["y"].to_numpy(), comb["family"].to_numpy()
    Xf, yf = fri[feats].to_numpy(), fri["y"].to_numpy()
    Xt, yt, famt = thu[feats].to_numpy(), thu["y"].to_numpy(), thu["family"].to_numpy()

    models = {"logreg": LogisticRegression, "rf": RandomForestClassifier, "histgb": HistGradientBoostingClassifier}
    acc = {m: [] for m in models}; ece_ = {m: [] for m in models}
    aurc = {m: [] for m in models}; risk80 = {m: [] for m in models}
    web_seen, web_unseen, drift_ece, drift_rej = [], [], [], []
    curves = {}

    for seed in range(K):
        Xtr, Xte, ytr, yte, _, ft = train_test_split(Xc, yc, famc, test_size=0.3, random_state=seed, stratify=yc)
        sc = StandardScaler().fit(Xtr); Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)
        for name, M in models.items():
            kw = {} if name == "logreg" else {"random_state": seed}
            if name == "logreg":
                kw = {"max_iter": 300}
            elif name == "rf":
                kw = {"n_estimators": 150, "n_jobs": -1, "random_state": seed}
            else:
                kw = {"random_state": seed}
            clf = M(**kw).fit(Xtr_s, ytr)
            p = clf.predict_proba(Xte_s); conf, pred = p.max(1), p.argmax(1); cor = (pred == yte).astype(float)
            acc[name].append(float(cor.mean())); ece_[name].append(float(ece(conf, cor)))
            cov, risks, a = risk_coverage(conf, cor); aurc[name].append(float(a))
            risk80[name].append(float(risk_at_coverage(conf, cor, 0.8)))
            if name == "histgb":
                web_seen.append(float((pred[ft == "Web"] == 1).mean()))
                if seed == 0:
                    curves = {name: (cov, risks)}
        # cross-day: train Friday, test Thursday (Web unknown)
        scd = StandardScaler().fit(Xf)
        clf = HistGradientBoostingClassifier(random_state=seed).fit(scd.transform(Xf), yf)
        pthu = clf.predict_proba(scd.transform(Xt)); confd, predd = pthu.max(1), pthu.argmax(1)
        web = famt == "Web"; tau = np.quantile(confd, 0.20)
        web_unseen.append(float((predd[web] == 1).mean()))
        drift_ece.append(float(ece(confd, (predd == yt).astype(float))))
        drift_rej.append(float((confd[web] < tau).mean()))
        print(f"seed {seed} done")

    flat = {"cic_n_train": int(len(yc) * 0.7), "cic_n_test": int(len(yc) * 0.3), "cic_n_web_thu": int((famt == "Web").sum())}
    hws = []
    for name in models:
        for tag, store in (("acc", acc), ("ece", ece_), ("aurc", aurc), ("risk80", risk80)):
            m, h = ci(store[name]); flat[f"cic_{name}_{tag}"] = round(m, 4); hws.append(h)
    for key, store in (("cic_web_seen", web_seen), ("cic_web_unseen", web_unseen),
                       ("cic_drift_ece", drift_ece), ("cic_drift_reject_web", drift_rej)):
        m, h = ci(store); flat[key] = round(m, 4); hws.append(h)
    flat["cic_maxhw"] = round(max(hws), 4)
    RES.mkdir(exist_ok=True); (RES / "cicids.json").write_text(json.dumps(flat, indent=2))

    FIG.mkdir(exist_ok=True)
    plt.figure(figsize=(3.4, 2.6))
    for name, (cov, risks) in curves.items():
        plt.plot(cov, risks, label=name, lw=1.4)
    plt.xlabel("coverage"); plt.ylabel("selective risk"); plt.title("CIC-IDS-2017", fontsize=8)
    plt.legend(fontsize=7); plt.grid(alpha=.3); plt.tight_layout()
    plt.savefig(FIG / "risk_coverage_cic.pdf"); plt.close()
    print("CIC means + max CI half-width", flat["cic_maxhw"])


if __name__ == "__main__":
    main()
