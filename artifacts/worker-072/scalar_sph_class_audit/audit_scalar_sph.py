#!/usr/bin/env python3
"""W072-A: class-bound conformance & falsifier audit for AF-WCC-SCALAR-SPH.

Bounded worker task taken from research_map/formulation_taxonomy.yaml coverage gap CG1
("AF-WCC-SCALAR-SPH has no schema node (F-node)") and open question Q4 (which literature
statements are actually theorems, with primary-source scope quotes and hashes).

What this does (offline, deterministic, stdlib only):
  1. Fails closed unless the pinned input revisions match the measured sha256.
  2. Reads the class definition (H1..H4, conclusion, exclusions) from F0 taxonomy.
  3. Classifies every L0 ledger entry bound to the class against H1..H3, the H4
     genericity-naming requirement, and the class conclusion predicate.
  4. Runs calibration controls, including a mutant that MUST discharge the conclusion:
     a detector that can only answer "no" would be vacuous.
  5. Audits the resolvability of every L1 citation row bound to the class.
  6. Writes spotcheck_report.json next to this file.

No claim of completion: worker evidence only, validation_status=unverified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLASS = "AF-WCC-SCALAR-SPH"
TAX = ROOT / "research_map" / "formulation_taxonomy.yaml"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
CITATIONS = ROOT / "ledger" / "citation_audit.csv"
OUT = Path(__file__).resolve().parent / "spotcheck_report.json"
CST = timezone(timedelta(hours=8))

# Pinned revisions at which this audit is valid. Abort (fail closed) on drift.
PINS = {
    "research_map/formulation_taxonomy.yaml": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "ledger/theorems.jsonl": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_taxonomy(path: Path) -> dict:
    """Minimal reader for the one class block we need (avoids a yaml dependency)."""
    text = path.read_text()
    m = re.search(r'^  "?%s"?:\n(.*?)(?=^  \S|\Z)' % re.escape(CLASS), text, re.S | re.M)
    if not m:
        raise SystemExit(f"class {CLASS} not found in {path}")
    block = m.group(1)
    hyps = [{"id": hid, "text": htext.strip()}
            for hid, htext in re.findall(r'id: (H\d+)\n\s*text: "([^"]+)"', block)]
    axes_m = re.search(r"axes:\n((?:\s+\w+:.*\n)+)", block)
    axes = dict(re.findall(r"^\s+(\w+): (\S+)", axes_m.group(1), re.M)) if axes_m else {}
    return {
        "label": (re.search(r'label: "([^"]+)"', block) or [None, ""])[1],
        "axes": axes,
        "hypotheses": hyps,
        "conclusion_type": (re.search(r'conclusion:\n\s*type: (\S+)', block) or [None, ""])[1],
    }


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).lower()


GEN_POS = ("dense open", "dense-open", "comeager", "residual", "full measure",
           "full-measure", "positive probability", "measure one", "generic set")
GEN_NEG = ("not", "no ", "never", "without", "unresolved", "unspecified", "does not",
           "cannot", "fails to", "neither", "nor ")


def genericity_named(gen_raw) -> tuple:
    """H4 requires an explicit genericity notion. A positive token negated nearby does not count."""
    g = norm(gen_raw)
    if not g:
        return False, "genericity field empty"
    for tok in GEN_POS:
        i = g.find(tok)
        if i >= 0:
            window = g[max(0, i - 90):i]
            if any(neg in window for neg in GEN_NEG):
                return False, f"'{tok}' present but negated/unresolved nearby: ...{g[max(0, i - 70):i + len(tok) + 20]}"
            return True, f"'{tok}' asserted without negation nearby"
    return False, "no explicit genericity notion token (dense-open/comeager/full-measure/positive-probability)"


def entry_text(e: dict) -> str:
    parts = []
    for k in ("label", "statement_exact", "assumptions", "genericity", "regularity",
              "topology", "scope_caveats", "does_not_imply", "unresolved"):
        v = e.get(k)
        parts.append(" ".join(map(str, v)) if isinstance(v, list) else str(v or ""))
    return norm(" ".join(parts))


def classify(e: dict, hyp: dict) -> dict:
    """Conformance of one entry against the class hypotheses + conclusion predicate."""
    t = entry_text(e)
    scalar = ("scalar" in t) and not re.search(r"\bvacuum data\b|\bno scalar field\b", t)
    spherical = "spherical" in t
    af = ("asymptotically flat" in t) or ("asymptotic" in t)
    h4_named, h4_why = genericity_named(e.get("genericity"))
    ctype = norm(e.get("conclusion_type"))
    discharges = ctype == "weak_cosmic_censorship"
    h1 = {"id": "H1", "pass": bool(scalar),
          "evidence": "scalar token in entry text" if scalar else "no massless-scalar token / vacuum-only text"}
    h2 = {"id": "H2", "pass": bool(spherical),
          "evidence": "spherical token present" if spherical else "no spherical-symmetry token"}
    h3 = {"id": "H3", "pass": bool(af),
          "evidence": "asymptotic-flatness token present" if af else "no asymptotic-flatness token"}
    h4 = {"id": "H4", "pass": bool(h4_named), "evidence": h4_why}
    return {
        "theorem_id": e.get("theorem_id"),
        "evidence_level": e.get("evidence_level"),
        "entry_kind": e.get("entry_kind"),
        "conclusion_type": e.get("conclusion_type"),
        "status": e.get("status"),
        "source_ids": e.get("source_ids", []),
        "hypotheses": [h1, h2, h3, h4],
        "conforms_mechanical": all(h["pass"] for h in (h1, h2, h3)),
        "h4_genericity_named": h4_named,
        "discharges_class_conclusion": discharges,
        "in_class_evidence_no_conclusion": all(h["pass"] for h in (h1, h2, h3)) and not discharges,
    }


def main() -> int:
    for rel, want in PINS.items():
        got = sha256(ROOT / rel)
        if got != want:
            print(f"ABORT: {rel} sha256={got} != pinned {want}", file=sys.stderr)
            return 2

    tax = parse_taxonomy(TAX)
    hyp_ids = [h["id"] for h in tax["hypotheses"]]

    entries = []
    for line in THEOREMS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        cids = d.get("class_ids") or d.get("class_mapping") or []
        if isinstance(cids, str):
            cids = [cids]
        if CLASS in cids:
            entries.append(d)

    rows = [r for r in csv.DictReader(CITATIONS.open()) if CLASS in (r.get("class_mapping") or "")]

    results = [classify(e, tax) for e in entries]
    n = len(results)
    n_conform = sum(r["conforms_mechanical"] for r in results)
    n_discharge = sum(r["discharges_class_conclusion"] for r in results)
    n_inclass_noconc = sum(r["in_class_evidence_no_conclusion"] for r in results)

    # --- calibration controls: the detector must be able to say BOTH yes and no ---
    src = next(e for e in entries if e.get("theorem_id") == "T-101")
    vacuum = dict(src, theorem_id="CTRL-VACUUM", assumptions=["Vacuum data, no scalar field"],
                  label="CONTROL: vacuum entry must fall out of the scalar class",
                  statement_exact="Schwarzschild vacuum data with a 4-cycle-free graph.")
    full = dict(src, theorem_id="CTRL-FULL-WCC", conclusion_type="weak_cosmic_censorship",
                genericity="comeager (dense G-delta) in the weighted Sobolev topology",
                label="CONTROL: complete in-class WCC claim must discharge the conclusion")
    controls = {
        "CTRL-VACUUM": {"expected_in_class": False, "observed": classify(vacuum, tax)},
        "CTRL-FULL-WCC": {"expected_discharges": True, "observed": classify(full, tax)},
    }
    c_ok = (controls["CTRL-VACUUM"]["observed"]["conforms_mechanical"] is False
            and controls["CTRL-FULL-WCC"]["observed"]["discharges_class_conclusion"] is True)

    # --- L1 locator resolvability for class-bound rows ---
    doi_re = re.compile(r"^10\.\d{4,9}/\S+$")
    arxiv_re = re.compile(r"^(arXiv:)?\d{4}\.\d{4,5}$")
    url_re = re.compile(r"^https?://\S+$")
    loc_audit = []
    for r in rows:
        doi, ax, url = (r.get("doi") or "").strip(), (r.get("arxiv_id") or "").strip(), (r.get("url") or "").strip()
        locator = r.get("exact_locator") or doi or ax or url
        kind = ("doi" if doi_re.match(doi) else "arxiv" if arxiv_re.match(ax)
                else "url" if url_re.match(url) else "none")
        loc_audit.append({
            "citation_id": r["citation_id"], "locator_kind": kind, "locator": locator,
            "resolvable": kind != "none",
            "status": r.get("status"), "used_by_theorems": r.get("used_by_theorems"),
        })
    n_unresolvable = sum(not l["resolvable"] for l in loc_audit)

    report = {
        "schema_version": "w072-class-audit/1",
        "task_id": "W072-A",
        "class_id": CLASS,
        "node_ids": ["F0", "L1", "A1"],
        "gate": "G-FORM/G-LIT (evidence only; no verdict claimed)",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "worker-072",
        "runner_sha256": sha256(Path(__file__).resolve()),
        "pins": {rel: {"sha256": sha256(ROOT / rel), "pinned": want} for rel, want in PINS.items()},
        "input_drift_observed_during_task": {
            "research_map/formulation_taxonomy.yaml": {
                "sha256_at_00:17:41": "0fcc6a1928fd40b02529f59c8a23095191001f84858346bf83d00818c29d7b31",
                "sha256_at_pin_time": PINS["research_map/formulation_taxonomy.yaml"],
                "handling": "fail-closed abort on first run (rc=2), re-pinned to the later revision, re-ran; "
                            "class H1-H4 and conclusion_type verified unchanged across the two revisions",
            },
            "ledger/theorems.jsonl": {"drift": "none observed during task"},
            "ledger/citation_audit.csv": {"drift": "none observed during task"},
        },
        "class_definition": {
            "label": tax["label"], "axes": tax["axes"],
            "hypotheses": tax["hypotheses"], "conclusion_type": tax["conclusion_type"],
            "addressed_artifacts": ["F0 coverage gap CG1", "F0 open question Q4"],
        },
        "ledger_entries_bound": n,
        "summary": {
            "entries_bound": n,
            "mechanically_conform_H1_H2_H3": n_conform,
            "genericity_H4_named": sum(r["h4_genericity_named"] for r in results),
            "discharge_class_WCC_conclusion": n_discharge,
            "in_class_evidence_without_conclusion": n_inclass_noconc,
            "citation_rows_bound": len(rows),
            "citation_rows_with_unresolvable_locator": n_unresolvable,
        },
        "per_entry": results,
        "controls": {
            "CTRL-VACUUM": {k: v for k, v in controls["CTRL-VACUUM"].items()},
            "CTRL-FULL-WCC": {k: v for k, v in controls["CTRL-FULL-WCC"].items()},
            "discriminating_power_ok": c_ok,
        },
        "citation_locator_audit": loc_audit,
        "findings": [
            {"id": "W072-F1",
             "text": f"{n_discharge}/{n} ledger entries bound to {CLASS} state the class's WCC conclusion. "
                     f"{n_inclass_noconc}/{n} are mechanically in-class (H1-H3) but carry an obstruction/instability "
                     "or numerical result instead of the class conclusion: the class is evidence-rich, conclusion-poor.",
             "falsifier": "any bound entry whose conclusion_type is weak_cosmic_censorship and whose H1-H3 pass, "
                          "or a class-conforming WCC entry omitted from the bound set."},
            {"id": "W072-F2",
             "text": f"H4 (genericity notion) is named in {sum(r['h4_genericity_named'] for r in results)}/{n} bound entries; "
                     "taxonomy marks H4 unresolved and owned by L0/L1 with no F-node for this class (CG1). "
                     "Any WCC conclusion for this class is therefore not yet stateable, independent of entry count.",
             "falsifier": "a bound entry naming a specific genericity notion (dense-open/comeager/full-measure) with a "
                          "stated data-space topology and primary-source scope."},
            {"id": "W072-F3",
             "text": f"{n_unresolvable}/{len(rows)} class-bound citation rows have no machine-resolvable locator "
                     "(doi/arxiv/url).", "falsifier": "a resolvable locator found for each flagged row."},
            {"id": "W072-F4",
             "text": "F0 taxonomy was rewritten during this task (0fcc6a1928fd -> "
                     + PINS["research_map/formulation_taxonomy.yaml"][:12]
                     + "); H1-H4 and the class conclusion_type are unchanged across the two revisions, but any "
                       "G-FORM verdict must cite a measured sha256 because F0 is volatile on a minutes timescale.",
             "falsifier": "a G-FORM verdict bound to the pre-revision sha256 that still validates against the "
                          "post-revision taxonomy."},
        ],
        "not_claimed": ["node done", "gate pass", "theorem", "physics result"],
        "validation_status": "unverified",
        "falsifier": "Re-run at the pinned hashes and obtain a different per-entry classification, or produce one "
                     "in-class bound entry that discharges the class WCC conclusion with H4 named.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)), "summary": report["summary"],
                      "controls_ok": c_ok}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
