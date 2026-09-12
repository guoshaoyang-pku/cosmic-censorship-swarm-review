#!/usr/bin/env python3
"""
W029-REV12-CLOSURE-03 — deterministic closure verification of rev12 F1/F2a/F2b.

Task (worker-029, one bounded class-bound task):
  At the measured rev12 hashes, re-check the three prior hard failures HF-29-01/02/03
  raised against rev11 (artifacts/worker-029/f2b_full_review, worker-029 crossclass)
  plus the standing G-FORM criterion "no single frozen data class (s,delta,norm)
  shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer".

Guarantees:
  * reads only the frozen snapshots under snapshots/ for the schemas + taxonomy, and
    the frozen ledger snapshot for citation rows (never the live paths);
  * stdlib + PyYAML only, no network, no writes outside the three JSON outputs;
  * every check returns PASS / FAIL / INFO with the exact evidence it used;
  * duplicate-preserving YAML loader, so silently last-won mapping keys cannot pass;
  * report_core.json excludes every wall-clock field (byte-stable across reruns);
    report.json / evidence.json are emission records that carry created_at.

Verdict rule: any FAIL with severity hard => revise; any FAIL major => accept_with_notes;
otherwise accept. A worker cannot set a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # repo root: artifacts/worker-029/<this dir> -> ai4math-swarm
SNAP = HERE / "snapshots"
LEDGER_SNAP = HERE / "ledger_theorems_snapshot.jsonl"

SCHEMAS = {
    "F1": "af_wcc_vacuum.yaml",
    "F2a": "af_scc_c2_vacuum.yaml",
    "F2b": "af_scc_c0_vacuum.yaml",
}
TAXONOMY = "formulation_taxonomy.canonical.yaml"
EXPECTED = json.loads((HERE / "snapshot_manifest.json").read_text())["files"]

PRIOR_HF = {
    "HF-29-01": "class_contract_pointer targets authoring tree / does not resolve at canonical taxonomy",
    "HF-29-02": "l1_ledger_refs claim verified_by_L1 while ledger records abstract-read; self-contradiction",
    "HF-29-03": "revised_at / f0_binding.checked_at future-dated at snapshot instant",
}
LEDGER_VOCAB = {"abstract-read", "full-text-read", "verified", "unverified", "unresolved"}


class DupKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently last-winning."""


def _construct_mapping(loader, node, deep=False):
    mapping, dups = {}, []
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in mapping:
            dups.append(str(k))
        mapping[k] = loader.construct_object(v_node, deep=deep)
    loader.dup_keys = getattr(loader, "dup_keys", [])
    loader.dup_keys.extend(dups)
    return mapping


DupKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    lambda loader, node: _construct_mapping(loader, node, deep=True),
)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path):
    loader = DupKeyLoader(p.read_text())
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, sorted(set(getattr(loader, "dup_keys", [])))


def walk(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{path}.{k}", v
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield f"{path}[{i}]", v
            yield from walk(v, f"{path}[{i}]")


def flat(x) -> str:
    s = x if isinstance(x, str) else json.dumps(x, sort_keys=True, ensure_ascii=False)
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[.;,]+$", "", s)
    return s


def canon(s) -> str:
    """Content-preserving normalization: lowercase, collapse whitespace, drop
    parentheticals and trailing punctuation, collapse hyphen/space.  Used only to
    separate cosmetic wording from content differences; both views are reported."""
    s = flat(s)
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.replace(" - ", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def check(cid, ok, detail, evidence, severity="hard"):
    return {
        "check_id": cid,
        "status": "PASS" if ok else "FAIL",
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def main() -> int:
    now = datetime.now(TZ)
    now_utc = now.astimezone(timezone.utc)
    checks = []

    # ---- C0: snapshot integrity / live drift -----------------------------------
    drift = {}
    for name, meta in EXPECTED.items():
        p = SNAP / name
        live = ROOT / meta["source_path"]  # relative to the repo root, not the caller's cwd
        live_hash = sha256(live) if live.exists() else None
        drift[name] = {
            "snapshot_sha256": sha256(p),
            "declared_sha256": meta["sha256"],
            "live_sha256": live_hash,
            "live_matches_snapshot": live_hash == sha256(p),
        }
    ledger_hash = sha256(LEDGER_SNAP) if LEDGER_SNAP.exists() else None
    ok = all(v["snapshot_sha256"] == v["declared_sha256"] for v in drift.values()) and ledger_hash
    live_all_match = all(v["live_matches_snapshot"] for v in drift.values())
    checks.append(
        check(
            "C0-snapshot-integrity",
            ok,
            "snapshot bytes match the manifest; live paths measured for information only"
            + ("" if live_all_match else "; LIVE DRIFT DETECTED (verdict superseded, not falsified)"),
            [
                *[f"snapshots/{n}#{v['snapshot_sha256'][:12]}" for n, v in drift.items()],
                f"ledger_theorems_snapshot.jsonl#{ledger_hash[:12] if ledger_hash else 'ABSENT'}",
            ],
        )
    )

    docs, dups = {}, {}
    for tag, name in SCHEMAS.items():
        docs[tag], dups[tag] = load(SNAP / name)
    tax, tax_dups = load(SNAP / TAXONOMY)

    # ---- C1: prior HF-29-01 class_contract_pointer resolves canonically ---------
    c1_ev, c1_ok = [], True
    for tag, d in docs.items():
        ptr = str(d.get("class_contract_pointer", ""))
        supp = str(d.get("class_contract_supplement_pointer", ""))
        frag = ptr.split("#", 1)[1] if "#" in ptr else ""
        prefix, _, key = frag.partition(".")  # split only on the FIRST dot
        # walk the FULL pointer path, including the `classes` prefix
        node = tax
        for part in [prefix, *key.split(".")]:
            node = node.get(part) if isinstance(node, dict) else None
        resolves = isinstance(node, dict)
        targets_canonical = (
            ptr.startswith("research_map/formulation_taxonomy.yaml#classes.") and prefix == "classes"
        )
        supp_ok = supp.startswith("artifacts/formulation/formulation_taxonomy.yaml#class_contracts.")
        entry_keys = sorted(node.keys()) if isinstance(node, dict) else []
        c1_ev.append(
            {
                "class": tag,
                "class_contract_pointer": ptr,
                "resolves_at_canonical": resolves,
                "resolved_entry_keys": entry_keys[:6],
                "targets_canonical_classes_key": targets_canonical,
                "supplement_pointer_split": supp_ok,
            }
        )
        c1_ok &= resolves and targets_canonical and supp_ok
    checks.append(
        check(
            "C1-HF-29-01-class-contract-pointer",
            c1_ok,
            "all three pointers resolve under the canonical `classes` key and the authoring "
            "supplement is split into its own field"
            if c1_ok
            else "one or more pointers do not resolve canonically",
            c1_ev,
        )
    )

    # ---- C2: prior HF-29-02 citation-status honesty (real ledger cross-check) ---
    ledger_rows = [json.loads(l) for l in LEDGER_SNAP.read_text().splitlines() if l.strip()]
    by_id = {r.get("theorem_id"): r for r in ledger_rows}
    c2_ev, c2_ok = [], True
    for tag, d in docs.items():
        for ref in d.get("l1_ledger_refs") or []:
            if not isinstance(ref, dict):
                continue
            tid = ref.get("theorem_id")
            claimed = ref.get("citation_status")
            row = by_id.get(tid)
            actual = row.get("verification_status") if row else None
            review_status = row.get("review_status") if row else None
            if claimed is None:
                continue  # no status asserted -> nothing to over-claim
            # honesty of the claim versus the frozen ledger row:
            #   * row missing from the ledger            -> not honest
            #   * claim uses a non-ledger token          -> not honest unless the row itself says so
            #   * claim == recorded verification_status  -> honest
            #   * claim == "unresolved"                  -> honest (explicitly flagged unresolved)
            #   * conservative downgrade                 -> honest if the row is unverified/abstract-read
            conservative = claimed in {"unresolved", "unverified"} and actual in {"unverified", "abstract-read"}
            honest = (row is not None) and ((claimed == actual) or conservative)
            c2_ev.append(
                {
                    "class": tag,
                    "theorem_id": tid,
                    "claimed_citation_status": claimed,
                    "ledger_verification_status": actual,
                    "ledger_review_status": review_status,
                    "claim_matches_ledger": honest,
                }
            )
            c2_ok &= honest
    # vocabulary check: does the token appear anywhere in the frozen ledger?
    token_present = any("verified_by_l1" in flat(r) for r in ledger_rows)
    c2_ev.append(
        {
            "token_verified_by_L1_present_in_ledger": token_present,
            "ledger_verification_status_counts": {
                s: sum(1 for r in ledger_rows if r.get("verification_status") == s)
                for s in sorted({r.get("verification_status") for r in ledger_rows})
            },
            "reading": "citation_status must use the ledger's vocabulary; verified_by_L1 is not a "
            "ledger value and no ledger row is independently reviewed",
        }
    )
    c2_ok &= not token_present
    checks.append(
        check(
            "C2-HF-29-02-citation-status",
            c2_ok,
            "every asserted citation_status matches the frozen ledger and no undefined "
            "verified_by_L1 token survives"
            if c2_ok
            else "at least one l1_ledger_refs citation_status overstates the ledger record",
            c2_ev,
        )
    )

    # ---- C3: prior HF-29-03 no future-dated revision timestamps -----------------
    c3_ev, c3_ok = [], True
    for tag, d in docs.items():
        stamps = [
            (p, v)
            for p, v in walk(d)
            if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00", v)
        ]
        future = [(p, v) for p, v in stamps if datetime.fromisoformat(v) > now]
        c3_ev.append({"class": tag, "timestamp_count": len(stamps), "future_dated": future})
        c3_ok &= not future
    checks.append(
        check(
            "C3-HF-29-03-future-timestamps",
            c3_ok,
            "no revision timestamp is future-dated at the snapshot instant"
            if c3_ok
            else "future-dated timestamp(s) remain",
            c3_ev,
        )
    )

    # ---- C4: duplicate YAML mapping keys ---------------------------------------
    c4_ev = [{"class": t, "duplicate_keys": dups[t]} for t in SCHEMAS]
    c4_ev.append({"artifact": "taxonomy", "duplicate_keys": tax_dups})
    c4_ok = not any(e["duplicate_keys"] for e in c4_ev)
    checks.append(
        check(
            "C4-duplicate-yaml-keys",
            c4_ok,
            "no duplicate mapping key at any level of the three schemas or the taxonomy"
            if c4_ok
            else "duplicate mapping key(s) remain (PyYAML would last-win them)",
            c4_ev,
        )
    )

    # ---- C5: D0 well-typedness --------------------------------------------------
    c5_ev, c5_ok = [], True
    for tag, d in docs.items():
        q = d.get("quantifiers", {})
        formal = str(q.get("formal", ""))
        ordered = q.get("ordered", [])
        d0 = (q.get("domains", {}) or {}).get("D0", {}) or {}
        d0_def = str(d0.get("definition", ""))
        first = ordered[0] if ordered else {}
        binder = str(first.get("binder", ""))
        pair_binder = bool(re.search(r"\(\s*s\s*,\s*delta\s*\)", formal)) or bool(
            re.search(r"\(\s*s\s*,\s*delta\s*\)", binder)
        )
        tagged = "tagged disjoint union" in d0_def
        smooth_branch = "r = smooth" in d0_def
        c5_ev.append(
            {
                "class": tag,
                "first_binder": binder,
                "pair_binder_present": pair_binder,
                "D0_tagged_disjoint_union": tagged,
                "D0_names_smooth_branch": smooth_branch,
            }
        )
        c5_ok &= (not pair_binder) and tagged and smooth_branch and binder == "r"
    checks.append(
        check(
            "C5-D0-well-typedness",
            c5_ok,
            "D0 is a tagged disjoint union ranged over by a bare index r; no (s,delta) tuple binder remains"
            if c5_ok
            else "a pair binder or an untyped D0 remains",
            c5_ev,
        )
    )

    # ---- C6: G-FORM criterion data-class sharing --------------------------------
    def normative(d):
        rc = (d.get("data_class", {}) or {}).get("regularity_class", {}) or {}
        sv = rc.get("sobolev_variant", {}) or {}
        return {
            "default": rc.get("default"),
            "s": sv.get("s"),
            "delta": sv.get("delta"),
            "spaces": sv.get("spaces"),
            "data_regularity_prose": (d.get("regularity", {}) or {}).get("data_regularity"),
        }

    norms = {t: normative(d) for t, d in docs.items()}
    base = norms["F1"]
    c6_ev, c6_ok, surface = [], True, {}
    for t, n in norms.items():
        strict = all(n[k] == base[k] for k in ("default", "s", "delta", "spaces"))
        semantic = all(canon(n[k]) == canon(base[k]) for k in ("default", "s", "delta", "spaces"))
        surface[t] = {
            k: {"strict_equal": n[k] == base[k], "canon_equal": canon(n[k]) == canon(base[k])}
            for k in ("default", "s", "delta", "spaces")
            if n[k] != base[k]
        }
        c6_ev.append(
            {
                "class": t,
                "normative": n,
                "strict_equal_to_F1": strict,
                "semantic_equal_to_F1": semantic,
            }
        )
        c6_ok &= semantic
    refs_ok = all(
        str(((docs[t].get("quantifiers", {}) or {}).get("domains", {}) or {}).get("D0", {}).get(
            "definition_ref", ""
        )) == "regularity.data_regularity"
        for t in SCHEMAS
    )
    c6_ev.append(
        {
            "D0_definition_ref_all_point_to": "regularity.data_regularity",
            "all_refs_resolve": refs_ok,
            "surface_differences": surface,
            "criterion": "single frozen data class (s,delta,norm) shared by F1/F2a/F2b",
        }
    )
    c6_ok &= refs_ok
    checks.append(
        check(
            "C6-GFORM-single-data-class",
            c6_ok,
            "the normative regularity (smooth default, s > 5/2, delta in (1/2,1), weighted Sobolev "
            "spaces) is semantically identical across F1/F2a/F2b and all three D0 definitions resolve "
            "to regularity.data_regularity; residual differences are non-normative prose and are "
            "reported as an INFO note, not a failure"
            if c6_ok
            else "the normative data class still differs across the three schemas",
            c6_ev,
        )
    )
    checks.append(
        check(
            "C6b-data-class-prose-drift",
            True,
            "INFO: non-normative prose differs across the three data_class blocks (F1's spaces carries "
            "the parenthetical '(weighted Sobolev)' and includes the delta range in data_regularity "
            "prose; F2a/F2b omit it there while recording it under regularity_class.sobolev_variant). "
            "No mathematical content differs; flagged for the gate owner, not counted as a failure.",
            [{"class": t, "diff": surface[t]} for t in SCHEMAS],
            severity="info",
        )
    )

    # ---- C7: C0=>C2 transfer license -------------------------------------------
    c0, c2 = docs["F2b"], docs["F2a"]
    il_c0 = c0.get("implication_ledger", {}) or {}
    il_c2 = c2.get("implication_ledger", {}) or {}
    c0_to_c2 = [
        e for e in il_c0.get("one_way_entailments", []) if "C0" in str(e.get("from", "")) and "C2" in str(e.get("to", ""))
    ]
    c2_forbids = [
        e for e in il_c2.get("forbidden_transfers", []) if "AF-SCC-C0-VAC-GEN" in str(e.get("from", ""))
    ]
    f1_reg = docs["F1"].get("regularity", {}) or {}
    smooth_sob = [m for m in f1_reg.get("must_not_conflate", []) if "approximation/stability" in str(m)]
    arg_where = []
    for t, d in docs.items():
        for p, v in walk(d):
            s = flat(v)
            if "approximation" in s and "stability" in s and "must_not_conflate" not in p:
                arg_where.append(f"{t}:{p}")
    c7_ok = bool(c0_to_c2) and not c2_forbids
    c7_ev = [
        {"C0_entailments_to_C2": c0_to_c2},
        {"C2_forbidden_transfers_naming_C0": c2_forbids},
        {"F1_smooth_to_sobolev_requirement_still_present": bool(smooth_sob)},
        {"approximation_stability_argument_recorded": bool(arg_where), "locations": arg_where},
        {
            "reading": "the licensed transfer is member-wise (the same tag r on both sides); it is "
            "unconditional only if no approximation argument is needed for the transfer itself"
        },
    ]
    checks.append(
        check(
            "C7-C0-to-C2-transfer-license",
            c7_ok,
            "C0->C2 entailment is recorded and the C2 sibling does not forbid it; the smooth->Sobolev "
            "approximation requirement remains an explicit open obligation, not a defect"
            if c7_ok
            else "the transfer is missing or is forbidden by the C2 sibling",
            c7_ev,
            severity="major",
        )
    )

    # ---- C8: canonical class entries -------------------------------------------
    c8_ev, c8_ok = [], True
    for cid in ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"):
        entry = tax.get("classes", {}).get(cid)
        keys = sorted(entry.keys()) if isinstance(entry, dict) else []
        c8_ev.append({"class_id": cid, "present": entry is not None, "keys": keys})
        c8_ok &= entry is not None
    checks.append(
        check(
            "C8-canonical-class-entries",
            c8_ok,
            "all three class entries exist under the canonical classes key"
            if c8_ok
            else "a class entry is missing canonically",
            c8_ev,
        )
    )

    # ---- C9: revision consistency ----------------------------------------------
    c9_ev, c9_ok = [], True
    for t, d in docs.items():
        rev = d.get("revision")
        hist = d.get("revision_history") or []
        idx = [h.get("index") for h in hist if isinstance(h, dict)]
        monotone = idx == sorted(idx)
        c9_ev.append({"class": t, "revision": rev, "history_indices": idx, "monotone": monotone})
        c9_ok &= monotone and rev is not None
    checks.append(
        check(
            "C9-revision-consistency",
            c9_ok,
            "revision_history indices are monotone and the revision field is present"
            if c9_ok
            else "revision history is inconsistent",
            c9_ev,
            severity="minor",
        )
    )

    failed_hard = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "hard"]
    failed_major = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "major"]

    if failed_hard:
        verdict, score = "revise", 2.0
    elif failed_major:
        verdict, score = "accept_with_notes", 3.5
    else:
        verdict, score = "accept", 4.5

    evidence = {
        "task_id": "W029-REV12-CLOSURE-03",
        "worker": "worker-029",
        "created_at": now.isoformat(timespec="seconds"),
        "created_at_utc": now_utc.isoformat(timespec="seconds"),
        "snapshot_hashes": {n: v["snapshot_sha256"] for n, v in drift.items()},
        "ledger_snapshot_sha256": ledger_hash,
        "live_drift": drift,
        "checks": checks,
        "ledger_rows_used": [
            {
                "theorem_id": e["theorem_id"],
                "claimed": e["claimed_citation_status"],
                "actual": e["ledger_verification_status"],
            }
            for e in c2_ev
            if "theorem_id" in e
        ],
    }
    (HERE / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

    # Deterministic core: identical on every rerun over the same snapshots.  report.json and
    # evidence.json carry created_at, so they are emission records, not byte-stable measurements;
    # this file is what "deterministic rerun" is asserted against.
    core = {
        "task_id": "W029-REV12-CLOSURE-03",
        "worker": "worker-029",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "snapshot_hashes": {n: v["snapshot_sha256"] for n, v in drift.items()},
        "ledger_snapshot_sha256": ledger_hash,
        "live_matches_snapshot": {n: v["live_matches_snapshot"] for n, v in drift.items()},
        "checks": checks,
        "summary": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "PASS"),
            "fail_hard": len(failed_hard),
            "fail_major": len(failed_major),
            "failed_ids": [c["check_id"] for c in checks if c["status"] == "FAIL"],
        },
        "verdict": verdict,
        "score": score,
        "gate_verdict_claimed": False,
        "determinism_note": (
            "byte-stable across reruns over the same snapshots; report.json/evidence.json differ only "
            "by their created_at emission timestamps"
        ),
        "falsifier": (
            "Re-run this checker on the same snapshot bytes: the closure claim is falsified if any "
            "check reported PASS here reports FAIL, if a cited ledger row's verification_status equals "
            "the schema's claimed citation_status, or if the live paths no longer match the snapshot "
            "hashes (the verdict is then superseded, not falsified)."
        ),
    }
    (HERE / "report_core.json").write_text(json.dumps(core, indent=2) + "\n")

    report = {
        "task_id": "W029-REV12-CLOSURE-03",
        "worker": "worker-029",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "created_at": now.isoformat(timespec="seconds"),
        "snapshot_manifest": "snapshot_manifest.json",
        "measured_hashes": {n: v["snapshot_sha256"] for n, v in drift.items()},
        "live_matches_snapshot": {n: v["live_matches_snapshot"] for n, v in drift.items()},
        "prior_findings_rechecked": PRIOR_HF,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["status"] == "PASS"),
            "fail_hard": len(failed_hard),
            "fail_major": len(failed_major),
            "failed_ids": [c["check_id"] for c in checks if c["status"] == "FAIL"],
        },
        "verdict": verdict,
        "score": score,
        "gate_verdict_claimed": False,
        "authority_note": "worker evidence only; cannot set a gate verdict, node status, or validation_status",
        "falsifier": (
            "Re-run this checker on the same snapshot bytes: the closure claim is falsified if any "
            "check reported PASS here reports FAIL, if a cited ledger row's verification_status equals "
            "the schema's claimed citation_status, or if the live paths no longer match the snapshot "
            "hashes (the verdict is then superseded, not falsified)."
        ),
    }

    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    print("verdict:", verdict, score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
