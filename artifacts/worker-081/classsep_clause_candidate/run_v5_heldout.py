#!/usr/bin/env python3
"""One-shot held-out v4 evaluation. Refuses to run if the frozen pins moved.
No tuning after this run: any candidate rule change voids the out-of-sample claim."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    freeze = json.loads((D / "heldout_v5_freeze.json").read_text())
    checks = {
        "candidate": (D / "class_separation_clause.py", freeze["candidate_module"]["sha256"]),
        "corpus": (D / "corpus_v5_heldout.json", freeze["heldout_corpus"]["sha256"]),
        "pre_registration": (D / "pre_registration.json", freeze["pre_registration"]["sha256"]),
    }
    pins_ok = True
    for k, (p, want) in checks.items():
        got = sha(p)
        ok = got == want
        pins_ok &= ok
        print(f"pin {k}: {'OK' if ok else 'MOVED'} {got}")
    if not pins_ok:
        print("FREEZE VIOLATION: refusing to run held-out evaluation.")
        return 2

    spec = importlib.util.spec_from_file_location("cand_heldout", D / "class_separation_clause.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    corpus = json.loads((D / "corpus_v5_heldout.json").read_text())
    rows = []
    for f in corpus["fixtures"]:
        got = bool(mod.findings_for_text(f["text"], f"heldout {f['id']}"))
        rows.append({**f, "fired": got, "pass": got == f["expect_fire"]})
    by_id = {r["id"]: r for r in rows}
    cue_fn, mention_fp, plain_fn = [], [], []
    for r in rows:
        if r["category"] == "ADVERSARIAL_ASSERTION" and not r["fired"]:
            twin = by_id.get(r.get("twin_of") or "")
            if twin and twin["fired"]:
                cue_fn.append({"id": r["id"], "twin": twin["id"], "confidence": r["confidence"], "cue": r["cue"]})
        if r["category"] == "MENTION" and r["fired"]:
            mention_fp.append(r["id"])
        if r["category"] == "PLAIN_POSITIVE" and not r["fired"]:
            plain_fn.append(r["id"])
    cue_fn_high = [x for x in cue_fn if x["confidence"] == "HIGH"]
    result = {
        "schema": "worker-081/classsep-clause-heldout-result/v1",
        "candidate_sha256": freeze["candidate_module"]["sha256"],
        "corpus_sha256": freeze["heldout_corpus"]["sha256"],
        "rows": rows,
        "cue_induced_fn": cue_fn,
        "cue_induced_fn_high": cue_fn_high,
        "mention_fp": mention_fp,
        "plain_positive_fn": plain_fn,
        "passed": len(cue_fn_high) == 0 and len(mention_fp) == 0 and len(plain_fn) == 0,
        "n": len(rows),
        "n_pass": sum(r["pass"] for r in rows),
    }
    (D / "heldout_v5_results.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: result[k] for k in ("passed", "n", "n_pass", "cue_induced_fn_high",
                                             "mention_fp", "plain_positive_fn")}, indent=1))
    for r in rows:
        if not r["pass"]:
            print(("FAIL " if not r["pass"] else "ok   "), r["id"], r["category"], "|", r["text"][:100])
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
