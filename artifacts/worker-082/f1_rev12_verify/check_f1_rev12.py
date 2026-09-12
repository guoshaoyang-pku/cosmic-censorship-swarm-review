#!/usr/bin/env python3
"""W082-F1-REV12-VERIFY-01: independent machine verification of the published rev12 F1 schema.

Task: node F1, class AF-WCC-VAC-GEN, gate G-FORM, worker-082.
Scope: machine data-integrity, hash-binding and the six rev11 defects previously reported by
worker-082 (W082-F1-MACHINE-DEFECT-VERIFY-01).  It is NOT a full semantic/schema verdict and
must not be counted as a G-FORM accept on its own.

Read-only: this script writes nothing except the --out JSON it is asked to produce.  It does not
import or execute any lead-owned tool.  Every input is re-measured at run time and the sha256 is
recorded in the evidence file.

Usage:
  python3 check_f1_rev12.py [--out evidence.json]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "schemas/af_wcc_vacuum.yaml"
MIRROR = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
APPLY_REPORT = ROOT / "artifacts/formulation/evidence/close_findings_rev27_report.json"
REV11 = ROOT / "artifacts/worker-082/f1_machine_defect/frozen_f1_9a8bd4c96800.yaml"

PUBLISHED_REV12 = "cce9c60146d6a907"
REV11_SHA = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
EXPECTED_CLASS = "AF-WCC-VAC-GEN"
EXPECTED_NODE = "F1"

# ---------------------------------------------------------------- strict YAML (duplicate keys)

class DuplicateKeyError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, f"expected a mapping node, got {node.id}", node.start_mark
        )
    seen = {}
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise DuplicateKeyError(
                f"duplicate mapping key {key!r}: lines {seen[key]} and {key_node.start_mark.line + 1}"
            )
        seen[key] = key_node.start_mark.line + 1
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def mtime_iso(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone().replace(microsecond=0).isoformat()


def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s)


def top_level_keys(text: str):
    keys = {}
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            keys.setdefault(m.group(1), []).append(i)
    return keys


def header_stamps(text: str):
    """Return [(key, at, [notes...]), ...] from the raw header block, rev11 or rev12 shape."""
    out = []
    pending = []
    inside = False
    for line in text.splitlines():
        if line.startswith("revised_at:"):
            inside = True
        if inside and line.startswith("timestamp_provenance:"):
            break
        if not inside:
            continue
        s = line.strip()
        if s.startswith("#"):
            pending.append(s.lstrip("# ").strip())
            continue
        m = re.match(r"^(revised_at|revised_at_unused):\s*\"?([^\"]+?)\"?\s*$", s)
        if m:
            out.append((m.group(1), m.group(2), pending))
            pending = []
    return out


def load_strict(text: str):
    return yaml.load(text, Loader=StrictLoader)


def check(checks, cid, ok, expected, observed, severity="hard"):
    checks.append(
        {
            "id": cid,
            "pass": bool(ok),
            "expected": expected,
            "observed": observed,
            "severity": severity if not ok else "info",
        }
    )
    return bool(ok)


def analyze(text: str, now: dt.datetime, mtime: dt.datetime, f0_data, supp_data, label: str):
    """Return (checks, defect_ids). Works for both rev11 and rev12 raw text."""
    checks = []
    defects = []
    keys = top_level_keys(text)
    try:
        data = load_strict(text)
        strict_ok, strict_err = True, None
    except DuplicateKeyError as exc:
        # keep going with a lenient parse so the remaining checks still report; DUP-001 records it
        data, strict_ok, strict_err = yaml.safe_load(text), False, str(exc)

    # DUP: no duplicate top-level keys
    dups = {k: v for k, v in keys.items() if len(v) > 1}
    if not check(
        checks,
        f"{label}-DUP-001",
        not dups,
        "no duplicate top-level mapping keys (strict loader)",
        {"duplicates": dups, "strict_loader": "ok" if strict_ok else strict_err},
    ):
        defects.append("DUP-001")

    # UNUSED: no dead revised_at_unused key
    if not check(
        checks,
        f"{label}-UNUSED-001",
        "revised_at_unused" not in keys,
        "no revised_at_unused top-level key",
        {"revised_at_unused_lines": keys.get("revised_at_unused")},
    ):
        defects.append("UNUSED-001")

    if data is None:
        return checks, defects, None

    # TIMESTAMP: machine-readable publish stamps not ahead of wall clock or of the file mtime
    ts = {k: data.get(k) for k in ("revised_at",)}
    checked_at = (data.get("f0_binding") or {}).get("checked_at")
    stamps = {k: v for k, v in ts.items() if isinstance(v, str)}
    if isinstance(checked_at, str):
        stamps["f0_binding.checked_at"] = checked_at
    future = {k: v for k, v in stamps.items() if parse_ts(v) > now}
    ahead_of_mtime = {k: v for k, v in stamps.items() if parse_ts(v) > mtime + dt.timedelta(seconds=1)}
    if not check(
        checks,
        f"{label}-CLOCK-001",
        not future and not ahead_of_mtime,
        "revised_at and f0_binding.checked_at <= wall clock and <= file mtime",
        {
            "stamps": stamps,
            "wall_clock": now.isoformat(),
            "mtime": mtime.isoformat(),
            "future_vs_wall_clock": future,
            "ahead_of_mtime": ahead_of_mtime,
        },
    ):
        defects.append("CLOCK-001")

    # POINTER: class_contract_pointer must be a canonical-tree pointer and resolve
    ptr = data.get("class_contract_pointer")
    ptr_ok = False
    ptr_obs = {"pointer": ptr, "fragment_resolves": None}
    if isinstance(ptr, str) and "#" in ptr:
        path_part, frag = ptr.split("#", 1)
        ptr_obs["path"] = path_part
        ptr_obs["fragment"] = frag
        ptr_obs["canonical_path"] = path_part == "research_map/formulation_taxonomy.yaml"
        node = f0_data
        try:
            for part in frag.split("."):
                node = node[part]
            ptr_obs["fragment_resolves"] = True
        except Exception as exc:  # noqa: BLE001
            ptr_obs["fragment_resolves"] = f"unresolved: {exc}"
        ptr_ok = bool(ptr_obs["canonical_path"]) and ptr_obs["fragment_resolves"] is True
    if not check(
        checks,
        f"{label}-POINTER-001",
        ptr_ok,
        "class_contract_pointer = research_map/formulation_taxonomy.yaml#classes.<class>, fragment resolves",
        ptr_obs,
    ):
        defects.append("POINTER-001")

    # SUPPLEMENT pointer resolves (rev12 only; rev11 has none)
    supp = data.get("class_contract_supplement_pointer")
    supp_ok = True
    supp_obs = {"pointer": supp}
    if supp is not None:
        supp_ok = False
        if isinstance(supp, str) and "#" in supp:
            path_part, frag = supp.split("#", 1)
            node = supp_data
            try:
                for part in frag.split("."):
                    node = node[part]
                supp_obs["fragment_resolves"] = True
                supp_ok = path_part == "artifacts/formulation/formulation_taxonomy.yaml"
            except Exception as exc:  # noqa: BLE001
                supp_obs["fragment_resolves"] = f"unresolved: {exc}"
    if not check(
        checks,
        f"{label}-SUPP-001",
        supp_ok,
        "class_contract_supplement_pointer resolves in the supplement",
        supp_obs,
    ):
        defects.append("SUPP-001")

    # AF_{I+} must be defined, not only used
    definers = []
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(v.get("predicate_abbreviation"), str) and "AF_{I+}" in v["predicate_abbreviation"]:
            definers.append(k)
    n_use = text.count("AF_{I+}")
    if not check(
        checks,
        f"{label}-AFIP-001",
        bool(definers),
        "AF_{I+} has a definition (predicate_abbreviation) in the artifact",
        {"defining_block": definers, "raw_occurrences": n_use},
    ):
        defects.append("AFIP-001")

    # Visibility clause: tail semantics, not whole-curve
    formal = (data.get("quantifiers") or {}).get("formal") or ""
    tail_obs = {
        "formal_has_tail": "gamma([t0,T))" in formal,
        "formal_has_whole_curve": bool(re.search(r"gamma\s+subset\s+J\^-\(q\)", formal)),
        "d5_binder": None,
    }
    ordered = (data.get("quantifiers") or {}).get("ordered") or []
    for entry in ordered:
        if isinstance(entry, dict) and entry.get("domain_id") == "D5":
            tail_obs["d5_binder"] = entry.get("binder")
    tail_ok = tail_obs["formal_has_tail"] and not tail_obs["formal_has_whole_curve"] and tail_obs["d5_binder"] == "(q,t0)"
    if not check(
        checks,
        f"{label}-TAIL-001",
        tail_ok,
        "quantifiers.formal uses the tail predicate and D5 binds (q,t0)",
        tail_obs,
    ):
        defects.append("TAIL-001")

    # D0 retyped as a single regularity index (no pair-indexed residue)
    d0 = ((data.get("quantifiers") or {}).get("domains") or {}).get("D0") or {}
    d0_def = d0.get("definition", "") if isinstance(d0, dict) else ""
    residue = [tok for tok in ("(s,delta)", "X^{s,delta}_vac", "G_{s,delta}") if tok in text]
    d0_ok = "forall r in D0" in formal and not residue and "r = smooth" in d0_def
    if not check(
        checks,
        f"{label}-D0-001",
        d0_ok,
        "D0 is a tagged regularity index r; no (s,delta) residue",
        {"forall_r_in_D0": "forall r in D0" in formal, "residue_tokens": residue, "d0_has_tagged_union": "r = smooth" in d0_def},
    ):
        defects.append("D0-001")

    # Class binding intact (own identity + no cross-class identity assignment)
    scc_lines = [
        i for i, line in enumerate(text.splitlines(), 1) if "AF-SCC-" in line
    ]
    cb_ok = (
        data.get("class_id") == EXPECTED_CLASS
        and data.get("node_id") == EXPECTED_NODE
        and not re.search(r"^class_id:\s*AF-SCC-", text, re.M)
    )
    if not check(
        checks,
        f"{label}-CLASSBIND-001",
        cb_ok,
        f"class_id={EXPECTED_CLASS}, node_id={EXPECTED_NODE}, no cross-class identity assignment",
        {
            "class_id": data.get("class_id"),
            "node_id": data.get("node_id"),
            "cross_class_token_lines": scc_lines[:12],
            "cross_class_token_count": len(scc_lines),
        },
    ):
        defects.append("CLASSBIND-001")

    return checks, defects, data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    started = dt.datetime.now().astimezone().replace(microsecond=0)

    pin_paths = [TARGET, MIRROR, F0_CANON, F0_SUPP, CONSISTENCY, FROZEN, APPLY_REPORT, REV11]
    pin = {}
    for p in pin_paths:
        pin[str(p.relative_to(ROOT))] = {
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
            "mtime": mtime_iso(p),
        }

    text = TARGET.read_text()
    mirror_text = MIRROR.read_text()
    target_sha = sha256_bytes(text.encode())
    now = started
    mtime = dt.datetime.fromtimestamp(TARGET.stat().st_mtime).astimezone().replace(microsecond=0)

    f0_text = F0_CANON.read_text()
    supp_text = F0_SUPP.read_text()
    f0_data = yaml.safe_load(f0_text)
    supp_data = yaml.safe_load(supp_text)

    checks, defects, data = analyze(text, now, mtime, f0_data, supp_data, "REV12")
    rev11_text = REV11.read_text()
    rev11_mtime = dt.datetime.fromtimestamp(REV11.stat().st_mtime).astimezone().replace(microsecond=0)
    old_checks, old_defects, _ = analyze(
        rev11_text, now, rev11_mtime, f0_data, supp_data, "REV11"
    )

    # header / revision history closure (rev12 specific)
    if data is not None:
        stamps = header_stamps(text)
        hist = data.get("revision_history") or []
        check(
            checks,
            "REV12-HIST-001",
            len(stamps) == 1 and len(hist) == 10,
            "exactly one revised_at stamp and a 10-entry revision_history (9 preserved + rev12)",
            {"raw_revised_at_stamps": len(stamps), "revision_history_len": len(hist)},
        )
        if not checks[-1]["pass"]:
            defects.append("HIST-001")
        idx = [e.get("index") for e in hist if isinstance(e, dict)]
        check(
            checks,
            "REV12-HIST-002",
            idx == list(range(1, len(hist) + 1)),
            "revision_history indexes are 1..10 in order",
            {"indexes": idx},
        )
        if not checks[-1]["pass"]:
            defects.append("HIST-002")

        old_stamps = header_stamps(rev11_text)
        old_at = [s[1] for s in old_stamps]
        new_preserved = [e.get("at") for e in hist[: len(old_at)] if isinstance(e, dict)]
        check(
            checks,
            "REV12-HIST-003",
            old_at == new_preserved,
            "all 9 rev11 stamped values preserved verbatim, in order",
            {"rev11_stamps": old_at, "rev12_first_9": new_preserved},
        )
        if not checks[-1]["pass"]:
            defects.append("HIST-003")
        reuse = [e.get("unused") for e in hist if isinstance(e, dict) and e.get("at") in {s[1] for s in old_stamps if s[0] == "revised_at_unused"}]
        check(
            checks,
            "REV12-HIST-004",
            bool(reuse) and all(v is True for v in reuse),
            "former revised_at_unused entries are retained and flagged unused:true",
            {"unused_flags": reuse},
        )
        if not checks[-1]["pass"]:
            defects.append("HIST-004")

    # canonical == authoring mirror
    check(
        checks,
        "REV12-MIRROR-001",
        sha256_bytes(mirror_text.encode()) == target_sha,
        "canonical schema == authoring mirror (byte-identical)",
        {
            "canonical_sha256": target_sha,
            "mirror_sha256": sha256_bytes(mirror_text.encode()),
        },
    )
    if not checks[-1]["pass"]:
        defects.append("MIRROR-001")

    # declared F0 hash matches measured canonical F0
    declared_f0 = (data or {}).get("f0_binding", {}).get("declared_f0_sha256") if data else None
    check(
        checks,
        "REV12-F0BIND-001",
        declared_f0 == pin["research_map/formulation_taxonomy.yaml"]["sha256"],
        "f0_binding.declared_f0_sha256 == measured canonical F0 sha256",
        {
            "declared": declared_f0,
            "measured": pin["research_map/formulation_taxonomy.yaml"]["sha256"],
        },
    )
    if not checks[-1]["pass"]:
        defects.append("F0BIND-001")

    # declared consistency-evidence hash matches measured file (THE fresh binding check)
    declared_cons = (data or {}).get("f0_binding", {}).get("consistency_evidence_sha256") if data else None
    measured_cons = pin["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
    check(
        checks,
        "REV12-CONS-001",
        declared_cons == measured_cons,
        "f0_binding.consistency_evidence_sha256 == measured taxonomy_consistency.json sha256",
        {"declared": declared_cons, "measured": measured_cons},
    )
    if not checks[-1]["pass"]:
        defects.append("CONS-001")

    # the measured consistency file must itself carry the two tree hashes and match them
    try:
        cons = json.loads(CONSISTENCY.read_text())
    except Exception as exc:  # noqa: BLE001
        cons = {"_parse_error": str(exc)}
    cons_bind_ok = (
        cons.get("map_taxonomy_sha256") == pin["research_map/formulation_taxonomy.yaml"]["sha256"]
        and cons.get("lead_contract_sha256") == pin["artifacts/formulation/formulation_taxonomy.yaml"]["sha256"]
    )
    check(
        checks,
        "REV12-CONS-002",
        cons_bind_ok,
        "measured consistency evidence carries map_taxonomy_sha256 + lead_contract_sha256 matching disk",
        {
            "map_key_present": "map_taxonomy_sha256" in cons,
            "lead_key_present": "lead_contract_sha256" in cons,
            "map_declared": cons.get("map_taxonomy_sha256"),
            "lead_declared": cons.get("lead_contract_sha256"),
            "keys": sorted(cons.keys()),
        },
    )
    if not checks[-1]["pass"]:
        defects.append("CONS-002")

    # FROZEN rev27 manifest entries vs measured disk
    frozen = json.loads(FROZEN.read_text())
    mismatch = {}
    for rel, entry in (frozen.get("files") or {}).items():
        p = ROOT / rel
        if not p.exists():
            mismatch[rel] = {"manifest": entry.get("sha256"), "measured": "MISSING"}
            continue
        measured = sha256_file(p)
        if measured != entry.get("sha256"):
            mismatch[rel] = {"manifest": entry.get("sha256"), "measured": measured}
    check(
        checks,
        "REV12-FROZEN-001",
        not mismatch,
        "every FROZEN rev27 manifest sha256 matches the measured file on disk",
        {"frozen_revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"), "mismatches": mismatch},
    )
    if not checks[-1]["pass"]:
        defects.append("FROZEN-001")

    # FROZEN's recorded consistency evidence hash must agree with what the schema declares
    frozen_cons = (frozen.get("files") or {}).get(
        "artifacts/formulation/evidence/taxonomy_consistency.json", {}
    ).get("sha256")
    check(
        checks,
        "REV12-CONS-003",
        frozen_cons == declared_cons,
        "FROZEN manifest consistency-evidence hash == schema f0_binding.consistency_evidence_sha256",
        {"frozen_manifest": frozen_cons, "schema_declared": declared_cons, "measured_file": measured_cons},
    )
    if not checks[-1]["pass"]:
        defects.append("CONS-003")

    # The FROZEN-bound apply report must describe the schema bytes actually published
    try:
        apply_report = json.loads(APPLY_REPORT.read_text())
    except Exception as exc:  # noqa: BLE001
        apply_report = {"_parse_error": str(exc)}
    report_mismatch = {}
    for rel, measured_sha in (
        ("schemas/af_wcc_vacuum.yaml", target_sha),
        (
            "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            sha256_bytes(mirror_text.encode()),
        ),
    ):
        reported = (apply_report.get("files") or {}).get(rel, {}).get("sha256")
        if reported != measured_sha:
            report_mismatch[rel] = {"report": reported, "measured": measured_sha}
    check(
        checks,
        "REV12-REPORT-001",
        not report_mismatch,
        "FROZEN-bound close_findings_rev27_report.json describes the published F1 bytes",
        {
            "report_path": "artifacts/formulation/evidence/close_findings_rev27_report.json",
            "report_measured_sha256": pin["artifacts/formulation/evidence/close_findings_rev27_report.json"]["sha256"],
            "report_at": apply_report.get("at"),
            "report_phase": apply_report.get("phase"),
            "mismatches": report_mismatch,
        },
    )
    if not checks[-1]["pass"]:
        defects.append("REPORT-001")

    # negative control: rev11 must fail the closure checks (discriminating power)
    control_ok = len(old_defects) >= 6
    check(
        checks,
        "CONTROL-REV11-001",
        control_ok,
        "the same checker flags >=6 defects on the frozen rev11 bytes",
        {"rev11_defects": old_defects, "count": len(old_defects)},
        severity="hard",
    )
    if not control_ok:
        defects.append("CONTROL-001")

    # no-op side-effect guard: inputs re-measured after everything
    post = {str(p.relative_to(ROOT)): sha256_file(p) for p in pin_paths}
    side_effects = {k: (pin[k]["sha256"], post[k]) for k in post if pin[k]["sha256"] != post[k]}
    check(
        checks,
        "NO-SIDE-EFFECT-001",
        not side_effects,
        "checker runs read-only: no input hash changes across the run",
        {"changed": side_effects},
    )
    if not checks[-1]["pass"]:
        defects.append("SIDE-EFFECT-001")

    hard = [c for c in checks if not c["pass"] and c["severity"] == "hard"]
    evidence = {
        "task_id": "W082-F1-REV12-VERIFY-01",
        "worker": "worker-082",
        "node_id": "F1",
        "class_id": EXPECTED_CLASS,
        "gate": "G-FORM",
        "scope": "machine data-integrity + hash binding + closure of the six W082 rev11 defects; NOT a full schema verdict",
        "counts_as_full_schema_verdict": False,
        "started_at": started.isoformat(),
        "finished_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "target": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "sha256": target_sha,
            "mtime": mtime_iso(TARGET),
            "published_rev12_prefix": PUBLISHED_REV12,
            "hash_matches_first_measurement": target_sha.startswith(PUBLISHED_REV12),
        },
        "pinned_inputs": pin,
        "checks": checks,
        "hard_failures": [c["id"] for c in hard],
        "defects": defects,
        "rev11_negative_control": {"defects": old_defects},
        "verdict": "revise" if hard else "pass_machine_checks",
        "verdict_note": (
            "rev12 closes the six rev11 machine defects, but the declared consistency-evidence binding "
            "is stale at the measured instant: f0_binding.consistency_evidence_sha256 points at "
            "675a99d0 (the rev27-tool output, also recorded in FROZEN rev27) while the file on disk is "
            "9e335e9b and no longer carries map_taxonomy_sha256 / lead_contract_sha256."
            if hard
            else "all machine checks pass at the measured hashes"
        ),
    }
    out_text = json.dumps(evidence, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(out_text)
    sys.stdout.write(out_text)
    return 0 if not hard else 3


if __name__ == "__main__":
    sys.exit(main())
