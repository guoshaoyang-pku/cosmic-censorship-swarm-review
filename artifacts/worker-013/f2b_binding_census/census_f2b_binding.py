#!/usr/bin/env python3
"""W013-F2B-BINDING-CENSUS-01 — independent read-only census of F2b review verdicts.

Task card: artifacts/worker-013/f2b_binding_census/PRE_REGISTRATION.md
Class: AF-SCC-C0-VAC-GEN | node: F2b | gate: G-FORM (measurement only, no gate verdict).

Reads only: schemas/af_scc_c0_vacuum.yaml, artifacts/formulation/schemas/af_scc_c0_vacuum.yaml,
reviews/*.json. Writes only inside this script's own directory.

Rules S / B / B2 / L are fixed in the pre-registration and are not tuned here.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE

LIVE = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
REVIEWS = ROOT / "reviews"

VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
# controller TARGET_ALIASES (astra_lifecycle.py:135-141), mirrored so Rule S is comparable
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
CLASS_F2B = "AF-SCC-C0-VAC-GEN"

# defect carriers (located before registration; see PRE_REGISTRATION.md)
D1_RE = re.compile(r"strictly larger|forbidden_transfers")
D2_RE = re.compile(r"No containment with C2 or C0|must_not_conflate")
FLAG_RE = re.compile(r"invert|contradict|denial|defect|inconsist|wrong", re.I)
FULL_TEXT_RE = re.compile(r"full[- ]schema|full schema verdict|whole schema|entire schema", re.I)
SCOPED_TEXT_RE = re.compile(r"\b(scoped|partial|subset|axis[- ]scoped)\b", re.I)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(p: Path) -> str:
    return _dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def snapshot_corpus() -> dict:
    snap = {}
    for p in sorted(REVIEWS.glob("*.json")):
        snap[p.name] = {"sha256": sha256_file(p), "mtime": mtime_iso(p)}
    return snap


def _targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return {TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)) for t in out}


def _explicit_pins_scan(d: dict) -> list:
    """Mirror of astra_lifecycle._explicit_pins (controller scan)."""
    pins = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def _explicit_pins_all(d: dict) -> list:
    """Scan pins plus other *explicit* pin fields (nested reviewed_pins, frozen pin)."""
    pins = list(_explicit_pins_scan(d))
    rp = d.get("reviewed_pins")
    if isinstance(rp, dict):
        for v in rp.values():
            if isinstance(v, str):
                pins.append(v.lower())
    for key in ("reviewed_frozen_sha256", "reviewed_mirror_sha256", "supersedes_sha256"):
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    return pins


def norm_verdict(d: dict) -> str:
    v = d.get("verdict")
    if isinstance(v, dict):
        v = v.get("verdict")
    return str(v or "").strip().lower()


def full_claim(d: dict, text: str) -> str:
    if "counts_as_full_schema_verdict" in d:
        return "true" if d.get("counts_as_full_schema_verdict") else "false"
    scope = ""
    for key in ("review_scope", "scope", "review_scope_note"):
        v = d.get(key)
        if isinstance(v, str):
            scope += " " + v
    if FULL_TEXT_RE.search(scope):
        return "text_full"
    if SCOPED_TEXT_RE.search(scope):
        return "text_scoped"
    return "absent"


def hard_failure_counts(d: dict) -> tuple[int, int, int]:
    hf = d.get("hard_failures") or []
    if not isinstance(hf, list):
        hf = []
    blocking_hf = sum(1 for x in hf if isinstance(x, dict) and (x.get("blocking") is True or "block" in str(x.get("severity", "")).lower()))
    fd = d.get("findings") or []
    if not isinstance(fd, list):
        fd = []
    blocking_fd = sum(1 for x in fd if isinstance(x, dict) and x.get("blocking") is True)
    return len(hf), blocking_hf, blocking_fd


def prior_accept_in_history(d: dict) -> bool:
    hist = d.get("revision_history")
    if isinstance(hist, list):
        return any(isinstance(h, dict) and str(h.get("verdict", "")).lower() == "accept" for h in hist)
    return False


def carrier_context(raw: str, rx: re.Pattern, span: int = 110) -> list:
    out = []
    for m in rx.finditer(raw):
        out.append(raw[max(0, m.start() - span):m.end() + span].replace("\n", " "))
        if len(out) >= 2:
            break
    return out


def main() -> int:
    live_sha = sha256_file(LIVE)
    frozen_sha = sha256_file(FROZEN)
    live12 = live_sha[:12]

    t0_corpus = snapshot_corpus()

    rows = []
    for name, snap in t0_corpus.items():
        p = REVIEWS / name
        try:
            raw = p.read_text()
            d = json.loads(raw)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        verdict = norm_verdict(d)
        if verdict not in VERDICT_KINDS:
            continue
        targets = _targets_in_review(d)
        classes = set()
        v = d.get("class_id")
        if isinstance(v, str):
            classes.add(v)
        v = d.get("class_ids")
        if isinstance(v, list):
            classes.update(str(x) for x in v)
        pins_scan = _explicit_pins_scan(d)
        pins_all = _explicit_pins_all(d)

        candidate = (
            "F2b" in targets
            or CLASS_F2B in classes
            or "af_scc_c0_vacuum" in raw
            or any(pin.startswith(live12) or live_sha.startswith(pin[:12]) for pin in pins_scan if pin)
        )
        if not candidate:
            continue

        prefix_scan = any((pin.startswith(live12) or live_sha.startswith(pin[:12])) for pin in pins_scan if pin)
        exact_scan = any(pin == live_sha for pin in pins_scan)
        exact_all = any(pin == live_sha for pin in pins_all)
        hf_n, hf_block, fd_block = hard_failure_counts(d)
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")

        rows.append({
            "file": name,
            "file_sha256": snap["sha256"],
            "mtime": snap["mtime"],
            "declared_created_at": d.get("created_at") or d.get("generated_at"),
            "declared_revised_at": d.get("revised_at"),
            "reviewer": reviewer,
            "verdict": verdict,
            "targets": sorted(targets),
            "class_ids": sorted(classes),
            "pins_explicit_scan": pins_scan,
            "prefix_live_scan": prefix_scan,
            "exact_live_scan": exact_scan,
            "exact_live_all": exact_all,
            "full_schema_claim": full_claim(d, raw),
            "hard_failures_n": hf_n,
            "blocking_hard_failures_n": hf_block,
            "blocking_findings_n": fd_block,
            "prior_accept_in_revision_history": prior_accept_in_history(d),
            "mentions_D1_carrier": bool(D1_RE.search(raw)),
            "mentions_D2_carrier": bool(D2_RE.search(raw)),
            "defect_flag_heuristic": bool((D1_RE.search(raw) or D2_RE.search(raw)) and FLAG_RE.search(raw)),
            "carrier_context": carrier_context(raw, D2_RE) + carrier_context(raw, D1_RE),
            "reviewed_path": d.get("reviewed_path"),
            "reviewed_revision": d.get("reviewed_revision"),
            "n_checks": (d.get("checks_run") or {}).get("n_checks") if isinstance(d.get("checks_run"), dict) else None,
            "n_checks_pass": (d.get("checks_run") or {}).get("n_pass") if isinstance(d.get("checks_run"), dict) else None,
            "criteria_axes_n": len(d.get("criteria_checked")) if isinstance(d.get("criteria_checked"), list) else None,
            "reviewer_is_author": d.get("reviewer_is_author"),
        })

    # reviewer-latest flag
    latest_mtime: dict[str, str] = {}
    for r in rows:
        cur = latest_mtime.get(r["reviewer"])
        if cur is None or r["mtime"] > cur:
            latest_mtime[r["reviewer"]] = r["mtime"]
    for r in rows:
        r["reviewer_latest_for_f2b"] = r["mtime"] == latest_mtime.get(r["reviewer"])

    def uniq(rs):
        return sorted({r["reviewer"] for r in rs})

    rule_s_rows = [r for r in rows if r["verdict"] == "accept" and r["full_schema_claim"] != "false" and r["prefix_live_scan"]]
    rule_s = uniq(rule_s_rows)
    rule_s_files = sorted(r["file"] for r in rule_s_rows)
    rule_s_hist = uniq([r for r in rows if (r["verdict"] == "accept" and r["full_schema_claim"] != "false" and r["prefix_live_scan"])
                        or (r["prior_accept_in_revision_history"] and r["prefix_live_scan"])])
    rule_b_rows = [r for r in rows if r["verdict"] == "accept" and r["exact_live_all"]
                   and r["full_schema_claim"] == "true" and r["reviewer_latest_for_f2b"]
                   and r["blocking_hard_failures_n"] == 0]
    rule_b = uniq(rule_b_rows)
    rule_b_files = sorted(r["file"] for r in rule_b_rows)
    rule_b2 = uniq([r for r in rule_b_rows if r["mentions_D1_carrier"] or r["mentions_D2_carrier"]])
    full_rows = [r for r in rows if r["full_schema_claim"] in ("true", "text_full")]
    latest_full_mtime = {}
    for r in full_rows:
        cur = latest_full_mtime.get(r["reviewer"])
        if cur is None or r["mtime"] > cur:
            latest_full_mtime[r["reviewer"]] = r["mtime"]
    rule_b_sens_rows = [r for r in rows if r["verdict"] == "accept" and r["exact_live_all"]
                        and r["full_schema_claim"] == "true"
                        and r["mtime"] == latest_full_mtime.get(r["reviewer"])
                        and r["blocking_hard_failures_n"] == 0]
    rule_b_sens = uniq(rule_b_sens_rows)
    rule_l = uniq([r for r in rows if r["verdict"] == "revise" and (r["exact_live_all"] or r["prefix_live_scan"])])
    rule_l_files = sorted(r["file"] for r in rows if r["verdict"] == "revise" and (r["exact_live_all"] or r["prefix_live_scan"]))

    t1_corpus = snapshot_corpus()
    corpus_drift = sorted(
        k for k in set(t0_corpus) | set(t1_corpus)
        if t0_corpus.get(k, {}).get("sha256") != t1_corpus.get(k, {}).get("sha256")
    )
    t1_live = sha256_file(LIVE)
    t1_frozen = sha256_file(FROZEN)

    table = {
        "schema": "w013-f2b-binding-census/v1",
        "task_id": "W013-F2B-BINDING-CENSUS-01",
        "class_id": CLASS_F2B,
        "node_id": "F2b",
        "gate": "G-FORM",
        "live_path": str(LIVE.relative_to(ROOT)),
        "live_sha256": live_sha,
        "frozen_path": str(FROZEN.relative_to(ROOT)),
        "frozen_sha256": frozen_sha,
        "live_equals_frozen": live_sha == frozen_sha,
        "corpus_size": len(t0_corpus),
        "candidate_rows": len(rows),
        "rows": sorted(rows, key=lambda r: (r["mtime"], r["file"])),
    }
    (OUT / "binding_table.json").write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n")

    snaps = {
        "t0": {"live_sha256": live_sha, "frozen_sha256": frozen_sha, "corpus": t0_corpus},
        "t1": {"live_sha256": t1_live, "frozen_sha256": t1_frozen, "corpus": t1_corpus},
        "corpus_drift": corpus_drift,
        "live_drift": live_sha != t1_live,
        "frozen_drift": frozen_sha != t1_frozen,
    }
    (OUT / "corpus_snapshot_t0.json").write_text(json.dumps(snaps["t0"], indent=1, ensure_ascii=False) + "\n")
    (OUT / "corpus_snapshot_t1.json").write_text(json.dumps(snaps["t1"], indent=1, ensure_ascii=False) + "\n")

    report = {
        "schema": "w013-f2b-binding-census-report/v1",
        "task_id": "W013-F2B-BINDING-CENSUS-01",
        "worker": "worker-013",
        "node_id": "F2b",
        "class_id": CLASS_F2B,
        "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "authority": "independent read-only measurement; no gate verdict, no node status, no canonical write",
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "target_pin": live_sha,
        "target_pin_matches_frozen": live_sha == frozen_sha,
        "counts": {
            "rule_S_scan_rule": {"reviewers": rule_s, "n": len(rule_s), "files": rule_s_files},
            "rule_S_plus_selfsuperseded_accept": {"reviewers": rule_s_hist, "n": len(rule_s_hist)},
            "rule_B_strict_binding": {"reviewers": rule_b, "n": len(rule_b), "files": rule_b_files},
            "rule_B_sensitivity_latest_full_schema": {
                "reviewers": rule_b_sens, "n": len(rule_b_sens),
                "files": sorted(r["file"] for r in rule_b_sens_rows),
                "note": ("same as Rule B but 'latest' is taken over the reviewer's full-schema F2b rows "
                         "only; the only difference is worker-090, whose later 01:14:43 row is an "
                         "A1-scoped detector-pin verification (full_schema_claim=false, target A1) that "
                         "cites the F2b pin but is not a superseding F2b schema verdict"),
            },
            "rule_B2_defect_aware_binding": {"reviewers": rule_b2, "n": len(rule_b2)},
            "rule_L_revise_live": {"reviewers": rule_l, "n": len(rule_l), "files": rule_l_files},
        },
        "rule_definitions": {
            "S": "accept AND counts_as_full_schema_verdict is not False AND declared pin prefix-matches live (controller scan rule, re-implemented)",
            "B": "accept AND an explicit declared pin equals live exactly AND explicit full-schema claim AND reviewer-latest F2b verdict AND 0 blocking hard failures",
            "B2": "B AND the file text addresses the confirmed W075R-D1/D2 carriers",
            "L": "revise at an exact or prefix-bound live pin",
        },
        "cf31_adjudication": {
            "scan_historical_accept_set": rule_s_hist,
            "scan_current_accept_set": rule_s,
            "strict_binding_accept_set": rule_b,
            "strict_binding_sensitivity_set": rule_b_sens,
            "defect_aware_accept_set": rule_b2,
            "revise_live_set": rule_l,
            "accepted_files_current": rule_s_files,
            "strict_binding_files": rule_b_files,
        },
        "corrections_after_inspection": [
            "rule_B2 was first implemented reviewer-scoped (a carrier mention in any file by a "
            "Rule-B reviewer counted). Post-run inspection showed worker-071's Rule-B accept row "
            "mentions neither carrier, while a different 071 file (F1-review-rev27-a.json) does; "
            "the rule was corrected to be row-scoped before publication. The pre-registered rule "
            "text was not changed.",
            "Rule B as pre-registered classifies worker-090's full accept as superseded because a "
            "later 01:14:43 A1-scoped file by the same reviewer cites the F2b pin. The "
            "rule_B_sensitivity_latest_full_schema row reports the alternative without changing Rule B.",
        ],
        "scan_only_rows_notes": [
            {k: r[k] for k in ("file", "reviewer", "verdict", "full_schema_claim", "reviewed_path",
                                "reviewed_revision", "n_checks", "n_checks_pass", "criteria_axes_n",
                                "blocking_hard_failures_n", "reviewer_latest_for_f2b")}
            for r in rule_s_rows if r["reviewer"] not in rule_b
        ],
        "drift": snaps,
        "accept_row_defect_coverage": [
            {k: r[k] for k in ("file", "reviewer", "verdict", "full_schema_claim", "prefix_live_scan",
                                "exact_live_all", "blocking_hard_failures_n", "mentions_D1_carrier",
                                "mentions_D2_carrier", "defect_flag_heuristic", "carrier_context")}
            for r in table["rows"] if r["verdict"] == "accept" and (r["prefix_live_scan"] or r["exact_live_all"])
        ],
        "artifact_hashes": {
            "binding_table.json": sha256_file(OUT / "binding_table.json"),
            "census_f2b_binding.py": sha256_file(HERE / "census_f2b_binding.py"),
            "PRE_REGISTRATION.md": sha256_file(HERE / "PRE_REGISTRATION.md"),
            "corpus_snapshot_t0.json": sha256_file(OUT / "corpus_snapshot_t0.json"),
            "corpus_snapshot_t1.json": sha256_file(OUT / "corpus_snapshot_t1.json"),
        },
        "claims_not_made": [
            "not a G-FORM gate verdict and no gate movement",
            "not an F2b node verdict and no node transition",
            "no adjudication of which schema revision is scientifically correct",
            "no numerics lock change",
        ],
        "falsifier": ("Re-run census_f2b_binding.py at the cited pins: any count differing from report.json, "
                      "any Rule S accept whose declared hash differs from the live schema hash, any row that "
                      "changes on re-read of the same bytes, or unreported t0/t1 drift flips this census."),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")

    print(json.dumps({
        "live": live_sha,
        "frozen_match": live_sha == frozen_sha,
        "rows": len(rows),
        "rule_S": rule_s,
        "rule_S_hist": rule_s_hist,
        "rule_B": rule_b,
        "rule_B2": rule_b2,
        "rule_L_n": len(rule_l),
        "corpus_drift": corpus_drift,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
