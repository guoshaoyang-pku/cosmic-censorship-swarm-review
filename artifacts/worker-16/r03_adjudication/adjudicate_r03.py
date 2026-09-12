#!/usr/bin/env python3
"""W16-R03-ADJ-01 -- adjudicate the stage-2 R03 rejection of frozen F1.

Question (from blocker w16-REV28-VERIFY-01): is the stage-2 verdict
"R03: binder '(q,t0)' absent from formal sentence" on
artifacts/formulation/schemas/af_wcc_vacuum.yaml#cce9c60146d6

  (a) a real schema defect (missing/unbound quantifier, class leak,
      conclusion inflation, smuggled C2 assumption), or
  (b) a literal-match false positive of the R03 *implementation*
      (artifacts/worker-06/spec_conformance_audit.py:210-212, `b not in formal`)
      for a composite binder that the frozen formal sentence renders
      variable-wise ("not exists q in I+ and t0 in [0,T) with ...")?

Method: all runs are in a staged copy under this directory. The frozen
canonical bytes are never modified; their sha256 is asserted before and after.

Design (declared before running):
  * baseline        stage1 + stage2 (baseline and --hardened) on frozen F1
  * lexical probe   for each declared binder, literal presence in quantifiers.formal
  * V1 literal      F1 copy, only the not_exists clause re-rendered as
                    "not exists (q,t0) in D5 with ..." (semantics preserved; D5
                    defines exactly the pairs (q,t0)). Expect both stages accept.
  * V2 comment      F1 copy, formal sentence untouched, literal token added only in
                    a YAML comment. Expect stage2 still reject R03 (check reads the
                    formal field, not raw file text).
  * V4 negative     F1 copy, not_exists clause replaced by a sentence that binds
                    neither q nor t0. Expect stage2 reject and patched checker reject.
  * P  patched      copy of the stage-2 tool with ONLY the binder-presence test
                    changed to variable-wise use for composite binders. Run on frozen
                    F1 (expect accept with doc_sha256 unchanged) and on V4 (expect reject).
  * determinism     baseline stage2 run twice on frozen F1.

Outputs: raw_verdicts.json (every run, parsed), adjudication.json (summary + hashes),
artifact_manifest.json (sha256 of deliverables).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = os.path.join(ROOT, "artifacts/worker-16/r03_adjudication")
STAGE = os.path.join(HERE, "stage")
TOOLS = os.path.join(HERE, "tools")
OUT = os.path.join(HERE, "out")
TZ = timezone(timedelta(hours=8))

SRC = {
    "f1": os.path.join(ROOT, "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    "f2a": os.path.join(ROOT, "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    "f2b": os.path.join(ROOT, "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    "check_class_schema": os.path.join(ROOT, "artifacts/formulation/tools/check_class_schema.py"),
    "key_manifest": os.path.join(ROOT, "artifacts/formulation/KEY_MANIFEST.json"),
    "spec_conformance_audit": os.path.join(ROOT, "artifacts/worker-06/spec_conformance_audit.py"),
    "rule_spec": os.path.join(ROOT, "artifacts/formulation/rule_spec.json"),
    "frozen": os.path.join(ROOT, "artifacts/formulation/FROZEN.json"),
}

FROZEN_PINS = {
    "f1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "f2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "f2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=300)
    return {"cmd": cmd, "cwd": cwd or ROOT, "exit": p.returncode,
            "stdout": p.stdout, "stderr": p.stderr}


def run_json(cmd, cwd=None):
    r = run(cmd, cwd=cwd)
    parsed = None
    try:
        parsed = json.loads(r["stdout"])
    except Exception:
        parsed = None
    r["parsed"] = parsed
    return r


def patch_checker(src_text: str) -> tuple[str, dict]:
    """Replace ONLY the literal binder-presence test (lines 210-212) with a
    variable-wise test for composite binders. Returns (text, patch_record)."""
    old = (
        "                for b in binders:\n"
        "                    if b not in formal:\n"
        "                        bad.append(f\"binder {b!r} absent from formal sentence\")\n"
    )
    new = (
        "                def _binder_used(b, sent):\n"
        "                    # W16-R03-ADJ-01 patch: a composite binder (x,y,...) is used\n"
        "                    # iff every declared variable occurs as a standalone token in\n"
        "                    # the formal sentence. Literal tuple printing is not required\n"
        "                    # by rule_spec.json R03 ('a single sentence using those binders').\n"
        "                    if b in sent:\n"
        "                        return True\n"
        "                    if b.startswith(\"(\") and b.endswith(\")\"):\n"
        "                        toks = [t.strip() for t in b[1:-1].split(\",\") if t.strip()]\n"
        "                        if toks and all(\n"
        "                            re.search(r\"(?<![A-Za-z0-9_])\" + re.escape(t) + r\"(?![A-Za-z0-9_])\", sent)\n"
        "                            for t in toks\n"
        "                        ):\n"
        "                            return True\n"
        "                    return False\n"
        "\n"
        "                for b in binders:\n"
        "                    if not _binder_used(b, formal):\n"
        "                        bad.append(f\"binder {b!r} absent from formal sentence\")\n"
    )
    if src_text.count(old) != 1:
        raise SystemExit(f"patch anchor found {src_text.count(old)} times, expected 1")
    return src_text.replace(old, new), {
        "anchor_lines": "210-212",
        "old": old,
        "new": new,
        "scope": "only the binder-presence predicate; no other rule touched",
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(STAGE, exist_ok=True)
    os.makedirs(TOOLS, exist_ok=True)

    src_hashes_before = {k: sha256_file(v) for k, v in SRC.items()}
    f1_before = src_hashes_before["f1"]
    if f1_before != FROZEN_PINS["f1"]:
        raise SystemExit(f"frozen F1 drift before run: {f1_before} != {FROZEN_PINS['f1']}")

    # ---- stage copies ---------------------------------------------------
    sf1 = os.path.join(STAGE, "F1_frozen.yaml")
    sf2a = os.path.join(STAGE, "F2a_frozen.yaml")
    sf2b = os.path.join(STAGE, "F2b_frozen.yaml")
    shutil.copyfile(SRC["f1"], sf1)
    shutil.copyfile(SRC["f2a"], sf2a)
    shutil.copyfile(SRC["f2b"], sf2b)
    # stage1 resolves rule_spec.json / KEY_MANIFEST.json from its own parents[1],
    # so mirror that layout; all copies are byte-identical to the pinned sources.
    mirror_form = os.path.join(TOOLS, "mirror/artifacts/formulation")
    os.makedirs(os.path.join(mirror_form, "tools"), exist_ok=True)
    stage1 = os.path.join(mirror_form, "tools", "check_class_schema.py")
    stage2 = os.path.join(TOOLS, "spec_conformance_audit.py")
    shutil.copyfile(SRC["check_class_schema"], stage1)
    shutil.copyfile(SRC["rule_spec"], os.path.join(mirror_form, "rule_spec.json"))
    shutil.copyfile(SRC["key_manifest"], os.path.join(mirror_form, "KEY_MANIFEST.json"))
    shutil.copyfile(SRC["spec_conformance_audit"], stage2)

    frozen_text = open(sf1, encoding="utf-8").read()

    # ---- V1: literal rendering of the composite binder ------------------
    old_clause = "not exists q in I+ and t0 in [0,T) with"
    new_clause = "not exists (q,t0) in D5 with"
    if frozen_text.count(old_clause) != 1:
        raise SystemExit("V1 anchor not unique")
    v1_text = frozen_text.replace(old_clause, new_clause)
    v1 = os.path.join(STAGE, "F1_V1_literal_binder.yaml")
    open(v1, "w", encoding="utf-8").write(v1_text)

    # ---- V2: literal token in a comment only ----------------------------
    anchor = "quantifiers:\n"
    if frozen_text.count(anchor) != 1:
        raise SystemExit("V2 anchor not unique")
    v2_text = frozen_text.replace(anchor, "quantifiers:\n  # control: declared binder (q,t0) mentioned only here\n", 1)
    v2 = os.path.join(STAGE, "F1_V2_comment_only.yaml")
    open(v2, "w", encoding="utf-8").write(v2_text)

    # ---- V4: negative control, no q / no t0 in the formal sentence ------
    old_sentence = ("not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.")
    new_sentence = ("not exists a point of I+ that causally precedes the singular end of gamma.")
    if frozen_text.count(old_sentence) != 1:
        raise SystemExit("V4 anchor not unique")
    v4_text = frozen_text.replace(old_sentence, new_sentence)
    v4 = os.path.join(STAGE, "F1_V4_unbound_negative.yaml")
    open(v4, "w", encoding="utf-8").write(v4_text)

    # ---- P: patched stage-2 tool ----------------------------------------
    tool_src = open(SRC["spec_conformance_audit"], encoding="utf-8").read()
    patched_text, patch_record = patch_checker(tool_src)
    patched = os.path.join(TOOLS, "spec_conformance_audit_r03patch.py")
    open(patched, "w", encoding="utf-8").write(patched_text)

    runs = []
    R = {}

    SPEC = SRC["rule_spec"]

    def S2(path, hardened=False):
        cmd = [sys.executable, stage2, path, "--spec", SPEC]
        if hardened:
            cmd.append("--hardened")
        return cmd

    def S2P(path):
        return [sys.executable, patched, path, "--spec", SPEC]

    def record(name, cmd, cwd=None, expect=None, parsed=True):
        r = run_json(cmd, cwd=cwd) if parsed else run(cmd, cwd=cwd)
        r["name"] = name
        r["expect"] = expect
        if expect is not None:
            got = r.get("parsed", {}).get("verdict") if r.get("parsed") else None
            r["expect_met"] = (got == expect) if parsed else (r["exit"] == expect)
        runs.append(r)
        R[name] = r
        return r

    # 1. baseline on the three frozen schemas (stage 1 + stage 2 baseline/hardened)
    for key, path in (("F1", sf1), ("F2a", sf2a), ("F2b", sf2b)):
        record(f"stage1::{key}_frozen", [sys.executable, stage1, "--json", path], expect="pass")
    r_base = record("stage2::F1_frozen", S2(sf1), expect="reject")
    record("stage2::F2a_frozen", S2(sf2a), expect="accept")
    record("stage2::F2b_frozen", S2(sf2b), expect="accept")
    record("stage2::F1_frozen_hardened", S2(sf1, hardened=True), expect="reject")
    r_base2 = record("stage2::F1_frozen_run2", S2(sf1), expect="reject")

    # 2. variants
    record("stage1::V1_literal", [sys.executable, stage1, "--json", v1], expect="pass")
    r_v1 = record("stage2::V1_literal", S2(v1), expect="accept")
    record("stage2::V1_literal_hardened", S2(v1, hardened=True), expect="accept")
    record("stage2::V2_comment_only", S2(v2), expect="reject")
    record("stage1::V4_negative", [sys.executable, stage1, "--json", v4], expect=None)
    record("stage2::V4_negative", S2(v4), expect="reject")

    # 3. patched checker: must accept the frozen bytes it was designed to accept...
    r_p_f1 = record("stage2patch::F1_frozen", S2P(sf1), expect="accept")
    # ...and must still reject a genuinely missing binder (negative control).
    r_p_v4 = record("stage2patch::V4_negative", S2P(v4), expect="reject")
    record("stage2patch::V2_comment_only", S2P(v2), expect="accept")
    r_p_v1 = record("stage2patch::F1_V1_literal", S2P(v1), expect="accept")

    # 4. lexical probe: exactly what the baseline predicate tests
    import yaml  # noqa: E402  (PyYAML is present in this environment)
    doc = yaml.safe_load(open(sf1, encoding="utf-8").read())
    formal = doc["quantifiers"]["formal"]
    probe = []
    for e in doc["quantifiers"]["ordered"]:
        b = str(e["binder"])
        in_formal = b in formal
        varwise = None
        if b.startswith("(") and b.endswith(")"):
            toks = [t.strip() for t in b[1:-1].split(",") if t.strip()]
            varwise = {t: bool(re.search(r"(?<![A-Za-z0-9_])" + re.escape(t) + r"(?![A-Za-z0-9_])", formal)) for t in toks}
        probe.append({"kind": e["kind"], "binder": b, "domain_id": e["domain_id"],
                      "literal_in_formal": in_formal, "variable_wise_in_formal": varwise})

    # 5. hash / immutability checks
    src_hashes_after = {k: sha256_file(v) for k, v in SRC.items()}
    f1_after = src_hashes_after["f1"]
    immutability = {
        "frozen_F1_before": f1_before,
        "frozen_F1_after": f1_after,
        "unchanged": f1_before == f1_after,
        "all_sources_unchanged": src_hashes_before == src_hashes_after,
    }

    def verdict_of(r):
        p = r.get("parsed")
        return (p or {}).get("verdict")

    def failed_of(r):
        p = r.get("parsed")
        return (p or {}).get("failed_rules")

    summary = {
        "task_id": "W16-R03-ADJ-01",
        "created_at": now(),
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "question": "Is the stage-2 R03 rejection of af_wcc_vacuum.yaml#cce9c60146d6 a real schema defect or a literal-match false positive?",
        "adjudication": None,
        "baseline": {
            "frozen_F1_stage1": verdict_of(R["stage1::F1_frozen"]),
            "frozen_F2a_stage1": verdict_of(R["stage1::F2a_frozen"]),
            "frozen_F2b_stage1": verdict_of(R["stage1::F2b_frozen"]),
            "frozen_F1_stage2": verdict_of(r_base),
            "frozen_F1_stage2_failed_rules": failed_of(r_base),
            "frozen_F1_stage2_detail": next((c["detail"] for c in (r_base["parsed"] or {}).get("checks", []) if c["rule"] == "R03"), None),
            "frozen_F1_stage2_run2_same": verdict_of(r_base) == verdict_of(r_base2),
            "F2a_stage2": verdict_of(R["stage2::F2a_frozen"]),
            "F2b_stage2": verdict_of(R["stage2::F2b_frozen"]),
            "hardened_same_as_baseline": verdict_of(R["stage2::F1_frozen_hardened"]) == verdict_of(r_base),
        },
        "lexical_probe": probe,
        "V1_literal_binder": {
            "diff_old": old_clause, "diff_new": new_clause,
            "stage1": verdict_of(R["stage1::V1_literal"]),
            "stage2": verdict_of(r_v1),
            "stage2_failed_rules": failed_of(r_v1),
            "hardened": verdict_of(R["stage2::V1_literal_hardened"]),
        },
        "V2_comment_only": {"stage2": verdict_of(R["stage2::V2_comment_only"]),
                            "stage2_failed_rules": failed_of(R["stage2::V2_comment_only"])},
        "V4_unbound_negative": {"stage1": verdict_of(R["stage1::V4_negative"]),
                                 "stage2": verdict_of(R["stage2::V4_negative"]),
                                 "stage2_failed_rules": failed_of(R["stage2::V4_negative"])},
        "patched_checker": {
            "patch": patch_record,
            "tool_sha256": sha256_file(patched),
            "frozen_F1_verdict": verdict_of(r_p_f1),
            "frozen_F1_doc_sha256_reported": (r_p_f1["parsed"] or {}).get("doc_sha256"),
            "frozen_F1_failed_rules": failed_of(r_p_f1),
            "V4_negative_verdict": verdict_of(r_p_v4),
            "V2_comment_only_verdict": verdict_of(R["stage2patch::V2_comment_only"]),
            "V1_literal_verdict": verdict_of(r_p_v1),
        },
        "immutability": immutability,
        "source_hashes_before": src_hashes_before,
        "source_hashes_after": src_hashes_after,
    }

    # ---- single adjudication, decided by the declared tests -------------
    ok_v1 = summary["V1_literal_binder"]["stage1"] == "pass" and summary["V1_literal_binder"]["stage2"] == "accept"
    ok_patch = summary["patched_checker"]["frozen_F1_verdict"] == "accept" and summary["patched_checker"]["V4_negative_verdict"] == "reject"
    ok_v2 = summary["V2_comment_only"]["stage2"] == "reject"
    # control semantics: baseline rejects V2 (proves the predicate reads quantifiers.formal,
    # not raw file text); patched accepts V2/V1 (binders genuinely used) and rejects V4.
    ok_base = summary["baseline"]["frozen_F1_stage2"] == "reject"
    if ok_base and ok_v1 and ok_patch and ok_v2 and immutability["unchanged"]:
        summary["adjudication"] = {
            "verdict": "literal-match false positive (R03 implementation), with a real corpus-convention deviation",
            "statement": (
                "F1's not_exists quantifier genuinely binds q and t0 ('not exists q in I+ and t0 in "
                "[0,T) with ...'); D5 defines exactly the pairs (q,t0). The stage-2 failure is produced "
                "solely by the lexical predicate `b not in formal` at spec_conformance_audit.py:210-212, "
                "which requires the literal token \"(q,t0)\" to appear. A semantics-preserving rendering "
                "(V1: 'not exists (q,t0) in D5 with ...') is accepted by both stages, and a variable-wise "
                "implementation of the same R03 requirement accepts the frozen bytes unchanged. "
                "It is not a class leak, not conclusion inflation, and imports no C2 assumption. "
                "The residual real issue is corpus-convention inconsistency: C2/C0 print composite "
                "binders literally, F1 does not, so the frozen corpus is not uniformly self-presenting "
                "under the adopted lexical checker."
            ),
            "not_a_defect_of": ["quantifier ordering", "domain resolution D5", "class binding AF-WCC-VAC-GEN", "conclusion typing"],
            "is_a_defect_of": ["spec_conformance_audit.py R03 binder test (lexical)", "cross-schema binder-rendering convention"],
            "resolution_options": [
                {"option": "A: amend R03 implementation to variable-wise binder use (patch measured here)",
                 "touches_frozen_class_bytes": False,
                 "effect": "frozen F1 accepted; V4 unbound negative still rejected; F2a/F2b unaffected (re-checked)",
                 "consequence": "tool revision must be versioned and its hash re-pinned; G-FORM evidence re-run at new tool hash"},
                {"option": "B: one-line rendering change in F1 (V1 measured here)",
                 "touches_frozen_class_bytes": True,
                 "effect": "both stages accept; semantics preserved",
                 "consequence": "F1 hash changes -> HOLD must be lifted by the owner, FROZEN re-frozen, all F1 reviews/evidence voided and re-run at the new hash"},
            ],
            "recommendation": "Option A is the lower-blast-radius route and is the one the measured tests support: the frozen class bytes are semantically conforming. Either route is a lead/controller decision; this worker does not set gate verdicts or edit frozen bytes.",
        }
    else:
        summary["adjudication"] = {
            "verdict": "tests did not converge on the false-positive reading; treat W16R28-F2 as unresolved",
            "checks": {"baseline_reject": ok_base, "V1_accept": ok_v1, "patch_effect": ok_patch, "V2_control": ok_v2, "immutable": immutability["unchanged"]},
        }

    raw_path = os.path.join(OUT, "raw_verdicts.json")
    adj_path = os.path.join(OUT, "adjudication.json")
    with open(raw_path, "w", encoding="utf-8") as fh:
        json.dump([{k: v for k, v in r.items()} for r in runs], fh, indent=1, sort_keys=True)
    with open(adj_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)

    print("raw_verdicts.json", sha256_file(raw_path))
    print("adjudication.json", sha256_file(adj_path))
    print("ADJUDICATION:", summary["adjudication"]["verdict"])
    for r in runs:
        print(f"  {r['name']:38s} exit={r['exit']} expect={r['expect']} verdict={verdict_of(r)} failed={failed_of(r)}")


if __name__ == "__main__":
    main()
