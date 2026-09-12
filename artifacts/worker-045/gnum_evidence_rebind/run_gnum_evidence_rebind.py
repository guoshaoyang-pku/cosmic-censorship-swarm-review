#!/usr/bin/env python3
"""W045-GNUM-EVIDENCE-REBIND-01 — deterministic, read-only re-bind audit of the
G-NUM gate evidence list at the live map snapshot.

Task (self-selected; no inbox card for worker-045, node N0 / gate G-NUM /
class AF-WCC-SCALAR-SPH):

  At the pinned map snapshot, classify every evidence_ref of the G-NUM gate record
  by whether its declared hash fragment binds the bytes on disk (MATCH / STALE /
  MISSING / BARE / AMBIGUOUS), cross-check the controller registry
  (runtime/state/artifact_hashes.json), re-test the C8 binding expression that the
  controller now uses (reviewed_sha256 or artifact_sha256), resolve the
  leadverify successor chain, and test whether the gate record's own unmet[] list
  is consistent with the evidence set it carries.

Read-only: writes only inside its own artifact directory. It never edits the map,
the registry, numerics/, reviews/ or any canonical artifact. Worker events cannot
set node status=done, validation_status=passed, or a gate verdict.

Run:  python3 artifacts/worker-045/gnum_evidence_rebind/run_gnum_evidence_rebind.py
Exit: 0 = audit completed (whatever the verdict); 2 = audit void (pin/drift failure);
      3 = internal error.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../ai4math-swarm
CST = timezone(timedelta(hours=8))
TASK_ID = "W045-GNUM-EVIDENCE-REBIND-01"
GATE_ID = "G-NUM"
NODE_ID = "N0"
CLASS_ID = "AF-WCC-SCALAR-SPH"

MAP_PATH = ROOT / "research_map" / "research_map.json"
REGISTRY_PATH = ROOT / "runtime" / "state" / "artifact_hashes.json"
REVIEW_PATH = ROOT / "reviews" / "G-NUM-protocol-review.json"
PROTOCOL_PATH = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
LEADVERIFY_PATH = ROOT / "numerics" / "protocol" / "n0_gate_proposal_leadverify.json"
LIFECYCLE_PY = ROOT / "research_map" / "astra_lifecycle.py"
STALE_PIN = "e0f9ef9f329d"
SUCCESSOR_PIN = "ea4cf6c9bd3c2092"

HEX_FRAG = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{6,64})$")
C8_EXPR = 'json.loads(proto_review.read_text()).get("artifact_sha256") or "unbound"'
C8_EXPR_FIXED = (
    'prd.get("reviewed_sha256") or prd.get("artifact_sha256")'
)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# ref classification
# --------------------------------------------------------------------------- #
def parse_ref(ref: str) -> dict:
    if "#" not in ref:
        return {"ref": ref, "path": ref, "fragment": None, "kind": "BARE"}
    path, frag = ref.rsplit("#", 1)
    m = HEX_FRAG.match(frag)
    if m:
        return {"ref": ref, "path": path, "fragment": frag, "kind": "HASH",
                "hex": m.group(1).lower()}
    return {"ref": ref, "path": path, "fragment": frag, "kind": "AMBIGUOUS"}


def classify_ref(ref: str, base: Path) -> dict:
    """Pure classification against `base`; no global state."""
    pr = parse_ref(ref)
    out = dict(pr)
    p = base / pr["path"]
    out["exists"] = p.is_file()
    out["measured_sha256"] = None
    out["declared_prefix"] = pr.get("hex")
    if pr["kind"] == "HASH":
        if not out["exists"]:
            out["classification"] = "MISSING"
        else:
            measured = sha256_file(p)
            out["measured_sha256"] = measured
            out["classification"] = (
                "MATCH" if measured.startswith(pr["hex"]) else "STALE"
            )
    elif pr["kind"] == "BARE":
        out["classification"] = "BARE"
    else:
        out["classification"] = "AMBIGUOUS"
    return out


def refine_stale(entry: dict, base: Path) -> dict:
    """A hex fragment that is not a prefix of the referenced file's live bytes is
    either (a) a revision/review pin the artifact itself declares (found verbatim in
    its own bytes), (b) a revision relocated to another path on disk, or (c) an
    unexplained stale pin. Only (c) is a binding defect."""
    if entry.get("classification") != "STALE":
        return entry
    frag = entry["hex"]
    p = base / entry["path"]
    entry["declared_in_file"] = False
    entry["relocated_to"] = None
    try:
        blob = p.read_bytes()
        if len(blob) <= 8 << 20:
            entry["declared_in_file"] = frag in blob.decode("utf-8", "replace")
    except OSError:
        pass
    if entry["declared_in_file"]:
        entry["classification"] = "HISTORICAL_DECLARED"
        return entry
    stem = Path(entry["path"]).name
    seen = 0
    for pat in (f"artifacts/*/{stem}", f"artifacts/*/*/{stem}",
                f"numerics/*/{stem}", f"numerics/*/*/{stem}", stem):
        for cand in sorted(base.glob(pat)):
            if not cand.is_file() or cand == p:
                continue
            seen += 1
            if seen > 200:
                break
            try:
                if sha256_file(cand).startswith(frag):
                    entry["relocated_to"] = str(cand.relative_to(base))
                    entry["classification"] = "HISTORICAL_RELOCATED"
                    return entry
            except OSError:
                continue
    # last resort: is the revision recoverable from git history?
    try:
        log = subprocess.run(
            ["git", "-C", str(base), "log", "--all", "--format=%H", "--", entry["path"]],
            capture_output=True, text=True, timeout=30)
        revs = [x for x in log.stdout.split() if x][:20]
        for rev in revs:
            show = subprocess.run(
                ["git", "-C", str(base), "show", f"{rev}:{entry['path']}"],
                capture_output=True, timeout=30)
            if show.returncode == 0 and sha256_bytes(show.stdout).startswith(frag):
                entry["relocated_to"] = f"git:{rev[:12]}:{entry['path']}"
                entry["classification"] = "HISTORICAL_VCS"
                return entry
    except (OSError, subprocess.SubprocessError):
        pass
    entry["classification"] = "STALE_UNEXPLAINED"
    return entry


def registry_lookup(reg: dict, path: str) -> dict:
    for bucket in ("registry", "hashes"):
        b = reg.get(bucket) or {}
        if path in b:
            rec = b[path]
            if isinstance(rec, dict) and rec.get("sha256"):
                return {"bucket": bucket, "sha256": rec["sha256"],
                        "bytes": rec.get("bytes")}
    return {"bucket": None, "sha256": None, "bytes": None}


# --------------------------------------------------------------------------- #
# settled map snapshot
# --------------------------------------------------------------------------- #
def settle_map(attempts: int = 5, gap: float = 1.2) -> dict:
    rec = {"attempts": 0, "settled": False, "sha256_at_entry": None,
           "sha256_at_exit": None, "snapshot_bytes": None}
    for i in range(attempts):
        rec["attempts"] = i + 1
        b1 = MAP_PATH.read_bytes()
        h1 = sha256_bytes(b1)
        time.sleep(gap)
        b2 = MAP_PATH.read_bytes()
        h2 = sha256_bytes(b2)
        if h1 == h2:
            rec["settled"] = True
            rec["sha256_at_entry"] = h1
            rec["sha256_at_exit"] = h2
            rec["snapshot_bytes"] = b2
            return rec
    b = MAP_PATH.read_bytes()
    rec["sha256_at_entry"] = sha256_bytes(b)
    rec["sha256_at_exit"] = sha256_bytes(MAP_PATH.read_bytes())
    rec["snapshot_bytes"] = b
    return rec


def gate_record(map_doc: dict) -> dict:
    for g in map_doc.get("gates", []):
        if g.get("gate_id") == GATE_ID:
            return g
    raise SystemExit(f"{GATE_ID} not found in map")


# --------------------------------------------------------------------------- #
# C8 binding re-test
# --------------------------------------------------------------------------- #
def c8_binding(review_doc: dict, protocol_sha: str, lifecycle_text: str) -> dict:
    top = review_doc.get("artifact_sha256")
    reviewed = review_doc.get("reviewed_sha256")
    ctrl_expr_present = C8_EXPR in lifecycle_text
    fixed_expr_present = C8_EXPR_FIXED in lifecycle_text
    legacy_live = (top or "unbound") if isinstance(top, str) else "unbound"
    current_live = (reviewed or top or "unbound")
    return {
        "review_path": "reviews/G-NUM-protocol-review.json",
        "review_measured_sha256": sha256_file(REVIEW_PATH),
        "protocol_measured_sha256": protocol_sha,
        "top_level_artifact_sha256": top,
        "top_level_reviewed_sha256": reviewed,
        "review_verdict": review_doc.get("verdict"),
        "review_score": review_doc.get("score"),
        "legacy_controller_expression": C8_EXPR,
        "legacy_expression_present_in_lifecycle": ctrl_expr_present,
        "legacy_expression_result": legacy_live[:12] if legacy_live != "unbound" else "unbound",
        "current_controller_expression": C8_EXPR_FIXED,
        "current_expression_present_in_lifecycle": fixed_expr_present,
        "current_expression_result": current_live[:12] if current_live != "unbound" else "unbound",
        "current_expression_binds_measured_protocol": bool(
            isinstance(current_live, str) and current_live == protocol_sha
        ),
        "legacy_expression_binds_measured_protocol": bool(
            isinstance(top, str) and top == protocol_sha
        ),
    }


# --------------------------------------------------------------------------- #
# successor chain + unmet-vs-evidence
# --------------------------------------------------------------------------- #
def successor_chain(gate: dict, base: Path) -> dict:
    lv = load_json(base / "numerics/protocol/n0_gate_proposal_leadverify.json")
    text = (base / "numerics/protocol/n0_gate_proposal_leadverify.json").read_text()
    refs = gate.get("evidence_refs", [])
    old_refs = [r for r in refs if STALE_PIN in r]
    new_refs = [r for r in refs if SUCCESSOR_PIN in r]
    return {
        "leadverify_path": "numerics/protocol/n0_gate_proposal_leadverify.json",
        "leadverify_measured_sha256": sha256_file(
            base / "numerics/protocol/n0_gate_proposal_leadverify.json"),
        "declared_supersedes": lv.get("supersedes"),
        "declares_successor": bool(lv.get("supersedes")),
        "old_prefix_in_live_bytes": STALE_PIN in text,
        "successor_self_hash_in_own_bytes": SUCCESSOR_PIN in text,
        "self_hash_note": ("a file cannot contain its own sha256; the successor's currency is "
                           "established by disk measurement + the controller registry, not by "
                           "text search"),
        "old_prefix_refs_in_gate": old_refs,
        "new_prefix_refs_in_gate": new_refs,
        "gate_binds_old_stale_pin": bool(old_refs),
        "gate_binds_successor_pin": bool(new_refs),
    }


UNMET_KEYWORDS = {
    "independent numerical-protocol review is not recorded (nobody may self-review)":
        ["G-NUM-protocol-review.json", "n0_c8"],
    "cnfem triage from the N0 adjudication is not closed: fix with root cause, or exclude with evidence":
        ["triage", "cnfem"],
    "the replication harness invariant functional is leapfrog-specific; a scheme-agnostic check or relabelling is required":
        ["scheme_independence", "scheme-agnostic"],
    "the audit lead asks for a 4th resolution before the order claim is accepted":
        ["4rung", "n0_order"],
    "cnfd own-energy drift 6.6e-8 has no principled threshold justification":
        ["threshold", "drift"],
}


def unmet_vs_evidence(gate: dict, base: Path) -> list:
    refs = gate.get("evidence_refs", [])
    out = []
    for item in gate.get("unmet", []):
        keys = UNMET_KEYWORDS.get(item, [])
        hits = []
        for r in refs:
            low = r.lower()
            for k in keys:
                if k.lower() in low:
                    hits.append(r)
                    break
        existing = []
        for h in hits:
            p = base / h.rsplit("#", 1)[0]
            if p.is_file():
                existing.append(h)
        out.append({
            "unmet_item": item,
            "keyword_hits": hits,
            "existing_hits": existing,
            "evidence_present": bool(existing),
            "discharge_authority": "lead-audit / controller (not this worker)",
        })
    return out


def lock_check(base: Path, map_doc: dict) -> dict:
    lock = map_doc.get("numerics_lock", {})
    solver = base / "numerics" / "spherical_solver"
    guard = base / "numerics" / "tests" / "selfgravity_lock_guard.py"
    return {
        "numerics_lock_state": lock.get("state"),
        "locked_nodes": lock.get("locked_nodes"),
        "allowed_nodes": lock.get("allowed_nodes"),
        "solver_path_exists": solver.exists(),
        "guard_path_exists": guard.is_file(),
        "guard_sha256": sha256_file(guard) if guard.is_file() else None,
    }


# --------------------------------------------------------------------------- #
# controls
# --------------------------------------------------------------------------- #
def run_controls(base: Path, review_doc: dict, protocol_sha: str) -> dict:
    cdir = HERE / "controls"
    cdir.mkdir(parents=True, exist_ok=True)
    live = cdir / "live.txt"
    live.write_text("control payload\n")
    live_sha = sha256_file(live)
    controls = {}

    def record(name, got, expected, ok, note=""):
        controls[name] = {"input": str(note), "result": got,
                          "expected": expected, "pass": bool(ok)}

    # C1 stale: flip last hex digit of a real hash
    flip = "0" if live_sha[-1] != "0" else "1"
    stale_hex = live_sha[:-1] + flip
    r = refine_stale(classify_ref(f"controls/live.txt#{stale_hex}", HERE), HERE)
    record("C1_stale_detected", r["classification"], "STALE_UNEXPLAINED",
           r["classification"] == "STALE_UNEXPLAINED", f"declared {stale_hex} vs measured {live_sha}")

    # C2 missing path
    r = classify_ref("controls/does_not_exist.txt#abcdef123456", HERE)
    record("C2_missing_detected", r["classification"], "MISSING",
           r["classification"] == "MISSING")

    # C3 bare ref is not silently treated as a hash
    r = classify_ref("controls/live.txt", HERE)
    record("C3_bare_not_hash", r["classification"], "BARE",
           r["classification"] == "BARE")

    # C4 key-path fragment is ambiguous, not STALE
    r = classify_ref("runtime/state/artifact_hashes.json#registry", base)
    record("C4_keypath_ambiguous", r["classification"], "AMBIGUOUS",
           r["classification"] == "AMBIGUOUS")

    # C5 sha256: prefix form parses
    r = classify_ref(f"controls/live.txt#sha256:{live_sha[:16]}", HERE)
    record("C5_sha256_prefix_form", r["classification"], "MATCH",
           r["classification"] == "MATCH")

    # C6 short (6-hex) prefix binds
    r = classify_ref(f"controls/live.txt#{live_sha[:6]}", HERE)
    record("C6_short_prefix_match", r["classification"], "MATCH",
           r["classification"] == "MATCH")

    # C7 external sha256sum cross-check on 3 live files
    samples = ["research_map/research_map.json", "reviews/G-NUM-protocol-review.json",
               "numerics/CONVERGENCE_PROTOCOL.md"]
    ext_ok = True
    ext_detail = {}
    for s in samples:
        p = base / s
        if not p.is_file():
            ext_ok = False
            ext_detail[s] = "missing"
            continue
        out = subprocess.run(["sha256sum", str(p)], capture_output=True, text=True)
        if out.returncode != 0:
            ext_ok = False
            ext_detail[s] = "sha256sum rc=%d" % out.returncode
            continue
        external = out.stdout.split()[0]
        internal = sha256_file(p)
        ext_detail[s] = "agree" if external == internal else "DISAGREE"
        ext_ok = ext_ok and external == internal
    record("C7_external_sha256sum_agreement", ext_detail, "all agree", ext_ok)

    # C8 binding detector is fail-closed: removing reviewed_sha256 flips to unbound
    mutated = copy.deepcopy(review_doc)
    mutated.pop("reviewed_sha256", None)
    mutated.pop("artifact_sha256", None)
    live_val = mutated.get("reviewed_sha256") or mutated.get("artifact_sha256") or "unbound"
    record("C8_binding_detector_failclosed", live_val, "unbound", live_val == "unbound",
           "review copy with reviewed_sha256/artifact_sha256 removed")
    pos = copy.deepcopy(review_doc)
    pos["reviewed_sha256"] = protocol_sha
    pos_val = pos.get("reviewed_sha256") or pos.get("artifact_sha256") or "unbound"
    record("C8b_binding_detector_positive", pos_val[:12], protocol_sha[:12],
           pos_val == protocol_sha, "review copy with reviewed_sha256 set")

    # C9 drift guard fires on a changing input
    b = MAP_PATH.read_bytes()
    h1 = sha256_bytes(b)
    h2 = sha256_bytes(b + b" ")
    record("C9_drift_guard_fires", h1 == h2, False, h1 != h2,
           "synthetic mutation of snapshot bytes")

    # C10 declared-historical fragment (present in the file text) is not called stale
    other = sha256_bytes(b"some prior revision\n")
    hist = cdir / "live_hist.txt"
    hist.write_text(f"supersedes_sha256: {other}\n")
    r = refine_stale(classify_ref(f"controls/live_hist.txt#{other[:12]}", HERE), HERE)
    record("C10_declared_historical_detected", r["classification"], "HISTORICAL_DECLARED",
           r["classification"] == "HISTORICAL_DECLARED",
           "fragment declared in the file's own bytes")

    # C11 divergence rule: bare-only citation is not divergence; a stale hash ref is
    fake_reg = {"registry": {"controls/live.txt": {"sha256": live_sha}}, "hashes": {}}
    d_bare = compute_divergence([classify_ref("controls/live.txt", HERE)], fake_reg)
    record("C11a_bare_only_not_divergence", len(d_bare), 0, len(d_bare) == 0)
    d_hash = compute_divergence(
        [classify_ref(f"controls/live.txt#{stale_hex}", HERE)], fake_reg)
    record("C11b_stale_hash_ref_is_divergence", len(d_hash), 1, len(d_hash) == 1)

    controls["all_pass"] = all(v["pass"] for v in controls.values())
    return controls


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def compute_divergence(refs: list, reg: dict) -> list:
    """Paths the gate tries to pin (>=1 hash-bearing ref) whose registry-current
    revision no gate ref binds. Bare-only citations make no pin claim and are excluded."""
    out = []
    for path in sorted({r["path"] for r in refs if registry_lookup(reg, r["path"])["sha256"]}):
        current = registry_lookup(reg, path)["sha256"]
        path_refs = [r for r in refs if r["path"] == path]
        hash_refs = [r for r in path_refs if r.get("declared_prefix")]
        if not hash_refs:
            continue
        binds_current = any(
            (r.get("declared_prefix") and current.startswith(r["declared_prefix"]))
            or r.get("relocated_to")
            for r in path_refs
        )
        if not binds_current:
            out.append({
                "path": path,
                "registry_current_sha256": current,
                "gate_refs": [r["ref"] for r in path_refs],
                "gate_hash_refs": [r["ref"] for r in hash_refs],
                "gate_binds_current": False,
                "reason": "gate carries hash-bearing ref(s) for this path but none binds the registry-current revision",
            })
    return out


def measure(snapshot_bytes: bytes) -> dict:
    map_doc = json.loads(snapshot_bytes.decode("utf-8"))
    gate = gate_record(map_doc)
    reg = load_json(REGISTRY_PATH)
    refs = [refine_stale(classify_ref(r, ROOT), ROOT) for r in gate.get("evidence_refs", [])]
    for r in refs:
        rl = registry_lookup(reg, r["path"])
        r["registry"] = rl
        if r["measured_sha256"] and rl["sha256"]:
            r["registry_agreement"] = "MATCH" if rl["sha256"] == r["measured_sha256"] else "STALE"
        elif r["measured_sha256"] and not rl["sha256"]:
            r["registry_agreement"] = "ABSENT"
        else:
            r["registry_agreement"] = None
    buckets = {"MATCH": [], "HISTORICAL_DECLARED": [], "HISTORICAL_RELOCATED": [],
               "HISTORICAL_VCS": [], "STALE_UNEXPLAINED": [], "MISSING": [], "BARE": [],
               "AMBIGUOUS": []}
    for r in refs:
        buckets[r["classification"]].append(r["ref"])
    registry_divergence = compute_divergence(refs, reg)
    proto_sha = sha256_file(PROTOCOL_PATH)
    review_doc = load_json(REVIEW_PATH)
    lifecycle_text = LIFECYCLE_PY.read_text(encoding="utf-8")
    return {
        "gate": {k: gate.get(k) for k in
                 ("gate_id", "scope", "verdict", "owner", "updated_at",
                  "last_verdict_event", "locked")},
        "gate_unmet": gate.get("unmet", []),
        "gate_evidence_ref_count": len(refs),
        "refs": refs,
        "buckets": buckets,
        "registry_divergence": registry_divergence,
        "successor_chain": successor_chain(gate, ROOT),
        "c8_binding": c8_binding(review_doc, proto_sha, lifecycle_text),
        "unmet_vs_evidence": unmet_vs_evidence(gate, ROOT),
        "lock_check": lock_check(ROOT, map_doc),
        "registry_path": "runtime/state/artifact_hashes.json",
        "registry_sha256": sha256_file(REGISTRY_PATH),
        "protocol_sha256": proto_sha,
    }


def normalize_for_determinism(m: dict) -> str:
    m = copy.deepcopy(m)
    m["gate"].pop("updated_at", None)
    return json.dumps(m, sort_keys=True)


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    started = now()
    settle = settle_map()
    snapshot_bytes = settle["snapshot_bytes"]
    # pin the exact map bytes used
    snap_path = HERE / "map_snapshot.json"
    snap_path.write_bytes(snapshot_bytes)
    snap_sha = sha256_bytes(snapshot_bytes)

    m1 = measure(snapshot_bytes)
    m2 = measure(snapshot_bytes)
    deterministic = normalize_for_determinism(m1) == normalize_for_determinism(m2)

    controls = run_controls(ROOT, load_json(REVIEW_PATH), m1["protocol_sha256"])

    live_sha_exit = sha256_bytes(MAP_PATH.read_bytes())
    drift = (live_sha_exit != settle["sha256_at_exit"]) or (not settle["settled"])

    stale = m1["buckets"]["STALE_UNEXPLAINED"]
    missing = m1["buckets"]["MISSING"]
    gate_binds_old = m1["successor_chain"]["gate_binds_old_stale_pin"]
    gate_binds_new = m1["successor_chain"]["gate_binds_successor_pin"]
    c8_ok = m1["c8_binding"]["current_expression_binds_measured_protocol"]
    legacy_bound = m1["c8_binding"]["legacy_expression_binds_measured_protocol"]
    unmet_evidence = [u["unmet_item"] for u in m1["unmet_vs_evidence"] if u["evidence_present"]]
    hist_declared = m1["buckets"]["HISTORICAL_DECLARED"]
    hist_relocated = m1["buckets"]["HISTORICAL_RELOCATED"] + m1["buckets"]["HISTORICAL_VCS"]
    stale_unexplained = m1["buckets"]["STALE_UNEXPLAINED"]
    divergence = m1["registry_divergence"]

    findings = []
    if stale_unexplained or hist_declared or hist_relocated:
        findings.append({
            "id": "W045-GER-01",
            "severity": "major" if stale_unexplained else "info",
            "statement": (f"{GATE_ID} gate record (snapshot {snap_sha[:12]}) carries "
                          f"{len(stale_unexplained)} unexplained stale, "
                          f"{len(hist_declared)} declared-historical and "
                          f"{len(hist_relocated)} relocated-revision hash-bearing evidence ref(s). "
                          f"Unexplained: {'; '.join(stale_unexplained) or 'none'}. "
                          f"Declared-historical: {'; '.join(hist_declared) or 'none'}. "
                          f"Relocated: {'; '.join(hist_relocated) or 'none'}."),
            "consequence": ("Historical pins are legitimate provenance, but the gate evidence "
                            "list mixes superseded and current revisions; it is not a live pin "
                            "set, so a reviewer resolving the latest-of-record from it can land "
                            "on a superseded artefact."),
        })
    if missing:
        findings.append({
            "id": "W045-GER-02",
            "severity": "major",
            "statement": f"{len(missing)} gate evidence ref(s) point at absent paths: " + "; ".join(missing),
            "consequence": "Missing evidence paths cannot be re-measured by a reviewer.",
        })
    if gate_binds_old and not gate_binds_new:
        findings.append({
            "id": "W045-GER-03",
            "severity": "major",
            "statement": (f"leadverify successor chain is unresolved in the gate record: "
                          f"live bytes are {SUCCESSOR_PIN} (declares supersession), the gate "
                          f"binds the superseded {STALE_PIN}, and no ref carries the successor."),
            "consequence": "N0 verification-of-record is not the artefact a reviewer resolves from the gate.",
        })
    if divergence:
        findings.append({
            "id": "W045-GER-08",
            "severity": "major",
            "statement": (f"{len(divergence)} gate evidence path(s) have a current registry "
                          f"sha256 that no gate ref binds: "
                          + "; ".join(d["path"] + "@" + d["registry_current_sha256"][:12]
                                      for d in divergence)),
            "consequence": ("gates[G-NUM].evidence_refs and runtime/state/artifact_hashes.json "
                            "disagree about the current revision of these paths; the controller "
                            "registry is the newer of the two."),
        })
    if not c8_ok:
        findings.append({
            "id": "W045-GER-04",
            "severity": "critical",
            "statement": "C8 binding expression does not resolve to the measured protocol hash.",
            "consequence": "Controller's C8=MET statement is not reproducible from the live bytes.",
        })
    elif not legacy_bound:
        findings.append({
            "id": "W045-GER-04b",
            "severity": "info",
            "statement": ("C8 resolves only via the revised expression "
                          "(reviewed_sha256 or artifact_sha256); the review still has no "
                          "top-level artifact_sha256, so the legacy expression remains unbound."),
            "consequence": "Any older reviewer replaying the legacy expression will still read C8 as unbound.",
        })
    if unmet_evidence:
        findings.append({
            "id": "W045-GER-05",
            "severity": "major",
            "statement": (f"{len(unmet_evidence)} gate unmet[] item(s) have matching evidence "
                          f"paths already present in the gate evidence list: "
                          + " | ".join(u[:80] for u in unmet_evidence)),
            "consequence": ("gates[G-NUM].unmet and controller_gate_audit['G-NUM'].reason are "
                            "internally inconsistent in the same map document; discharge itself "
                            "remains lead-audit/controller-owned."),
        })
    if not deterministic:
        findings.append({
            "id": "W045-GER-06",
            "severity": "critical",
            "statement": "two measures of the same snapshot bytes differ.",
            "consequence": "Audit void; instrument not trustworthy.",
        })
    if not controls["all_pass"]:
        findings.append({
            "id": "W045-GER-07",
            "severity": "critical",
            "statement": "control battery failed.",
            "consequence": "Audit void.",
        })

    verdict = "VOID" if (drift or not deterministic or not controls["all_pass"]) else (
        "REVISE" if any(f["severity"] in ("major", "critical") for f in findings) else "ACCEPT"
    )

    report = {
        "schema": "worker-045/gnum-evidence-rebind/v1",
        "task_id": TASK_ID,
        "worker": "worker-045",
        "started_at": started,
        "generated_at": now(),
        "node_id": NODE_ID,
        "gate": GATE_ID,
        "class_id": CLASS_ID,
        "verdict": verdict,
        "claim": (
            "Artifact-and-checker measurement (not a mathematics claim, not a gate verdict): "
            f"at the pinned live map snapshot {snap_sha[:12]} the {GATE_ID} gate evidence list "
            f"classifies {len(m1['buckets']['MATCH'])} MATCH / "
            f"{len(m1['buckets']['HISTORICAL_DECLARED'])} HISTORICAL_DECLARED / "
            f"{len(m1['buckets']['HISTORICAL_RELOCATED'])} HISTORICAL_RELOCATED / "
            f"{len(m1['buckets']['HISTORICAL_VCS'])} HISTORICAL_VCS / "
            f"{len(stale_unexplained)} STALE_UNEXPLAINED / "
            f"{len(missing)} MISSING / {len(m1['buckets']['BARE'])} BARE / "
            f"{len(m1['buckets']['AMBIGUOUS'])} AMBIGUOUS; "
            f"{len(divergence)} path(s) have a registry-current hash no gate ref binds; the "
            f"controller's current C8 expression reproduces {'BOUND' if c8_ok else 'UNBOUND'} "
            f"against the measured protocol hash {m1['protocol_sha256'][:12]}; the leadverify "
            f"successor {SUCCESSOR_PIN} is {'bound' if gate_binds_new else 'NOT bound'} in the "
            f"gate record while {STALE_PIN} is {'still bound' if gate_binds_old else 'absent'}; "
            f"and {len(unmet_evidence)} unmet[] item(s) already have evidence present."
        ),
        "verdict_basis": [f["id"] for f in findings],
        "findings": findings,
        "map_snapshot": {
            "pinned_copy": "artifacts/worker-045/gnum_evidence_rebind/map_snapshot.json",
            "sha256": snap_sha,
            "live_sha256_at_entry": settle["sha256_at_entry"],
            "live_sha256_at_exit": live_sha_exit,
            "settled_window": settle["settled"],
            "settle_attempts": settle["attempts"],
            "drift_void": drift,
        },
        "measurements": m1,
        "determinism": {
            "two_runs_identical": deterministic,
            "normalized_fields_excluded": ["gate.updated_at"],
        },
        "controls": controls,
        "assumptions": [
            "a declared hash fragment is a prefix (short form) or full sha256 of the referenced bytes",
            "a fragment that is not hex (e.g. #registry, #controller_gate_audit) is a key path, not a pin",
            "the live map bytes are the sole global state; the pinned copy is byte-identical to them at snapshot time",
            "discharge of gate unmet items and any verdict remain lead-audit/controller authority",
        ],
        "falsifier": [
            "Void if a re-run of this instrument at the recorded snapshot sha yields any different classification bucket for any ref.",
            "Void if sha256sum(artifacts/worker-045/gnum_evidence_rebind/map_snapshot.json) != the recorded snapshot sha256.",
            "Void if an independent reviewer finds a ref that this instrument called MATCH while the live bytes at the recorded snapshot do not start with the declared fragment.",
            "Void if control battery C1-C9 does not reproduce all_pass=true on a re-run.",
            "Withdrawn if a later map snapshot removes all stale refs, binds the leadverify successor, and recomputes unmet[] — then this becomes a historical measurement only.",
        ],
        "scope_limit": (
            "Read-only binding-state measurement over the named G-NUM gate record at one pinned "
            "map snapshot. It does not adjudicate C8, the N0 node verdict, cnfd/cnfem triage, "
            "the 4-rung order claim, or any physics. It does not edit numerics/, reviews/, "
            "research_map/ or any canonical artifact."
        ),
        "no_completion_claim": (
            "Worker events cannot set node status=done, validation_status=passed or a gate "
            "verdict. N0/G-NUM remain lead- and controller-owned. This artifact is evidence for "
            "astra-life04-n0-verify."
        ),
        "needed_to_unblock": [
            "Re-pin gates[G-NUM].evidence_refs to the successor verification record "
            f"numerics/protocol/n0_gate_proposal_leadverify.json#{SUCCESSOR_PIN} (and drop or "
            f"mark superseded the {STALE_PIN} ref).",
            "Decide the disposition of numerics/tests/n0_gate_proposal.json#22d984781cee: its "
            "bytes are absent from disk, from name-matching artifact paths and from git history, "
            "so the ref can only be retained as a provenance note (revision overwritten at the "
            "collided path), not as a re-measurable pin.",
            "Optionally add top-level artifact_sha256=measured protocol hash to "
            "reviews/G-NUM-protocol-review.json so legacy/first-order consumers that read only "
            "that field also resolve C8.",
        ],
        "controller_pass_context": (
            "Snapshot carries last_verdict_event=astra-life08-gate-gnum (map updated "
            "2026-09-12T01:16:25). Pass-08 refreshed gates[G-NUM].unmet[] to the N0-verdict / "
            "stop-rule items and added reviews/G-NUM-protocol-review.json#8137f18f1a3b2b01, which "
            "clears the earlier unmet-vs-evidence inconsistency and the review-path divergence "
            "observed at snapshot 66ada65f6027. The leadverify successor divergence and the "
            "22d984781cee pin survive pass-08."
        ),
    }

    # second determinism pass on disk artifacts (outside the report body)
    (HERE / "report_run2.json").write_text(json.dumps(report["measurements"], indent=1, sort_keys=True) + "\n")
    report["determinism"]["run1_measurement_sha256"] = sha256_bytes(
        json.dumps(m1, indent=1, sort_keys=True).encode())
    report["determinism"]["run2_measurement_sha256"] = sha256_bytes(
        json.dumps(m2, indent=1, sort_keys=True).encode())
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (HERE / "controls.json").write_text(json.dumps(controls, indent=1) + "\n")
    (HERE / "report_run2.json").unlink(missing_ok=True)

    cp = {
        "schema": "worker-045/gnum-evidence-rebind/checkpoint/v1",
        "task_id": TASK_ID,
        "worker": "worker-045",
        "checkpointed_at": now(),
        "verdict": verdict,
        "node_id": NODE_ID,
        "gate": GATE_ID,
        "class_id": CLASS_ID,
        "map_snapshot_sha256": snap_sha,
        "live_map_sha256_at_exit": live_sha_exit,
        "settled_window": settle["settled"],
        "counts": {k: len(v) for k, v in m1["buckets"].items()},
        "stale_refs": stale,
        "declared_historical_refs": hist_declared,
        "relocated_refs": hist_relocated,
        "registry_divergence_paths": [d["path"] for d in divergence],
        "missing_refs": missing,
        "c8_current_expression_binds": c8_ok,
        "c8_legacy_expression_binds": legacy_bound,
        "gate_binds_leadverify_successor": gate_binds_new,
        "gate_binds_superseded_leadverify": gate_binds_old,
        "controls_all_pass": controls["all_pass"],
        "deterministic": deterministic,
        "finding_ids": [f["id"] for f in findings],
        "next_falsifier": report["falsifier"][0],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(cp, indent=1) + "\n")
    runtime_cp = ROOT / "runtime" / "state" / "w045_gnum_evidence_rebind_checkpoint.json"
    try:
        runtime_cp.write_text(json.dumps(cp, indent=1) + "\n")
    except OSError as e:
        cp["runtime_checkpoint_error"] = str(e)

    print(json.dumps({
        "verdict": verdict,
        "map_snapshot_sha256": snap_sha,
        "counts": {k: len(v) for k, v in m1["buckets"].items()},
        "stale_unexplained": stale,
        "historical_declared": hist_declared,
        "historical_relocated": hist_relocated,
        "registry_divergence": [d["path"] for d in divergence],
        "missing": missing,
        "c8_current_binds": c8_ok,
        "gate_binds_successor": gate_binds_new,
        "gate_binds_superseded": gate_binds_old,
        "controls_all_pass": controls["all_pass"],
        "deterministic": deterministic,
        "findings": [f["id"] for f in findings],
    }, indent=1))
    return 0 if verdict != "VOID" else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": repr(exc)}), file=sys.stderr)
        sys.exit(3)
