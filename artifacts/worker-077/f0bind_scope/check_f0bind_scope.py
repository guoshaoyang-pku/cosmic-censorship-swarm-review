#!/usr/bin/env python3
"""W077-F0BIND-SCOPE-01 - read-only scope audit of the declared f0_binding consistency evidence.

Question: at the live pins, does the f0_binding.consistency_evidence declared by the three vacuum
class schemas establish the F0-to-schema consistency it is relied upon for - specifically, does its
check domain cover the visibility strength direction on which F0 (rev5) and F1 (rev13) disagree?

Method: reproduce the declared evidence byte-for-byte by running the EXACT canonical checker bytes in
a sandbox ROOT, then mutate the sandbox inputs to census what the checker can and cannot see. No
canonical path is written; canonical pins are re-measured at exit and drift is fatal (exit 3).

Exit codes: 0 = SCOPE_GAP_CONFIRMED (all hypotheses hold), 2 = SCOPE_GAP_REFUTED, 3 = pin drift or
harness failure. Deterministic: no wall-clock unless W077_MEASURED_AT is set.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG_PATH = HERE / "PREREGISTRATION.json"
SANDBOX = HERE / "sandbox" / "root"
CHECKER_REL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
EVIDENCE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
F0_REL = "research_map/formulation_taxonomy.yaml"
SUPP_REL = "artifacts/formulation/formulation_taxonomy.yaml"
ALIAS_REL = "artifacts/formulation/VOCAB_ALIASES.json"
SCHEMAS = {
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    "F2a": ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def check(cid, status, detail, evidence):
    return {"id": cid, "status": status, "detail": detail, "evidence": evidence}


def scalar_lines(path):
    """path -> (line, text) for every scalar node, using compose marks."""
    node = yaml.compose(Path(path).read_text())
    out = {}

    def walk(n, p):
        if isinstance(n, yaml.MappingNode):
            for k, v in n.value:
                walk(v, p + "." + str(k.value))
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, p + "[%d]" % i)
        elif isinstance(n, yaml.ScalarNode):
            out[p] = (n.start_mark.line + 1, str(n.value))
    walk(node, "")
    return out


def line_of(path, needle):
    for i, line in enumerate(Path(path).read_text().splitlines(), 1):
        if needle in line:
            return i
    return None


def build_sandbox():
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    copies = [
        (ROOT / F0_REL, SANDBOX / F0_REL),
        (ROOT / SUPP_REL, SANDBOX / SUPP_REL),
        (ROOT / ALIAS_REL, SANDBOX / ALIAS_REL),
        (ROOT / CHECKER_REL, SANDBOX / CHECKER_REL),
        (ROOT / EVIDENCE_REL, SANDBOX / EVIDENCE_REL),
    ]
    for cid, (_, rel) in SCHEMAS.items():
        copies.append((ROOT / rel, SANDBOX / rel))
    for src, dst in copies:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def run_sandbox():
    proc = subprocess.run(
        [sys.executable, str(SANDBOX / CHECKER_REL)],
        cwd=str(SANDBOX), capture_output=True, text=True, timeout=120,
    )
    ev_path = SANDBOX / EVIDENCE_REL
    ev = json.loads(ev_path.read_text()) if ev_path.exists() else None
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), ev, ev_path.read_bytes()


def main():
    prereg = json.loads(PREREG_PATH.read_text())
    measured_at = os.environ.get("W077_MEASURED_AT")
    pins = prereg["pins"]
    report = {
        "task_id": prereg["task_id"],
        "actor": prereg["actor"],
        "measured_at": measured_at,
        "class_id": prereg["class_id"],
        "class_ids": prereg["class_ids"],
        "node_id": prereg["node_id"],
        "gate": prereg["gate"],
        "conclusion_type": "artifact_and_checker_measurement",
        "question": prereg["question"],
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "sandbox": {"root": str(SANDBOX.relative_to(HERE)), "canonical_paths_written": []},
        "checks": [],
        "binding_blocks": {},
        "f0_direction_statements": [],
        "f1_corrected_statements": [],
        "checker_domain": {},
        "controls": [],
        "reliance": {},
        "findings": [],
        "verdict": None,
        "falsifier": prereg["falsifier"],
        "non_claims": prereg["non_claims"],
    }

    # ---- P1: pins stable at entry ----
    start_hashes = {rel: sha256_file(ROOT / rel) for rel in pins}
    drift = {rel: {"declared": pins[rel], "measured": start_hashes[rel]}
             for rel in pins if start_hashes[rel] != pins[rel]}
    report["pins_at_start"] = start_hashes
    report["checks"].append(check(
        "P1-PINS-DECLARED-AT-ENTRY", "PASS" if not drift else "FAIL",
        "all %d preregistered pins resolve to their declared sha256" % len(pins) if not drift
        else "pin drift at entry: %s" % sorted(drift),
        ["%s#sha256:%s" % (r, start_hashes[r]) for r in sorted(pins)],
    ))
    if drift:
        report["verdict"] = "PIN_DRIFT_AT_ENTRY"
        return finish(report, 3, start_hashes)

    # ---- B1: the three f0_binding blocks ----
    blocks = {}
    for cid, (cls, rel) in SCHEMAS.items():
        sch = yaml.safe_load((ROOT / rel).read_text())
        blk = sch.get("f0_binding") or {}
        ev_path = blk.get("consistency_evidence")
        ev_sha = blk.get("consistency_evidence_sha256")
        live_sha = sha256_file(ROOT / ev_path) if ev_path else None
        blocks[cid] = {
            "class_id": sch.get("class_id") or cls,
            "schema": rel,
            "schema_sha256": start_hashes[rel],
            "declared_f0_artifact": blk.get("declared_f0_artifact"),
            "declared_f0_sha256": blk.get("declared_f0_sha256"),
            "consistency_evidence": ev_path,
            "consistency_evidence_sha256": ev_sha,
            "consistency_evidence_resolves": ev_sha == live_sha,
            "checked_at": blk.get("checked_at"),
            "rule": blk.get("rule"),
            "binding_note": blk.get("binding_note"),
        }
    report["binding_blocks"] = blocks
    all_same_ev = len({b["consistency_evidence"] for b in blocks.values()}) == 1
    all_resolve = all(b["consistency_evidence_resolves"] for b in blocks.values())
    all_f0 = len({b["declared_f0_sha256"] for b in blocks.values()}) == 1
    report["checks"].append(check(
        "B1-THREE-BINDINGS-ONE-EVIDENCE", "PASS" if (all_same_ev and all_resolve and all_f0) else "FAIL",
        "3/3 schemas declare the same evidence path+hash resolving on disk and the same declared F0 hash"
        if (all_same_ev and all_resolve and all_f0) else "binding blocks disagree or a declared evidence hash does not resolve",
        ["%s#sha256:%s" % (blocks[c]["schema"], blocks[c]["schema_sha256"]) for c in sorted(blocks)]
        + ["%s#sha256:%s" % (EVIDENCE_REL, start_hashes[EVIDENCE_REL])],
    ))

    # ---- B2: reproduce the declared evidence inside the sandbox ----
    build_sandbox()
    rc0, out0, err0, ev0, ev0_bytes = run_sandbox()
    ev_identical = ev0_bytes == (ROOT / EVIDENCE_REL).read_bytes()
    report["checks"].append(check(
        "B2-EVIDENCE-REPRODUCES-BYTE-IDENTICAL",
        "PASS" if (rc0 == 0 and out0.startswith("CONSISTENT") and ev_identical) else "FAIL",
        "canonical checker bytes in sandbox ROOT: exit=%d stdout=%r; sandbox evidence byte-identical to live evidence=%s"
        % (rc0, out0, ev_identical),
        ["%s#sha256:%s" % (CHECKER_REL, start_hashes[CHECKER_REL]),
         "%s#sha256:%s" % (EVIDENCE_REL, sha256_bytes(ev0_bytes))],
    ))
    report["live_evidence"] = {
        "path": EVIDENCE_REL, "sha256": start_hashes[EVIDENCE_REL],
        "consistent": (ev0 or {}).get("consistent"), "errors": (ev0 or {}).get("errors"),
        "contract_divergences": (ev0 or {}).get("contract_divergences"),
        "classes_compared": (ev0 or {}).get("classes_compared"),
    }

    # ---- C1/C2: live direction statements ----
    f0_lines = scalar_lines(ROOT / F0_REL)
    for path, (line, text) in sorted(f0_lines.items(), key=lambda kv: kv[1][0]):
        if not re.search(r"strong(er)?\b", text, re.I):
            continue
        cls = path.split(".")[2] if path.startswith(".classes.") else None
        report["f0_direction_statements"].append({
            "yaml_path": path, "line": line, "class": cls,
            "direction": "stronger" if re.search(r"stronger", text, re.I) else "other",
            "text_excerpt": " ".join(text.split())[:260],
            "checker_reads_this_field": bool(path.endswith(".conclusion.text")),
        })
    live_set_stronger = []
    raw_lines = (ROOT / F0_REL).read_text().splitlines()
    for i, line in enumerate(raw_lines, 1):
        if "Strictly stronger than the parent class" in line or "is strictly stronger; it is registered as variant" in line:
            live_set_stronger.append({"line": i, "text": line.strip()})
    conclusion_text = ((yaml.safe_load((ROOT / F0_REL).read_text())["classes"]["AF-WCC-VAC-GEN"]
                        .get("conclusion") or {}).get("text") or "")
    probe_token = ("J-(I+)" in conclusion_text.replace(" ", "")) or ("J^-(I+)" in conclusion_text.replace(" ", ""))
    report["checks"].append(check(
        "C1-F0-LIVE-SUPERSEDED-DIRECTION",
        "PASS" if len(live_set_stronger) >= 2 else "FAIL",
        "live F0 asserts SET strictly stronger at %d sites; AF-WCC-VAC-GEN conclusion.text is read by the checker's D1 probe but contains no probe token (J-(I+)/J^-(I+))=%s"
        % (len(live_set_stronger), probe_token),
        ["%s#sha256:%s:line%d" % (F0_REL, start_hashes[F0_REL], s["line"]) for s in live_set_stronger],
    ))
    report["f0_set_stronger_live_sites"] = live_set_stronger
    report["f0_d1_probe_token_present"] = probe_token

    f1 = yaml.safe_load((ROOT / SCHEMAS["F1"][1]).read_text())
    civ = f1.get("class_identity_variants") or []
    set_var = next((v for v in civ if str(v.get("variant_id")) == "SET"), civ[0] if civ else {})
    f1_lines = scalar_lines(ROOT / SCHEMAS["F1"][1])
    set_relation = str(set_var.get("relation", ""))
    relation_line = next((ln for p, (ln, t) in f1_lines.items()
                          if p.startswith(".class_identity_variants[0]") and p.endswith(".relation")), None)
    report["f1_corrected_statements"] = [{
        "yaml_path": "class_identity_variants[variant_id=SET].relation",
        "line": relation_line,
        "direction": "weaker" if "strictly WEAKER" in set_relation else "other",
        "text_excerpt": " ".join(set_relation.split())[:400],
    }]
    rev_notes = json.dumps(f1.get("revision_history", []))
    report["checks"].append(check(
        "C2-F1-LIVE-CORRECTED-DIRECTION",
        "PASS" if "strictly WEAKER" in set_relation and "strictly STRONGER" in rev_notes else "FAIL",
        "F1 rev13 SET relation asserts strictly WEAKER and its revision history discloses the correction from strictly STRONGER",
        ["%s#sha256:%s" % (SCHEMAS["F1"][1], start_hashes[SCHEMAS["F1"][1]])],
    ))

    # ---- D1: checker domain census from source ----
    src = (ROOT / CHECKER_REL).read_text()
    read_paths = sorted({m[1] for m in re.findall(r'ROOT/(["\'])([^"\']+)\1', src)})
    out_match = re.search(r'out\s*=\s*ROOT/(["\'])([^"\']+)\1', src)
    written_output = out_match.group(2) if out_match else None
    probe_lines = [(i, l.strip()) for i, l in enumerate(src.splitlines(), 1)
                   if "J^-(I+)" in l or "J-(I+)" in l]
    compared = sorted(set(re.findall(r'\[["\']([a-z_]+)["\']\]', src))
                      | set(re.findall(r'\.get\(["\']([a-z_]+)["\']', src)))
    report["checker_domain"] = {
        "checker": CHECKER_REL,
        "checker_sha256": start_hashes[CHECKER_REL],
        "files_referenced_from_ROOT": read_paths,
        "written_output": written_output,
        "opens_any_schema": "schemas/" in src,
        "compares_top_level_variants_key": bool(re.search(r'A(\.get\(|\[)["\']variants["\']', src)),
        "direction_probe_lines": [{"line": i, "code": c} for i, c in probe_lines],
        "compared_field_tokens": compared,
    }
    # derived coverage metric: how many live superseded-direction sites does the probe cover?
    direction_sites_covered = []
    for s in report["f0_direction_statements"]:
        if s["direction"] != "stronger" or s["class"] not in (None, "AF-WCC-VAC-GEN"):
            continue
        covered = bool(s["checker_reads_this_field"] and probe_token)
        direction_sites_covered.append({"line": s["line"], "yaml_path": s["yaml_path"], "covered": covered})
    report["direction_sites"] = {
        "live_set_stronger_sites": len(report["f0_set_stronger_live_sites"]),
        "covered_by_declared_evidence_probe": sum(1 for s in direction_sites_covered if s["covered"]),
        "per_site": direction_sites_covered,
    }
    domain_ok = (not report["checker_domain"]["opens_any_schema"]
                 and not report["checker_domain"]["compares_top_level_variants_key"]
                 and len(probe_lines) >= 1)
    report["checks"].append(check(
        "D1-CHECKER-DOMAIN-EXCLUDES-SCHEMAS-AND-VARIANTS",
        "PASS" if domain_ok else "FAIL",
        "canonical checker references %s; opens any schema=%s; compares top-level F0 variants key=%s; %d direction probe line(s)"
        % (read_paths, report["checker_domain"]["opens_any_schema"],
           report["checker_domain"]["compares_top_level_variants_key"], len(probe_lines)),
        ["%s#sha256:%s" % (CHECKER_REL, start_hashes[CHECKER_REL])],
    ))
    report["checks"].append(check(
        "D2-DIRECTION-SITE-COVERAGE",
        "PASS" if (report["direction_sites"]["live_set_stronger_sites"] >= 2
                   and report["direction_sites"]["covered_by_declared_evidence_probe"] == 0) else "FAIL",
        "live F0 SET-stronger sites=%d; covered by the declared evidence probe=%d"
        % (report["direction_sites"]["live_set_stronger_sites"],
           report["direction_sites"]["covered_by_declared_evidence_probe"]),
        ["%s#sha256:%s:lines%s" % (F0_REL, start_hashes[F0_REL],
                                   [s["line"] for s in report["f0_set_stronger_live_sites"]])],
    ))

    # ---- M-series mutation controls in the sandbox ----
    controls = []

    def control(mid, desc, mutate, expect_rc, expect_consistent, expect_divergence=None,
                expect_evidence_unchanged=False, expect_in_domain_error=None):
        build_sandbox()
        mutate()
        rc, out, err, ev, ev_bytes = run_sandbox()
        cons = (ev or {}).get("consistent")
        divs = (ev or {}).get("contract_divergences") or []
        div_ids = [d.get("id") for d in divs]
        ok = (rc == expect_rc and cons is expect_consistent)
        if expect_divergence is not None:
            ok = ok and (expect_divergence in div_ids)
        if expect_evidence_unchanged:
            ok = ok and ev_bytes == (ROOT / EVIDENCE_REL).read_bytes()
        if expect_in_domain_error is not None:
            errs = (ev or {}).get("errors") or []
            ok = ok and any(expect_in_domain_error in e for e in errs)
        controls.append({
            "id": mid, "description": desc, "sandbox_exit": rc, "sandbox_stdout": out,
            "consistent": cons, "contract_divergences": div_ids,
            "expected": {"exit": expect_rc, "consistent": expect_consistent,
                         "divergence": expect_divergence,
                         "evidence_unchanged": expect_evidence_unchanged,
                         "in_domain_error": expect_in_domain_error},
            "status": "PASS" if ok else "FAIL",
        })
        return ok

    def mutate_text(rel, old, new):
        p = SANDBOX / rel
        t = p.read_text()
        assert old in t, "mutation target missing: %r" % old
        p.write_text(t.replace(old, new, 1))

    def mutate_yaml(rel, fn):
        p = SANDBOX / rel
        d = yaml.safe_load(p.read_text())
        fn(d)
        p.write_text(yaml.safe_dump(d, sort_keys=False))

    control("M1a-PROBE-TOKEN-FIRES",
            "inject the D1 lexical probe token J-(I+) into the AF-WCC-VAC-GEN conclusion text",
            lambda: mutate_yaml(F0_REL, lambda d: d["classes"]["AF-WCC-VAC-GEN"]["conclusion"].__setitem__(
                "text", "Set-based reading: every future-inextendible causal geodesic contained in J-(I+) is complete.")),
            expect_rc=1, expect_consistent=False, expect_divergence="D1")
    control("M1b-VARIANTS-RELATION-MUTATION-INVISIBLE",
            "flip the live F0 variants[0].definition 'Strictly stronger than the parent class' to 'Strictly weaker'",
            lambda: mutate_text(F0_REL, "Strictly stronger than the parent class", "Strictly weaker than the parent class"),
            expect_rc=0, expect_consistent=True)
    control("M1c-CONCLUSION-PROSE-MUTATION-INVISIBLE",
            "flip the live F0 conclusion prose 'is strictly stronger; it is registered as variant' to 'is strictly weaker'",
            lambda: mutate_text(F0_REL, "is strictly stronger; it is registered as variant", "is strictly weaker; it is registered as variant"),
            expect_rc=0, expect_consistent=True)
    control("M2-IN-DOMAIN-MUTATION-FIRES",
            "set the lead-contract regularity_token of AF-WCC-VAC-GEN to C2 (in-domain compared field)",
            lambda: mutate_yaml(SUPP_REL, lambda d: d["class_contracts"]["AF-WCC-VAC-GEN"]["components"].__setitem__("regularity_token", "C2")),
            expect_rc=1, expect_consistent=False, expect_in_domain_error="regularity")
    control("M3-SCHEMA-MUTATION-INVISIBLE",
            "flip the F1 schema SET relation strictly WEAKER -> strictly STRONGER",
            lambda: mutate_yaml(SCHEMAS["F1"][1], lambda d: d["class_identity_variants"][0].__setitem__(
                "relation", str(d["class_identity_variants"][0]["relation"]).replace("strictly WEAKER", "strictly STRONGER"))),
            expect_rc=0, expect_consistent=True, expect_evidence_unchanged=True)
    report["controls"] = controls
    report["checks"].append(check(
        "M-CONTROLS", "PASS" if all(c["status"] == "PASS" for c in controls) else "FAIL",
        "%d/%d mutation controls behaved as preregistered" % (sum(c["status"] == "PASS" for c in controls), len(controls)),
        [EVIDENCE_REL + "#sha256:" + start_hashes[EVIDENCE_REL]],
    ))

    # ---- R1: reliance census over reviews/ ----
    reviews_dir = ROOT / "reviews"
    citing, examples = 0, []
    for f in sorted(reviews_dir.glob("*.json")):
        try:
            t = f.read_text()
        except OSError:
            continue
        if "9e335e9b" not in t and "taxonomy_consistency" not in t:
            continue
        citing += 1
        low = t.lower()
        if len(examples) < 8:
            i = t.find("9e335e9b")
            examples.append({
                "path": str(f.relative_to(ROOT)), "sha256": sha256_file(f),
                "records_consistent_true": "consistent" in low,
                "excerpt": " ".join(t[max(0, i - 120):i + 180].split()) if i >= 0 else "",
            })
    report["reliance"] = {
        "review_files_citing_declared_evidence": citing,
        "examples": examples,
        "f1_binding_note": blocks["F1"]["binding_note"],
        "f1_rule": blocks["F1"]["rule"],
    }
    report["checks"].append(check(
        "R1-RELIANCE-RECORDED", "PASS" if citing > 0 else "NOTE",
        "%d review file(s) cite the declared evidence hash/path; examples pinned" % citing,
        ["%s#sha256:%s" % (e["path"], e["sha256"]) for e in examples[:4]],
    ))

    # ---- findings ----
    report["related_evidence"] = [
        {"path": "artifacts/worker-079/rev29_bindchain/report.json",
         "sha256": "c7330f9799eb5cf6faccb82b171805a01cc5948222e836efb6d1ce5c12e9fd72",
         "role": "independent structural bind-chain census: 36 PASS at the same pins; it checks hash resolution and pointer resolution, not direction semantics"},
        {"path": "artifacts/worker-004/f1_strictness_direction/report.json",
         "sha256": "c70cdbb306aa8d32299522cefef57d5a87168e4ffd1ddeb700131efb69377fd0",
         "role": "independent direction proof: SET/union reading is strictly weaker; overall F1 axis accept, F0 still asserts the opposite"},
        {"path": "reviews/F1-review-worker-089.json",
         "sha256": "9a4bb3f3268cec2b4966a0115a5f14a6890b954e620a8a2a966996456af6a96c",
         "role": "review reliance example: records the rev13 f0_binding refresh as resolving via consistency_evidence.consistent=true"},
    ]
    report["decision_inputs"] = [
        {"option": "A-evidence-scope-repair",
         "change": "extend the canonical checker (or add a companion probe) to compare the F0 SET relation/variants text against the schemas' class_identity_variants relation, and to key the D1 test on the union wording rather than the literal J-(I+) token; then re-run and re-stamp all three f0_binding.consistency_evidence_sha256",
         "blast_radius": "evidence artifact, checker, three schema f0_binding blocks (hash moves; all current verdicts at those hashes void)"},
        {"option": "B-f0-erratum-or-revision",
         "change": "controller/ESC-2 corrects or explicitly scopes the two live F0 sites (variants[0].definition line 94; classes.AF-WCC-VAC-GEN.conclusion.text line 200); a write to research_map/formulation_taxonomy.yaml voids G-F0 and requires fresh accepts",
         "blast_radius": "G-F0 verdict; every artifact binding 0abb9ed8a961; FROZEN manifest"},
        {"option": "C-record-binding-scope",
         "change": "record in binding_note/rule that the declared evidence certifies map-vs-supplement token/axis consistency only and is not direction evidence; no byte moves",
         "blast_radius": "three schema f0_binding binding_note fields (hash moves); no G-F0 change"},
    ]
    report["findings"] = [
        {
            "id": "W077-FBS-01",
            "severity": "major",
            "type": "declared_consistency_evidence_does_not_cover_bound_direction_axis",
            "finding": "All three vacuum class schemas bind F0 0abb9ed8a961 with consistency_evidence "
                       "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9b, but that evidence "
                       "is produced by a map-taxonomy-vs-lead-contract checker whose compared-field domain "
                       "contains no schema file and no F0 variants block. The one direction-sensitive probe "
                       "(D1) is a lexical test for 'J-(I+)'/'J^-(I+)' in the AF-WCC-VAC-GEN conclusion text and "
                       "does not fire on the live rev5 wording, so the evidence reports consistent=true while "
                       "live F0 asserts SET is strictly stronger (variants[0].definition; conclusion.text) and "
                       "live F1 rev13 asserts strictly weaker.",
            "falsifier": "a pipeline checker whose compared fields cover the F0-variants vs schema-SET strength relation; or live F0/F1 direction agreement.",
        },
        {
            "id": "W077-FBS-02",
            "severity": "minor",
            "type": "dormant_direction_bearing_text_in_checker",
            "finding": "The canonical checker's only direction-bearing text is its dormant D1 divergence record "
                       "(relation: 'the F0 condition is strictly STRONGER'), which encodes the superseded label; if "
                       "D1 fires at a future hash the emitted evidence would record that direction as the tool's ruling.",
            "falsifier": "a canonical checker revision whose D1 record states the independently proved direction (set-based weaker).",
        },
    ]

    # ---- verdict ----
    h = {c["id"]: c["status"] for c in report["checks"]}
    confirmed = all(h.get(k) == "PASS" for k in (
        "B1-THREE-BINDINGS-ONE-EVIDENCE", "B2-EVIDENCE-REPRODUCES-BYTE-IDENTICAL",
        "C1-F0-LIVE-SUPERSEDED-DIRECTION", "C2-F1-LIVE-CORRECTED-DIRECTION",
        "D1-CHECKER-DOMAIN-EXCLUDES-SCHEMAS-AND-VARIANTS", "D2-DIRECTION-SITE-COVERAGE",
        "M-CONTROLS", "R1-RELIANCE-RECORDED"))
    report["verdict"] = "SCOPE_GAP_CONFIRMED" if confirmed else "SCOPE_GAP_REFUTED"
    report["next_falsifier"] = (
        "Re-run at the same pins: any schema whose f0_binding names a direction-covering checker or evidence; "
        "any live F0/F1 revision whose SET strength statements agree; any checker revision that compares F0 "
        "variants text against the schemas; or drift of any pinned input (voids the run).")
    return finish(report, 0 if confirmed else 2, start_hashes)


def finish(report, rc, start_hashes):
    # exit pins: drift is fatal
    end_hashes = {rel: sha256_file(ROOT / rel) for rel in start_hashes}
    drift = {rel: {"start": start_hashes[rel], "end": end_hashes[rel]}
             for rel in start_hashes if end_hashes[rel] != start_hashes[rel]}
    report["pins_at_exit"] = end_hashes
    report["in_run_drift"] = drift
    if drift and report.get("verdict") not in (None, "PIN_DRIFT_AT_ENTRY"):
        report["verdict"] = "VOIDED_PIN_DRIFT"
        rc = 3
    body = {k: v for k, v in report.items() if k != "content_digest"}
    report["content_digest"] = sha256_bytes(canonical(body).encode())
    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": report["verdict"], "exit": rc,
                      "checks": {c["id"]: c["status"] for c in report["checks"]},
                      "in_run_drift": sorted(drift), "content_digest": report["content_digest"]},
                     indent=1, sort_keys=True))
    return rc


if __name__ == "__main__":
    sys.exit(main())
