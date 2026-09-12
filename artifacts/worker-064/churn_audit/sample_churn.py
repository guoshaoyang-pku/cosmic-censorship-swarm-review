#!/usr/bin/env python3
"""W064-CHURN-01: bounded publication-churn sampler.
Samples sha256/size/mtime of the four frozen-class canonical artifacts,
their authoring mirrors, FROZEN.json and VARIANT_REGISTRY.json every INTERVAL s
for WINDOW s.  Read-only; writes only into artifacts/worker-064/churn_audit/.
"""
import hashlib, json, os, sys, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "artifacts", "worker-064", "churn_audit", "samples.jsonl")
INTERVAL = 5.0
WINDOW = 90.0
CANON = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "ledger/theorems.jsonl",
]
MIRROR = [
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]
EXTRA = ["artifacts/formulation/FROZEN.json", "artifacts/formulation/VARIANT_REGISTRY.json"]
PATHS = CANON + MIRROR + EXTRA

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def snap():
    rec = {"at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "files": {}}
    for rel in PATHS:
        p = os.path.join(ROOT, rel)
        try:
            st = os.stat(p)
            rec["files"][rel] = {"sha256": sha(p), "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
        except FileNotFoundError:
            rec["files"][rel] = {"sha256": None, "bytes": None, "mtime_ns": None}
    try:
        fz = json.load(open(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")))
        rec["frozen"] = {
            "revision": fz.get("revision"),
            "frozen_at": fz.get("frozen_at"),
            "manifest_sha256": {k: v.get("sha256") for k, v in fz.get("files", {}).items()
                                 if k in PATHS or k in CANON},
        }
    except Exception as e:
        rec["frozen"] = {"error": str(e)}
    for rel in CANON:
        m = (rec.get("frozen") or {}).get("manifest_sha256", {}).get(rel)
        rec.setdefault("frozen_match", {})[rel] = (m == rec["files"][rel]["sha256"])
    return rec

def main():
    t0 = time.time()
    n = 0
    with open(OUT, "a") as f:
        while time.time() - t0 <= WINDOW:
            rec = snap()
            rec["t_rel_s"] = round(time.time() - t0, 2)
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            n += 1
            time.sleep(INTERVAL)
    print(json.dumps({"samples": n, "path": OUT, "interval_s": INTERVAL, "window_s": WINDOW}))

if __name__ == "__main__":
    main()
