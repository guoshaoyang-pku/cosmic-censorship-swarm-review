#!/usr/bin/env python3
"""Build REVIEW.json/.md, CHECKPOINT.json and SHA256SUMS.txt for W061-F1-VARSTRENGTH-05
from the probe output.  Deterministic; writes only inside the task directory."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


with open(os.path.join(HERE, "probe_output.json"), encoding="utf-8") as f:
    P = json.load(f)

PINS = {k: v["live_sha256"] for k, v in P["pins"].items()}

review = {
    "review_id": "W061-F1-VARSTRENGTH-05",
    "reviewer": "worker-061",
    "created_at": NOW,
    "node_id": "F1",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "target_id": "F1",
    "target_artifacts": {
        "schemas/af_wcc_vacuum.yaml": PINS["F1"],
        "schemas/af_scc_c0_vacuum.yaml": PINS["F2b"],
        "artifacts/formulation/VARIANT_REGISTRY.json": PINS["registry"],
        "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json": PINS["set_delta"],
        "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json": PINS["ch_delta"],
        "artifacts/formulation/FROZEN.json": PINS["frozen"],
    },
    "verdict": P["verdict"],
    "score": P["score"],
    "hard_failures": P["hard_failures"],
    "findings": P["findings"] + [
        "F-W061-VAR-05 (ESC-2 consequence): option (A) 'reconcile to one predicate' cannot be "
        "justified as 'the two readings are equivalent' - the omega chain refutes equivalence. "
        "Option (C) 'keep named variants' needs a two-level strength statement: the SET predicate is "
        "strictly weaker; the SET-variant negation is strictly stronger. Neither option is settled by "
        "this review; this review only fixes the direction at each level.",
        "F-W061-VAR-06 (independence): this review did not read reviews/*F1*, reviews/*F2b* or any "
        "other reviewer's verdict before writing; it did read worker-076's blocker event and the "
        "adjudicated F0 review finding flash-19 F0-19-04/05 (used only as prior-art citations, not "
        "reused text). The probe re-implements the semantics from the pinned definitions; no worker-076 "
        "code was executed or copied.",
    ],
    "assumptions": [
        "the pinned copies are byte-identical to the live canonical bytes at review time (all six pin checks true); any later byte change voids the verdict",
        "causal past J^-(q) is modelled as the downset of a preorder, and gamma is a future-directed chain; this is the order-theoretic content the definitions use",
        "the omega-chain model is an abstract causal-order countermodel; its realisability by an admissible asymptotically flat vacuum completion is NOT decided here (see falsifier (a))",
        "the review compares predicate labels and negation/class labels separately; it does not decide which convention the corpus should adopt",
    ],
    "falsifier": (
        "On the pins F1 cce9c60146d6 / F2b 55d0a1ea9bda / registry 5eb42f9a384a / SET delta "
        "45b9b6a8d192 / CH delta c28795b0fdfc, this revise is falsified by any one of: (a) a proof "
        "that in every admissible asymptotically flat completion the family of witnessing points on "
        "I+ is down-directed (then S => T and the omega certificate is inadmissible, making the two "
        "readings equivalent); (b) a canonical convention, recorded elsewhere in the frozen corpus or "
        "by controller decision, under which 'X is strictly stronger than predicate P' means 'the "
        "negation of X is stronger than the negation of P' - under that convention F1:234 is "
        "consistent and only the delta's 'implied by, and strictly stronger than' remains a defect; "
        "(c) the labels being repaired to an explicit two-level statement, which resolves HF-01/02 "
        "without changing either direction."
    ),
    "next_falsifier": (
        "Re-measure all six pinned files. Any change voids this verdict. If the repair lands, re-run "
        "probe_variant_strength.py against the new bytes: the SET predicate label must read weaker "
        "(or state both levels), the SET negation/class label must stay stronger, the CH label must "
        "stay weaker, and the delta must no longer contain both 'implied by' and 'strictly stronger' "
        "about the same predicate."
    ),
    "evidence": {
        "probe_output": "probe_output.json",
        "probe_script": "probe_variant_strength.py",
        "pinned_copies": sorted(os.listdir(os.path.join(HERE, "pinned"))),
        "finite_corpus": P["finite_corpus"],
        "omega_certificate": P["omega_certificate"],
        "controls": P["control_summary"],
    },
    "authority": "worker evidence only: no gate verdict, no node status, no validation_status promotion",
}

with open(os.path.join(HERE, "REVIEW.json"), "w", encoding="utf-8") as f:
    json.dump(review, f, indent=2)
    f.write("\n")

md = []
md.append("# W061-F1-VARSTRENGTH-05 — independent variant strictness-direction adjudication\n")
md.append(f"- worker: worker-061\n- created_at: {NOW}\n- node: F1 (primary AF-WCC-VAC-GEN); F2b CH secondary (AF-SCC-C0-VAC-GEN)\n- gate: G-FORM\n")
md.append(f"\n## Verdict: **revise** (score {P['score']})\n")
md.append("\n## Hard failures\n")
for hf in review["hard_failures"]:
    md.append(f"- {hf}\n")
md.append("\n## Findings\n")
for i, fd in enumerate(review["findings"], 1):
    md.append(f"{i}. {fd}\n")
md.append("\n## Machine checks\n")
md.append(f"- finite corpus: {P['finite_corpus']['models']} preorders, {P['finite_corpus']['cases']} cases, "
          f"T=>S violations {P['finite_corpus']['T_and_not_S']}, S=>T violations {P['finite_corpus']['S_and_not_T']}\n")
md.append(f"- omega chain: S={P['omega_certificate']['S_on_gamma']}, T={P['omega_certificate']['T_on_gamma']}, "
          f"escape certificate {P['omega_certificate']['escape_certificate_pairs_checked']} pairs all hold "
          f"= {P['omega_certificate']['escape_certificate_all_hold']}\n")
md.append(f"- controls: {P['control_summary']['n']} mutants, all detectors fired = {P['control_summary']['all_ok']}\n")
md.append("\n## Pins\n")
for k, v in P["pins"].items():
    md.append(f"- `{v['path']}` = `{v['live_sha256']}` (pin matches live: {v['pin_matches_live']})\n")
md.append(f"\n## Falsifier\n{review['falsifier']}\n")
md.append("\n## Authority\nWorker evidence only. No gate verdict, node status or validation_status is claimed.\n")
with open(os.path.join(HERE, "REVIEW.md"), "w", encoding="utf-8") as f:
    f.write("".join(md))

# --- checkpoint + sums --------------------------------------------------------------
artifacts = [
    ("probe_variant_strength.py", "rerunnable_probe"),
    ("probe_output.json", "machine_probe_output"),
    ("build_review.py", "artifact_builder"),
    ("REVIEW.json", "independent_review_json"),
    ("REVIEW.md", "independent_review_markdown"),
]
for name in sorted(os.listdir(os.path.join(HERE, "pinned"))):
    artifacts.append((os.path.join("pinned", name), "pinned_source_copy"))

entries = []
for rel, role in artifacts:
    p = os.path.join(HERE, rel)
    entries.append({"path": f"artifacts/worker-061/f1_variant_strength/{rel}",
                    "role": role, "sha256": sha256(p)})

checkpoint = {
    "checkpoint_id": "w061-f1-variant-strength-20260912",
    "task_id": "W061-F1-VARSTRENGTH-05",
    "worker": "worker-061",
    "created_at": NOW,
    "pins": PINS,
    "verdict": P["verdict"],
    "score": P["score"],
    "hard_failures": len(P["hard_failures"]),
    "controls_all_ok": P["control_summary"]["all_ok"],
    "artifacts": entries,
    "authority": "worker evidence only",
}
with open(os.path.join(HERE, "CHECKPOINT.json"), "w", encoding="utf-8") as f:
    json.dump(checkpoint, f, indent=2)
    f.write("\n")

all_files = sorted(set([rel for rel, _ in artifacts] + ["CHECKPOINT.json", "SHA256SUMS.txt"]))
lines = []
for rel in all_files:
    p = os.path.join(HERE, rel)
    if rel == "SHA256SUMS.txt":
        continue
    lines.append(f"{sha256(p)}  {rel}")
with open(os.path.join(HERE, "SHA256SUMS.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(json.dumps({"review": os.path.join(HERE, "REVIEW.json"),
                  "checkpoint": os.path.join(HERE, "CHECKPOINT.json"),
                  "artifacts": len(entries)}, indent=1))
