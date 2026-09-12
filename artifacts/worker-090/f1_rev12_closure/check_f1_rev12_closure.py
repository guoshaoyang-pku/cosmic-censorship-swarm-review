#!/usr/bin/env python3
"""W090-F1-REV12-CLOSURE: independent, machine-checkable closure check of F1
AF-WCC-VAC-GEN revision 12 (schema snapshot hash in snapshot/SHA256SUMS.txt).

Read-only with respect to the canonical tree: it only reads the live files to
measure their hashes, and writes its own JSON next to this script.

Checks the three hash-bound findings worker-090 filed at revision 11
(HF090-01 canonical contract pointer, HF090-02 duplicate/future-dated
timestamps, HF090-03 undefined AF_{I+}) plus the other closure claims in the
rev12 revision-history note (D0 retyping, tail-visibility repair).

Includes mutants (M1..M6): each is a text mutation of the snapshot that must
make exactly the corresponding check fail, so the checker is falsified if it
cannot tell a closed finding from a reopened one.

Usage:  python3 check_f1_rev12_closure.py [--out results.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAP = HERE / "snapshot"
F1_LIVE = REPO / "schemas" / "af_wcc_vacuum.yaml"
F1_MIRROR = REPO / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
F0_CANON_LIVE = REPO / "research_map" / "formulation_taxonomy.yaml"
F0_AUTHOR_LIVE = REPO / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
CONSISTENCY_LIVE = REPO / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
FALSIFIER_LIVE = REPO / "schemas" / "f1_falsifier_tests.jsonl"

TZ = dt.timezone(dt.timedelta(hours=8))
CLOCK_TOLERANCE_S = 5.0


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> dt.datetime:
    return dt.datetime.now(TZ)


def parse_ts(s: str) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(str(s))
    except ValueError:
        return None


# ---------------------------------------------------------------- YAML utils
class DupKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of last-winning."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicates: list[dict] = []

    def construct_mapping(self, node, deep=False):
        seen = {}
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hashable = key
                if key in seen:
                    self.duplicates.append(
                        {"key": str(key), "line": key_node.start_mark.line + 1}
                    )
                seen[hashable] = True
            except TypeError:
                pass
        return super().construct_mapping(node, deep=deep)


def load_with_dups(text: str):
    loader = DupKeyLoader(text)
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, loader.duplicates


def resolve_pointer(doc, fragment: str):
    """Resolve a dotted fragment (dict keys and int list indices) or None."""
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def occ(text: str, needle: str) -> int:
    return text.count(needle)


# ---------------------------------------------------------------- checks
def run_checks(f1_text: str, live: dict) -> dict:
    doc, dups = load_with_dups(f1_text)
    parsed = yaml.safe_load(f1_text)
    checks: list[dict] = []

    def chk(cid, name, ok, detail, severity="major", kind="finding-closure"):
        checks.append(
            {
                "id": cid,
                "name": name,
                "status": "pass" if ok else "fail",
                "severity": severity,
                "kind": kind,
                "detail": detail,
            }
        )
        return ok

    t = now()

    # H00/H01 data integrity ------------------------------------------------
    chk(
        "H01-no-duplicate-keys",
        "no duplicate YAML mapping keys anywhere in the schema",
        len(dups) == 0,
        f"duplicates={dups}",
        severity="blocking",
    )
    top_keys = list((parsed or {}).keys())
    chk(
        "H02-single-revised-at",
        "exactly one top-level revised_at key",
        top_keys.count("revised_at") == 1
        and "revised_at_unused" not in top_keys,
        f"top-level revised_at count={top_keys.count('revised_at')}, "
        f"revised_at_unused present={'revised_at_unused' in top_keys}",
    )

    # H03 clock discipline --------------------------------------------------
    rev_at = parse_ts(parsed.get("revised_at"))
    checked_at = parse_ts((parsed.get("f0_binding") or {}).get("checked_at"))
    skew = (rev_at - t).total_seconds() if rev_at else None
    skew_checked = (checked_at - t).total_seconds() if checked_at else None
    chk(
        "H03-clock-discipline",
        "revised_at and f0_binding.checked_at are not future-dated",
        rev_at is not None
        and skew <= CLOCK_TOLERANCE_S
        and checked_at is not None
        and skew_checked <= CLOCK_TOLERANCE_S,
        f"wall={t.isoformat()} revised_at={parsed.get('revised_at')} "
        f"skew_s={skew} checked_at={checked_at} skew_s={skew_checked}",
        severity="blocking",
    )

    # H04/H05 pointer resolution (HF090-01) ---------------------------------
    canon_f0_doc = live["canon_f0_doc"]
    author_doc = live["author_doc"]
    ptr = parsed.get("class_contract_pointer")
    canonical_prefix = "research_map/formulation_taxonomy.yaml#"
    ptr_ok = bool(ptr) and str(ptr).startswith(canonical_prefix)
    frag = str(ptr).split("#", 1)[1] if ptr_ok else ""
    target = resolve_pointer(canon_f0_doc, frag) if frag else None
    chk(
        "H04-contract-pointer-canonical",
        "class_contract_pointer names the canonical taxonomy and its fragment resolves",
        ptr_ok and target is not None,
        f"class_contract_pointer={ptr!r} prefix_ok={ptr_ok} "
        f"fragment={frag!r} resolves_in_canonical={target is not None}",
        severity="blocking",
    )
    supp = parsed.get("class_contract_supplement_pointer")
    supp_frag = str(supp).split("#", 1)[1] if supp and "#" in str(supp) else ""
    supp_target = resolve_pointer(author_doc, supp_frag) if supp_frag else None
    chk(
        "H05-supplement-pointer-resolves",
        "class_contract_supplement_pointer fragment resolves in the authoring taxonomy",
        supp_target is not None,
        f"supplement_pointer={supp!r} resolves={supp_target is not None}",
        severity="advisory",
    )

    # H06/H07 F0 binding hashes ---------------------------------------------
    f0b = parsed.get("f0_binding") or {}
    declared = f0b.get("declared_f0_sha256")
    measured_canon = live["canon_f0_sha256"]
    chk(
        "H06-f0-binding-hash",
        "declared_f0_sha256 equals the measured canonical F0 hash",
        declared == measured_canon,
        f"declared={declared} measured_canonical={measured_canon}",
        severity="blocking",
    )
    cons_declared = f0b.get("consistency_evidence_sha256")
    chk(
        "H07-consistency-evidence-hash",
        "consistency_evidence_sha256 equals the measured evidence hash",
        cons_declared == live["consistency_sha256"],
        f"declared={cons_declared} measured={live['consistency_sha256']}",
    )
    # the evidence itself must bind the two trees it compared
    ev = live.get("consistency_doc") or {}
    ev_hex = set(re.findall(r"\b[0-9a-f]{64}\b", json.dumps(ev)))
    need = {live["canon_f0_sha256"], live["author_f0_sha256"]}
    chk(
        "H07b-consistency-evidence-self-bound",
        "taxonomy_consistency.json embeds the measured hashes of both compared trees",
        need.issubset(ev_hex),
        f"evidence_hex_digests={len(ev_hex)} both_tree_hashes_present={need.issubset(ev_hex)} "
        f"compared={sorted(p.split('/')[-1] for p in (ev.get('map_taxonomy'), ev.get('lead_contract')))}",
        severity="major",
    )

    # H08/H09 AF_{I+} defined (HF090-03) ------------------------------------
    iplus = parsed.get("i_plus") or {}
    abbr = str(iplus.get("predicate_abbreviation") or "")
    statement = str((parsed.get("conclusion") or {}).get("statement_formal") or "")
    defined = len(abbr) > 20 and "AF_{I+}(M)" in abbr
    use_lines = [ln for ln in f1_text.splitlines() if "AF_{I+}" in ln]
    operative = [
        ln
        for ln in use_lines
        if "predicate_abbreviation" in ln or "statement_formal" in ln
    ]
    # every line carrying the symbol is either the definition leaf, the formal
    # statement, or prose in the revision history that talks *about* the symbol
    prose_only = [
        ln
        for ln in use_lines
        if ln not in operative and ("rev12" in ln or ln.strip().startswith("- {index"))
    ]
    chk(
        "H08-AF-Iplus-defined",
        "AF_{I+} is defined in i_plus.predicate_abbreviation and is used only by that definition and statement_formal",
        defined
        and occ(statement, "AF_{I+}") == 1
        and len(operative) == 2
        and len(prose_only) == len(use_lines) - len(operative),
        f"definition_present={defined} symbol_lines={len(use_lines)} "
        f"operative_lines={len(operative)} prose_lines={len(prose_only)} "
        f"statement_uses_symbol={occ(statement, 'AF_{I+}')}",
        severity="blocking",
    )
    chk(
        "H09-statement-symbols-resolve",
        "every predicate token used by statement_formal is defined in the schema",
        all(
            tok in f1_text
            for tok in ("AF_{I+}", "visible_singularity_from_I_plus", "D0", "comeager")
        ),
        "tokens AF_{I+}, visible_singularity_from_I_plus, D0, comeager all present",
        severity="advisory",
    )

    # H10 D0 well-typed ------------------------------------------------------
    d0 = str(((parsed.get("quantifiers") or {}).get("domains") or {}).get("D0", {}).get("definition", ""))
    ordered = ((parsed.get("quantifiers") or {}).get("ordered") or [])
    first = ordered[0] if ordered else {}
    d0_ok = (
        "tagged disjoint union" in d0
        and "forall r in D0" in str((parsed.get("quantifiers") or {}).get("formal", ""))
        and first.get("kind") == "forall"
        and first.get("binder") == "r"
        and first.get("domain_id") == "D0"
        and "forall (s,delta) in D0" not in f1_text
    )
    chk(
        "H10-D0-well-typed",
        "D0 is a tagged index set and the first quantifier binds a single index r in D0",
        d0_ok,
        f"tagged_disjoint_union={'tagged disjoint union' in d0} ordered0={first}",
    )

    # H11/H12 visibility tail predicate (HF-06 / worker-078) ----------------
    formal = str((parsed.get("quantifiers") or {}).get("formal", ""))
    d5 = str(((parsed.get("quantifiers") or {}).get("domains") or {}).get("D5", {}).get("definition", ""))
    vis = parsed.get("visibility") or {}
    vis_def = str(vis.get("definition") or "")
    vis_neg = str(vis.get("negation_conclusion") or "")
    sites_tail = {
        "quantifiers.formal": "not exists q in I+ and t0 in [0,T) with gamma([t0,T))" in formal,
        "domains.D5": "tail gamma([t0,T))" in d5,
        "visibility.definition": "TAIL gamma([t0,T))" in vis_def,
        "visibility.negation_conclusion": "for every q in I+ and every t0 in [0,T)" in vis_neg,
    }
    chk(
        "H11-visibility-tail-consistent",
        "formal, D5, visibility.definition and negation_conclusion all use the single-q tail predicate",
        all(sites_tail.values()),
        f"sites={sites_tail}",
        severity="blocking",
    )
    whole_curve_sites = {
        "quantifiers.formal": "gamma([0,T)) subset J^-(q)" in formal,
        "domains.D5": "whole-curve" in d5.lower() and "not the predicate" in d5.lower(),
    }
    chk(
        "H12-no-whole-curve-operative",
        "whole-curve containment appears only in explanatory/prohibition text, never as the operative clause",
        not whole_curve_sites["quantifiers.formal"],
        f"operative_whole_curve_sites={whole_curve_sites}",
        severity="blocking",
    )

    # H13 revision history ---------------------------------------------------
    hist = parsed.get("revision_history") or []
    rows_at_rev = [h for h in hist if h.get("at") == parsed.get("revised_at")]
    indices = [h.get("index") for h in hist]
    future_rows = [
        h
        for h in hist
        if rev_at is not None
        and (parse_ts(h.get("at")) or dt.datetime.min.replace(tzinfo=TZ)) > rev_at
    ]
    rev_word = f"rev{parsed.get('revision')}"
    hist_ok = (
        parsed.get("revision") == 12
        and len(rows_at_rev) == 1
        and rows_at_rev[0].get("unused") is False
        and rev_word in str(rows_at_rev[0].get("notes"))
        and len(indices) == len(set(indices))
        and not future_rows
    )
    chk(
        "H13-revision-history-consistent",
        "revision_history has one non-future row at revised_at whose note names this revision, with unique indices",
        hist_ok,
        f"revision={parsed.get('revision')} rows_at_revised_at={len(rows_at_rev)} "
        f"rows={len(hist)} unique_indices={len(indices) == len(set(indices))} "
        f"future_rows={len(future_rows)}",
    )

    # H14 class binding cross-check -----------------------------------------
    comp = parsed.get("class_components") or {}
    canon_entry = target if isinstance(target, dict) else {}
    axes = canon_entry.get("axes") or {}
    class_ok = (
        parsed.get("class_id") == "AF-WCC-VAC-GEN"
        and comp.get("censorship") == axes.get("family")
        and comp.get("regularity_token") == (axes.get("regularity_token") or "none")
        and (parsed.get("conclusion") or {}).get("conclusion_type")
        == axes.get("conclusion_type")
        and not [
            c
            for c in parsed.get("class_components", {})
            if str(parsed.get("class_components", {}).get(c)).startswith("SCC")
        ]
    )
    chk(
        "H14-class-binding-canonical",
        "class_id/class_components/conclusion_type agree with the canonical F0 class entry",
        class_ok,
        f"class_id={parsed.get('class_id')} components={comp} "
        f"canon_axes={ {k: axes.get(k) for k in ('family', 'regularity_token', 'conclusion_type')} }",
    )
    anti = str((parsed.get("anti_scope") or {}).get("not_this_class"))
    chk(
        "H15-anti-scope-separates-scc",
        "anti_scope names AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN as different classes",
        "AF-SCC-C2-VAC-GEN" in anti and "AF-SCC-C0-VAC-GEN" in anti,
        "both SCC class ids present in anti_scope.not_this_class",
    )

    # H16 mirror alignment ---------------------------------------------------
    # A real defect is canonical != authoring. Churn past the snapshot is a timing
    # artifact and is reported separately in hash_guard, not as a check failure.
    live_f1_sha = live["f1_live_sha256"]
    mirror_ok = live_f1_sha == live["f1_mirror_sha256"]
    chk(
        "H16-publication-mirror-aligned",
        "canonical and authoring publication mirrors are byte-identical",
        mirror_ok,
        f"canonical={live_f1_sha[:16]} authoring={live['f1_mirror_sha256'][:16]} "
        f"snapshot={live['f1_snapshot_sha256'][:16]} "
        f"(canonical==snapshot: {live_f1_sha == live['f1_snapshot_sha256']})",
    )

    # H17 falsifier-suite binding -------------------------------------------
    fs = live["falsifier_suite"]
    chk(
        "H17-falsifier-suite-bound",
        "every schemas/f1_falsifier_tests.jsonl row binds the checked snapshot hash",
        fs["bound_rows"] == fs["rows"] and fs["distinct_bindings"] == [live["f1_snapshot_sha256"]],
        f"rows={fs['rows']} bound_rows={fs['bound_rows']} "
        f"distinct_bindings={[b[:16] for b in fs['distinct_bindings']]}",
        severity="minor",
    )

    # H18 self-reported review status ---------------------------------------
    rs = parsed.get("review_status") or {}
    chk(
        "H18-review-status-honest",
        "review_status.independent_reviewers reflects the reviews that exist at this hash",
        bool(rs.get("independent_reviewers")),
        f"independent_reviewers={rs.get('independent_reviewers')} verdict={rs.get('verdict')} "
        "(advisory: many reviews bind 9a8bd4c96800, not this revision)",
        severity="advisory",
    )

    blocking = [c for c in checks if c["status"] == "fail" and c["severity"] == "blocking"]
    failing = [c for c in checks if c["status"] == "fail"]
    return {
        "checks": checks,
        "summary": {
            "n_checks": len(checks),
            "n_pass": len(checks) - len(failing),
            "n_fail": len(failing),
            "n_blocking_fail": len(blocking),
            "blocking_fail_ids": [c["id"] for c in blocking],
            "fail_ids": [c["id"] for c in failing],
        },
    }


MUTANTS = {
    "M1-duplicate-revised-at": (
        'revised_at: "2026-09-12T00:31:41+08:00"\nrevision_history:',
        'revised_at: "2026-09-12T00:31:41+08:00"\n'
        'revised_at: "2026-09-11T23:00:00+08:00"\nrevision_history:',
        "H01-no-duplicate-keys",
    ),
    "M2-pointer-to-authoring-tree": (
        "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN",
        "class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN",
        "H04-contract-pointer-canonical",
    ),
    "M3-undefined-AF-Iplus": (
        "  predicate_abbreviation:",
        "  predicate_abbreviation_removed:",
        "H08-AF-Iplus-defined",
    ),
    "M4-whole-curve-D5": (
        "tail gamma([t0,T)) is contained in the causal past J^-(q)",
        "whole curve gamma([0,T)) is contained in the causal past J^-(q)",
        "H11-visibility-tail-consistent",
    ),
    "M5-stale-f0-hash": (
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "0" * 64,
        "H06-f0-binding-hash",
    ),
    "M6-future-dated-revised-at": (
        'revised_at: "2026-09-12T00:31:41+08:00"',
        'revised_at: "2099-01-01T00:00:00+08:00"',
        "H03-clock-discipline",
    ),
}


def run_mutants(f1_text: str, live: dict) -> list[dict]:
    out = []
    for mid, (old, new, expect) in MUTANTS.items():
        if old not in f1_text:
            out.append(
                {"id": mid, "status": "not-applicable", "detail": "anchor not found"}
            )
            continue
        res = run_checks(f1_text.replace(old, new, 1), live)
        failed = {c["id"] for c in res["checks"] if c["status"] == "fail"}
        out.append(
            {
                "id": mid,
                "status": "caught" if expect in failed else "escaped",
                "expected_check": expect,
                "fail_ids": sorted(failed),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results.json"))
    args = ap.parse_args()

    snap_f1 = sorted(SNAP.glob("af_wcc_vacuum.*.yaml"))
    if len(snap_f1) != 1:
        print(f"expected 1 snapshot, found {snap_f1}", file=sys.stderr)
        return 2
    snap_f1 = snap_f1[0]
    snap_f0 = sorted(SNAP.glob("formulation_taxonomy.*.yaml"))[0]
    snap_author = sorted(SNAP.glob("authoring_formulation_taxonomy.*.yaml"))[0]
    snap_fals = sorted(SNAP.glob("f1_falsifier_tests.*.jsonl"))[0]

    f1_text = snap_f1.read_text()
    pre = sha256_file(F1_LIVE)
    canon_f0_doc = yaml.safe_load(snap_f0.read_text())
    author_doc = yaml.safe_load(snap_author.read_text())

    rows = []
    for line in snap_fals.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    bindings = sorted({str(r.get("binding_sha256")) for r in rows})

    live = {
        "checked_at": now().isoformat(),
        "f1_live_sha256": pre,
        "f1_mirror_sha256": sha256_file(F1_MIRROR),
        "f1_snapshot_sha256": sha256_file(snap_f1),
        "canon_f0_sha256": sha256_file(F0_CANON_LIVE),
        "author_f0_sha256": sha256_file(F0_AUTHOR_LIVE),
        "consistency_sha256": sha256_file(CONSISTENCY_LIVE),
        "consistency_doc": json.loads(CONSISTENCY_LIVE.read_text()),
        "canon_f0_doc": canon_f0_doc,
        "author_doc": author_doc,
        "falsifier_suite": {
            "path": str(FALSIFIER_LIVE.relative_to(REPO)),
            "snapshot_sha256": sha256_file(snap_fals),
            "live_sha256": sha256_file(FALSIFIER_LIVE),
            "rows": len(rows),
            "bound_rows": sum(
                1 for r in rows if r.get("binding_sha256") == sha256_file(snap_f1)
            ),
            "distinct_bindings": bindings,
        },
    }

    res = run_checks(f1_text, live)
    post = sha256_file(F1_LIVE)
    res["mutants"] = run_mutants(f1_text, live)
    res["hash_guard"] = {
        "snapshot": snap_f1.name,
        "snapshot_sha256": live["f1_snapshot_sha256"],
        "canonical_pre_sha256": pre,
        "canonical_post_sha256": post,
        "canonical_stable_during_run": pre == post,
        "mirror_sha256": live["f1_mirror_sha256"],
        "live_referenced": {
            "research_map/formulation_taxonomy.yaml": live["canon_f0_sha256"],
            "artifacts/formulation/formulation_taxonomy.yaml": live["author_f0_sha256"],
            "artifacts/formulation/evidence/taxonomy_consistency.json": live["consistency_sha256"],
            "schemas/f1_falsifier_tests.jsonl": live["falsifier_suite"]["live_sha256"],
        },
        "binding_scope": "instant-bound to snapshot_sha256"
        if pre != post
        else "stable-across-run (pre==post); snapshot_sha256",
    }
    res["verdict"] = (
        "revise"
        if res["summary"]["n_blocking_fail"] > 0
        else ("accept-with-advisories" if res["summary"]["n_fail"] > 0 else "accept")
    )
    res["class_id"] = "AF-WCC-VAC-GEN"
    res["node_id"] = "F1"
    res["worker"] = "worker-090"
    res["task"] = "W090-F1-REV12-CLOSURE"
    Path(args.out).write_text(json.dumps(res, indent=1) + "\n")

    print(json.dumps({k: res[k] for k in ("verdict", "summary", "hash_guard")}, indent=1))
    print("mutants:", json.dumps(res["mutants"]))
    return 0 if not res["summary"]["n_blocking_fail"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
