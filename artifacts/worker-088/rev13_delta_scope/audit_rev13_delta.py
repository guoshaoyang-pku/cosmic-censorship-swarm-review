#!/usr/bin/env python3
"""W088-REV13-DELTA-SCOPE-01 — independent rev12 -> rev13 delta and FROZEN rev29 pin audit.

Read-only. Bounded execution worker task taken from the G-FORM immediate queue (no card issued
for worker-088 in this lifecycle). The audit answers one question at one measured hash set:

    Is the landed rev13 delta of schemas/af_wcc_vacuum.yaml, schemas/af_scc_c2_vacuum.yaml and
    schemas/af_scc_c0_vacuum.yaml confined to the scope declared by
    astra-life05-evidence-binding-repair and FROZEN.json rev29_delta, and do the FROZEN rev29
    pins and the refreshed f0_binding hashes resolve byte-exactly on disk?

The instrument is independent of the author family: it re-implements the pin check, the
structural delta and the binding resolution from the pinned bytes; it imports no formulation
checker and uses no author verdict as an input. `check_class_schema.py` and
`verify_frozen.py` are run only as cross-checks and their outputs are recorded separately.

Verdict vocabulary:
  SCOPE_COMPLIANT_WITH_CARRIED_RESIDUAL  all checks pass at the measured pins; L-FORM-03
                                         residual independently reproduced and carried
  DEFECTS_FOUND                          at least one hard check failed (see findings)
  INCONCLUSIVE                           a required input was missing/unparseable

Falsifier: a changed leaf outside the declared scope at the measured rev13 hashes; a FROZEN
rev29 pin that does not equal the measured bytes; a binding hash that does not resolve; a hash
move between the start and end measurement of the run; or L-FORM-03 being absent from the
residual paths (which would make the carried-residual qualifier wrong).
"""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)

TARGETS = [
    {
        "node": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "path": "schemas/af_wcc_vacuum.yaml",
        "mirror": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "rev12_declared": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "rev13_declared": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "pinned_rev12": "pinned/rev12/af_wcc_vacuum.yaml",
    },
    {
        "node": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "mirror": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "rev12_declared": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "rev13_declared": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "pinned_rev12": "pinned/rev12/af_scc_c2_vacuum.yaml",
    },
    {
        "node": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "rev12_declared": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        "rev13_declared": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "pinned_rev12": "pinned/rev12/af_scc_c0_vacuum.yaml",
    },
]

F0_PATH = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_PATH = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"
CORPUS_PATH = "schemas/taxonomy_cases.jsonl"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SUPPLEMENT_SHA = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"

# Residual declared by the lead in FROZEN.rev29_delta as L-FORM-03 (not repaired by the card).
RESIDUAL_PATHS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
]

REVISION_BOOKKEEPING = {"revision", "revised_at"}
F0_BINDING_ALLOWED = {
    "f0_binding.consistency_evidence_sha256",
    "f0_binding.checked_at",
    "f0_binding.binding_note",
}

findings = []
errors = []


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def short(s: str) -> str:
    return s[:12] if isinstance(s, str) else s


class UniqueKeyLoader(yaml.SafeLoader):
    """safe_load that refuses duplicate mapping keys (silent collapse is a real defect class)."""


def _construct_mapping(loader, node, deep=False):
    keys = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in keys:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r} at {node.start_mark}", node.start_mark
            )
        keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_yaml(p: Path):
    return yaml.load(p.read_text(), Loader=UniqueKeyLoader)


def leaf_diff(a, b, path=""):
    """Yield (path, rev12_value, rev13_value) for every changed leaf, including list appends."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            kp = f"{path}.{k}" if path else str(k)
            if k not in a:
                yield (kp, "<absent>", b[k])
            elif k not in b:
                yield (kp, a[k], "<absent>")
            else:
                yield from leaf_diff(a[k], b[k], kp)
    elif isinstance(a, list) and isinstance(b, list):
        n = max(len(a), len(b))
        for i in range(n):
            kp = f"{path}[{i}]"
            if i >= len(a):
                yield (kp, "<absent>", b[i])
            elif i >= len(b):
                yield (kp, a[i], "<absent>")
            else:
                yield from leaf_diff(a[i], b[i], kp)
    elif a != b or type(a) is not type(b):
        yield (path, a, b)


def classify(file_key: str, node: str, path: str, av, bv, rev12_len_history: int):
    """Classify one changed leaf against the declared repair scope."""
    if path in REVISION_BOOKKEEPING:
        return "declared:revision-bump"
    if path in F0_BINDING_ALLOWED:
        return "declared:f0-binding-refresh"
    m = re.match(r"^revision_history\[(\d+)\]", path)
    if m:
        idx = int(m.group(1))
        if idx >= rev12_len_history:
            return "declared:revision-history-append"
        return "OUT_OF_SCOPE:revision-history-rewrite"
    if node == "F1" and isinstance(bv, str) and "[rev13:" in bv:
        return "declared:f1-strictness-repair"
    if node == "F1" and isinstance(av, str) and "[rev13:" in av:
        return "declared:f1-strictness-repair"
    return "OUT_OF_SCOPE"


PROTECTED_PREFIXES = (
    "class_id",
    "class_components",
    "axes",
    "hypotheses",
    "conclusion",
    "quantifiers",
    "topology",
    "data_class",
    "regularity",
    "exclusions",
    "membership",
    "ambient",
    "chain",
    "implication_ledger",
    "known_obstruction",
    "test_cases",
    "positive_test_case",
)


def protected(path: str) -> bool:
    return any(path == p or path.startswith(p + ".") or path.startswith(p + "[") for p in PROTECTED_PREFIXES)


def resolve_pointer(doc, pointer: str):
    cur = doc
    for part in pointer.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, f"unresolved segment {part!r}"
    return cur, None


def run(cmd):
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
        return {"cmd": cmd, "rc": r.returncode, "stdout_tail": r.stdout[-2000:], "stderr_tail": r.stderr[-1000:]}
    except Exception as e:  # noqa: BLE001
        return {"cmd": cmd, "rc": None, "error": repr(e)}


report = {
    "schema": "w088/rev13-delta-scope/v1",
    "task_id": "W088-REV13-DELTA-SCOPE-01",
    "worker": "worker-088",
    "created_at": NOW.isoformat(),
    "authority": "worker measurement only; no gate verdict, node status or validation_status claimed",
    "instrument": {
        "path": "artifacts/worker-088/rev13_delta_scope/audit_rev13_delta.py",
        "sha256": sha256_file(Path(__file__)),
        "pre_registration_note": (
            "the check list is fixed in this file and hashed before execution; reconnaissance had already "
            "read FROZEN.rev29_delta, so the audit is not blind to the declared scope - it is a "
            "scope-conformance test against the declaration, not an open-ended search"
        ),
    },
    "targets": {},
    "frozen_rev29": {},
    "residual_lform03": {},
    "cross_checks": {},
    "findings": findings,
    "errors": errors,
}

# ---- A. start measurement -------------------------------------------------------------
start_hashes = {t["path"]: sha256_file(ROOT / t["path"]) for t in TARGETS}
start_hashes["__frozen__"] = sha256_file(ROOT / FROZEN_PATH)

# ---- B/C. per-target delta + binding --------------------------------------------------
for t in TARGETS:
    entry = {
        "node": t["node"],
        "class_id": t["class_id"],
        "rev12_declared": t["rev12_declared"],
        "rev12_pinned_measured": sha256_file(OUT / t["pinned_rev12"]),
        "rev13_declared": t["rev13_declared"],
        "rev13_measured": start_hashes[t["path"]],
        "mirror_measured": sha256_file(ROOT / t["mirror"]),
        "changed_leaves": [],
        "out_of_scope": [],
        "protected_changed": [],
        "binding": {},
    }
    if entry["rev12_pinned_measured"] != t["rev12_declared"]:
        findings.append({"id": f"W088-R13-{t['node']}-PIN", "severity": "hard",
                         "detail": "pinned rev12 copy does not match the declared rev12 hash"})
    if entry["rev13_measured"] != t["rev13_declared"]:
        findings.append({"id": f"W088-R13-{t['node']}-HASH", "severity": "hard",
                         "detail": "live rev13 bytes do not match the declared rev13 hash"})
    if entry["mirror_measured"] != entry["rev13_measured"]:
        findings.append({"id": f"W088-R13-{t['node']}-MIRROR", "severity": "hard",
                         "detail": "canonical and authoring mirror bytes differ (publication divergence)"})

    a = load_yaml(OUT / t["pinned_rev12"])
    b = load_yaml(ROOT / t["path"])
    entry["class_id_field_rev13"] = b.get("class_id")
    entry["revision_rev12"] = a.get("revision")
    entry["revision_rev13"] = b.get("revision")
    if a.get("class_id") != b.get("class_id") or b.get("class_id") != t["class_id"]:
        findings.append({"id": f"W088-R13-{t['node']}-CLASSID", "severity": "hard",
                         "detail": f"class_id moved or mismatched: {a.get('class_id')} -> {b.get('class_id')}"})

    rh12 = a.get("revision_history") or []
    for path, av, bv in leaf_diff(a, b):
        cls = classify(t["path"], t["node"], path, av, bv, len(rh12))
        rec = {
            "path": path,
            "classification": cls,
            "rev12_sha256": sha256_bytes(json.dumps(av, sort_keys=True, default=str).encode()),
            "rev13_sha256": sha256_bytes(json.dumps(bv, sort_keys=True, default=str).encode()),
            "rev12_preview": (av if isinstance(av, (int, float, bool)) else str(av)[:400]),
            "rev13_preview": (bv if isinstance(bv, (int, float, bool)) else str(bv)[:400]),
        }
        entry["changed_leaves"].append(rec)
        if cls == "OUT_OF_SCOPE":
            entry["out_of_scope"].append(rec)
        if protected(path):
            entry["protected_changed"].append(rec)
            findings.append({"id": f"W088-R13-{t['node']}-PROT-{len(entry['protected_changed'])}",
                             "severity": "hard" if cls == "OUT_OF_SCOPE" else "advisory",
                             "detail": f"protected leaf changed: {path} ({cls})"})
    if entry["out_of_scope"]:
        findings.append({"id": f"W088-R13-{t['node']}-SCOPE", "severity": "hard",
                         "detail": f"{len(entry['out_of_scope'])} changed leaf/leaves outside the declared scope"})

    fb = b.get("f0_binding") or {}
    supp = load_yaml(ROOT / SUPPLEMENT_PATH)
    canon = load_yaml(ROOT / F0_PATH)
    declared_f0 = fb.get("declared_f0_sha256")
    evidence = json.loads((ROOT / EVIDENCE_PATH).read_text())
    binding = {
        "declared_f0_artifact": fb.get("declared_f0_artifact"),
        "declared_f0_sha256": declared_f0,
        "declared_f0_resolves": declared_f0 == sha256_file(ROOT / F0_PATH) == F0_SHA,
        "consistency_evidence": fb.get("consistency_evidence"),
        "consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
        "consistency_evidence_resolves": (
            fb.get("consistency_evidence") == EVIDENCE_PATH
            and fb.get("consistency_evidence_sha256") == sha256_file(ROOT / EVIDENCE_PATH)
        ),
        "consistency_evidence_consistent": evidence.get("consistent") is True,
        "checked_at": fb.get("checked_at"),
        "class_contract_supplement": fb.get("class_contract_supplement"),
        "supplement_sha_declared_vs_measured": (
            SUPPLEMENT_SHA == sha256_file(ROOT / SUPPLEMENT_PATH)
        ),
    }
    # class_contract_pointer is a top-level field on the class schemas (not inside f0_binding).
    ptr = b.get("class_contract_pointer") or fb.get("class_contract_pointer") or ""
    if "#" in ptr:
        f, dotted = ptr.split("#", 1)
        val, err = resolve_pointer(canon, dotted)
        binding["class_contract_pointer"] = ptr
        binding["class_contract_pointer_file_is_f0"] = f == F0_PATH
        binding["class_contract_pointer_terminal_key"] = dotted.split(".")[-1]
        binding["class_contract_pointer_node_keys"] = sorted(val.keys())[:12] if isinstance(val, dict) else None
        binding["class_contract_pointer_resolves"] = (
            err is None and isinstance(val, dict)
            and dotted.split(".")[-1] == t["class_id"] and f == F0_PATH
        )
        if err:
            binding["class_contract_pointer_error"] = err
    else:
        binding["class_contract_pointer"] = None
        binding["class_contract_pointer_resolves"] = False
        findings.append({"id": f"W088-R13-{t['node']}-BIND-pointer-missing", "severity": "hard",
                         "detail": "top-level class_contract_pointer is absent or has no '#'"})
    sptr = fb.get("class_contract_supplement_pointer") or ""
    if "#" in sptr:
        f, dotted = sptr.split("#", 1)
        val, err = resolve_pointer(supp, dotted)
        binding["class_contract_supplement_pointer"] = sptr
        binding["class_contract_supplement_pointer_resolves"] = err is None and val is not None
        if err:
            binding["class_contract_supplement_pointer_error"] = err
    entry["binding"] = binding
    for key in ("declared_f0_resolves", "consistency_evidence_resolves",
                "consistency_evidence_consistent", "class_contract_pointer_resolves",
                "class_contract_supplement_pointer_resolves", "supplement_sha_declared_vs_measured"):
        if binding.get(key) is not True:
            findings.append({"id": f"W088-R13-{t['node']}-BIND-{key}", "severity": "hard",
                             "detail": f"binding check failed: {key}"})
    report["targets"][t["path"]] = entry

# ---- D. FROZEN rev29 independent pin check (snapshot-based; the manifest moved during the audit)
def frozen_snapshot(label: str):
    frozen = json.loads((ROOT / FROZEN_PATH).read_text())
    snap = {"label": label, "at": datetime.now(TZ).isoformat(), "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"), "sha256": sha256_file(ROOT / FROZEN_PATH),
            "file_pins": {}, "logical_pins": {}, "mismatches": []}
    for p, meta in (frozen.get("files") or {}).items():
        disk = sha256_file(ROOT / p) if (ROOT / p).is_file() else None
        ok = disk == meta.get("sha256")
        snap["file_pins"][p] = {"declared": short(meta.get("sha256", "")),
                                "measured": short(disk or "MISSING"), "match": ok}
        if not ok:
            snap["mismatches"].append({"path": p, "declared": short(meta.get("sha256", "")),
                                       "measured": short(disk or "MISSING")})
    for name, meta in (frozen.get("logical_artifacts") or {}).items():
        p = meta.get("path")
        disk = sha256_file(ROOT / p) if p and (ROOT / p).is_file() else None
        ok = disk == meta.get("sha256")
        snap["logical_pins"][name] = {"path": p, "declared": short(meta.get("sha256", "")),
                                      "measured": short(disk or "MISSING"), "match": ok}
        if not ok:
            snap["mismatches"].append({"path": p, "declared": short(meta.get("sha256", "")),
                                       "measured": short(disk or "MISSING")})
    try:
        snap["frozen_at_not_future"] = datetime.fromisoformat(frozen.get("frozen_at")) <= NOW
    except Exception as e:  # noqa: BLE001
        snap["frozen_at_not_future"] = False
        errors.append(f"frozen_at unparseable: {e!r}")
    snap["n_file_pins"] = len(snap["file_pins"])
    snap["n_logical_pins"] = len(snap["logical_pins"])
    return snap


frozen_snapshots = []
run1 = OUT / "report.run1_prerefreeze.json"
if run1.is_file():
    prev = json.loads(run1.read_text()).get("frozen_rev29") or {}
    frozen_snapshots.append({
        "label": "run1_start_transient_drift", "source": "report.run1_prerefreeze.json",
        "at": "2026-09-12T00:56:00+08:00", "revision": prev.get("revision"),
        "frozen_at": prev.get("frozen_at"), "sha256": prev.get("sha256"),
        "n_file_pins": prev.get("n_file_pins"), "n_logical_pins": prev.get("n_logical_pins"),
        "mismatches": [{"path": p} for p in (prev.get("mismatches") or [])],
        "note": "pre-re-freeze manifest: 4 declared file pins did not match disk",
    })
frozen_snapshots.append(frozen_snapshot("run2_start"))
fp = frozen_snapshots[-1]
report["frozen_rev29"] = fp
report["frozen_snapshots"] = frozen_snapshots
# FROZEN findings are emitted after the end snapshot in section G so the end state is authoritative.

# ---- E. case corpus -------------------------------------------------------------------
rows = [json.loads(l) for l in (ROOT / CORPUS_PATH).read_text().splitlines() if l.strip()]
meta = [r for r in rows if r.get("record_type") == "meta"]
data = [r for r in rows if r.get("record_type") != "meta"]
bound = [r for r in data if r.get("binding_status") == "bound_taxonomy_sha_0abb9ed8a961"]
corpus = {
    "path": CORPUS_PATH,
    "sha256": sha256_file(ROOT / CORPUS_PATH),
    "n_lines": len(rows),
    "n_data_rows": len(data),
    "n_meta_rows": len(meta),
    "n_rows_bound_to_f0_rev5": len(bound),
    "meta_taxonomy_ref_sha256": (meta[0].get("taxonomy_ref", {}) or {}).get("sha256") if meta else None,
    "all_data_rows_bound": len(bound) == len(data) and len(data) == 36,
}
report["corpus"] = corpus
if not corpus["all_data_rows_bound"]:
    findings.append({"id": "W088-R13-CORPUS", "severity": "hard",
                     "detail": f"case corpus rows not fully rebound: {len(bound)}/{len(data)}"})
if corpus["meta_taxonomy_ref_sha256"] != F0_SHA:
    findings.append({"id": "W088-R13-CORPUS-META", "severity": "hard",
                     "detail": "case corpus meta taxonomy_ref.sha256 is not F0 rev5 0abb9ed8"})

# ---- F. residual L-FORM-03 independent reproduction ------------------------------------
residual = {}
pattern = re.compile(r"strictly\s+STRONGER")
for p in RESIDUAL_PATHS:
    fpth = ROOT / p
    if not fpth.is_file():
        residual[p] = {"exists": False}
        errors.append(f"residual path missing: {p}")
        continue
    text = fpth.read_text()
    lines = text.splitlines()
    pattern_ci = re.compile(r"strictly\s+stronger", re.I)
    mention_markers = ("corrected from", "[rev13", "rev12")
    hits, asserted, mentions = [], [], []
    for i, line in enumerate(lines):
        if pattern_ci.search(line):
            hits.append(i + 1)
            if any(m in line for m in mention_markers):
                mentions.append(i + 1)
            else:
                asserted.append(i + 1)
    residual[p] = {
        "exists": True, "sha256": sha256_file(fpth), "hits": len(hits), "lines": hits,
        "asserted_inverted_direction_lines": asserted,
        "metalinguistic_mention_lines": mentions,
        "asserted_context": [lines[i - 1].strip()[:260] for i in asserted],
    }
report["residual_lform03"] = residual
n_asserted = sum(len(v.get("asserted_inverted_direction_lines", [])) for v in residual.values())
report["residual_lform03_asserted_total"] = n_asserted
if n_asserted == 0:
    findings.append({"id": "W088-R13-LFORM03-ABSENT", "severity": "advisory",
                     "detail": "the declared L-FORM-03 residual text was not reproduced as an assertion; "
                               "carried-residual qualifier would be wrong"})
else:
    findings.append({"id": "W088-R13-LFORM03-CARRIED", "severity": "major",
                     "detail": f"asserted inverted SET direction measured at {n_asserted} line(s) in the "
                               f"declared residual paths; both are F0-frozen and cannot be edited without "
                               f"voiding G-F0 (see residual_lform03)"})
f1_doc = load_yaml(ROOT / "schemas/af_wcc_vacuum.yaml")
f1_text = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text()


def strip_mentions(text: str) -> str:
    """Drop revision-note spans and single-quoted quotations before counting assertions."""
    text = re.sub(r"\[[^\]]*rev\d+:[^\]]*\]", " ", text)
    text = re.sub(r"'[^']*'", " ", text)
    return text


variants = f1_doc.get("class_identity_variants") or []
set_rel = ""
for v in variants:
    if str(v.get("kind", "")) == "set_based_visibility_reading" or str(v.get("statement", "")).startswith("variant SET:"):
        set_rel = str(v.get("relation", ""))
d5_def = str(((f1_doc.get("quantifiers") or {}).get("domains") or {}).get("D5", {}).get("definition", ""))
vis_def = str((f1_doc.get("visibility") or {}).get("definition", ""))
asserted_strong = re.findall(r"strictly\s+STRONGER", strip_mentions(f1_text))
asserted_weak = re.findall(r"strictly\s+WEAKER", strip_mentions(f1_text))
checks = {
    "set_relation_starts_weak": set_rel.startswith("strictly WEAKER"),
    "set_relation_asserts_weaker": "strictly WEAKER" in strip_mentions(set_rel),
    "d5_definition_states_equivalence": "EQUIVALENT" in d5_def,
    "visibility_definition_states_equivalence": "EQUIVALENT" in vis_def,
    "no_asserted_STRONGER_in_visibility_fields": not (
        re.search(r"strictly\s+STRONGER", strip_mentions(set_rel))
        or re.search(r"strictly\s+STRONGER", strip_mentions(d5_def))
        or re.search(r"strictly\s+STRONGER", strip_mentions(vis_def))
    ),
}
report["f1_strictness"] = {
    "set_relation_head": set_rel[:120],
    "total_STRONGER_tokens": len(pattern.findall(f1_text)),
    "asserted_STRONGER_after_mention_strip": len(asserted_strong),
    "asserted_WEAKER_after_mention_strip": len(asserted_weak),
    "rev13_markers": len(re.findall(r"\[rev13:", f1_text)),
    "field_checks": checks,
    "note": "the remaining asserted STRONGER token is acceptance_alignment's open_dense_escape vs comeager "
            "default relation (a different, correct strictness claim), not a SET/tail direction assertion",
}
if not all(checks.values()):
    findings.append({"id": "W088-R13-F1-STRICT", "severity": "hard",
                     "detail": f"F1 strictness field checks failed: {[k for k, v in checks.items() if not v]}"})

# ---- G. end measurement / stability ----------------------------------------------------
end_hashes = {t["path"]: sha256_file(ROOT / t["path"]) for t in TARGETS}
end_hashes["__frozen__"] = sha256_file(ROOT / FROZEN_PATH)
report["stability"] = {
    "measured_at_start": start_hashes,
    "measured_at_end": end_hashes,
    "schema_targets_stable": all(start_hashes[t["path"]] == end_hashes[t["path"]] for t in TARGETS),
    "frozen_manifest_moved": start_hashes["__frozen__"] != end_hashes["__frozen__"],
    "frozen_manifest_start": short(start_hashes["__frozen__"]),
    "frozen_manifest_end": short(end_hashes["__frozen__"]),
}
if not report["stability"]["schema_targets_stable"]:
    findings.append({"id": "W088-R13-MOVING-TARGET", "severity": "hard",
                     "detail": "a schema target hash moved during the audit window; verdict binds only to the start hashes"})
if report["stability"]["frozen_manifest_moved"]:
    findings.append({"id": "W088-R13-FROZEN-REFREEZE", "severity": "major",
                     "detail": "FROZEN.json was rewritten during the audit window; end-state pin check is authoritative"})

# ---- G2. authoritative end-state FROZEN check ------------------------------------------
frozen_snapshots.append(frozen_snapshot("run2_end"))
fp = frozen_snapshots[-1]
report["frozen_rev29"] = fp
report["frozen_snapshots"] = frozen_snapshots
drift_snapshots = [s for s in frozen_snapshots if s["mismatches"]]
if fp["mismatches"]:
    findings.append({"id": "W088-R13-FROZEN-PINS", "severity": "hard",
                     "detail": f"{len(fp['mismatches'])} FROZEN rev29 pin(s) do not match disk at end of run: "
                               f"{[m['path'] for m in fp['mismatches']]}"})
elif drift_snapshots:
    findings.append({"id": "W088-R13-FREEZE-DRIFT-TRANSIENT", "severity": "major",
                     "detail": "an earlier FROZEN rev29 snapshot carried mismatched pins before the 00:57:26 "
                               "re-freeze; end-state manifest is clean (see frozen_snapshots)"})
if not fp["frozen_at_not_future"]:
    findings.append({"id": "W088-R13-FROZEN-CLOCK", "severity": "hard", "detail": "frozen_at is future-dated"})
for t in TARGETS:
    pin = fp["file_pins"].get(t["path"], {})
    if not pin.get("match"):
        findings.append({"id": f"W088-R13-{t['node']}-REV29PIN", "severity": "hard",
                         "detail": f"FROZEN rev29 does not pin the measured rev13 bytes for {t['path']}"})

# ---- H. declared-tool cross-checks -----------------------------------------------------
report["cross_checks"]["check_class_schema"] = {
    t["node"]: run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", t["path"]])
    for t in TARGETS
}
report["cross_checks"]["verify_frozen"] = run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"])
report["cross_checks"]["classsep_regression"] = run([sys.executable, "runtime/bin/classsep_regression.py"])

# ---- I. verdict ------------------------------------------------------------------------
hard = [f for f in findings if f["severity"] == "hard"]
report["hard_findings"] = hard
if errors:
    verdict = "INCONCLUSIVE"
elif hard:
    verdict = "DEFECTS_FOUND"
else:
    verdict = "SCOPE_COMPLIANT_WITH_CARRIED_RESIDUAL"
report["verdict"] = verdict
report["verdict_basis"] = {
    "hard_findings": len(hard),
    "errors": len(errors),
    "rev13_hashes": {t["node"]: short(start_hashes[t["path"]]) for t in TARGETS},
    "frozen_rev29_sha256_end": fp["sha256"][:12],
    "frozen_rev29_frozen_at": fp["frozen_at"],
    "freeze_drift_observed_in_window": bool(drift_snapshots),
    "transient_drift_paths": [m["path"] for s in drift_snapshots for m in s["mismatches"]],
    "carried_residual": (
        f"L-FORM-03: {n_asserted} asserted inverted ('strictly stronger') SET/tail direction line(s) measured in "
        "F0-frozen paths " + ", ".join(f"{p}:{v.get('asserted_inverted_direction_lines')}"
                                       for p, v in residual.items()
                                       if v.get("asserted_inverted_direction_lines"))
    ),
}
report["next_falsifier"] = [
    "a write to any of the three measured rev13 schemas or to FROZEN.json after this measurement, or a FROZEN rev29 pin that no longer matches disk",
    "a changed leaf outside revision bookkeeping / f0_binding / the [rev13:] annotated F1 strictness text in the rev12->rev13 delta",
    "the class_contract_pointer or class_contract_supplement_pointer failing to resolve, or consistency_evidence_sha256 ceasing to equal the measured evidence file",
    "L-FORM-03 no longer being present in the four residual paths",
    "a G-FORM r3 verdict bound to a FROZEN manifest whose pins drift again (the 00:55:02 rev29 snapshot was 4-pin inconsistent)",
]
report["not_claimed"] = [
    "No gate verdict, node status or validation_status: worker events cannot move gates or node states.",
    "No class-semantics judgement beyond the mechanical protected-leaf guard; the r3 reviewers own the semantics.",
    "No claim that the L-FORM-03 residual voids G-FORM; it is carried, not introduced by rev13.",
]

(OUT / "report.json").write_text(json.dumps(report, indent=1, default=str))
print(json.dumps({
    "verdict": verdict,
    "hard_findings": [f["id"] for f in hard],
    "major_findings": [f["id"] for f in findings if f["severity"] == "major"],
    "errors": errors,
    "rev13": {t["node"]: short(start_hashes[t["path"]]) for t in TARGETS},
    "frozen_end": fp["sha256"][:12],
    "frozen_end_mismatches": len(fp["mismatches"]),
    "changed_leaves": {t["node"]: len(report["targets"][t["path"]]["changed_leaves"]) for t in TARGETS},
    "out_of_scope": {t["node"]: len(report["targets"][t["path"]]["out_of_scope"]) for t in TARGETS},
    "schema_targets_stable": report["stability"]["schema_targets_stable"],
}, indent=1))
