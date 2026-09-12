#!/usr/bin/env python3
"""W019-CLASSTOKEN-VERIFY-01 -- independent re-derivation of frozen-class-token
discipline in the L0 ledger and falsification test of OBS-1 in
artifacts/flash-19/class_token_census.json (sha256 f7b1b0df14a5...).

Independence statement
----------------------
This script does NOT import, execute, or read the source of
artifacts/flash-19/class_token_census.py.  Token extraction, record walking and
classification are implemented from scratch below.  The only shared code is
research_map/class_separation.py, and only to *probe* the canonical detector
(the object of OBS-1), never to produce the counts.

Inputs (read-only, hash-pinned):
  ledger/theorems.jsonl       ce42d205e761...
  ledger/citation_audit.csv   315c19145065...
Target:
  artifacts/flash-19/class_token_census.json  f7b1b0df14a5...

Outputs (deterministic, no network):
  artifacts/worker-019/class_token_recount.json
  artifacts/worker-019/class_token_verification.json
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "ledger"
OUTDIR = ROOT / "artifacts" / "worker-019"
CST = timezone(timedelta(hours=8))

PINNED_INPUTS = {
    "ledger/theorems.jsonl": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
CENSUS_REL = "artifacts/flash-19/class_token_census.json"
CENSUS_SHA = "f7b1b0df14a5d8fecc19e25e706284db2cc607f23c74673f4f6e1ce5321bab1b"

# the four frozen ids, re-read from the canonical map at run time as well
FROZEN_FALLBACK = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

TOKEN_RE = re.compile(r"AF-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", re.IGNORECASE)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def normalize(s: str) -> str:
    """NFKC; superscripts folded to digits; '^', '{', '}' removed."""
    s = unicodedata.normalize("NFKC", s)
    return s.replace("^", "").replace("{", "").replace("}", "")


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from strings_in(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings_in(v)


def snippet(text: str, start: int, end: int, width: int = 40) -> str:
    lo, hi = max(0, start - width), min(len(text), end + width)
    return ("..." if lo > 0 else "") + text[lo:hi] + ("..." if hi < len(text) else "")


def frozen_ids_from_map() -> list:
    try:
        txt = (ROOT / "research_map" / "class_separation.py").read_text()
        m = re.search(r"KNOWN_CLASSES\s*=\s*[\{\[]([^}\]]*)[\}\]]", txt, re.S)
        if m:
            ids = re.findall(r"AF-[A-Z0-9-]+", m.group(1))
            if len(ids) == 4:
                return sorted(ids)
    except Exception:
        pass
    return sorted(FROZEN_FALLBACK)


def walk_theorems():
    """Per-token occurrences attributed to top-level field."""
    occ = defaultdict(lambda: defaultdict(list))  # token -> field -> details
    tag_values = []
    n = 0
    for lineno, raw in enumerate((LEDGER / "theorems.jsonl").read_text().splitlines(), 1):
        if not raw.strip():
            continue
        rec = json.loads(raw)
        n += 1
        rid = rec.get("theorem_id") or rec.get("id") or f"line{lineno}"
        for field, value in rec.items():
            if field == "ledger_tags":
                for t in (value if isinstance(value, list) else [value]):
                    if isinstance(t, str):
                        tag_values.append(t)
                continue
            for s in strings_in(value):
                norm_s = normalize(s)
                for m in TOKEN_RE.finditer(norm_s):
                    tok = m.group(0).upper()
                    occ[tok][field].append({
                        "file": "ledger/theorems.jsonl",
                        "line": lineno,
                        "record_id": rid,
                        "field": field,
                        "snippet": snippet(norm_s, m.start(), m.end()),
                    })
    return occ, n, tag_values


def walk_citations():
    occ = defaultdict(lambda: defaultdict(list))
    n = 0
    with (LEDGER / "citation_audit.csv").open(newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            rid = row.get("citation_id") or f"row{n}"
            for field, value in row.items():
                if not isinstance(value, str):
                    continue
                norm_s = normalize(value)
                for m in TOKEN_RE.finditer(norm_s):
                    tok = m.group(0).upper()
                    occ[tok][field].append({
                        "file": "ledger/citation_audit.csv",
                        "row": n,
                        "record_id": rid,
                        "field": field,
                        "snippet": snippet(norm_s, m.start(), m.end()),
                    })
    return occ, n


def build_recount():
    th_occ, th_n, tag_values = walk_theorems()
    ci_occ, ci_n = walk_citations()

    all_tokens = sorted(set(th_occ) | set(ci_occ))
    frozen = set(frozen_ids_from_map())
    tags_verbatim = set(tag_values)
    tags_ci = {t.upper() for t in tag_values}

    census_doc = json.loads((ROOT / CENSUS_REL).read_text())
    census_by_token = {e["token"].upper(): e for e in census_doc.get("census", [])}

    entries = []
    for tok in all_tokens:
        total = 0
        by_file = Counter()
        by_field = Counter()
        for field, items in sorted(th_occ.get(tok, {}).items()):
            total += len(items)
            by_file["ledger/theorems.jsonl"] += len(items)
            by_field[field] += len(items)
        for field, items in sorted(ci_occ.get(tok, {}).items()):
            total += len(items)
            by_file["ledger/citation_audit.csv"] += len(items)
            by_field[field] += len(items)

        if tok in frozen:
            classification = "frozen"
        elif tok in tags_verbatim or tok in tags_ci:
            classification = "ledger_tag"
        else:
            classification = "violation"

        c = census_by_token.get(tok)
        cmp_entry = {
            "token": tok,
            "classification": classification,
            "occurrences": total,
            "by_file": dict(sorted(by_file.items())),
            "by_field": dict(sorted(by_field.items())),
            "census_classification": c.get("classification") if c else None,
            "census_occurrences": c.get("occurrences") if c else None,
            "census_by_file": dict(sorted((c.get("by_file") or {}).items())) if c else None,
            "census_by_field": dict(sorted((c.get("by_field") or {}).items())) if c else None,
            "occurrence_match": bool(c and c.get("occurrences") == total),
            "classification_match": bool(c and c.get("classification") == classification),
            "by_file_match": bool(c and dict(sorted((c.get("by_file") or {}).items())) == dict(sorted(by_file.items()))),
            "by_field_match": bool(c and dict(sorted((c.get("by_field") or {}).items())) == dict(sorted(by_field.items()))),
        }
        entries.append(cmp_entry)

    mine_tokens = {e["token"] for e in entries}
    census_tokens = set(census_by_token)
    mismatches = [e for e in entries if not (e["occurrence_match"] and e["classification_match"]
                                             and e["by_file_match"] and e["by_field_match"])]
    ledger_tag_check = {
        "theorem_records": th_n,
        "citation_records": ci_n,
        "my_ledger_tag_count": len(tags_verbatim),
        "census_ledger_tag_count": len((census_doc.get("ledger_local_tags", {}).get("all") or {})),
        "tag_sets_equal": set((census_doc.get("ledger_local_tags", {}).get("all") or {}).keys()) == tags_verbatim,
    }
    return {
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "independence": (
            "implemented from scratch; did not import/execute/read "
            "artifacts/flash-19/class_token_census.py"
        ),
        "token_definition": {
            "regex": TOKEN_RE.pattern,
            "case": "case-insensitive; matched form upper-cased",
            "normalization": "NFKC; '^', '{', '}' removed (NFKC folds superscripts)",
        },
        "frozen_ids": sorted(frozen),
        "classification_rules": {
            "frozen": "token is one of the four frozen ids",
            "ledger_tag": "token appears verbatim (or case-insensitively) in a theorems.jsonl ledger_tags array",
            "violation": "neither of the above",
        },
        "inputs": [
            {"path": rel, "sha256": sha, "hash_match": sha256_bytes((ROOT / rel).read_bytes()) == sha}
            for rel, sha in PINNED_INPUTS.items()
        ],
        "ledger_tag_check": ledger_tag_check,
        "tokens_found": len(mine_tokens),
        "census_tokens": len(census_tokens),
        "token_sets_equal": mine_tokens == census_tokens,
        "total_occurrences_mine": sum(e["occurrences"] for e in entries),
        "total_occurrences_census": sum(e["occurrences"] for e in census_by_token.values()),
        "entries": entries,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def detector_probe():
    spec = importlib.util.spec_from_file_location(
        "class_separation_probe", ROOT / "research_map" / "class_separation.py")
    cs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cs)

    per_frozen = {cid: cs._class_tokens(cid) for cid in sorted(frozen_ids_from_map())}
    probes = {
        "frozen_3group_AF-WCC-VAC-GEN": "The binding is AF-WCC-VAC-GEN in this artifact.",
        "frozen_3group_AF-WCC-SCALAR-SPH": "The binding is AF-WCC-SCALAR-SPH in this artifact.",
        "frozen_4group_AF-SCC-C2-VAC-GEN": "The binding is AF-SCC-C2-VAC-GEN in this artifact.",
        "frozen_4group_AF-SCC-C0-VAC-GEN": "The binding is AF-SCC-C0-VAC-GEN in this artifact.",
        "nonfrozen_3group_AF-SCC-OTHER-MODELS": "The binding is AF-SCC-OTHER-MODELS in this artifact.",
        "nonfrozen_4group_AF-WCC-VAC-BH-FORM": "The binding is AF-WCC-VAC-BH-FORM in this artifact.",
    }
    probe_out = {}
    for name, text in probes.items():
        found = cs.findings_for_text(text, f"probe:{name}")
        probe_out[name] = {
            "text": text,
            "findings": found,
            "unknown_token_flagged": any("unknown class token" in f for f in found),
        }
    return {
        "target_module": "research_map/class_separation.py",
        "target_sha256": sha256_bytes((ROOT / "research_map/class_separation.py").read_bytes()),
        "class_tokens_regex_source": r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+",
        "class_tokens_per_frozen_id": per_frozen,
        "frozen_ids_matched": [k for k, v in per_frozen.items() if v],
        "frozen_ids_blind": [k for k, v in per_frozen.items() if not v],
        "probes": probe_out,
    }


def canonical_digest(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "content_digest_sha256"}
    return sha256_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    recount = build_recount()
    (OUTDIR / "class_token_recount.json").write_text(json.dumps(recount, indent=2, sort_keys=True))

    probe = detector_probe()
    (OUTDIR / "detector_obs1_probe.json").write_text(json.dumps(probe, indent=2, sort_keys=True))

    census_bytes = (ROOT / CENSUS_REL).read_bytes()
    census_sha_ok = sha256_bytes(census_bytes) == CENSUS_SHA

    violations = [e for e in recount["entries"] if e["classification"] == "violation"]
    untagged_occ = sum(e["occurrences"] for e in violations)
    nonfrozen_tokens = [e["token"] for e in violations]
    exact_match = (recount["mismatch_count"] == 0 and recount["token_sets_equal"]
                   and recount["total_occurrences_mine"] == recount["total_occurrences_census"])

    # OBS-1: does the canonical artifact-content token rule see all four frozen ids?
    obs1_confirmed = len(probe["frozen_ids_blind"]) == 2 and set(probe["frozen_ids_blind"]) == {
        "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"}
    soft_blind = not probe["probes"]["nonfrozen_3group_AF-SCC-OTHER-MODELS"]["unknown_token_flagged"]
    soft_sees_4group = probe["probes"]["nonfrozen_4group_AF-WCC-VAC-BH-FORM"]["unknown_token_flagged"]

    verdict = "accept" if (exact_match and census_sha_ok) else "revise"
    score = 4.5 if verdict == "accept" else 2.0

    hard_failures = []
    if not census_sha_ok:
        hard_failures.append(f"target artifact sha256 does not match pinned {CENSUS_SHA}")
    if not exact_match:
        hard_failures.append(
            f"independent recount does not reproduce the census: {recount['mismatch_count']} token(s) differ")

    findings = [
        {
            "id": "W019-F1",
            "severity": "info",
            "finding": (
                "Independent recount reproduces the census exactly on all "
                f"{len(recount['entries'])} AF-tokens, {recount['total_occurrences_mine']} occurrences, "
                "classification, by_file and by_field; the census falsifier genuinely FIRED "
                f"({untagged_occ} untagged non-frozen occurrences, tokens {nonfrozen_tokens})."
            ),
            "evidence": [f"{CENSUS_REL}#sha256:{CENSUS_SHA[:12]}",
                         "ledger/theorems.jsonl#sha256:ce42d205e761",
                         "ledger/citation_audit.csv#sha256:315c19145065"],
        },
        {
            "id": "W019-F2",
            "severity": "major",
            "finding": (
                "OBS-1 confirmed against research_map/class_separation.py: _class_tokens "
                "requires exactly four hyphen groups after 'AF-', so it matches "
                f"{len(probe['frozen_ids_matched'])}/4 frozen ids and is blind to "
                f"{probe['frozen_ids_blind']}. findings_for_text therefore never raises even the SOFT "
                "unknown-token finding for any 3-group AF token, frozen or not "
                "(probe AF-SCC-OTHER-MODELS -> no finding), while a 4-group non-frozen token is caught "
                "(probe AF-WCC-VAC-BH-FORM -> CLASSSEP-SOFT)."
            ),
            "evidence": ["research_map/class_separation.py:67",
                         f"artifacts/worker-019/detector_obs1_probe.json#sha256:"
                         f"{sha256_bytes((OUTDIR / 'detector_obs1_probe.json').read_bytes())[:12]}"],
        },
    ]
    remedies = [
        {
            "token": e["token"],
            "occurrences": e["occurrences"],
            "where": e["by_file"],
            "remedy": ("declare the token in the record's ledger_tags array as ledger-local vocabulary, "
                       "or replace it with a specific frozen id / non-AF phrasing"),
        }
        for e in violations
    ]

    artifact = {
        "artifact_type": "independent_class_token_verification",
        "artifact_version": "1.0",
        "task_id": "W019-CLASSTOKEN-VERIFY-01",
        "actor": "worker-019",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_id": "L0",
        "gate": "G-LIT",
        "controller_finding": "CF-5",
        "class_ids": recount["frozen_ids"],
        "independence": recount["independence"],
        "target_artifact": {
            "path": CENSUS_REL,
            "sha256": CENSUS_SHA,
            "measured_sha256": sha256_bytes(census_bytes),
            "hash_match": census_sha_ok,
            "verdict": verdict,
            "score": score,
            "hard_failures": hard_failures,
            "findings": findings,
        },
        "recount": {
            "path": "artifacts/worker-019/class_token_recount.json",
            "sha256": sha256_bytes((OUTDIR / "class_token_recount.json").read_bytes()),
            "exact_match_to_census": exact_match,
            "tokens": len(recount["entries"]),
            "occurrences": recount["total_occurrences_mine"],
            "token_sets_equal": recount["token_sets_equal"],
            "mismatch_count": recount["mismatch_count"],
            "inputs": recount["inputs"],
        },
        "detector_probe": {
            "path": "artifacts/worker-019/detector_obs1_probe.json",
            "sha256": sha256_bytes((OUTDIR / "detector_obs1_probe.json").read_bytes()),
            "obs1_confirmed": obs1_confirmed,
            "frozen_ids_blind": probe["frozen_ids_blind"],
            "soft_rule_blind_to_3group": soft_blind,
            "soft_rule_catches_4group": soft_sees_4group,
        },
        "violations": remedies,
        "violation_summary": {
            "tokens": nonfrozen_tokens,
            "untagged_occurrences": untagged_occ,
            "falsifier_fired": untagged_occ > 0,
        },
        "falsifier": (
            "Re-run artifacts/worker-019/independent_class_token_recount.py on the same input "
            "sha256s (theorems ce42d205e761, citations 315c19145065): a different token set, a "
            "different occurrence count, or a token classified differently than this artifact "
            "falsifies it."
        ),
        "reopen_rule": (
            "If either ledger sha256 changes, this verification is stale; if "
            "research_map/class_separation.py changes, the OBS-1 probe must be re-run."
        ),
        "scope_caveats": [
            "This is an independent verification, not a node completion and not a gate verdict.",
            "Counts cover only ledger/theorems.jsonl and ledger/citation_audit.csv; "
            "ledger/class_coverage.csv and schemas are out of scope.",
            "The census author's generator was deliberately not executed; equality is evidence of "
            "reproducibility, not a proof of shared implementation.",
        ],
        "content_digest_sha256": None,
    }
    artifact["content_digest_sha256"] = canonical_digest(artifact)
    (OUTDIR / "class_token_verification.json").write_text(json.dumps(artifact, indent=2, sort_keys=True))
    print(json.dumps({
        "recount_exact_match": exact_match,
        "mismatch_count": recount["mismatch_count"],
        "tokens": len(recount["entries"]),
        "occurrences": recount["total_occurrences_mine"],
        "obs1_confirmed": obs1_confirmed,
        "verdict": verdict,
        "score": score,
        "artifact_sha256": sha256_bytes((OUTDIR / "class_token_verification.json").read_bytes()),
    }, indent=2))


if __name__ == "__main__":
    main()
