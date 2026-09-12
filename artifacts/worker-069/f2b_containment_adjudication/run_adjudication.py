#!/usr/bin/env python3
"""Runner for W069-F2B-CONTAINMENT-ADJ-01.

Pins the canonical F2b bytes, snapshots them, runs the independent containment checker on the
canonical file and on five mutation controls, reconciles the hash-bound accept corpus, and writes
report.json + raw/*.json + SHA256SUMS. Read-only on every canonical path: controls are written
under this artifact directory only.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-069/<task>/ -> repo root

sys.path.insert(0, str(HERE))
import check_f2b_containment as chk  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(CST).isoformat(timespec="seconds")  # noqa: E731

TARGET = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
MIRROR = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
F0_CANON = ROOT / "research_map" / "formulation_taxonomy.yaml"
MAP = ROOT / "research_map" / "research_map.json"

PIN = chk.CANONICAL_SHA256
REL = "schemas/af_scc_c0_vacuum.yaml"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure_inputs() -> dict:
    out = {}
    for name, p in [("target", TARGET), ("authoring_mirror", MIRROR), ("frozen", FROZEN),
                    ("canonical_f0", F0_CANON), ("map", MAP)]:
        out[name] = {"path": str(p.relative_to(ROOT)), "exists": p.is_file(),
                     "sha256": sha(p) if p.is_file() else None,
                     "bytes": p.stat().st_size if p.is_file() else None,
                     "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds") if p.is_file() else None}
    return out


def frozen_pins() -> dict:
    d = json.loads(FROZEN.read_text())
    return {"revision": d.get("revision"), "frozen_at": d.get("frozen_at"),
            "entries": {k: v.get("sha256") for k, v in (d.get("files") or {}).items()
                        if "af_scc_c0_vacuum" in k}}


def build_controls() -> list[dict]:
    base = TARGET.read_text()
    cdir = HERE / "controls"
    cdir.mkdir(exist_ok=True)
    controls = []

    def w(name: str, text: str, expect: dict, note: str):
        p = cdir / name
        p.write_text(text)
        controls.append({"id": name.replace(".yaml", ""), "file": str(p.relative_to(ROOT)),
                         "expect": expect, "note": note})

    # M0: byte-identical copy -> must reproduce the canonical result exactly (determinism).
    w("M0_byte_identical_copy.yaml", base,
      {"C3_forbidden_transfer_reason.contradiction": True, "C6_duplicate_top_level_keys.ok": False},
      "determinism control: identical bytes, identical verdict")

    # M1: the one-word repair the blockers proposed -> the contradiction must disappear.
    m1 = base.replace("C2 is a strictly larger extension class", "C2 is a strictly smaller extension class")
    assert m1 != base
    w("M1_repair_larger_to_smaller.yaml", m1,
      {"C3_forbidden_transfer_reason.contradiction": False, "C3_forbidden_transfer_reason.ok": True},
      "repair control: 'larger' -> 'smaller' clears HF-069-F2B-1")

    # M2: invert the containment chain -> the chain check must fail (sensitivity to direction).
    m2 = base.replace(
        "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0")
    assert m2 != base
    w("M2_inverted_chain.yaml", m2,
      {"C2_chain_declared.ok": False},
      "sensitivity control: an inverted chain must be detected")

    # M3: replace the reason with a corrected, self-consistent sentence.
    m3 = base.replace(
        "reason: \"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker\"",
        "reason: \"C2 regularity is a strictly stronger requirement (E_C2 is a strict subset of E_C0), so C2-inextendibility is strictly weaker\"")
    assert m3 != base
    w("M3_repaired_reason_sentence.yaml", m3,
      {"C3_forbidden_transfer_reason.contradiction": False, "C5_operative_direction.ok": True},
      "repair control: an explicit subset reason clears the defect and keeps the direction")

    # M4: decoy insertion elsewhere -> C3 must NOT change (specificity).
    m4 = base + "\n# decoy note: C2 is a strictly larger extension class when misread\n"
    w("M4_decoy_elsewhere.yaml", m4,
      {"C3_forbidden_transfer_reason.contradiction": True},
      "specificity control: decoy text outside the ledger must not change C3")

    # M5: remove the duplicate revised_at keys (hygiene control for the parser).
    lines = base.splitlines(keepends=True)
    seen = 0
    keep = []
    for ln in lines:
        if re.match(r"^revised_at:", ln):
            seen += 1
            if seen < 8:
                continue
        keep.append(ln)
    m5 = "".join(keep)
    assert m5 != base
    w("M5_deduplicated_revised_at.yaml", m5,
      {"C6_duplicate_top_level_keys.ok": True},
      "parser control: removing 7 of 8 revised_at keys clears the duplicate finding")
    return controls


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def run_controls(controls: list[dict]) -> list[dict]:
    results = []
    for c in controls:
        res = chk.run(ROOT / c["file"], expect_canonical=False)
        flat = flatten(res["checks"])
        checks = []
        for path, want in c["expect"].items():
            got = flat.get(path)
            checks.append({"assertion": path, "expected": want, "measured": got,
                           "pass": got == want})
        results.append({"id": c["id"], "file": c["file"], "note": c["note"],
                        "assertions": checks, "controls_pass": all(x["pass"] for x in checks),
                        "summary": res["summary"], "target_sha256": res["target_sha256"]})
    return results


ACCEPT_PIN = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"


def scan_accept_corpus() -> dict:
    docs = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        if str(d.get("verdict", "")).lower() != "accept":
            continue
        blob = json.dumps(d)
        if ACCEPT_PIN[:12] not in blob and ACCEPT_PIN not in blob:
            continue
        # does this accept touch the F2b/C0 target at all?
        targets = json.dumps({k: d.get(k) for k in ("target_id", "node_id", "class_id", "artifact",
                                                    "artifact_path", "reviewed_sha256",
                                                    "artifact_sha256")})
        if "F2b" not in targets and "c0_vacuum" not in targets and "AF-SCC-C0" not in targets:
            continue
        findings_text = json.dumps(d.get("findings") or []) + json.dumps(d.get("hard_failures") or [])
        docs.append({
            "file": str(p.relative_to(ROOT)),
            "reviewer": d.get("reviewer") or d.get("actor"),
            "score": d.get("score"),
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "mentions_strictly_larger": "strictly larger" in blob,
            "mentions_denial_sentence": "No containment with C2 or C0" in blob,
            "findings_mention_strictly_larger": "strictly larger" in findings_text,
            "findings_mention_denial_sentence": "No containment with C2 or C0" in findings_text,
            "mentions_implication_ledger": "implication_ledger" in blob,
            "mentions_line_251": bool(re.search(r"(?:line|:)\s*251\b", blob)),
            "mentions_line_157": bool(re.search(r"(?:line|:)\s*157\b", blob)),
        })
    dispo = [x for x in docs if x["findings_mention_strictly_larger"]
             or x["findings_mention_denial_sentence"]]
    return {"pin": ACCEPT_PIN, "accept_docs_at_pin": len(docs), "docs": docs,
            "accepts_listing_either_sentence_as_a_finding": len(dispo),
            "disposition_docs": [x["file"] for x in dispo],
            "note": ("mention in the whole document is not treated as disposition; only findings/"
                     "hard_failures text counts")}


def main() -> int:
    started = NOW()
    inputs_start = measure_inputs()
    if inputs_start["target"]["sha256"] != PIN:
        print(json.dumps({"error": "canonical F2b hash moved", "measured": inputs_start["target"]["sha256"],
                          "pin": PIN}, indent=1))
        return 2

    # byte snapshot (read-only copy of canonical bytes)
    snap = HERE / "snapshot" / "af_scc_c0_vacuum.yaml"
    shutil.copyfile(TARGET, snap)

    canonical = chk.run(TARGET, expect_canonical=True)
    (HERE / "raw" / "checker_canonical.json").write_text(json.dumps(canonical, indent=1, sort_keys=True))

    controls = run_controls(build_controls())
    (HERE / "raw" / "checker_mutants.json").write_text(json.dumps(controls, indent=1, sort_keys=True))

    corpus = scan_accept_corpus()
    (HERE / "raw" / "accept_corpus_scan.json").write_text(json.dumps(corpus, indent=1, sort_keys=True))

    inputs_end = measure_inputs()
    drift = {k: (inputs_start[k]["sha256"], inputs_end[k]["sha256"])
             for k in inputs_start if inputs_start[k]["sha256"] != inputs_end[k]["sha256"]}
    (HERE / "raw" / "input_hashes.json").write_text(json.dumps(
        {"start": inputs_start, "end": inputs_end, "drift": drift}, indent=1, sort_keys=True))

    c = canonical["checks"]
    controls_pass = all(x["controls_pass"] for x in controls)
    hf1 = c["C3_forbidden_transfer_reason"]["contradiction"]
    amb = c["C4_must_not_conflate_denial"]
    hard_failures = []
    if hf1:
        hard_failures.append({
            "id": "HF-069-F2B-1",
            "severity": "blocking-for-clean-accept",
            "label": "false class-size premise inside a forbidden-transfer reason",
            "detail": (f"schemas/af_scc_c0_vacuum.yaml:{c['C3_forbidden_transfer_reason']['line']} "
                       f"forbidden_transfers[0].reason says 'C2 is a strictly larger extension class' "
                       f"while the same file's extension_class_containment "
                       f"(line {c['C2_chain_declared']['line']}) declares E_C0 contains E_H2loc contains "
                       f"E_{{C^1,1}} contains E_C2, i.e. E_C2 is the strictly smaller extension set. "
                       f"The operative prohibition (P_C2 -> P_C0) and the consequent ('strictly weaker') "
                       f"are both correct; only the premise is inverted."),
            "evidence_refs": [f"{REL}#{PIN[:12]}:{c['C3_forbidden_transfer_reason']['line']}",
                              f"{REL}#{PIN[:12]}:{c['C2_chain_declared']['line']}"],
            "falsifier": ("show that 'extension class' in this ledger means the regularity strength "
                          "rather than the set of allowed extensions, with a source inside the pinned "
                          "bytes, or that the chain does not order E_C2 strictly below E_C0"),
        })
    findings = [
        {"id": "W069-F2B-2",
         "severity": "major" if amb["contradiction_filewide_reading"] else "minor",
         "kind": "ambiguity",
         "label": "scope of the must_not_conflate containment denial is not explicit",
         "detail": (f"{REL}:{amb['line']} says 'No containment with C2 or C0 is asserted here' inside "
                    f"regularity.must_not_conflate while implication_ledger asserts containment "
                    f"(E_C2 subset E_H2loc subset E_C0). Read in place the bullet is scoped to the "
                    f"H2_loc axis entry; read file-wide it contradicts the ledger. The defect is the "
                    f"missing scope, not a false ledger row."),
         "evidence_refs": [f"{REL}#{PIN[:12]}:{amb['line']}"],
         "falsifier": "point to an explicit scope marker in the sentence that restricts it to the axis entry"},
        {"id": "W069-F2B-3",
         "severity": "info",
         "kind": "positive",
         "label": "operative transfer rules are correct despite the premise inversion",
         "detail": (f"C5: forbidden direction P_C2 -> P_C0 is re-derived from E_C2 strict-subset E_C0 and "
                    f"is correct; 'strictly weaker' is correct. The repair is one sentence, not a "
                    f"containment re-adjudication."),
         "evidence_refs": [f"{REL}#{PIN[:12]}:{c['C5_operative_direction']['line'] if 'line' in c['C5_operative_direction'] else c['C3_forbidden_transfer_reason']['line']}"]},
        {"id": "W069-F2B-4",
         "severity": "info",
         "kind": "coverage",
         "label": "hash-bound accept corpus does not dispose either sentence",
         "detail": (f"{corpus['accept_docs_at_pin']} accept document(s) at the pinned hash; "
                    f"{corpus['accepts_listing_either_sentence_as_a_finding']} list either sentence in "
                    f"findings/hard_failures. Names: {corpus['disposition_docs']}. Measured mention "
                    f"flags are in raw/accept_corpus_scan.json."),
         "evidence_refs": ["artifacts/worker-069/f2b_containment_adjudication/raw/accept_corpus_scan.json"]},
    ]

    report = {
        "task_id": "W069-F2B-CONTAINMENT-ADJ-01",
        "actor": "worker-069",
        "role": "independent adjudicator; authored no part of the F2b schema, its mirror, F0 or the ledger",
        "created_at": NOW(),
        "started_at": started,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "question": ("At the frozen F2b hash 1bb78ce9, do the two containment-wording blockers reproduce, "
                     "what is their severity for the operative transfer rules, and did any hash-bound "
                     "accept at this hash disposition them?"),
        "target": {"path": REL, "sha256": PIN, "bytes": inputs_start["target"]["bytes"],
                   "authoring_mirror": inputs_start["authoring_mirror"]["sha256"],
                   "frozen": frozen_pins(), "map": inputs_start["map"]["sha256"]},
        "method": ["byte snapshot", "independent containment checker (PyYAML, strict-compose duplicate probe)",
                   "five mutation controls incl. determinism, repair, chain inversion, decoy and dedup",
                   "accept-corpus reconciliation over reviews/*.json pinned to the target hash"],
        "hash_stable_during_run": not drift,
        "drift": drift,
        "verdict": "revise",
        "verdict_scope": "containment-wording adjudication at one hash; not a full-schema verdict",
        "counts_as_full_schema_verdict": False,
        "score": 3.5,
        "hard_failures": hard_failures,
        "findings": findings,
        "checks": canonical["checks"],
        "controls": controls,
        "controls_pass": controls_pass,
        "accept_corpus": corpus,
        "non_claims": [
            "Not a gate verdict: G-FORM remains the controller's and the audit lead's to set.",
            "Not a physics or citation audit; no claim about strong cosmic censorship.",
            "Does not re-adjudicate the duplicate-key, D0-disjunction or pointer blockers already carried by worker-098; it neither confirms nor denies them beyond the parser probe reported here.",
            "Binds only the pinned bytes; any canonical revision voids it.",
        ],
        "next_falsifier": (
            "Re-run run_adjudication.py on a byte-identical copy of schemas/af_scc_c0_vacuum.yaml "
            f"(sha256 {PIN}). This adjudication is falsified if (a) HF-069-F2B-1 does not reproduce "
            "(reason no longer says 'larger', or the chain no longer orders E_C2 below E_C0); "
            "(b) the operative forbidden direction is shown valid as a licensed transfer; "
            "(c) any of the five mutation controls fails its expected assertion; "
            "(d) a hash-bound accept at this hash is found that already dispositions the "
            "forbidden_transfers[0] reason or the must_not_conflate denial sentence; or "
            "(e) the canonical/authoring/FROZEN pins drift from the values recorded here."),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))

    # SHA256SUMS over the task tree (excluding SHA256SUMS itself)
    lines = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(json.dumps({"verdict": report["verdict"], "hard_failures": [h["id"] for h in hard_failures],
                      "controls_pass": controls_pass, "accepts_at_pin": corpus["accept_docs_at_pin"],
                      "dispositioned_by_accepts": corpus["accepts_listing_either_sentence_as_a_finding"],
                      "hash_stable": not drift}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
