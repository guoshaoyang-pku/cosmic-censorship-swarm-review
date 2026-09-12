#!/usr/bin/env python3
"""W019-L0-HF14-MATRIX-01 (read-only).

Factual, reproducible trigger matrix for rubric HF-14 (self_certified_acceptance)
against the frozen L0 ledger and the frozen A0 rubric, to resolve the factual part
of the L0 verdict split (worker-011: 60/62 rows support-asserting with no reviewer
verdict; worker-079: 0/62 rows carrying status/validation_status/supports_claim).

This script:
  * pins and re-measures its three inputs before and after the run (drift => fail);
  * quotes the HF-14 detector verbatim from the rubric, with line numbers;
  * emits one row per ledger record with the fields the detector can key on;
  * computes the trigger set under three explicitly-named readings:
      L  literal-key reading   (status=accepted | validation_status=passed | supports_claim=true)
      S  semantic-support reading (author_asserts_supports truthy, no independent
         reviewer verdict field, no artifact hash)
      V  author-verification-label reading (content_status/verification_status in a
         verified vocabulary, no independent reviewer verdict, no artifact hash)
  * reports per-frozen-class counts for each reading.

No gate verdict, no node status, no shared/canonical file is written.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

INPUTS = {
    "ledger": ROOT / "ledger/theorems.jsonl",
    "rubric": ROOT / "evaluation_rubric.yaml",
    "taxonomy": ROOT / "research_map/formulation_taxonomy.yaml",
}

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

LITERAL_KEYS = ("status", "validation_status", "supports_claim")
VERDICT_KEY_RE = re.compile(r"(?i)^(reviewer_verdict|review_verdict|verdict|reviewer_decision|review_decision)$")
HASH_KEY_RE = re.compile(r"(?i)(sha256|artifact_ref|artifact_hash|review_artifact|evidence_hash)")
NON_VERDICT_REVIEW_STATUS = {"not_independently_reviewed", "", None}
VERIFIED_VOCAB = {"verified", "validated", "passed", "accepted", "proved"}


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows(p: pathlib.Path):
    rows = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        rows.append((i, json.loads(line)))
    return rows


def rubric_hf14(text: str):
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"\s*-\s*id:\s*HF-14\s*$", line):
            start = i
            break
    if start is None:
        raise SystemExit("HF-14 block not found in rubric")
    # block ends at the next top-level '- id:' or '# ---' header after start
    end = start + 1
    while end < len(lines):
        if re.match(r"\s*-\s*id:\s*HF-\d+\s*$", lines[end]) or lines[end].startswith("# ---"):
            break
        end += 1
    block = lines[start:end]
    return {
        "line_start": start + 1,
        "line_end": end,
        "verbatim": "\n".join(block),
        "detector_text": " ".join(
            l.strip() for l in block if not l.strip().startswith(("id:", "name:", "severity:", "evidence_"))
        ),
    }


def main() -> int:
    pre = {k: sha256(p) for k, p in INPUTS.items()}
    rows = read_rows(INPUTS["ledger"])
    rubric_text = INPUTS["rubric"].read_text()
    hf14 = rubric_hf14(rubric_text)

    matrix = []
    for lineno, r in rows:
        keys = set(r.keys())
        literal_present = {k: r.get(k) for k in LITERAL_KEYS if k in keys}
        verdict_fields = {k: r[k] for k in keys if VERDICT_KEY_RE.match(k) and r[k] not in (None, "")}
        hash_fields = {k: str(r[k])[:80] for k in keys if HASH_KEY_RE.search(k) and r[k] not in (None, "", [], {})}
        review_status = r.get("review_status")
        has_reviewer_verdict = bool(verdict_fields) or (review_status not in NON_VERDICT_REVIEW_STATUS)
        has_artifact_hash = bool(hash_fields)

        literal_trigger = (
            str(r.get("status", "")).lower() in {"accepted", "passed", "verified"}
            or str(r.get("validation_status", "")).lower() in {"passed", "accepted", "verified"}
            or r.get("supports_claim") is True
        )
        support_assertion = r.get("author_asserts_supports") is True
        semantic_trigger = support_assertion and not has_reviewer_verdict and not has_artifact_hash
        vlabel_trigger = (
            str(r.get("content_status", "")).lower() in VERIFIED_VOCAB
            or str(r.get("verification_status", "")).lower() in VERIFIED_VOCAB
        ) and not has_reviewer_verdict and not has_artifact_hash

        matrix.append({
            "ledger_line": lineno,
            "theorem_id": r.get("theorem_id"),
            "class_ids": r.get("class_ids"),
            "entry_kind": r.get("entry_kind"),
            "conclusion_type": r.get("conclusion_type"),
            "content_status": r.get("content_status"),
            "verification_status": r.get("verification_status"),
            "review_status": review_status,
            "author_asserts_supports": r.get("author_asserts_supports"),
            "acceptance_authority": r.get("acceptance_authority"),
            "literal_keys_present": literal_present,
            "reviewer_verdict_fields": verdict_fields,
            "artifact_hash_fields": hash_fields,
            "has_reviewer_verdict": has_reviewer_verdict,
            "has_artifact_hash": has_artifact_hash,
            "trigger_L_literal_key": literal_trigger,
            "trigger_S_semantic_support": semantic_trigger,
            "trigger_V_author_verification_label": vlabel_trigger,
        })

    def trigger_set(field):
        return sorted(m["theorem_id"] for m in matrix if m[field])

    def by_class(field):
        out = {c: [] for c in CLASS_IDS}
        out["<no-frozen-class>"] = []
        for m in matrix:
            if not m[field]:
                continue
            cids = [c for c in (m["class_ids"] or []) if c in CLASS_IDS]
            if not cids:
                out["<no-frozen-class>"].append(m["theorem_id"])
            for c in cids:
                out[c].append(m["theorem_id"])
        return {k: {"n": len(v), "ids": sorted(v)} for k, v in out.items()}

    readings = {
        "L_literal_key": {
            "definition": "row sets any of the literal keys named by the HF-14 detector: status in {accepted,passed,verified} or validation_status in {passed,accepted,verified} or supports_claim=true",
            "trigger_n": len(trigger_set("trigger_L_literal_key")),
            "trigger_ids": trigger_set("trigger_L_literal_key"),
            "by_class": by_class("trigger_L_literal_key"),
        },
        "S_semantic_support": {
            "definition": "row has author_asserts_supports=true AND no independent reviewer verdict field AND no artifact hash field",
            "trigger_n": len(trigger_set("trigger_S_semantic_support")),
            "trigger_ids": trigger_set("trigger_S_semantic_support"),
            "by_class": by_class("trigger_S_semantic_support"),
        },
        "V_author_verification_label": {
            "definition": "row has content_status or verification_status in {verified,validated,passed,accepted,proved} AND no independent reviewer verdict field AND no artifact hash field",
            "trigger_n": len(trigger_set("trigger_V_author_verification_label")),
            "trigger_ids": trigger_set("trigger_V_author_verification_label"),
            "by_class": by_class("trigger_V_author_verification_label"),
        },
    }

    post = {k: sha256(p) for k, p in INPUTS.items()}
    drift = {k: {"pre": pre[k], "post": post[k], "drift": pre[k] != post[k]} for k in INPUTS}

    def frozen_ids(row):
        return [c for c in (row["class_ids"] or []) if c in CLASS_IDS]

    class_binding = {
        "rows": len(matrix),
        "rows_with_empty_class_ids": sum(1 for row in matrix if not (row["class_ids"] or [])),
        "rows_with_any_frozen_class_id": sum(1 for row in matrix if frozen_ids(row)),
        "frozen_class_id_occurrences": sum(len(frozen_ids(row)) for row in matrix),
        "dual_frozen_rows": sorted(row["theorem_id"] for row in matrix if len(frozen_ids(row)) > 1),
        "non_frozen_class_id_tokens": sorted({c for row in matrix for c in (row["class_ids"] or []) if c not in CLASS_IDS}),
    }

    result = {
        "task_id": "W019-L0-HF14-MATRIX-01",
        "actor": "worker-019",
        "kind": "read_only_measurement",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "inputs": {k: {"path": str(p.relative_to(ROOT)), "sha256": pre[k], "bytes": p.stat().st_size} for k, p in INPUTS.items()},
        "input_drift": drift,
        "drift_free": not any(v["drift"] for v in drift.values()),
        "rubric_hf14": hf14,
        "ledger_rows": len(rows),
        "distinct_theorem_ids": len({m["theorem_id"] for m in matrix}),
        "class_binding": class_binding,
        "value_census": {
            "author_asserts_supports": _census(matrix, "author_asserts_supports"),
            "review_status": _census(matrix, "review_status"),
            "content_status": _census(matrix, "content_status"),
            "verification_status": _census(matrix, "verification_status"),
            "literal_keys_present_any_row": sorted({k for m in matrix for k in m["literal_keys_present"]}),
            "reviewer_verdict_fields_seen": sorted({k for m in matrix for k in m["reviewer_verdict_fields"]}),
            "artifact_hash_fields_seen": sorted({k for m in matrix for k in m["artifact_hash_fields"]}),
        },
        "readings": readings,
        "rows": matrix,
        "findings": [
            "HF-14 detector is keyed on the literal names status=accepted / validation_status=passed / supports_claim=true; counts under that literal reading reproduce worker-079's 0/62.",
            "The same detector's rationale is semantic ('an author's own selftest is not a reviewer verdict'); under that reading the truthy author_asserts_supports field on 60/62 rows with review_status=not_independently_reviewed and no reviewer-verdict or artifact-hash field reproduces worker-011's 60/62.",
            "The row-level matrix, not the disputed count, is the decisive input; the adjudicator must rule whether author_asserts_supports is a 'support assertion' in the detector's sense.",
        ],
        "authority_note": "Worker measurement only: no gate verdict, no node status, no validation_status=passed, no canonical/shared file written.",
        "falsifier": "Re-run this script at the pinned input sha256s: a different value census, trigger set, or per-class split falsifies this matrix; any input hash move voids it and requires re-pinning.",
    }
    OUT.joinpath("matrix.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("drift_free", "ledger_rows", "value_census", "readings")}, indent=1, sort_keys=True))
    return 0 if result["drift_free"] else 2


def _census(matrix, key):
    out = {}
    for m in matrix:
        v = m.get(key)
        out[repr(v)] = out.get(repr(v), 0) + 1
    return out


if __name__ == "__main__":
    sys.exit(main())
