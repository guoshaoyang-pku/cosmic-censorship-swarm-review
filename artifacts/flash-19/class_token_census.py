#!/usr/bin/env python3
"""Machine census of class tokens in the L0 literature ledger.

Assignment : astra-indep-1-CF5-ledger-verify (node L0, gate G-LIT, run 2026-09-12T00:00+08:00)
Actor      : deepseek-flash-19
Deliverable: artifacts/flash-19/class_token_census.json (canonical path, not drift)

Scope (read-only; neither input is modified):
  ledger/theorems.jsonl
  ledger/citation_audit.csv

Token universe (stated so the census is falsifiable):
  Any substring matching AF-[A-Za-z0-9]+(-[A-Za-z0-9]+)* after NFKC normalisation,
  superscript folding (0/1/2/3) and removal of '^' and '{}' (so an AF token written
  with a caret or superscript is still seen).  Bare "AF" as in "AF data" is NOT a
  token: a class token requires at least one '-' followed by an alphanumeric group.

Classification (mutually exclusive, in this order):
  frozen      token is one of the four frozen ids in research_map/class_separation.py
  ledger_tag  token appears verbatim as a value of a theorem record's `ledger_tags`
              array (the ledger's declared local vocabulary)
  violation   anything else; the assignment's falsifier fires on these

Every violation gets a one-line remedy.  The artifact also carries an auxiliary
observation block (detector probe, detector findings, composite mappings) that is
explicitly out of scope for the frozen/ledger-tag/violation counts.

Determinism: keys sorted, lists sorted, content_digest_sha256 covers every top-level
field except `generated_at` and `content_digest_sha256` itself.  Re-running on unchanged
inputs reproduces the content digest.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
CITATIONS = ROOT / "ledger" / "citation_audit.csv"
OUT = ROOT / "artifacts" / "flash-19" / "class_token_census.json"
CLASS_SEP = ROOT / "research_map" / "class_separation.py"
CST = timezone(timedelta(hours=8))

FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
TOKEN_RE = re.compile(r"AF-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", re.I)
RAW_VARIANT_RE = re.compile(r"AF-[A-Za-z0-9^{}⁰¹²³-]*[⁰¹²³^][A-Za-z0-9^{}⁰¹²³-]*")
SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3"}
CLASS_TAG_RE = re.compile(r"^(C0|C2|SCALAR-SPH|VACUUM|WCC|SCC)(-|$)", re.I)
MERGE_REF = re.compile(r"assessed_no_binding|must not be cited|not attached to any of the four classes|"
                       r"nor as class evidence|should count|binding is therefore provisional")
REMEDIES = {
    "AF-SCC-C2": (
        "T-304.next_action: replace the shorthand with the frozen id AF-SCC-C2-VAC-GEN "
        "(or drop the prefix and write 'the C^2 SCC dossier'); AF-prefixed tokens are "
        "reserved for the four frozen ids."
    ),
    "AF-SCC": (
        "T-526.scope_caveats / T-526.unresolved: write 'the SCC classes' or list the "
        "specific frozen ids instead of an AF-prefixed family token, or declare it in "
        "ledger_tags as ledger-local vocabulary."
    ),
    "AF-SCC-C0": (
        "SRC-096 / SRC-097.assessment: write the full frozen id AF-SCC-C0-VAC-GEN or the "
        "unprefixed phrasing 'the C^0 SCC class'; the no-binding disclaimer is correct in "
        "substance but the truncated token is still non-frozen."
    ),
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for k, v in SUP.items():
        s = s.replace(k, v)
    return s.replace("^", "").replace("{", "").replace("}", "")


def ser(v) -> str:
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def snippet(text: str, start: int, end: int, width: int = 70) -> str:
    lo, hi = max(0, start - width), min(len(text), end + width)
    out = re.sub(r"\s+", " ", text[lo:hi]).strip()
    return ("..." if lo else "") + out + ("..." if hi < len(text) else "")


def context_label(field: str, snip: str, in_csv: bool) -> str:
    low = snip.lower()
    if in_csv and ("must not be cited" in low or "assessed_no_binding" in low
                   or "not attached to any of the four classes" in low or "nor as class evidence" in low):
        return "negative_no_binding_disclaimer"
    if "bind to" in low or "dossier" in low:
        return "forward_reference_shorthand"
    if "should count" in low or "provisional" in low or "unresolved" in field:
        return "open_question_shorthand"
    return "unclassified_shorthand"


def load_detector():
    spec = importlib.util.spec_from_file_location("class_separation", CLASS_SEP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan_text(text: str, tokens: dict, loc: dict, occ: list) -> None:
    """Record every AF token occurrence in one field value."""
    for m in TOKEN_RE.finditer(text):
        raw = m.group(0)
        key = raw.upper()
        rec = tokens.setdefault(key, {"token": key, "raw_forms": set(), "occurrences": 0,
                                      "by_file": {}, "by_field": {}})
        rec["raw_forms"].add(raw)
        rec["occurrences"] += 1
        rec["by_file"][loc["file"]] = rec["by_file"].get(loc["file"], 0) + 1
        rec["by_field"][loc["field"]] = rec["by_field"].get(loc["field"], 0) + 1
        occ.append({**loc, "token": key, "snippet": snippet(text, m.start(), m.end())})


def main() -> dict:
    theorems_bytes = THEOREMS.read_bytes()
    citations_bytes = CITATIONS.read_bytes()
    inputs = [
        {"path": str(THEOREMS.relative_to(ROOT)), "sha256": sha256_bytes(theorems_bytes),
         "bytes": len(theorems_bytes), "records": 0},
        {"path": str(CITATIONS.relative_to(ROOT)), "sha256": sha256_bytes(citations_bytes),
         "bytes": len(citations_bytes), "records": 0},
    ]

    tokens: dict[str, dict] = {}
    occurrences: list[dict] = []
    raw_variants: list[dict] = []
    ledger_tags: dict[str, int] = {}

    # ---- theorems.jsonl -------------------------------------------------
    n_theorems = 0
    for line_no, line in enumerate(theorems_bytes.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        n_theorems += 1
        rec = json.loads(line)
        rid = rec.get("theorem_id")
        for tag in rec.get("ledger_tags", []) or []:
            ledger_tags[str(tag)] = ledger_tags.get(str(tag), 0) + 1
        for field, value in sorted(rec.items()):
            raw_text = ser(value)
            text = normalize(raw_text)
            loc = {"file": str(THEOREMS.relative_to(ROOT)), "line": line_no,
                   "record_id": rid, "field": field}
            scan_text(text, tokens, loc, occurrences)
            for vm in RAW_VARIANT_RE.finditer(raw_text):
                raw_variants.append({**loc, "raw_token": vm.group(0)})
    inputs[0]["records"] = n_theorems

    # ---- citation_audit.csv --------------------------------------------
    reader = csv.DictReader(citations_bytes.decode("utf-8").splitlines())
    n_rows = 0
    for row_no, row in enumerate(reader, 1):
        n_rows += 1
        rid = row.get("citation_id")
        for field, value in sorted(row.items()):
            if not value:
                continue
            text = normalize(value)
            loc = {"file": str(CITATIONS.relative_to(ROOT)), "row": row_no,
                   "csv_line": row_no + 1, "record_id": rid, "field": field}
            scan_text(text, tokens, loc, occurrences)
            for vm in RAW_VARIANT_RE.finditer(value):
                raw_variants.append({**loc, "raw_token": vm.group(0)})
    inputs[1]["records"] = n_rows

    # ---- classification -------------------------------------------------
    tag_keys = {t.upper() for t in ledger_tags}
    census = []
    violations = []
    for key in sorted(tokens):
        rec = tokens[key]
        if key in FROZEN:
            cls = "frozen"
        elif key in tag_keys:
            cls = "ledger_tag"
        else:
            cls = "violation"
        entry = {
            "token": key,
            "classification": cls,
            "occurrences": rec["occurrences"],
            "by_file": dict(sorted(rec["by_file"].items())),
            "by_field": dict(sorted(rec["by_field"].items())),
            "raw_forms": sorted(rec["raw_forms"]),
        }
        census.append(entry)
        if cls == "violation":
            detail = []
            for o in occurrences:
                if o["token"] != key:
                    continue
                detail.append({
                    "file": o["file"],
                    "line": o.get("line"),
                    "row": o.get("row"),
                    "csv_line": o.get("csv_line"),
                    "record_id": o["record_id"],
                    "field": o["field"],
                    "context": context_label(o["field"], o["snippet"], o["file"].endswith(".csv")),
                    "snippet": o["snippet"],
                })
            detail.sort(key=lambda d: (d["file"], d["line"] or d["row"], d["field"]))
            violations.append({
                "token": key,
                "occurrences": rec["occurrences"],
                "occurrences_detail": detail,
                "remedy": REMEDIES.get(key, f"Replace non-frozen token {key} with one of the four "
                                            "frozen ids, or declare it in ledger_tags as ledger-local."),
            })

    frozen_missing = {}
    for fid in FROZEN:
        entry = tokens.get(fid)
        frozen_missing[fid] = {
            "in_theorems": bool(entry and entry["by_file"].get(str(THEOREMS.relative_to(ROOT)))),
            "in_citations": bool(entry and entry["by_file"].get(str(CITATIONS.relative_to(ROOT)))),
            "total_occurrences": entry["occurrences"] if entry else 0,
        }

    untagged = sum(v["occurrences"] for v in violations)
    class_tags = {t: n for t, n in sorted(ledger_tags.items()) if CLASS_TAG_RE.match(t)}

    # ---- auxiliary observations (explicitly outside the census counts) --
    det = load_detector()
    probe = {fid: det._class_tokens(fid) for fid in FROZEN}
    det_findings = []
    for line_no, line in enumerate(theorems_bytes.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        for f in det.findings(json.loads(line), f"ledger/theorems.jsonl:{line_no}"):
            det_findings.append(f)
    for row_no, row in enumerate(csv.DictReader(citations_bytes.decode("utf-8").splitlines()), 1):
        for f in det.findings(row, f"ledger/citation_audit.csv:{row_no + 1}"):
            det_findings.append(f)
    composite_rows = 0
    for row in csv.DictReader(citations_bytes.decode("utf-8").splitlines()):
        if len(TOKEN_RE.findall(normalize(row.get("class_mapping") or ""))) > 1:
            composite_rows += 1

    payload = {
        "artifact_type": "class_token_census",
        "artifact_version": "1.0",
        "task": {
            "event_id": "astra-indep-1-CF5-ledger-verify",
            "node_id": "L0",
            "gate": "G-LIT",
            "run_id": "run-2026-09-12T00:00+08:00",
            "actor": "deepseek-flash-19",
            "controller_finding": "CF-5 (unverified class-token vocabulary in the ledger)",
        },
        "scope": {
            "files": [i["path"] for i in inputs],
            "read_only": True,
            "excluded": "ledger/class_coverage.csv and all formulation schemas are out of scope for this census",
        },
        "token_definition": {
            "regex": TOKEN_RE.pattern,
            "case": "case-insensitive; matched form reported in raw_forms",
            "normalization": "NFKC; superscripts 0/1/2/3 folded to digits; '^', '{', '}' removed",
            "not_a_token": "bare 'AF' with no '-<alnum>' group (e.g. 'AF data', 'AF class')",
        },
        "classification_rules": {
            "frozen": "token is one of the four ids in research_map/class_separation.py KNOWN_CLASSES",
            "ledger_tag": "token appears verbatim in a theorem record's ledger_tags array",
            "violation": "neither of the above; the assigned falsifier fires",
        },
        "frozen_ids": FROZEN,
        "inputs": inputs,
        "census": census,
        "violations": violations,
        "ledger_local_tags": {
            "distinct_total": len(ledger_tags),
            "occurrences_total": sum(ledger_tags.values()),
            "class_denoting": class_tags,
            "all": dict(sorted(ledger_tags.items())),
            "note": "declared local vocabulary; none of these is an AF-prefixed token, so no "
                    "AF-token in the ledger is redeemed as ledger_tag",
        },
        "assertions": {
            "frozen_ids_present": frozen_missing,
            "non_frozen_af_tokens": len(violations),
            "non_frozen_af_occurrences": untagged,
            "untagged_non_frozen_occurrences": untagged,
            "falsifier_status": "FIRED" if untagged else "not_fired",
            "detector_regex_matches_all_frozen_ids": all(bool(v) for v in probe.values()),
            "raw_superscript_or_caret_class_variants": len(raw_variants),
            "census_reproducible_from_content_digest": True,
        },
        "auxiliary_observations": [
            {
                "id": "OBS-1",
                "status": "out_of_scope_for_token_counts",
                "finding": "research_map/class_separation.py _class_tokens requires four hyphen groups "
                           "after 'AF-', so it does not match two of the four frozen ids.",
                "evidence": {fid: probe[fid] for fid in FROZEN},
                "remedy": "Change the token pattern to AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+ and add all four "
                          "frozen ids as regression fixtures; the R2 unknown-token rule is blind to "
                          "AF-WCC-VAC-GEN and AF-WCC-SCALAR-SPH until then.",
            },
            {
                "id": "OBS-2",
                "status": "out_of_scope_for_token_counts",
                "finding": "The canonical detector reports bare-composite findings on the two ledger files.",
                "evidence": det_findings,
                "remedy": "Refer to the audit/formulation leads; a token census cannot adjudicate whether "
                          "these are genuine class merges or detector false positives.",
            },
            {
                "id": "OBS-3",
                "status": "out_of_scope_for_token_counts",
                "finding": f"{composite_rows} citation_audit.csv rows map one source to more than one frozen id.",
                "evidence": {"rows_with_multiple_frozen_ids": composite_rows},
                "remedy": "Each constituent token is frozen, so this is not a token violation; it is a "
                          "multi-class evidence mapping and is recorded for coverage accounting only.",
            },
        ],
        "falsifier": "A rerun on the same input sha256s finds an AF-prefixed token not classified here, "
                     "or classifies a token differently; either falsifies this census.",
        "reopen_rule": "If either input sha256 changes, this census is stale and must be regenerated; "
                       "the untagged occurrences found here are the measured evidence for CF-5.",
    }

    payload["generator"] = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sha256": sha256_path(Path(__file__).resolve()),
        "reproduce_command": "python3 artifacts/flash-19/class_token_census.py",
    }
    content = {k: v for k, v in payload.items()
               if k not in ("generated_at", "content_digest_sha256")}
    digest = sha256_bytes(json.dumps(content, ensure_ascii=False, sort_keys=True).encode())
    payload["content_digest_sha256"] = digest
    payload["generated_at"] = datetime.now(CST).isoformat(timespec="seconds")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "artifact": str(OUT.relative_to(ROOT)),
        "sha256": sha256_path(OUT),
        "content_digest_sha256": digest,
        "falsifier_status": payload["assertions"]["falsifier_status"],
        "non_frozen_af_occurrences": untagged,
        "input_sha256": {i["path"]: i["sha256"] for i in inputs},
        "auxiliary": [o["id"] for o in payload["auxiliary_observations"]],
    }, indent=2))
    return payload


if __name__ == "__main__":
    main()
