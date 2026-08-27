"""NSL-KDD loader + preprocessing for the selective-prediction IDS study.

NSL-KDD (Tavallaee et al., 2009) is the cleaned KDD'99 successor: 41 features (3 categorical),
a binary normal/attack target, and a fine-grained attack label that maps to four families
(DoS, Probe, R2L, U2R). Crucially, KDDTest+ contains attack types absent from KDDTrain+ ("novel"
attacks) — the basis for our open-set / unknown-attack evaluation.

This module only loads/encodes; modelling and metrics live elsewhere so the data contract is small.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

COLUMNS = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", "land",
    "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "label", "difficulty",
]
CATEGORICAL = ["protocol_type", "service", "flag"]

# attack name -> family (standard NSL-KDD mapping)
_FAMILY = {
    "normal": "normal",
    # DoS
    "back": "DoS", "land": "DoS", "neptune": "DoS", "pod": "DoS", "smurf": "DoS",
    "teardrop": "DoS", "apache2": "DoS", "udpstorm": "DoS", "processtable": "DoS",
    "worm": "DoS", "mailbomb": "DoS",
    # Probe
    "satan": "Probe", "ipsweep": "Probe", "nmap": "Probe", "portsweep": "Probe",
    "mscan": "Probe", "saint": "Probe",
    # R2L
    "guess_passwd": "R2L", "ftp_write": "R2L", "imap": "R2L", "phf": "R2L", "multihop": "R2L",
    "warezmaster": "R2L", "warezclient": "R2L", "spy": "R2L", "xlock": "R2L", "xsnoop": "R2L",
    "snmpguess": "R2L", "snmpgetattack": "R2L", "httptunnel": "R2L", "sendmail": "R2L", "named": "R2L",
    # U2R
    "buffer_overflow": "U2R", "loadmodule": "U2R", "rootkit": "U2R", "perl": "U2R",
    "sqlattack": "U2R", "xterm": "U2R", "ps": "U2R",
}


def family(label: str) -> str:
    return _FAMILY.get(label, "unknown")


@dataclass
class NslKdd:
    """Raw NSL-KDD frames with label, family, and binary target columns added."""
    train: pd.DataFrame
    test: pd.DataFrame

    @staticmethod
    def load(data_dir: str | Path = "papers/paper2-ids-selective/data") -> "NslKdd":
        d = Path(data_dir)
        train = pd.read_csv(d / "KDDTrain+.txt", names=COLUMNS)
        test = pd.read_csv(d / "KDDTest+.txt", names=COLUMNS)
        for df in (train, test):
            df["family"] = df["label"].map(family)
            df["y"] = (df["label"] != "normal").astype(int)  # 1 = attack
        return NslKdd(train=train, test=test)

    def novel_attack_labels(self) -> list[str]:
        """Attack types present in TEST but not in TRAIN (the unknown-attack set)."""
        tr = set(self.train.loc[self.train.label != "normal", "label"])
        te = set(self.test.loc[self.test.label != "normal", "label"])
        return sorted(te - tr)


if __name__ == "__main__":  # quick sanity check
    ds = NslKdd.load()
    print("train", ds.train.shape, "test", ds.test.shape)
    print("train attack rate", round(ds.train.y.mean(), 3), "| test attack rate", round(ds.test.y.mean(), 3))
    print("train families:", ds.train.family.value_counts().to_dict())
    print("test  families:", ds.test.family.value_counts().to_dict())
    print("novel attack types in test (unknown):", ds.novel_attack_labels())
