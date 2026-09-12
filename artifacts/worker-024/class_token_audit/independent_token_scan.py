#!/usr/bin/env python3
"""W024 independent class-token audit of the four canonical class artifacts.

Bounded worker task (worker=024). Reads only; writes snapshots/report under this
directory. Claims no gate verdict and no node transition.

What is independently checked, at one pinned snapshot:
  1. every class-shaped token in the four canonical artifacts, maximal-match,
     with line numbers, classified against the frozen class_ids declared by
     research_map/formulation_taxonomy.yaml itself (authority read at the same
     instant -- not a hardcoded list);
  2. the same files through the project checker research_map/class_separation.py
     (findings_for_text), and the exact agreement/disagreement of the two
     unknown-token sets;
  3. three green-path project tools: verify_frozen.py, check_class_schema.py and
     audit_evidence.audit() (imported, never called with --write-hashes);
  4. a labeled probe corpus that falsifies or confirms whether the checker's
     unknown-token detector can even represent the token shapes it is asked to
     police;
  5. drift: every canonical file is re-hashed after the audit; a moved file is
     reported as unstable and its verdict is explicitly void.

Run:  python3 artifacts/worker-024/class_token_audit/independent_token_scan.py
Exit: 0 if the audit ran and the snapshots are internally consistent; 1 on drift
      or a checker crash (the report is still written).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshots"
CST = timezone(timedelta(hours=8))

CANONICAL = [
    ("F0", "research_map/formulation_taxonomy.yaml"),
    ("F1", "schemas/af_wcc_vacuum.yaml"),
    ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "schemas/af_scc_c0_vacuum.yaml"),
]
TOOLS = [
    "research_map/class_separation.py",
    "research_map/audit_evidence.py",
    "artifacts/formulation/tools/verify_frozen.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/FROZEN.json",
    "research_map/research_map.json",
]

# W024's own maximal-match extractor. Deliberately *not* the project regex:
# a class-shaped token is AF followed by one or more hyphen groups, matched
# greedily so that no token is silently truncated.
MAX_TOKEN = re.compile(r"(?<![A-Za-z0-9-])AF-[A-Z0-9]+(?:-[A-Z0-9]+)*(?![A-Za-z0-9-])", re.I)
FIRST_GROUP = re.compile(r"(?<![A-Za-z0-9-])AF(?:-[A-Z0-9]+)?", re.I)

# Probe corpus: (id, token, canonical?, expectation, why)
PROBES = [
    ("P1", "AF-WCC-VAC-GEN", True, "known: no unknown-token flag",
     "frozen F1 class id; 4 dash-components (AF+3)"),
    ("P2", "AF-WCC-VAC-NONGEN", False, "unknown: must be flagged",
     "4 dash-components, same shape family as the frozen F1 id"),
    ("P3", "AF-SCC-C0-CH-VAC-GEN", False, "unknown: must be flagged, whole token",
     "6 dash-components, the shape the rev-00:16 F0 token had"),
    ("P4", "AF-AAA-BBB-CCC-DDD-EEE", False, "unknown: must be flagged, whole token",
     "7 dash-components, synthetic"),
    ("P5", "AF-WCC-VAC-GEN-SET", False, "unknown: must be flagged",
     "5 dash-components, the variant token live at the 00:16 revision"),
    ("P6", "af-scc-c2-vac-gen", True, "known: case-folded, no flag",
     "lowercase spelling of a frozen class id"),
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def file_rec(p: Path) -> dict:
    st = p.stat()
    b = p.read_bytes()
    return {
        "path": str(p.relative_to(ROOT)),
        "sha256": sha256_bytes(b),
        "bytes": len(b),
        "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
    }


def frozen_classes() -> tuple[list[str], dict]:
    """The four frozen ids are read from the taxonomy at audit time, not hardcoded."""
    import yaml

    p = ROOT / "research_map/formulation_taxonomy.yaml"
    rec = file_rec(p)
    doc = yaml.safe_load(p.read_text())
    ids = [str(x) for x in (doc or {}).get("class_ids", [])]
    return ids, rec


def scan_maximal(text: str) -> list[dict]:
    lines = text.splitlines()
    hits: dict[str, dict] = {}
    for i, line in enumerate(lines, 1):
        for m in MAX_TOKEN.finditer(line):
            raw = m.group(0)
            tok = raw.upper()
            h = hits.setdefault(tok, {"token": tok, "raw_forms": set(), "lines": [], "count": 0,
                                      "line_text": {}})
            h["raw_forms"].add(raw)
            h["lines"].append(i)
            h["line_text"][i] = line.strip()[:200]
            h["count"] += 1
    out = []
    for tok in sorted(hits):
        h = hits[tok]
        out.append({"token": tok, "raw_forms": sorted(h["raw_forms"]),
                    "lines": sorted(set(h["lines"])), "count": h["count"],
                    "line_text": {str(k): v for k, v in sorted(h["line_text"].items())}})
    return out


def scan_first_group(text: str) -> list[str]:
    return sorted({m.group(0).upper() for m in FIRST_GROUP.finditer(text)})


def run(cmd: list[str], timeout=120) -> dict:
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return {"argv": cmd, "exit_code": p.returncode,
                "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}
    except Exception as e:  # noqa: BLE001 - a tool crash is a structured result
        return {"argv": cmd, "exit_code": None, "stdout": "", "stderr": f"{type(e).__name__}: {e}"}


def checker_findings(text: str, where: str) -> dict:
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # pinned by tool hash in the report

    findings = cs.findings_for_text(text, where)
    unknown = []
    for f in findings:
        m = re.search(r"unknown class token in .*?: '([^']+)'", f)
        if m:
            unknown.append(m.group(1).upper())
    return {
        "checker_known_classes": sorted(cs.KNOWN_CLASSES),
        "checker_token_regex": cs._class_tokens.__doc__ or None,
        "checker_regex_source": r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+",
        "findings": findings,
        "unknown_tokens_reported": sorted(set(unknown)),
    }


def probe_detector() -> dict:
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs

    pat = re.compile(r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+")
    rows = []
    for pid, tok, canonical, expectation, why in PROBES:
        regex_hits = pat.findall(tok.upper())
        findings = cs.findings_for_text(tok, f"probe-{pid}")
        rows.append({
            "probe_id": pid, "token": tok, "canonical": canonical,
            "expectation": expectation, "why": why,
            "checker_regex_hits": regex_hits,
            "checker_regex_full_match": regex_hits == [tok.upper()],
            "checker_flagged": bool(findings),
            "checker_findings": findings,
            "expectation_met": (findings == []) if canonical else (len(findings) == 1 and tok.upper() in findings[0]),
        })
    blind = [r["probe_id"] for r in rows if not r["canonical"] and not r["checker_flagged"]]
    truncated = [r["probe_id"] for r in rows
                 if not r["canonical"] and r["checker_flagged"]
                 and r["token"].upper() not in (r["checker_findings"][0] if r["checker_findings"] else "")]
    return {
        "rows": rows,
        "missed_unknown_tokens": blind,
        "truncated_reported_tokens": truncated,
        "regression_corpus": cs.regression(),
        "verdict": "DEFECTIVE_TOKEN_REPRESENTATION" if (blind or truncated) else "PASS",
        "falsifier": ("re-run this function; the verdict flips to PASS iff every non-canonical probe is "
                      "flagged with its full token string and every canonical probe is unflagged"),
    }


def main() -> int:
    started = now()
    SNAP.mkdir(parents=True, exist_ok=True)

    frozen, taxonomy_rec = frozen_classes()
    tools_before = {p: file_rec(ROOT / p) for p in TOOLS}
    git_head = run(["git", "rev-parse", "HEAD"])["stdout"].strip()

    per_file = []
    any_drift = False
    for node, rel in CANONICAL:
        p = ROOT / rel
        before = file_rec(p)
        b = p.read_bytes()
        snapshot = SNAP / f"{p.stem}.{before['sha256'][:8]}{p.suffix}"
        snapshot.write_bytes(b)
        snap_sha = sha256_bytes(snapshot.read_bytes())

        text = b.decode("utf-8", errors="replace")
        maximal = scan_maximal(text)
        unknown_mine = [t for t in maximal if t["token"] not in frozen]
        checker = checker_findings(text, rel)
        checker_unknown = set(checker["unknown_tokens_reported"])
        mine_unknown = {t["token"] for t in unknown_mine}

        schema_check = None
        if node in ("F1", "F2a", "F2b"):
            schema_check = run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", rel, "--json"])
            try:
                schema_check["report"] = json.loads(schema_check["stdout"])
            except Exception:  # noqa: BLE001
                schema_check["report"] = None

        after = file_rec(p)
        stable = after["sha256"] == before["sha256"]
        any_drift = any_drift or not stable
        per_file.append({
            "node_id": node, "path": rel,
            "read": before, "close": after, "stable_during_audit": stable,
            "snapshot": {"path": str(snapshot.relative_to(ROOT)), "sha256": snap_sha,
                         "byte_identical_to_read": snap_sha == before["sha256"]},
            "maximal_tokens": maximal,
            "unknown_tokens_independent": unknown_mine,
            "first_group_tokens": scan_first_group(text),
            "checker": checker,
            "unknown_set_agreement": mine_unknown == checker_unknown,
            "unknown_sets": {"independent": sorted(mine_unknown), "checker": sorted(checker_unknown)},
            "check_class_schema": schema_check,
        })

    verify_frozen = run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"])
    probe = probe_detector()

    # audit_evidence.audit() is imported, never run as __main__ (that variant writes
    # runtime/state/artifact_hashes.json -- a controller-owned file this worker must not touch).
    sys.path.insert(0, str(ROOT / "research_map"))
    import audit_evidence as ae

    ev = ae.audit(ROOT / "research_map" / "research_map.json")
    audit_evidence_view = {
        "hard_total": len(ev["hard"]), "soft_total": len(ev["soft"]),
        "hard_all": list(ev["hard"]),
        "soft_all": list(ev["soft"]),
        "hard_mentioning_canonical": [x for x in ev["hard"] if any(r in x for _, r in CANONICAL)],
        "soft_mentioning_canonical": [x for x in ev["soft"] if any(r in x for _, r in CANONICAL)],
        "wrote_artifact_hashes": False,
        "note": "audit() called directly; the project CLI's --write-hashes write was deliberately not performed",
    }

    tools_after = {p: file_rec(ROOT / p) for p in TOOLS}
    tool_drift = {p: {"before": tools_before[p]["sha256"], "after": tools_after[p]["sha256"]}
                  for p in TOOLS if tools_before[p]["sha256"] != tools_after[p]["sha256"]}

    report = {
        "schema_version": "0.1",
        "audit": "W024-canonical-class-token-audit",
        "actor": "worker-024",
        "task_id": "W024-CLASS-TOKEN-AUDIT-01",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": ";".join(frozen),
        "class_ids": frozen,
        "started_at": started, "finished_at": now(),
        "git_head": git_head,
        "no_authority_statement": ("worker event: this is evidence and a falsifiable claim only; it sets no gate verdict, "
                                   "no validation_status=passed and no node status=done"),
        "frozen_class_ids_source": {"path": taxonomy_rec["path"], "sha256": taxonomy_rec["sha256"]},
        "tool_hashes_at_read": {p: tools_before[p]["sha256"] for p in TOOLS},
        "tool_drift_during_audit": tool_drift,
        "canonical_files": per_file,
        "verify_frozen": verify_frozen,
        "audit_evidence_import_only": audit_evidence_view,
        "detector_probe": probe,
        "summary": {
            "unknown_tokens_independent_total": sum(len(f["unknown_tokens_independent"]) for f in per_file),
            "unknown_tokens_checker_total": sum(len(f["checker"]["unknown_tokens_reported"]) for f in per_file),
            "files_stable": [f["node_id"] for f in per_file if f["stable_during_audit"]],
            "files_drifted": [f["node_id"] for f in per_file if not f["stable_during_audit"]],
            "detector_verdict": probe["verdict"],
            "detector_missed_probes": probe["missed_unknown_tokens"],
            "detector_truncated_probes": probe["truncated_reported_tokens"],
        },
        "falsifier": ("Re-measure the four canonical paths. The snapshot claims are void for any file whose sha256 "
                      "differs from its 'read.sha256'. The detector claims are falsified by running "
                      "probe_detector(): PASS requires every non-canonical probe flagged with its full token and every "
                      "canonical probe unflagged under the pinned research_map/class_separation.py hash."),
        "status": "UNSTABLE_INPUT" if any_drift else "PINNED",
    }

    out = OUT / "report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({
        "report": str(out.relative_to(ROOT)),
        "report_sha256": file_rec(out)["sha256"],
        "status": report["status"],
        "files": {f["node_id"]: {"sha256": f["read"]["sha256"][:12], "stable": f["stable_during_audit"],
                                 "independent_unknown": [t["token"] for t in f["unknown_tokens_independent"]],
                                 "checker_unknown": f["checker"]["unknown_tokens_reported"]} for f in per_file},
        "detector": {"verdict": probe["verdict"], "missed": probe["missed_unknown_tokens"],
                     "truncated": probe["truncated_reported_tokens"]},
        "verify_frozen_exit": verify_frozen["exit_code"],
        "audit_evidence": {"hard": audit_evidence_view["hard_total"], "soft": audit_evidence_view["soft_total"]},
        "tool_drift": tool_drift,
    }, indent=2))
    return 1 if (any_drift or probe["verdict"] != "PASS") else 0


if __name__ == "__main__":
    sys.exit(main())
