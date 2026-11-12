"""Load and derive the numbers used on the slides (single source of truth)."""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def _rows(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load():
    d = {}
    main = _rows("main_results.csv")
    for r in main:
        for k in ("recall_at_5_mean", "recall_at_5_std", "em_mean", "em_std",
                  "f1_mean", "f1_std"):
            r[k] = float(r[k])
        r["n_seeds"] = int(r["n_seeds"])
    d["main"] = main
    d["datasets"] = ["HotpotQA", "2Wiki", "MuSiQue"]
    d["methods"] = ["BM25", "Dense", "Dense+CE", "QR+CE"]

    d["latency"] = [{k: (v if k == "method" else int(v)) for k, v in r.items()}
                    for r in _rows("latency.csv")]
    d["ablation"] = []
    for r in _rows("ablation.csv"):
        d["ablation"].append({
            "setting": r["setting"],
            "r5": float(r["recall_at_5_mean"]), "r5sd": float(r["recall_at_5_std"]),
            "em": float(r["em_mean"]), "emsd": float(r["em_std"]),
            "rerank": int(r["rerank_ms"]),
        })
    d["curve"] = [{k: (int(v) if k == "step" else float(v)) for k, v in r.items()}
                  for r in _rows("train_curve.csv")]
    d["errors"] = [{**r, "count": int(r["count"])} for r in _rows("error_types.csv")]

    # derived
    m = {(r["dataset"], r["method"]): r for r in main}
    d["m"] = m
    d["delta"] = {}
    for ds in d["datasets"]:
        a, b = m[(ds, "Dense+CE")], m[(ds, "QR+CE")]
        d["delta"][ds] = {
            "r5": b["recall_at_5_mean"] - a["recall_at_5_mean"],
            "em": b["em_mean"] - a["em_mean"],
        }
    lat = {r["method"]: r for r in d["latency"]}
    d["speedup"] = lat["QR+CE"]["total_ms"] / lat["Dense+CE"]["total_ms"]
    d["rewrite_share"] = lat["QR+CE"]["rewrite_ms"] / lat["QR+CE"]["total_ms"]
    d["err_total"] = sum(e["count"] for e in d["errors"])
    return d


if __name__ == "__main__":
    d = load()
    print("deltas", d["delta"], "speedup", round(d["speedup"], 2),
          "rewrite share", round(d["rewrite_share"], 3), "err total", d["err_total"])
