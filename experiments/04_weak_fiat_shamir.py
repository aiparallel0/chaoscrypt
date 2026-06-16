"""Fiat-Shamir completeness checks (fallback project): three forgery classes."""
from chaoscrypt.zk import make_group
from chaoscrypt.zk import fiat_shamir

G = make_group(256)
for name, result in fiat_shamir.run_all(G).items():
    print(name)
    for k, v in result.items():
        print(f"  {k}: {v}")
