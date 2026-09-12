#!/usr/bin/env python3
"""W081 adoption-bar harness: score one class-separation candidate module against the
pinned pre-registered corpora. Independent re-implementation (does not import any
worker-049 / audit harness; only the candidate module is imported).

Usage: python3 run_bar_eval.py <candidate_module.py> <out.json>
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../ai4math-swarm

PINS = {
    "corpus_a_worker07": ("artifacts/worker-07/class_separation_falsification/results.json",
                          "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "corpus_d_v1": ("artifacts/worker-049/classsep_fn_audit/corpus.json",
                    "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "corpus_d_v2": ("artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json",
                    "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b"),
    "corpus_d_v3": ("artifacts/worker-049/classsep_successor_audit/corpus_v3.json",
                    "6764c04978c994c377dfc1e31558029cacb1203c15f83258f16798ecd73b219f"),
    "corpus_e_worker035": ("artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                           "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
    "w098_controls": ("artifacts/worker-049/classsep_successor_audit/w098_controls.json",
                      "fe347760f1ebc8a875ef0763f90ae7bfcdbd4a430d18c88cf547d4b84be62414"),
    "labeled16_source": ("artifacts/audit/classsep_calibration.py",
                         "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464"),
    "frozen_pin": ("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
                   "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"),
}

CANONICAL_BAR = {
    "corpus_a_worker07": "PASS 17/0/10/0",
    "labeled16": "sensitivity >= 5/6 AND specificity >= 9/10",
    "worker049_v1": "0 HIGH-confidence cue-induced FN",
    "worker049_v2": "0 HIGH-confidence cue-induced FN",
    "worker049_v3": "0 HIGH-confidence cue-induced FN",
    "worker035": "23/23 controls",
    "w098_controls": "12 fire, 8 clean, growth 0, 2 tp",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cand_" + sha(path)[:8], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_pins():
    out = {}
    for k, (rel, want) in PINS.items():
        p = ROOT / rel
        got = sha(p) if p.exists() else None
        out[k] = {"path": rel, "expected": want, "measured": got, "ok": got == want}
    return out


def worker07_regression(mod):
    """Re-implementation matching the canonical semantics: declaration scan of each
    fixture map plus artifact prose scan."""
    res = json.loads((ROOT / PINS["corpus_a_worker07"][0]).read_text())
    tp = fn = tn = fp = 0
    rows = []
    for fx in res["fixtures"]:
        fpth = ROOT / fx["fixture_path"]
        if not fpth.exists():
            continue
        m = json.loads(fpth.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        cls = "TP" if (truth and got) else "FN" if truth else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fx.get("fixture_id") or fx.get("id"), "truth": truth, "fired": got, "class": cls,
                     "findings": det[:3]})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE", "rows": rows}


def worker049_corpus(mod, key):
    d = json.loads((ROOT / PINS[key][0]).read_text())
    fx = d["fixtures"]
    flags = {}
    for f in fx:
        flags[f["id"]] = bool(mod.findings_for_text(f["text"], f"fixture {f['id']}"))
    cue_fn, noncue_fn, mention_fp, plain_fn, clears = [], [], [], [], []
    for f in fx:
        fid = f["id"]
        got = flags[fid]
        cat = f.get("category")
        if cat == "ADVERSARIAL_ASSERTION":
            twin = f.get("twin_of")
            twin_id = None
            if twin:
                twin_id = twin
            else:
                cand = fid + "T"
                twin_id = cand if any(x["id"] == cand for x in fx) else None
            twin_flags = flags.get(twin_id) if twin_id else None
            if not got:
                clears.append(fid)
                if twin_flags:
                    (cue_fn if f.get("confidence") == "HIGH" else noncue_fn).append(
                        {"id": fid, "twin": twin_id, "confidence": f.get("confidence"), "cue": f.get("adversarial_cue")})
        elif cat == "MENTION" and got:
            mention_fp.append(fid)
        elif cat == "PLAIN_POSITIVE" and not got:
            plain_fn.append(fid)
    high_cue_fn = [x for x in cue_fn if x["confidence"] == "HIGH"]
    return {"n": len(fx), "flags": flags,
            "adversarial_cleared": clears,
            "cue_induced_fn_all": cue_fn,
            "cue_induced_fn_high": high_cue_fn,
            "cue_induced_fn_nonhigh": noncue_fn,
            "mention_fp": mention_fp, "plain_positive_fn": plain_fn,
            "twin_controls_flagged": sum(1 for f in fx if f.get("category") == "TWIN_CONTROL" and flags[f["id"]]),
            "twin_controls_total": sum(1 for f in fx if f.get("category") == "TWIN_CONTROL")}


def labeled16(mod):
    src = (ROOT / PINS["labeled16_source"][0]).read_text()
    tree = ast.parse(src)
    fixtures = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ASSERTION_MENTION_FIXTURES" for t in node.targets):
            fixtures = ast.literal_eval(node.value)
            break
    assert fixtures, "labeled fixture list not found"
    rows, tp, fn, fp, tn = [], 0, 0, 0, 0
    for fid, truth, text in fixtures:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        cls = "TP" if (truth and got) else "FN" if truth else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "expect": truth, "fired": got, "class": cls, "text": text})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(fixtures),
            "sensitivity": f"{tp}/{tp+fn}", "specificity": f"{tn}/{tn+fp}",
            "sens_num": tp, "sens_den": tp + fn, "spec_num": tn, "spec_den": tn + fp,
            "rows": rows}


def worker035(mod):
    d = json.loads((ROOT / PINS["corpus_e_worker035"][0]).read_text())
    rows, passed = [], 0
    for c in d["controls"]:
        expect_fire = str(c.get("expect", "")).upper().startswith("ASSERTION")
        got = bool(mod.findings_for_text(c["text"], f"control {c['control_id']}"))
        ok = got == expect_fire
        passed += ok
        rows.append({"id": c["control_id"], "expect": c.get("expect"), "fired": got, "pass": ok})
    return {"passed": passed, "total": len(d["controls"]), "rows": rows}


def w098(mod):
    d = json.loads((ROOT / PINS["w098_controls"][0]).read_text())
    out = {}
    for kind in ("fire", "clean", "growth", "tp"):
        rows = []
        for c in d[kind]:
            got = bool(mod.findings_for_text(c["text"], f"{kind} {c['name']}"))
            want = kind in ("fire", "tp")
            rows.append({"name": c["name"], "fired": got, "want": want, "pass": got == want, "text": c["text"]})
        out[kind] = {"passed": sum(r["pass"] for r in rows), "total": len(rows), "rows": rows}
    out["growth_findings"] = out["growth"]["total"] - out["growth"]["passed"]
    return out


def build_verdict(res):
    v = {}
    a = res["corpus_a_worker07"]
    v["corpus_a_worker07"] = {"value": f"{a['verdict']} {a['tp']}/{a['fn']}/{a['fp']}/{a['tn']}",
                              "pass": a["verdict"] == "PASS" and (a["tp"], a["fn"], a["fp"], a["tn"]) == (17, 0, 0, 10)}
    l = res["labeled16"]
    v["labeled16"] = {"value": f"sens {l['sensitivity']} spec {l['specificity']}",
                      "pass": l["sens_num"] * 6 >= 5 * l["sens_den"] and l["spec_num"] * 10 >= 9 * l["spec_den"]}
    for k in ("corpus_d_v1", "corpus_d_v2", "corpus_d_v3"):
        c = res[k]
        v[k] = {"value": f"{len(c['cue_induced_fn_high'])} HIGH cue-FN, {len(c['mention_fp'])} mention FP",
                "pass": len(c["cue_induced_fn_high"]) == 0}
    e = res["corpus_e_worker035"]
    v["corpus_e_worker035"] = {"value": f"{e['passed']}/{e['total']}", "pass": e["passed"] == e["total"]}
    w = res["w098_controls"]
    v["w098_controls"] = {"value": f"fire {w['fire']['passed']}/{w['fire']['total']}, clean {w['clean']['passed']}/{w['clean']['total']}, "
                                   f"growth {w['growth']['passed']}/{w['growth']['total']}, tp {w['tp']['passed']}/{w['tp']['total']}",
                          "pass": w["fire"]["passed"] == w["fire"]["total"] and w["clean"]["passed"] == w["clean"]["total"]
                                  and w["growth"]["passed"] == w["growth"]["total"] and w["tp"]["passed"] == w["tp"]["total"]}
    v["all_primary_pass"] = all(v[k]["pass"] for k in ("corpus_a_worker07", "labeled16", "corpus_d_v1",
                                                       "corpus_d_v2", "corpus_d_v3", "corpus_e_worker035"))
    v["all_pass_including_secondary"] = v["all_primary_pass"] and v["w098_controls"]["pass"]
    return v


def main():
    cand_path = Path(sys.argv[1]).resolve()
    out_path = Path(sys.argv[2]).resolve()
    pins = check_pins()
    mod = load_module(cand_path)
    res = {
        "candidate": str(cand_path),
        "candidate_sha256": sha(cand_path),
        "pins": pins,
        "bar": CANONICAL_BAR,
        "corpus_a_worker07": worker07_regression(mod),
        "labeled16": labeled16(mod),
        "corpus_d_v1": worker049_corpus(mod, "corpus_d_v1"),
        "corpus_d_v2": worker049_corpus(mod, "corpus_d_v2"),
        "corpus_d_v3": worker049_corpus(mod, "corpus_d_v3"),
        "corpus_e_worker035": worker035(mod),
        "w098_controls": w098(mod),
    }
    res["verdict"] = build_verdict(res)
    out_path.write_text(json.dumps(res, indent=1))
    print(json.dumps(res["verdict"], indent=1))
    for k in ("corpus_a_worker07", "corpus_d_v1", "corpus_d_v2", "corpus_d_v3", "corpus_e_worker035"):
        c = res[k]
        if k == "corpus_a_worker07":
            bad = [r for r in c["rows"] if r["class"] in ("FN", "FP")]
            if bad:
                print(k, "MISMATCHES:", json.dumps(bad, indent=1)[:2000])
        elif k == "corpus_e_worker035":
            bad = [r for r in c["rows"] if not r["pass"]]
            if bad:
                print(k, "FAILS:", json.dumps(bad, indent=1))
        else:
            if c.get("cue_induced_fn_all") or c.get("mention_fp") or c.get("plain_positive_fn"):
                print(k, "cue_fn:", c.get("cue_induced_fn_all"), "mention_fp:", c.get("mention_fp"),
                      "plain_fn:", c.get("plain_positive_fn"))
    for kind in ("fire", "clean", "growth", "tp"):
        bad = [r for r in res["w098_controls"][kind]["rows"] if not r["pass"]]
        if bad:
            print("w098", kind, "FAILS:", json.dumps(bad, indent=1))
    return 0 if res["verdict"]["all_pass_including_secondary"] else 1


if __name__ == "__main__":
    sys.exit(main())
