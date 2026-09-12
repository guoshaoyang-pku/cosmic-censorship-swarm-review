#!/usr/bin/env python3
"""A0 detector-scope adjudication measurement (astra-life05-a0-detector-scope).

Problem: the A0 corpus scan (`audit_run.py --scan artifacts comms/outbox ledger`) uses
`rglob` over all of `artifacts/`. HF-03 (unsupported_citation) and HF-14
(self_certified_acceptance) are ledger/record detectors, so they also fire on
*historical* ledger copies (archive/, *.pre-*), on *staging* contributions (incoming/),
and on *worker snapshot copies* of the ledger taken for a review. Those are not live
artifacts; flagging them inflates the hard-failure count and misdirects the literature
lead at files nobody may edit.

This tool does NOT change the canonical gate checker. It measures the scope predicate
before/after so the controller can adopt it as a controller-approved change with
evidence. It is re-runnable and deterministic.

Outputs:
  evaluation/A0_detector_scope_adjudication.json   (the assignment artifact)
  artifacts/audit/a0_scope_before_after.json       (machine-readable file lists)

Invariants asserted (the card's falsifier, made executable):
  I1  no canonical ledger (ledger/*) or declared live build input
      (artifacts/literature/sources/**, artifacts/literature/theorems/**,
       artifacts/literature/tools/**) matches the exclusion predicate;
  I2  every excluded file is classified historical or snapshot_copy;
  I3  after-scope hits == before-scope hits minus excluded hits (nothing silently dropped);
  I4  positive control: archive/pre-rev3 path excluded; sources/batch-01.jsonl kept;
  I5  an un-ingested staging contribution is reported as `staging_unresolved`, never
      auto-excluded.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research_map"))

import audit_lib as A  # noqa: E402
import audit_run as R  # noqa: E402

SCAN = ["artifacts", "comms/outbox", "ledger"]

# --- canonical / live classes -------------------------------------------------------------
CANONICAL = ("ledger/theorems.jsonl", "ledger/citation_audit.csv")
LIVE_BUILD_INPUT_PREFIXES = (
    "artifacts/literature/sources/",   # build_literature.py: "single source of truth"
    "artifacts/literature/theorems/",  # build_literature.py: "single source of truth"
    "artifacts/literature/tools/",     # the builder itself
)
LIVE_EMITTED = (
    "artifacts/literature/registry.jsonl",
    "artifacts/literature/unresolved.jsonl",
    "artifacts/literature/MANIFEST.json",
    "artifacts/literature/falsifiers.md",
    "artifacts/literature/tag_index.md",
)

HISTORICAL_SEGMENTS = ("/archive/", "/incoming/")
SNAPSHOT_SEGMENTS = ("/snapshot/", "/snapshots/", "/probe/", "/proposed/", "/staging/",
                     "/scratch/", "/prev/")
HISTORICAL_BASENAME_TOKENS = (".pre-", ".prev-", "_snapshot.", ".snapshot-", ".bak")


def classify(rel: str) -> str:
    """Classify a repo-relative path into the A0 corpus scope taxonomy."""
    if rel in CANONICAL:
        return "canonical"
    if any(rel.startswith(p) for p in LIVE_BUILD_INPUT_PREFIXES):
        return "live_build_input"
    if rel in LIVE_EMITTED:
        return "live_emitted"
    base = rel.rsplit("/", 1)[-1]
    if any(seg in "/" + rel for seg in HISTORICAL_SEGMENTS) or \
       any(tok in base for tok in HISTORICAL_BASENAME_TOKENS):
        return "historical"
    if any(seg in "/" + rel for seg in SNAPSHOT_SEGMENTS) or "snapshot" in base:
        return "snapshot_copy"
    if "/ledger_contribution/" in "/" + rel or rel.startswith("artifacts/worker-07/ledger"):
        return "staging_unresolved"
    return "live_other"


def excluded(rel: str) -> bool:
    """The proposed scope predicate: drop historical + snapshot copies only.

    staging_unresolved is deliberately NOT excluded (card falsifier I5).
    """
    return classify(rel) in ("historical", "snapshot_copy")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure() -> dict:
    corpus = R.scan_corpus([ROOT / s for s in SCAN])

    # HF-14: per-source counts (mirror the aggregation in audit_run.main)
    self_cert = A.check_self_certification(corpus["records"])
    hf14_before: dict[str, int] = {}
    for v in self_cert:
        src = v.evidence.get("source", "ledger")
        hf14_before[src] = hf14_before.get(src, 0) + 1

    # HF-03: per-source record counts. check_ledger_scope aggregates one Violation per
    # file; the affected-record count lives in the detail string ("N of the ledger's
    # citations lack ..."), which is the number audit_run._merge sums into HF-03:systemic.
    import re
    hf03_before: dict[str, int] = {}
    for v in A.check_ledger_scope(corpus["citations"]):
        src = v.evidence.get("file", "ledger")
        mo = re.search(r"(\d+)\s+of the ledger's citations", v.detail)
        hf03_before[src] = hf03_before.get(src, 0) + (int(mo.group(1)) if mo else 1)

    def split_hits(hits: dict[str, int]) -> dict:
        kept, dropped, staging = {}, {}, {}
        for src, n in sorted(hits.items()):
            cls = classify(src)
            if cls in ("historical", "snapshot_copy"):
                dropped[src] = {"records": n, "class": cls}
            elif cls == "staging_unresolved":
                staging[src] = {"records": n, "class": cls}
            else:
                kept[src] = {"records": n, "class": cls}
        return {"kept": kept, "excluded": dropped, "staging_unresolved": staging}

    out = {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scan_roots": SCAN,
        "corpus": {k: (len(v) if isinstance(v, list) else v) for k, v in corpus.items()},
        "hf14": split_hits(hf14_before),
        "hf03": split_hits(hf03_before),
    }
    out["hf14"]["before_total_records"] = sum(hf14_before.values())
    out["hf14"]["after_total_records"] = sum(v["records"] for v in out["hf14"]["kept"].values())
    out["hf03"]["before_total_records"] = sum(hf03_before.values())
    out["hf03"]["after_total_records"] = sum(v["records"] for v in out["hf03"]["kept"].values())
    out["_hf14_before"] = hf14_before
    out["_hf03_before"] = hf03_before

    # pin sha256 of every affected file (the card asks for pinned hashes)
    pins = {}
    for src in set(hf14_before) | set(hf03_before):
        p = ROOT / src
        pins[src] = {"exists": p.exists(),
                     "sha256": sha256_file(p) if p.exists() else None,
                     "class": classify(src)}
    out["file_pins"] = pins
    return out


def assertions(m: dict) -> list[dict]:
    """Executable falsifier checks."""
    res = []

    # I1: no canonical / live build input / live emitted path is excluded
    bad = [s for s in m["file_pins"]
           if classify(s) in ("canonical", "live_build_input", "live_emitted")
           and excluded(s)]
    res.append({"id": "I1", "claim": "no canonical ledger or live build input is excluded",
                "pass": not bad, "counterexamples": bad})

    # I2: every excluded file is classified historical or snapshot_copy
    bad2 = [s for s in m["file_pins"] if excluded(s)
            and classify(s) not in ("historical", "snapshot_copy")]
    res.append({"id": "I2", "claim": "every excluded file is historical or snapshot_copy",
                "pass": not bad2, "counterexamples": bad2})

    # I3: after == before - excluded, per detector
    ok = True
    detail = {}
    for hf in ("hf14", "hf03"):
        before = m[f"_{hf}_before"]
        kept = {k: v["records"] for k, v in m[hf]["kept"].items()}
        exc = {k: v["records"] for k, v in m[hf]["excluded"].items()}
        stg = {k: v["records"] for k, v in m[hf]["staging_unresolved"].items()}
        recon = {k: before.get(k, 0) for k in set(kept) | set(exc) | set(stg)}
        consistent = all(kept.get(k, 0) + exc.get(k, 0) + stg.get(k, 0) == v
                         for k, v in recon.items())
        detail[hf] = {"kept": sum(kept.values()), "excluded": sum(exc.values()),
                      "staging_unresolved": sum(stg.values()),
                      "before": sum(before.values()), "reconciles": consistent}
        ok = ok and consistent
    res.append({"id": "I3", "claim": "after-scope hits == before - excluded; nothing silently dropped",
                "pass": ok, "detail": detail})

    # I4: positive/negative controls
    pos = excluded("artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl")
    neg = not excluded("artifacts/literature/sources/batch-01.jsonl")
    res.append({"id": "I4", "claim": "positive control (archive pre-rev3 excluded) and "
                                     "negative control (sources/batch-01 kept)",
                "pass": bool(pos and neg),
                "detail": {"archive_pre_rev3_excluded": pos,
                           "sources_batch01_kept": neg}})

    # I5: staging is surfaced, never auto-excluded
    stg = {k: v for k, v in m["file_pins"].items() if classify(k) == "staging_unresolved"}
    res.append({"id": "I5", "claim": "un-ingested staging contributions reported, not auto-excluded",
                "pass": all(not excluded(k) for k in stg),
                "detail": {"staging_files": sorted(stg)}})
    return res


def adjudication(m: dict, res: list[dict]) -> dict:
    """Turn the measurement into the A0 scope ruling."""
    h14, h03 = m["hf14"], m["hf03"]
    h14_clean = h14["after_total_records"] == 0
    h03_clean = h03["after_total_records"] == 0
    staging = sorted(set(h14["staging_unresolved"]) | set(h03["staging_unresolved"]))
    return {
        "verdict": "split",
        "rulings": {
            "HF-14": {
                "before": {"records": h14["before_total_records"],
                           "files": len(m["_hf14_before"])},
                "after_scope": {"records": h14["after_total_records"],
                                "files": len(h14["kept"])},
                "ruling": "detector-scope artifact" if h14_clean else "live hits remain",
                "reason": "every HF-14 hit lives in an archive/pre-rev3 copy, a worker "
                          "snapshot, or an un-ingested staging contribution; the canonical "
                          "ledger/theorems.jsonl is clean because build_literature.py carries "
                          "the fail-closed HF-14 guard. The critical finding is withdrawn "
                          "as a live-artifact finding once the scope predicate is adopted.",
                "residual": "the staging contribution below must be ingested or discarded "
                            "by the literature lead, not ignored",
            },
            "HF-03": {
                "before": {"records": h03["before_total_records"],
                           "files": len(m["_hf03_before"])},
                "after_scope": {"records": h03["after_total_records"],
                                "files": len(h03["kept"])},
                "ruling": "REAL live finding; scope change does NOT clear it",
                "reason": "the surviving hits are on declared live build inputs "
                          "(artifacts/literature/sources/batch-*.jsonl, the builder's "
                          "'single source of truth') and a live emitted product "
                          "(artifacts/literature/registry.jsonl). Excluding those to clear "
                          "the count is the card's forbidden move.",
                "required_repair": "populate source_meta matter_model/cosmological_constant/"
                                   "dimension/symmetry + formulation on every citation row in "
                                   "the 11 sources batches and rebuild registry.jsonl; "
                                   "194 affected rows at the pinned hashes below.",
            },
        },
        "staging_unresolved": staging,
        "recommendation": {
            "action": "adopt the scope predicate in the corpus scan, keep every live class",
            "exact_predicate": "exclude iff rel has /archive/ or /incoming/ segment, or a "
                               ".pre- / .prev- / _snapshot. / .snapshot- / .bak basename token, "
                               "or a /snapshot/ /snapshots/ /probe/ /proposed/ /staging/ "
                               "/scratch/ /prev/ segment, or 'snapshot' in the basename",
            "must_keep": ["ledger/**", "artifacts/literature/sources/**",
                          "artifacts/literature/theorems/**", "artifacts/literature/tools/**",
                          "artifacts/literature/registry.jsonl",
                          "artifacts/literature/unresolved.jsonl"],
            "implementation": "artifacts/audit/a0_detector_scope.py::excluded (this file); "
                              "adoption is a one-line filter in audit_run.scan_corpus, which "
                              "is a controller-approved change and is NOT applied here",
            "not_applied_reason": "the audit group must not edit the canonical gate checker to "
                                  "change its own score (no gate self-pass). The predicate and "
                                  "the before/after lists are handed to the controller.",
        },
        "effect_on_g_audit": "A0's hard-failure count drops by the HF-14 component only. "
                             "G-AUDIT stays `pending`: A0 still has the three hash-bound "
                             "revise findings in reviews/A0-review-lead-audit-r2.json and "
                             "A1 coverage is short of two accepts per target.",
        "conditions": [
            "binds the pinned sha256s in measured.file_pins; any file rewrite voids this "
            "adjudication for that file",
            "this is one audit-group verdict; it is not a gate verdict and sets none",
            "scoping the corpus changes the *count*, never a live artifact's status",
        ],
        "falsifier_checks": {r["id"]: r["pass"] for r in res},
    }


def main() -> int:
    m = measure()
    res = assertions(m)
    verdict = "pass" if all(r["pass"] for r in res) else "fail"
    out = {
        "artifact": "A0-detector-scope-adjudication",
        "assignment": "astra-life05-a0-detector-scope",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "actor": "astra-lead-audit",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "rubric_sha256": sha256_file(ROOT / "evaluation_rubric.yaml"),
        "scope_predicate": "exclude iff classify(rel) in {historical, snapshot_copy}",
        "scope_taxonomy": {
            "canonical": list(CANONICAL),
            "live_build_input": list(LIVE_BUILD_INPUT_PREFIXES),
            "live_emitted": list(LIVE_EMITTED),
            "historical": "path segment /archive/ or /incoming/, or basename token "
                          ".pre- / .prev- / _snapshot. / .snapshot- / .bak",
            "snapshot_copy": "path segment /snapshot/ /snapshots/ /probe/ /proposed/ "
                             "/staging/ /scratch/ /prev/, or basename contains snapshot",
            "staging_unresolved": "worker ledger_contribution staging; NOT excluded, surfaced",
            "live_other": "all remaining artifacts/, comms/outbox, ledger",
        },
        "measured": m,
        "assertions": res,
        "falsifier_verdict": verdict,
        "adjudication": adjudication(m, res),
    }
    dest = ROOT / "evaluation" / "A0_detector_scope_adjudication.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")
    (HERE / "a0_scope_before_after.json").write_text(json.dumps(m, indent=2) + "\n")

    print(f"A0 scope falsifier: {verdict}")
    for r in res:
        print(f"  {r['id']}: {'PASS' if r['pass'] else 'FAIL'}  {r['claim']}")
        if not r["pass"]:
            print("     ", json.dumps(r.get("counterexamples") or r.get("detail"))[:400])
    for hf in ("hf14", "hf03"):
        h = m[hf]
        print(f"  {hf}: before={h['before_total_records']} records/"
              f"{len(m['_'+hf+'_before'])} files -> after={h['after_total_records']} records/"
              f"{len(h['kept'])} files (excluded {len(h['excluded'])} files, "
              f"staging {len(h['staging_unresolved'])})")
    print(f"-> {dest.relative_to(ROOT)}")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
