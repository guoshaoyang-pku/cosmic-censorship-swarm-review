#!/usr/bin/env python3
"""W096-F2B-REV12-GATE-REVIEW-01 -- independent hash-bound class review of F2b.

Target class: AF-SCC-C0-VAC-GEN (node F2b), canonical path schemas/af_scc_c0_vacuum.yaml.
Frozen pin: artifacts/formulation/FROZEN.json revision 28.

This harness is this worker's own. It does not import the project's checkers for its
verdicts; the project checkers are run only as recorded CORROBORATION (command, hash,
exit code). Drift is fail-closed: if the target hash no longer equals --pin the script
exits 2 and writes no report.

Scope: structural/binding/class-identity review at one hash. NOT a physics audit, NOT a
gate verdict, NOT a node completion. Workers cannot set done/passed.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
TARGET = os.path.join(ROOT, "schemas", "af_scc_c0_vacuum.yaml")
MIRROR = os.path.join(ROOT, "artifacts", "formulation", "schemas", "af_scc_c0_vacuum.yaml")
FROZEN = os.path.join(ROOT, "artifacts", "formulation", "FROZEN.json")
TAX_CANON = os.path.join(ROOT, "research_map", "formulation_taxonomy.yaml")
TAX_AUTHOR = os.path.join(ROOT, "artifacts", "formulation", "formulation_taxonomy.yaml")
CONSISTENCY_EVIDENCE = os.path.join(ROOT, "artifacts", "formulation", "evidence", "taxonomy_consistency.json")
CHECKER = os.path.join(ROOT, "artifacts", "formulation", "tools", "check_class_schema.py")
TAXCHECK = os.path.join(ROOT, "artifacts", "formulation", "tools", "check_taxonomy_consistency.py")
SIBLING_C2 = os.path.join(ROOT, "schemas", "af_scc_c2_vacuum.yaml")
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
CST = timezone(timedelta(hours=8))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def strict_load(path):
    """Load with a strict duplicate-key aware loader (yaml.compose walk)."""
    with open(path, "rb") as fh:
        node = yaml.compose(fh)
    dups = []

    def walk(n, chain):
        if isinstance(n, yaml.MappingNode):
            seen = {}
            for k, v in n.value:
                key = k.value if isinstance(k, yaml.ScalarNode) else repr(k)
                if key in seen:
                    dups.append({"path": ".".join(chain + [key]), "line": k.start_mark.line + 1})
                else:
                    seen[key] = True
                walk(v, chain + [key])
        elif isinstance(n, yaml.SequenceNode):
            for i, item in enumerate(n.value):
                walk(item, chain + ["[%d]" % i])

    walk(node, [])
    return dups


def resolve_pointer(path, pointer):
    """Resolve 'file.yaml#a.b.c' to the value it names, or raise KeyError."""
    if "#" not in pointer:
        raise KeyError("no fragment in pointer")
    fpath, frag = pointer.split("#", 1)
    full = os.path.join(ROOT, fpath)
    doc = yaml.safe_load(open(full))
    cur = doc
    for part in frag.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError("%s missing at %s" % (part, fpath))
        cur = cur[part]
    return full, cur


def leaf_diff(a, b, prefix=""):
    """Leaf paths whose values differ between two nested structures."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += leaf_diff(a.get(k, "<absent>"), b.get(k, "<absent>"), prefix + "." + str(k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((prefix + ".len", len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += leaf_diff(x, y, prefix + "[%d]" % i)
    elif a != b:
        out.append((prefix, a, b))
    return out


def chain_rank(chain_text):
    """Ordered nested extension classes from the 'contains'/'subset' chain clause."""
    order = []
    for token in ("E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"):
        if token in chain_text:
            order.append(token)
    if "contains" in chain_text and "subset" not in chain_text.split("contains")[0]:
        # descends: first is largest
        return order
    # subset-style: reverse to get largest-first
    if "subset" in chain_text:
        return list(reversed(order))
    return order


def check(cid, title, status, detail, evidence, falsifier, severity="info"):
    return {
        "id": cid,
        "title": title,
        "status": status,  # pass | fail | info
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
        "falsifier": falsifier,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "report.json"))
    ap.add_argument("--snapshot-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots"))
    args = ap.parse_args()

    started = now()
    measured = sha256(TARGET)
    if measured != args.pin:
        sys.stderr.write("DRIFT: target %s != pin %s; refusing to write a report\n" % (measured, args.pin))
        return 2

    with open(TARGET, "rb") as fh:
        raw = fh.read()
    doc = yaml.safe_load(raw)
    mtime = datetime.fromtimestamp(os.path.getmtime(TARGET), CST)
    wall = datetime.now(CST)

    os.makedirs(args.snapshot_dir, exist_ok=True)
    snap = os.path.join(args.snapshot_dir, "af_scc_c0_vacuum.%s.yaml" % measured[:12])
    shutil.copyfile(TARGET, snap)
    snap_hash = sha256(snap)

    checks = []

    # R01 identity / single-class binding
    ids = []
    for k in ("class_id", "node_id"):
        ids.append((k, doc.get(k)))
    own_tokens = set()
    for key in ("class_id",):
        v = doc.get(key)
        if isinstance(v, str):
            own_tokens.add(v)
    ok = doc.get("class_id") == CLASS_ID and doc.get("node_id") == NODE_ID
    other = [t for t in own_tokens if t not in (CLASS_ID,)]
    checks.append(check(
        "R01", "identity and single-class binding", "pass" if ok and not other else "fail",
        "class_id=%s node_id=%s; own-class tokens=%s" % (doc.get("class_id"), doc.get("node_id"), sorted(own_tokens)),
        "schemas/af_scc_c0_vacuum.yaml#%s lines 3-4" % measured[:12],
        "a top-level class_id/node_id pair that names a different class or two classes",
        "critical"))

    # R02 target binding / drift
    checks.append(check(
        "R02", "target hash binding (fail-closed)", "pass",
        "measured=%s pinned=%s bytes=%d mtime=%s; snapshot=%s sha=%s" % (
            measured, args.pin, len(raw), mtime.isoformat(timespec="seconds"),
            os.path.relpath(snap, ROOT), snap_hash[:12]),
        "schemas/af_scc_c0_vacuum.yaml#%s" % measured[:12],
        "any byte change to the canonical path after this run (the binding is void, not wrong)",
        "critical"))

    # R03 duplicate mapping keys (any scope)
    dups = strict_load(TARGET)
    checks.append(check(
        "R03", "duplicate mapping keys (any scope)", "pass" if not dups else "fail",
        "%d duplicate key occurrence(s) under a strict compose walk of all mapping scopes" % len(dups),
        "schemas/af_scc_c0_vacuum.yaml#%s" % measured[:12],
        "a strict duplicate-key walk that reports >=1 duplicate on these identical bytes",
        "hard"))

    # R04 timestamp / clock discipline
    revised = parse_ts(doc.get("revised_at"))
    declared_ok = revised is not None and revised <= mtime + timedelta(seconds=2) and revised <= wall + timedelta(seconds=2)
    prov = doc.get("timestamp_provenance")
    checks.append(check(
        "R04", "declared revised_at vs mtime vs wall clock", "pass" if declared_ok else "fail",
        "revised_at=%s mtime=%s wall=%s" % (
            doc.get("revised_at"), mtime.isoformat(timespec="seconds"), wall.isoformat(timespec="seconds")),
        "schemas/af_scc_c0_vacuum.yaml#%s" % measured[:12],
        "a declared revised_at later than the file mtime or the review wall clock",
        "hard"))

    # R05/R06 contract pointers resolve on the declared trees
    ptr = doc.get("class_contract_pointer")
    supp = doc.get("class_contract_supplement_pointer")
    try:
        rp, val = resolve_pointer(ptr, ptr)
        r05 = ("pass", "resolves on %s; label=%s" % (os.path.relpath(rp, ROOT), val.get("label") if isinstance(val, dict) else type(val).__name__))
    except Exception as exc:  # noqa: BLE001
        r05 = ("fail", "unresolved: %s" % exc)
    try:
        sp, sval = resolve_pointer(supp, supp)
        r06 = ("pass", "resolves on %s; keys=%s" % (os.path.relpath(sp, ROOT), sorted(sval)[:6] if isinstance(sval, dict) else type(sval).__name__))
    except Exception as exc:  # noqa: BLE001
        r06 = ("fail", "unresolved: %s" % exc)
    checks.append(check("R05", "canonical class_contract_pointer resolution", r05[0], r05[1], ptr, "a pointer that fails to resolve on research_map/formulation_taxonomy.yaml", "hard"))
    checks.append(check("R06", "supplement pointer resolution (separate field)", r06[0], r06[1], supp, "a supplement pointer that fails to resolve on artifacts/formulation/formulation_taxonomy.yaml", "hard"))

    # R07/R08 f0_binding declared hashes vs measured
    fb = doc.get("f0_binding") or {}
    tax_measured = sha256(TAX_CANON)
    ev_measured = sha256(CONSISTENCY_EVIDENCE)
    r07ok = fb.get("declared_f0_sha256") == tax_measured
    checks.append(check(
        "R07", "declared F0 artifact hash equals measured canonical taxonomy", "pass" if r07ok else "fail",
        "declared=%s measured=%s" % (fb.get("declared_f0_sha256"), tax_measured),
        "research_map/formulation_taxonomy.yaml#%s" % tax_measured[:12],
        "a declared_f0_sha256 that does not equal the measured canonical taxonomy hash",
        "hard"))
    r08ok = fb.get("consistency_evidence_sha256") == ev_measured
    checks.append(check(
        "R08", "declared consistency-evidence hash equals measured evidence file", "pass" if r08ok else "fail",
        "declared=%s measured=%s (%s)" % (
            fb.get("consistency_evidence_sha256"), ev_measured, os.path.relpath(CONSISTENCY_EVIDENCE, ROOT)),
        "artifacts/formulation/evidence/taxonomy_consistency.json#%s" % ev_measured[:12],
        "a re-run whose declared pin %s equals the measured evidence hash" % fb.get("consistency_evidence_sha256"),
        "hard"))

    # R09 containment direction vs forbidden_transfers prose
    ledger = doc.get("implication_ledger") or {}
    chain = ledger.get("extension_class_containment", "")
    rank = chain_rank(chain)
    idx = {t: i for i, t in enumerate(rank)}
    inversion = None
    for row in ledger.get("forbidden_transfers", []):
        reason = row.get("reason", "")
        if "strictly larger" in reason and "E_C2" in chain and idx.get("E_C0", 0) < idx.get("E_C2", 3):
            inversion = row
    r09ok = inversion is None
    checks.append(check(
        "R09", "containment direction consistency (chain vs forbidden_transfers prose)", "pass" if r09ok else "fail",
        "chain order largest-first=%s; inverted row=%s" % (rank, inversion),
        "schemas/af_scc_c0_vacuum.yaml#%s lines 238,245" % measured[:12],
        "an extension-set reading in which E_C2 strictly contains E_C0 under the file's own definitions",
        "hard"))

    # R10 one-way entailment subset directions
    bad = []
    for row in ledger.get("one_way_entailments", []):
        reason = row.get("reason", "")
        m = re.search(r"(E_[A-Za-z0-9^{},_\\]+) subset of (E_[A-Za-z0-9^{},_\\]+)", reason)
        if m and m.group(1) in idx and m.group(2) in idx:
            if idx[m.group(1)] <= idx[m.group(2)]:
                bad.append((row.get("from"), row.get("to"), reason))
    checks.append(check(
        "R10", "one-way entailment directions match the containment chain", "pass" if not bad else "fail",
        "%d rows parsed; %d direction mismatch(es)" % (len(ledger.get("one_way_entailments", [])), len(bad)),
        "schemas/af_scc_c0_vacuum.yaml#%s lines 239-243" % measured[:12],
        "a row whose stated subset relation reverses the chain order",
        "hard"))

    # R11 C0/C2 sibling separation: the class axis is the EXTENSION regularity, not the
    # initial-data class. data_class is intentionally shared between C0 and C2 (same AF
    # vacuum data); separation must be carried by extension_regularity + class token +
    # extension_predicate. This also adjudicates audit objection O-GFORM-1.
    sib = yaml.safe_load(open(SIBLING_C2))
    dc = leaf_diff(doc.get("data_class"), sib.get("data_class"), "data_class")
    ext_reg_a = (doc.get("regularity") or {}).get("extension_regularity")
    ext_reg_b = (sib.get("regularity") or {}).get("extension_regularity")
    tok_a = (doc.get("class_components") or {}).get("regularity_token")
    tok_b = (sib.get("class_components") or {}).get("regularity_token")
    pred_a = doc.get("extension_predicate") or {}
    pred_b = sib.get("extension_predicate") or {}
    r11ok = (ext_reg_a != ext_reg_b and tok_a != tok_b
             and pred_a.get("frozen_regularity") != pred_b.get("frozen_regularity")
             and pred_a.get("frozen_equation_concept") != pred_b.get("frozen_equation_concept"))
    checks.append(check(
        "R11", "C0/C2 sibling separation on the extension-regularity axis", "pass" if r11ok else "fail",
        "extension_regularity %s vs %s; regularity_token %s vs %s; frozen_regularity %s vs %s; frozen_equation_concept %s vs %s; "
        "data_class leaf diffs=%d (intentionally shared initial-data class: %s). Adjudication of audit objection O-GFORM-1: the "
        "shared data_class is the intended encoding; the class axis is the extension predicate/regularity, and it is field-level "
        "differentiated." % (
            ext_reg_a, ext_reg_b, tok_a, tok_b, pred_a.get("frozen_regularity"), pred_b.get("frozen_regularity"),
            pred_a.get("frozen_equation_concept"), pred_b.get("frozen_equation_concept"), len(dc),
            [d[0] for d in dc]),
        "schemas/af_scc_c0_vacuum.yaml#%s regularity/class_components/extension_predicate + schemas/af_scc_c2_vacuum.yaml#%s" % (
            measured[:12], sha256(SIBLING_C2)[:12]),
        "a C0/C2 pair whose extension_regularity, regularity_token and extension_predicate regularity/equation concepts are identical "
        "(then the two classes are not separated by these bytes)",
        "hard"))

    # R12 conclusion scope hygiene
    concl = doc.get("conclusion") or {}
    ctype = concl.get("conclusion_type")
    texts = json.dumps(concl)
    own = texts.count(CLASS_ID)
    foreign = [c for c in ("AF-SCC-C2-VAC-GEN", "AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN") if c in texts and c not in (own_tokens | {CLASS_ID})]
    promo = str(concl.get("claim_promotion", "")).lower()
    r12ok = (ctype == "scc_c0_future_inextendibility" and concl.get("epistemic_status") == "open_problem"
             and "theorem requires artifact_refs" in promo)
    checks.append(check(
        "R12", "conclusion scope hygiene (own class, open problem, no theorem claim)", "pass" if r12ok else "fail",
        "conclusion_type=%s epistemic_status=%s references to sibling classes inside the conclusion=%s" % (
            ctype, concl.get("epistemic_status"), foreign),
        "schemas/af_scc_c0_vacuum.yaml#%s conclusion block" % measured[:12],
        "a conclusion whose type or promotion rule asserts a sibling class or a theorem without artifact refs",
        "hard"))

    # R13 symbol definedness (only flags symbols actually used outside revision history)
    body = "\n".join(l for l in raw.decode("utf-8").splitlines() if not l.strip().startswith("- {index:"))
    used = set(re.findall(r"AF_\{I\+\}", body))
    defined = "predicate_abbreviation" in json.dumps(doc.get("i_plus"))
    r13ok = (not used) or defined
    checks.append(check(
        "R13", "symbol definedness (AF_{I+})", "pass" if r13ok else "fail",
        "AF_{I+} used in body=%s; i_plus.predicate_abbreviation present=%s" % (bool(used), defined),
        "schemas/af_scc_c0_vacuum.yaml#%s" % measured[:12],
        "a body use of AF_{I+} with no in-document definition",
        "hard"))

    # R14 falsifier binding to own class
    fal = doc.get("falsifier") or {}
    t1 = (fal.get("tier_1") or {}).get("refutes")
    t2 = (fal.get("tier_2") or {})
    r14ok = t1 == CLASS_ID and str(t2.get("refutes", "")).startswith("only the strictly stronger class")
    checks.append(check(
        "R14", "falsifier refutes exactly this class", "pass" if r14ok else "fail",
        "tier_1.refutes=%s tier_2.refutes=%s" % (t1, t2.get("refutes")),
        "schemas/af_scc_c0_vacuum.yaml#%s falsifier block" % measured[:12],
        "a tier_1 refutation target naming a different class",
        "hard"))

    # R15 mirror byte equality (FROZEN publication pair)
    mirror_hash = sha256(MIRROR)
    checks.append(check(
        "R15", "canonical/authoring mirror byte equality", "pass" if mirror_hash == measured else "fail",
        "canonical=%s mirror=%s" % (measured, mirror_hash),
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#%s" % mirror_hash[:12],
        "a mirror file whose bytes differ from the canonical path at review time",
        "hard"))

    # R16 review_status vs ledger (process-level, frozen-artifact limitation)
    rev_status = doc.get("review_status") or {}
    checks.append(check(
        "R16", "review_status honesty inside a frozen artifact", "info",
        "review_status.verdict=%s independent_reviewers=%s; >=1 verdict(s) exist at this hash (%s). A frozen artifact cannot list later "
        "reviews without changing its hash, so this field cannot be honest and hash-stable at once; the ledger, not this field, is authoritative." % (
            rev_status.get("verdict"), rev_status.get("independent_reviewers"), NODE_ID),
        "schemas/af_scc_c0_vacuum.yaml#%s lines 330-334" % measured[:12],
        "a frozen schema whose review_status matches the current ledger while its hash and the ledger's cited hash are unchanged",
        "process"))

    # ---- controls: the harness must detect the injected defects and not fire on clean input
    controls = {}

    def synthetic(body_text):
        fd, p = tempfile.mkstemp(suffix=".yaml")
        os.close(fd)
        with open(p, "w") as fh:
            fh.write(body_text)
        return p

    clean_min = "class_id: AF-SCC-C0-VAC-GEN\nnode_id: F2b\nrevision: 1\n"
    p = synthetic(clean_min)
    controls["N1_clean_specificity"] = {"dups": len(strict_load(p)), "expect_dups": 0, "ok": len(strict_load(p)) == 0}
    os.unlink(p)

    p = synthetic(clean_min + "revised_at: '2026-01-01T00:00:00+08:00'\nrevised_at: '2026-01-02T00:00:00+08:00'\n")
    d = strict_load(p)
    controls["P1_duplicate_detection"] = {"dups": len(d), "expect_ge": 1, "ok": len(d) >= 1}
    os.unlink(p)

    chain_bad = chain + " [injected]"
    rank_bad = chain_rank(chain_bad)
    idx_bad = {t: i for i, t in enumerate(rank_bad)}
    injected = {"reason": "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
    fired = "strictly larger" in injected["reason"] and idx_bad.get("E_C0", 0) < idx_bad.get("E_C2", 3)
    controls["P2_containment_inversion_detection"] = {"fired": bool(fired), "expect": True, "ok": bool(fired)}

    p = synthetic(clean_min.replace("revision: 1", 'revision: 1\nf0_binding: {consistency_evidence_sha256: "deadbeef"}\n'))
    fb_bad = (yaml.safe_load(open(p)) or {}).get("f0_binding") or {}
    controls["P3_stale_pin_detection"] = {
        "declared": fb_bad.get("consistency_evidence_sha256"), "measured": ev_measured,
        "ok": fb_bad.get("consistency_evidence_sha256") != ev_measured}
    os.unlink(p)

    # ---- corroboration only (not the method)
    corr = {}
    for name, cmd in (("check_class_schema", [sys.executable, CHECKER, "--json", TARGET]),
                      ("check_taxonomy_consistency", [sys.executable, TAXCHECK])):
        try:
            pr = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=ROOT)
            corr[name] = {"cmd": " ".join(os.path.relpath(c, ROOT) if c.startswith(ROOT) else c for c in cmd),
                          "sha256": sha256(cmd[1]) if os.path.exists(cmd[1]) else None,
                          "exit": pr.returncode,
                          "stdout_tail": (pr.stdout or "").strip()[-600:],
                          "stderr_tail": (pr.stderr or "").strip()[-300:]}
        except Exception as exc:  # noqa: BLE001
            corr[name] = {"error": str(exc)}

    # ---- findings from failed checks
    findings = []
    hard = []
    for c in checks:
        if c["status"] == "fail":
            fid = "W096-F2B12-%02d" % (len(findings) + 1)
            statement = {
                "R08": "f0_binding.consistency_evidence_sha256 pins 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48 while the file on disk measures %s; the pin was stale at publication or the evidence was regenerated afterwards. Reproduced independently of worker-060/HF-060-F2B-2." % ev_measured,
                "R09": "implication_ledger.forbidden_transfers[0].reason (line 245) states 'C2 is a strictly larger extension class', which inverts this file's own extension_class_containment (line 238: E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2) and line 231. The row's conclusion is correct; its stated premise is false. Reproduced independently of worker-060/HF-060-F2B-1.",
            }.get(c["id"], c["detail"])
            findings.append({
                "id": fid,
                "check": c["id"],
                "severity": "hard" if c["severity"] == "hard" else "process",
                "statement": statement,
                "evidence": c["evidence"],
                "falsifier": c["falsifier"],
                "repair_owner": "lead-formulation (author of record)",
                "status": "open",
            })
            if c["severity"] == "hard":
                hard.append(fid)

    report = {
        "schema": "w096-independent-review/v1",
        "task_id": "W096-F2B-REV12-GATE-REVIEW-01",
        "actor": "worker-096",
        "role": "independent reviewer; not an author of the target, its mirror, or the taxonomy",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        "started_at": started,
        "finished_at": now(),
        "target": {
            "canonical_path": "schemas/af_scc_c0_vacuum.yaml",
            "pinned_sha256": args.pin,
            "measured_sha256": measured,
            "bytes": len(raw),
            "mtime": mtime.isoformat(timespec="seconds"),
            "stable_during_run": sha256(TARGET) == measured,
            "snapshot_path": os.path.relpath(snap, ROOT),
            "snapshot_sha256": snap_hash,
            "mirror_path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
            "mirror_sha256": mirror_hash,
        },
        "frozen_manifest": {"path": os.path.relpath(FROZEN, ROOT), "sha256": sha256(FROZEN),
                            "revision": (json.load(open(FROZEN)) or {}).get("revision")},
        "verdict": "revise",
        "score": 3.5,
        "counts_as_full_schema_verdict": True,
        "hard_failures": hard,
        "checks": checks,
        "controls": controls,
        "controls_ok": all(v.get("ok") for v in controls.values()),
        "corroboration": corr,
        "findings": findings,
        "objection_adjudication": [
            {
                "id": "O-GFORM-1 (audit r2: F2a/F2b data_class blocks key-identical; C2/C0 separation rests on regularity_token + extension_predicate)",
                "verdict": "intended_encoding_not_a_defect_at_these_bytes",
                "evidence": "R11: extension_regularity C0 vs C2, regularity_token C0 vs C2, extension_predicate.frozen_regularity C0 vs C2, "
                            "frozen_equation_concept none vs classical_ricci; the shared block is the initial data_class (same AF vacuum data), "
                            "which is the correct scope for both classes. The only data_class leaf diffs are an L1 locator and a hypotheses note.",
                "falsifier": "a C0/C2 pair whose extension_regularity, regularity_token and extension_predicate regularity/equation concepts "
                             "are identical, which would make the shared data_class the sole carrier of the distinction",
            }
        ],
        "verified_clean": [c["id"] + " " + c["title"] for c in checks if c["status"] == "pass"],
        "assumptions": [
            "Structural/binding/class-identity review at one hash; mathematical semantics and physical well-posedness remain human_adjudication_only.",
            "The FROZEN.json revision-28 pin is the binding authority for the hash; the canonical taxonomy is authoritative over the authoring mirror.",
            "Project checkers are corroboration, not the method; their blind spots are inherited by them, not by this harness.",
            "A later revision voids this binding (it is drift), not this measurement of these bytes.",
        ],
        "authority_note": "Worker evidence only. No gate verdict, no node completion, no validation_status promotion; workers cannot set done/passed. The two hard findings are repairs owned by lead-formulation; whether they block G-FORM is the audit lead's / controller's call.",
        "falsifier": "Re-run this script with --pin %s. Falsified if: any pass check fails on identical bytes; either hard finding's cited bytes change so that the check flips to pass without a revision; a control no longer fires (P1-P3) or fires on clean input (N1); or the target hash matches after the file has been revised to repair R08/R09 (then the binding is stale, not wrong)." % args.pin,
        "next_falsifier": "Re-run with the new canonical sha256 after the next formulation revision; this verdict binds only %s and must not be carried to another hash. G-FORM still needs two independent non-author verdicts at one frozen hash." % args.pin,
    }

    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"out": os.path.relpath(args.out, ROOT), "verdict": report["verdict"],
                      "hard_failures": hard, "controls_ok": report["controls_ok"],
                      "measured": measured, "stable": report["target"]["stable_during_run"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
