#!/usr/bin/env python3
"""W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01

Independent cross-adjudication of the two independently produced F1 falsifier-corpus
repair lineages at the FROZEN rev29 pins:

  lineage W031: artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tier{A,B}.jsonl
  lineage W077: artifacts/worker-077/f1_suite_rebind_dryrun/run/proposed_*.rev13.{mechanical,f0refresh}.jsonl

The corpus is class-bound evidence for AF-WCC-VAC-GEN (node F1, gate G-FORM).  Both
lineages claim to repair the L-FORM-04 record rot (25 rows bound to F1 rev12
cce9c60146d6 while the frozen F1 is rev13 d9cebb9404b2; two recorded probe passes are
false at the declared binding).  They disagree byte-for-byte; nobody has adjudicated
them against each other at one pinned state.

This instrument is read-only on every canonical path.  It emits:
  evidence.json  - full per-candidate check detail, leaf diffs, divergence table, controls
  report.json    - verdict, counts, falsifier

Probe evaluator semantics are copied verbatim from
artifacts/worker-034/f1_corpus_rebind_safety/run_rebind_safety.py (the instrument that
first measured L-FORM-04), so the two measurements are directly comparable.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-034/f1_repair_candidate_adjudication"
PINS = OUT / "pinned"
NOW = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

# ---------------------------------------------------------------------------
# Declared pins: every input is named by path + full sha256 and re-measured.
# ---------------------------------------------------------------------------
DECLARED = {
    "corpus_orig": (
        "schemas/f1_falsifier_tests.jsonl",
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    ),
    "f1_live_rev13": (
        "schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    ),
    "f1_rev12": (
        "artifacts/worker-090/f1_rev12_closure/snapshot/af_wcc_vacuum.cce9c60146d6a907.yaml",
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    ),
    "f1_authoring_rev11": (
        "artifacts/worker-048/f1_closure_preflight/snapshot/af_wcc_vacuum.9a8bd4c9.yaml",
        "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    ),
    "f0_live_rev5": (
        "research_map/formulation_taxonomy.yaml",
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    ),
    "frozen_rev29": (
        "artifacts/formulation/FROZEN.json",
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    ),
    "cand_w031_tierA": (
        "artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierA.jsonl",
        "e172020ccda52b605a06cb0d41e67d36e8854d326c3e92dda33c023339831dae",
    ),
    "cand_w031_tierB": (
        "artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierB.jsonl",
        "785e6a4e53d6437796fbe40a09ed391d54ec1c8264f3d338a93f5bd9f00c9b4a",
    ),
    "cand_w077_mechanical": (
        "artifacts/worker-077/f1_suite_rebind_dryrun/run/"
        "proposed_f1_falsifier_tests.rev13.mechanical.jsonl",
        "306480f5f45acc5012f5acae1079d95e77e343795565b195e224391dbc974ba4",
    ),
    "cand_w077_f0refresh": (
        "artifacts/worker-077/f1_suite_rebind_dryrun/run/"
        "proposed_f1_falsifier_tests.rev13.f0refresh.jsonl",
        "739d5b40dc97111dceff6df62ceaac8e22888dec6ca53981cbb308b3eb6ab1c6",
    ),
}

CANDIDATES = [
    "cand_w031_tierA",
    "cand_w031_tierB",
    "cand_w077_mechanical",
    "cand_w077_f0refresh",
]

F1_LIVE_SHA = DECLARED["f1_live_rev13"][1]
F0_LIVE_SHA = DECLARED["f0_live_rev5"][1]
DEFECT_PROBES = {
    ("F1-AMB-25", "f0_binding.declared_f0_sha256"),
    ("F1-AMB-25", "f0_binding.binding_note"),
}
# Pointers whose change is semantically forbidden: identity of the test and of every
# probe except the two known-stale expectations.
FORBIDDEN_TOP_KEYS = {
    "test_id",
    "class_id",
    "node_id",
    "gate",
    "title",
    "question",
    "why",
    "schema_finding",
    "falsifier",
    "probe_results",
    "schema_under_test",
    "schema_snapshot",
}
HISTORY_FIELDS = [
    "binding_at_authoring",
    "prior_binding_at_authoring",
    "prior_binding_ref",
    "prior_binding_sha256",
]


# ---------------------------------------------------------------------------
# helpers (evaluator copied from the L-FORM-04 instrument)
# ---------------------------------------------------------------------------
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def canon_dump(v, sort_keys: bool, ensure_ascii: bool) -> str:
    return json.dumps(v, ensure_ascii=ensure_ascii, sort_keys=sort_keys)


def resolve(doc, path: str):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


def evaluate(probe: dict, doc) -> bool:
    found, value = resolve(doc, probe["path"])
    kind = probe["kind"]
    if kind == "equals":
        return found and value == probe["expected"]
    if kind == "contains":
        return found and str(probe["expected"]) in canon(value)
    if kind == "is_true":
        return found and value is True
    if kind == "is_none":
        return found and value is None
    if kind == "path_exists":
        return found
    if kind == "nonnull":
        return found and value is not None
    raise ValueError("unknown probe kind %r in %s" % (kind, probe.get("path")))


def load_jsonl(p: Path):
    rows = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def leaf_diff(a, b, ptr: str = ""):
    """Recursive JSON-pointer leaf diff.  Returns [(ptr, before, after)]."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            sub = ptr + "/" + str(k)
            if k not in a:
                out.append((sub, "<absent>", b[k]))
            elif k not in b:
                out.append((sub, a[k], "<absent>"))
            else:
                out.extend(leaf_diff(a[k], b[k], sub))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((ptr + "/<length>", len(a), len(b)))
        for i in range(min(len(a), len(b))):
            out.extend(leaf_diff(a[i], b[i], ptr + "/" + str(i)))
    else:
        if a != b or type(a) is not type(b):
            out.append((ptr, a, b))
    return out


def scope_class(ptr: str) -> str:
    """Classify a changed JSON pointer (after stripping the leading test_id)."""
    p = ptr.lstrip("/")
    parts = p.split("/", 1)
    if len(parts) == 2 and parts[0].startswith("F1-AMB-"):
        p = parts[1]
    if p.startswith("probe_results/"):
        if p.endswith("/expected"):
            return "probe_expectation"
        if p.endswith("/observed_excerpt"):
            return "observation"
        if p.endswith("/pass"):
            return "probe_outcome"
        return "SEMANTIC_FORBIDDEN"
    if p in ("binding_ref", "binding_sha256", "binding_frozen_revision",
             "binding_frozen_revision_schema", "rebound_at", "rebind_note"):
        return "row_binding_or_provenance"
    if p in HISTORY_FIELDS:
        return "historical_provenance"
    if p.startswith("cross_artifact/"):
        return "cross_artifact_binding"
    if p.startswith("evidence_refs/"):
        return "citation"
    if p.startswith("delta_vs_"):
        return "historical_delta"
    if p.split("/")[0] in FORBIDDEN_TOP_KEYS:
        return "SEMANTIC_FORBIDDEN"
    return "other"


def excerpt_matches(recorded, resolved_value) -> bool:
    if recorded is None or resolved_value is None:
        return True
    rec = "".join(str(recorded).split()).rstrip(".…")
    variants = []
    for sk in (False, True):
        for ea in (False, True):
            variants.append("".join(canon_dump(resolved_value, sk, ea).split()))
    return any(v.startswith(rec) or rec.startswith(v) for v in variants)


def iso_parseable(s) -> bool:
    try:
        datetime.fromisoformat(str(s))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# per-candidate checks
# ---------------------------------------------------------------------------
def check_candidate(name: str, rows, orig_rows, live_doc, rev12_doc, authoring_doc):
    checks: list[dict] = []

    def chk(cid, ok, detail, falsifier=""):
        checks.append(
            {
                "check_id": cid,
                "status": "PASS" if ok else "FAIL",
                "detail": detail,
                "falsifier": falsifier
                or "re-run on the same pinned bytes yields the opposite status",
            }
        )
        return ok

    # ---- load / identity of the test set -----------------------------------
    orig_ids = [r["test_id"] for r in orig_rows]
    ids = [r["test_id"] for r in rows]
    chk("C1-LOAD-25-ROWS-ORDER",
        len(rows) == 25 and ids == orig_ids,
        "rows=%d, test_id order identical=%s" % (len(rows), ids == orig_ids),
        "a row dropped, duplicated, reordered or retitled")
    chk("C1b-CLASS-BINDING",
        all(r.get("class_id") == "AF-WCC-VAC-GEN" and r.get("node_id") == "F1" for r in rows),
        "all rows class_id=AF-WCC-VAC-GEN node_id=F1",
        "a row bound to another class or node")

    # ---- row binding to the frozen F1 revision ------------------------------
    bad_bind = [
        r["test_id"]
        for r in rows
        if r.get("binding_sha256") != F1_LIVE_SHA
        or not str(r.get("binding_ref", "")).endswith("d9cebb9404b2e79e")
    ]
    chk("C2-ROW-BINDING-REV13",
        not bad_bind,
        "rows not bound to F1 rev13 d9cebb9404b2: %s" % (bad_bind or "none"),
        "any row whose binding_sha256/binding_ref does not name the frozen F1 rev13 bytes")

    # ---- probe execution at the frozen revision -----------------------------
    exec_fail = []
    excerpt_fail = []
    total_probes = 0
    for r in rows:
        for p in r["probe_results"]:
            total_probes += 1
            if not evaluate(p, live_doc):
                exec_fail.append({"test_id": r["test_id"], "path": p["path"],
                                  "kind": p["kind"], "expected": p["expected"]})
            found, value = resolve(live_doc, p["path"])
            if p.get("observed_excerpt") is not None and found and not excerpt_matches(
                p["observed_excerpt"], value
            ):
                excerpt_fail.append({"test_id": r["test_id"], "path": p["path"],
                                     "recorded": str(p["observed_excerpt"])[:120]})
    chk("C3-PROBES-84-84-AT-REV13",
        total_probes == 84 and not exec_fail,
        "probes=%d, measured-fail=%d %s" % (total_probes, len(exec_fail),
                                            exec_fail[:4]),
        "a probe whose recorded pass value the frozen F1 rev13 bytes do not support")
    chk("C6-EXCERPT-FIDELITY-REV13",
        not excerpt_fail,
        "recorded excerpts not a truncation-tolerant match of rev13: %d %s"
        % (len(excerpt_fail), excerpt_fail[:4]),
        "a recorded observed_excerpt that does not match what rev13 resolves to")

    # ---- probe identity + expectation-change scope --------------------------
    ident_viol = []
    changed_expected = []
    for ro, rc in zip(orig_rows, rows):
        if len(ro["probe_results"]) != len(rc["probe_results"]):
            ident_viol.append({"test_id": ro["test_id"], "why": "probe count changed"})
            continue
        for po, pc in zip(ro["probe_results"], rc["probe_results"]):
            if (po["path"], po["kind"], po.get("role")) != (
                pc["path"], pc["kind"], pc.get("role")
            ):
                ident_viol.append({"test_id": ro["test_id"], "path": po["path"],
                                   "why": "path/kind/role changed"})
            if po.get("expected") != pc.get("expected"):
                changed_expected.append(
                    {"test_id": ro["test_id"], "path": po["path"],
                     "before": po.get("expected"), "after": pc.get("expected")}
                )
    chk("C4-PROBE-IDENTITY",
        not ident_viol,
        "probe path/kind/role changes: %d %s" % (len(ident_viol), ident_viol[:4]),
        "a probe whose kind, path or role was edited by the repair")
    unexpected = [
        c for c in changed_expected
        if (c["test_id"], c["path"]) not in DEFECT_PROBES
    ]
    chk("C4b-EXPECTATION-CHANGE-SCOPE",
        not unexpected,
        "%d expectation change(s), all in the two declared L-FORM-04 probes=%s"
        % (len(changed_expected), not unexpected),
        "an expectation changed outside the two stale F1-AMB-25 probes")

    # ---- truth anchors for the two repaired expectations --------------------
    live_f0 = live_doc["f0_binding"]["declared_f0_sha256"]
    authoring_note = canon(authoring_doc["f0_binding"]["binding_note"])
    live_note = canon(live_doc["f0_binding"]["binding_note"])
    row25 = next((r for r in rows if r["test_id"] == "F1-AMB-25"), None)
    p1 = next((p for p in row25["probe_results"]
               if p["path"] == "f0_binding.declared_f0_sha256"), None) if row25 else None
    p4 = next((p for p in row25["probe_results"]
               if p["path"] == "f0_binding.binding_note"), None) if row25 else None
    ok_p1 = bool(p1) and p1.get("expected") == live_f0 == F0_LIVE_SHA
    ok_p4 = (
        bool(p4)
        and isinstance(p4.get("expected"), str)
        and len(p4["expected"]) >= 20
        and p4["expected"] in live_note
        and p4["expected"] not in authoring_note
    )
    chk("C5a-P1-ANCHOR-LIVE-F0",
        ok_p1,
        "P1 expected == live F0 rev5 sha256: %s (%s)" % (ok_p1, (p1 or {}).get("expected")),
        "P1 left expecting the pre-rev5 F0 hash 276009f4 or any value != live F0")
    chk("C5b-P4-ANCHOR-REVISION-SPECIFIC",
        ok_p4,
        "P4 anchor len>=20 and present in rev13 note but absent from the authoring-rev11 "
        "note: %s (%r)" % (ok_p4, (p4 or {}).get("expected")),
        "P4 anchor too short or already present at authoring (a generic token would make "
        "the probe unable to detect the staleness it exists to detect)")

    # ---- provenance / freeze readiness (informational) ----------------------
    gap_fields = {
        "binding_frozen_revision_schema!=13": 0,
        "binding_frozen_revision<29": 0,
        "rebound_at unchanged": 0,
        "rebound_at not ISO": 0,
        "cross_artifact sha != live F0": 0,
    }
    prov_issues = []
    for r in rows:
        if r.get("binding_frozen_revision_schema") != 13:
            gap_fields["binding_frozen_revision_schema!=13"] += 1
            prov_issues.append("%s: binding_frozen_revision_schema=%r"
                               % (r["test_id"], r.get("binding_frozen_revision_schema")))
        if not isinstance(r.get("binding_frozen_revision"), int) or r["binding_frozen_revision"] < 29:
            gap_fields["binding_frozen_revision<29"] += 1
            prov_issues.append("%s: binding_frozen_revision=%r"
                               % (r["test_id"], r.get("binding_frozen_revision")))
        if r.get("rebound_at") == next(
            (o.get("rebound_at") for o in orig_rows if o["test_id"] == r["test_id"]), None
        ):
            gap_fields["rebound_at unchanged"] += 1
            prov_issues.append("%s: rebound_at unchanged" % r["test_id"])
        elif not iso_parseable(r.get("rebound_at")):
            gap_fields["rebound_at not ISO"] += 1
            prov_issues.append("%s: rebound_at not ISO-parseable" % r["test_id"])
    for r in rows:
        for ca in r.get("cross_artifact", []) or []:
            if isinstance(ca, dict) and "sha256" in ca and ca["sha256"] != F0_LIVE_SHA:
                gap_fields["cross_artifact sha != live F0"] += 1
                prov_issues.append("%s: cross_artifact sha=%s" % (r["test_id"], ca["sha256"]))
    chk("C7-PROVENANCE-COMPLETE",
        not prov_issues,
        "provenance gaps: %d %s (by field: %s)"
        % (len(prov_issues), prov_issues[:5], gap_fields),
        "a freeze-ready candidate must carry rev13/FROZEN rev29 provenance and the live F0 "
        "cross-artifact hash on every row")

    # ---- history preservation (a rebind must not rewrite the record) --------
    hist_issues = []
    for ro, rc in zip(orig_rows, rows):
        for f in HISTORY_FIELDS:
            if ro.get(f) != rc.get(f):
                hist_issues.append({"test_id": ro["test_id"], "field": f,
                                    "before": ro.get(f), "after": rc.get(f)})
    chk("C8-HISTORY-PRESERVED",
        not hist_issues,
        "historical provenance fields rewritten: %d %s"
        % (len(hist_issues), hist_issues[:4]),
        "a repair that rewrites binding_at_authoring/prior_binding_* changes what the row "
        "records about its own history; add a new field instead")

    truth_required = all(c["status"] == "PASS" for c in checks
                         if c["check_id"].startswith(("C1", "C2", "C3", "C4", "C5")))
    record_fidelity = all(c["status"] == "PASS" for c in checks
                          if c["check_id"].startswith("C6"))
    provenance = all(c["status"] == "PASS" for c in checks
                     if c["check_id"].startswith(("C7", "C8")))
    freeze_ready = truth_required and record_fidelity and provenance
    return {
        "candidate": name,
        "rows": len(rows),
        "probes": total_probes,
        "required_pass": truth_required,
        "record_fidelity_pass": record_fidelity,
        "provenance_pass": provenance,
        "freeze_ready": freeze_ready,
        "checks": checks,
        "changed_expectations": changed_expected,
        "exec_failures": exec_fail,
        "excerpt_failures": excerpt_fail,
        "provenance_gap_fields": gap_fields,
        "provenance_issues": prov_issues,
        "history_rewrites": hist_issues,
    }


def run_mutants(name, rows, orig_rows, live_doc, rev12_doc, authoring_doc):
    """Each mutant must be caught by the same check battery.  Returns controls."""
    import copy

    controls = []

    def caught(mutant_rows):
        res = check_candidate(name + "-mutant", mutant_rows, orig_rows, live_doc,
                              rev12_doc, authoring_doc)
        failed = [c["check_id"] for c in res["checks"] if c["status"] == "FAIL"]
        return failed

    m = copy.deepcopy(rows)
    m[0]["binding_sha256"] = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
    f = caught(m)
    controls.append({"mutant": "M1_row_binding_reverted_rev12",
                     "expected_failures": ["C2-ROW-BINDING-REV13"],
                     "observed_failures": f, "caught": "C2-ROW-BINDING-REV13" in f})

    m = copy.deepcopy(rows)
    m[0]["class_id"] = "AF-SCC-C0-VAC-GEN"
    f = caught(m)
    controls.append({"mutant": "M2_class_id_swapped",
                     "expected_failures": ["C1b-CLASS-BINDING"],
                     "observed_failures": f, "caught": "C1b-CLASS-BINDING" in f})

    m = copy.deepcopy(rows)
    m[0]["probe_results"][0]["kind"] = "path_exists"
    f = caught(m)
    controls.append({"mutant": "M3_probe_kind_swapped",
                     "expected_failures": ["C4-PROBE-IDENTITY"],
                     "observed_failures": f, "caught": "C4-PROBE-IDENTITY" in f})

    m = copy.deepcopy(rows)
    r25 = next(r for r in m if r["test_id"] == "F1-AMB-25")
    next(p for p in r25["probe_results"]
         if p["path"] == "f0_binding.declared_f0_sha256")["expected"] = (
        "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc")
    f = caught(m)
    controls.append({"mutant": "M4_P1_expectation_reverted",
                     "expected_failures": ["C3-PROBES-84-84-AT-REV13"],
                     "observed_failures": f, "caught": "C3-PROBES-84-84-AT-REV13" in f})

    m = copy.deepcopy(rows)
    r25 = next(r for r in m if r["test_id"] == "F1-AMB-25")
    next(p for p in r25["probe_results"]
         if p["path"] == "f0_binding.binding_note")["expected"] = "consistency"
    f = caught(m)
    controls.append({"mutant": "M5_P4_generic_anchor",
                     "expected_failures": ["C5b-P4-ANCHOR-REVISION-SPECIFIC"],
                     "observed_failures": f,
                     "caught": "C5b-P4-ANCHOR-REVISION-SPECIFIC" in f})

    m = copy.deepcopy(rows)
    del m[5]
    f = caught(m)
    controls.append({"mutant": "M6_row_dropped",
                     "expected_failures": ["C1-LOAD-25-ROWS-ORDER"],
                     "observed_failures": f, "caught": "C1-LOAD-25-ROWS-ORDER" in f})

    m = copy.deepcopy(rows)
    m[0]["probe_results"][0]["path"] = "no.such.path"
    f = caught(m)
    controls.append({"mutant": "M7_probe_path_broken",
                     "expected_failures": ["C3-PROBES-84-84-AT-REV13"],
                     "observed_failures": f, "caught": "C3-PROBES-84-84-AT-REV13" in f})

    m = copy.deepcopy(rows)
    m[0]["binding_at_authoring"] = "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2e79e"
    f = caught(m)
    controls.append({"mutant": "M8_history_field_rewritten",
                     "expected_failures": ["C8-HISTORY-PRESERVED"],
                     "observed_failures": f, "caught": "C8-HISTORY-PRESERVED" in f})

    return controls


def main() -> int:
    PINS.mkdir(parents=True, exist_ok=True)
    pins_measured = {}
    pin_checks = []
    copies = {}
    for role, (rel, want) in DECLARED.items():
        src = ROOT / rel
        got = sha256_file(src)
        dst = PINS / ("%s__%s" % (role, Path(rel).name))
        shutil.copyfile(src, dst)
        got_copy = sha256_file(dst)
        ok = got == want == got_copy
        pin_checks.append(
            {"pin": role, "path": rel, "declared": want, "measured": got,
             "copy": got_copy, "match": ok}
        )
        pins_measured[role] = got
        copies[role] = dst
    pins_ok = all(p["match"] for p in pin_checks)

    if not pins_ok:
        print("PIN MISMATCH — aborting", file=sys.stderr)
        for p in pin_checks:
            if not p["match"]:
                print("  ", p, file=sys.stderr)
        return 2

    orig_rows = load_jsonl(copies["corpus_orig"])
    live_doc = yaml.safe_load(copies["f1_live_rev13"].read_text())
    rev12_doc = yaml.safe_load(copies["f1_rev12"].read_text())
    authoring_doc = yaml.safe_load(copies["f1_authoring_rev11"].read_text())

    results = {}
    for name in CANDIDATES:
        rows = load_jsonl(copies[name])
        res = check_candidate(name, rows, orig_rows, live_doc, rev12_doc, authoring_doc)
        res["sha256"] = pins_measured[name]
        res["bytes"] = (ROOT / DECLARED[name][0]).stat().st_size
        res["controls"] = run_mutants(name, rows, orig_rows, live_doc, rev12_doc,
                                      authoring_doc)
        res["controls_all_caught"] = all(c["caught"] for c in res["controls"])
        # leaf diff vs canonical corpus
        diffs = []
        for ro, rc in zip(orig_rows, rows):
            for ptr, before, after in leaf_diff(ro, rc, "/" + ro["test_id"]):
                diffs.append({"pointer": ptr, "before": before, "after": after,
                              "scope": scope_class(ptr)})
        res["changed_pointer_count"] = len(diffs)
        res["changed_pointers_by_scope"] = {}
        for d in diffs:
            res["changed_pointers_by_scope"].setdefault(d["scope"], 0)
            res["changed_pointers_by_scope"][d["scope"]] += 1
        res["semantic_forbidden_changes"] = [
            d for d in diffs if d["scope"] == "SEMANTIC_FORBIDDEN"
        ]
        res["diff"] = diffs
        results[name] = res

    # ---- divergence table across lineages -----------------------------------
    loaded = {n: load_jsonl(copies[n]) for n in CANDIDATES}
    divergence = []
    for i in range(len(CANDIDATES)):
        for j in range(i + 1, len(CANDIDATES)):
            a, b = CANDIDATES[i], CANDIDATES[j]
            for ra, rb in zip(loaded[a], loaded[b]):
                for ptr, va, vb in leaf_diff(ra, rb, "/" + ra["test_id"]):
                    divergence.append({"pair": [a, b], "pointer": ptr,
                                       "value_a": va, "value_b": vb,
                                       "scope": scope_class(ptr)})
    pairwise_counts = {}
    for d in divergence:
        pairwise_counts.setdefault("%s__vs__%s" % tuple(d["pair"]), 0)
        pairwise_counts["%s__vs__%s" % tuple(d["pair"])] += 1
    # per-pointer after-value table: only pointers where the four candidates do not agree
    ptr_table = {}
    for ptr_key in {d["pointer"] for d in divergence}:
        cells = {}
        for n in CANDIDATES:
            cells[n] = "<absent>"
        # walk each candidate independently to get its value at this pointer
        for n in CANDIDATES:
            # direct lookup of this pointer in candidate n
            top = ptr_key.lstrip("/").split("/")
            tid = top[0]
            row = next((r for r in loaded[n] if r["test_id"] == tid), None)
            if row is None:
                cells[n] = "<no-row>"
                continue
            cur = row
            ok = True
            for part in top[1:]:
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                    cur = cur[int(part)]
                else:
                    ok = False
                    break
            cells[n] = canon(cur) if ok else "<absent>"
        if len(set(cells.values())) > 1:
            ptr_table[ptr_key] = {
                "scope": scope_class(ptr_key),
                "values": cells,
            }

    # ---- derived owner write set -------------------------------------------
    # base = truthful + record-fidelity-passing + history-preserving, if one exists;
    # else truthful + history-preserving (excerpts must then be refreshed by the owner).
    base = [n for n in CANDIDATES if results[n]["required_pass"]
            and results[n]["record_fidelity_pass"]
            and not results[n]["history_rewrites"]]
    if not base:
        base = [n for n in CANDIDATES if results[n]["required_pass"]
                and not results[n]["history_rewrites"]]
        # prefer the truthful history-preserving base with the least residual owner work
        base.sort(key=lambda n: (
            len(results[n]["excerpt_failures"])
            + sum(results[n]["provenance_gap_fields"].values())
        ))
    recommended_base = base[0] if base else None
    owner_write_set = None
    if recommended_base:
        # the best excerpt source among candidates that pass C6
        excerpt_src = next((n for n in CANDIDATES if results[n]["record_fidelity_pass"]),
                           recommended_base)
        src_rows = {r["test_id"]: r for r in loaded[excerpt_src]}
        residual_excerpts = []
        for f in results[recommended_base]["excerpt_failures"]:
            src = src_rows.get(f["test_id"], {})
            src_probe = next((p for p in src.get("probe_results", [])
                              if p["path"] == f["path"]), None)
            residual_excerpts.append({
                "test_id": f["test_id"],
                "path": f["path"],
                "stale_excerpt": f["recorded"],
                "refresh_from": excerpt_src,
                "fresh_excerpt": (src_probe or {}).get("observed_excerpt"),
            })
        owner_write_set = {
            "recommended_base": recommended_base,
            "recommended_base_sha256": pins_measured[recommended_base],
            "excerpt_source_for_residual_refresh": excerpt_src,
            "residual_excerpt_refreshes": residual_excerpts,
            "provenance_fields_owner_must_set": results[recommended_base]["provenance_gap_fields"],
            "history_rewrites_in_base": len(results[recommended_base]["history_rewrites"]),
            "policy_divergence": {
                "w077_lineage_rewrites_history": True,
                "w077_history_rewrite_instances": len(results["cand_w077_f0refresh"]["history_rewrites"]),
                "w031_lineage_rewrites_history": False,
                "note": "w077 rewrites binding_at_authoring/prior_binding_* to the new bindings "
                        "on all 25 rows; w031 preserves the original record. The owner must "
                        "choose a policy; preserving history and adding a new field is the "
                        "audit-safe option.",
            },
        }

    # ---- verdict ------------------------------------------------------------
    required_ok = [n for n in CANDIDATES if results[n]["required_pass"]]
    freeze_ok = [n for n in CANDIDATES if results[n]["freeze_ready"]]
    record_ok = [n for n in CANDIDATES if results[n]["record_fidelity_pass"]]
    semantic_bad = [n for n in CANDIDATES if results[n]["semantic_forbidden_changes"]]
    exec_bad = [n for n in CANDIDATES if results[n]["exec_failures"]]
    controls_bad = [n for n in CANDIDATES if not results[n]["controls_all_caught"]]
    distinct_freeze_hashes = sorted({pins_measured[n] for n in freeze_ok})

    if not pins_ok:
        verdict = "INVALID_PIN_DRIFT"
    elif controls_bad:
        verdict = "INVALID_CONTROLS"
    elif semantic_bad:
        verdict = "REJECT_SEMANTIC_EDIT"
    elif not required_ok:
        verdict = "NO_TRUTHFUL_CANDIDATE"
    elif len(distinct_freeze_hashes) > 1:
        verdict = "MULTIPLE_FREEZE_READY_DIVERGENT"
    elif len(distinct_freeze_hashes) == 1:
        verdict = "ONE_FREEZE_READY"
    else:
        verdict = "TRUTHFUL_NOT_FREEZE_READY"

    report = {
        "report_id": "W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01",
        "actor": "worker-034",
        "created_at": NOW,
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "task": "independent cross-adjudication of the W031 and W077 F1 falsifier-corpus "
                "repair candidates at FROZEN rev29 pins",
        "authority": "worker measurement only; read-only on every canonical path; no gate "
                     "verdict; no node status promotion; no canonical corpus write",
        "verdict": verdict,
        "required_pass": required_ok,
        "freeze_ready": freeze_ok,
        "freeze_ready_distinct_hashes": distinct_freeze_hashes,
        "semantic_forbidden_candidates": semantic_bad,
        "exec_failing_candidates": exec_bad,
        "controls_failing_candidates": controls_bad,
        "pins_ok": pins_ok,
        "counts": {
            n: {
                "sha256": pins_measured[n],
                "bytes": results[n]["bytes"],
                "changed_pointers": results[n]["changed_pointer_count"],
                "changed_by_scope": results[n]["changed_pointers_by_scope"],
                "required_pass": results[n]["required_pass"],
                "record_fidelity_pass": results[n]["record_fidelity_pass"],
                "provenance_pass": results[n]["provenance_pass"],
                "freeze_ready": results[n]["freeze_ready"],
                "controls_all_caught": results[n]["controls_all_caught"],
                "provenance_gap_fields": results[n]["provenance_gap_fields"],
                "history_rewrites": len(results[n]["history_rewrites"]),
            }
            for n in CANDIDATES
        },
        "record_fidelity_pass": record_ok,
        "owner_write_set": owner_write_set,
        "pairwise_divergent_pointers": pairwise_counts,
        "divergent_pointer_count": len(ptr_table),
        "falsifier": "any pinned input hash moving, any candidate re-measured to a different "
                     "sha256, a probe whose rev13 evaluation disagrees with this run, or a "
                     "candidate accepted here that a re-run shows failing C2/C3/C4/C5",
        "next_falsifier": "the owner's applied corpus: re-run this battery on the bytes that "
                          "actually land in schemas/f1_falsifier_tests.jsonl and on FROZEN "
                          "rev30's per-file pin; the applied bytes must equal one adjudicated "
                          "candidate hash",
    }

    evidence = {
        "evidence_id": "W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01-evidence",
        "created_at": NOW,
        "pins": pin_checks,
        "evaluator": {
            "source": "artifacts/worker-034/f1_corpus_rebind_safety/run_rebind_safety.py"
                      "#sha256:ff84cb04f4b2",
            "kinds": ["contains", "equals", "is_true", "is_none", "path_exists", "nonnull"],
            "note": "semantics copied verbatim so this run is comparable to the L-FORM-04 "
                    "measurement",
        },
        "candidates": results,
        "divergence": divergence,
        "pairwise_divergent_pointers": pairwise_counts,
        "divergent_pointer_table": ptr_table,
        "defect_probes": sorted(DEFECT_PROBES),
    }

    (OUT / "report.json").write_text(json.dumps(report, indent=1, default=str) + "\n")
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=1, default=str) + "\n")

    # human-readable summary
    lines = [
        "# W034 — F1 repair-candidate adjudication (AF-WCC-VAC-GEN / F1 / G-FORM)",
        "",
        "Task: cross-adjudicate the two independently produced F1 falsifier-corpus repair",
        "lineages at the FROZEN rev29 pins. Read-only on all canonical paths.",
        "",
        "Pins: corpus 56bcb4b3234bc86c; F1 rev13 d9cebb9404b2e79e; F1 rev12 cce9c60146d6a907;",
        "F0 rev5 0abb9ed8a96135c9; FROZEN rev29 815e08079aefbc16. All pins re-measured: %s." % pins_ok,
        "",
        "## Verdict: `%s`" % verdict,
        "",
        "| candidate | sha256 | changed ptrs | required | freeze-ready | controls |",
        "|---|---|---|---|---|---|",
    ]
    for n in CANDIDATES:
        r = results[n]
        lines.append("| %s | `%s` | %d | %s | %s | %s |" % (
            n, pins_measured[n][:16], r["changed_pointer_count"],
            "PASS" if r["required_pass"] else "FAIL",
            "yes" if r["freeze_ready"] else "no",
            "all caught" if r["controls_all_caught"] else "FAIL"))
    lines += [
        "",
        "Changed-pointer scope per candidate:",
        "",
    ]
    for n in CANDIDATES:
        lines.append("- **%s**: %s" % (n, results[n]["changed_pointers_by_scope"]))
    lines += [
        "",
        "Per-candidate required-check status:",
        "",
    ]
    for n in CANDIDATES:
        lines.append("- **%s**" % n)
        for c in results[n]["checks"]:
            lines.append("  - %s: %s — %s" % (c["check_id"], c["status"], c["detail"]))
    if owner_write_set:
        lines += [
            "",
            "## Derived owner write set (no canonical write performed here)",
            "",
            "- recommended base: **%s** (`%s`)" % (
                owner_write_set["recommended_base"],
                owner_write_set["recommended_base_sha256"][:16]),
            "- residual excerpt refreshes from **%s**: %s" % (
                owner_write_set["excerpt_source_for_residual_refresh"],
                [(e["test_id"], e["path"])
                 for e in owner_write_set["residual_excerpt_refreshes"]] or "none"),
            "- provenance fields the owner must still set: `%s`"
            % owner_write_set["provenance_fields_owner_must_set"],
            "",
            "Policy divergence between the lineages: %s"
            % owner_write_set["policy_divergence"]["note"],
            "",
            "Pairwise divergent JSON pointers between candidate lineages: `%s`."
            % report["pairwise_divergent_pointers"],
            "",
            "Machine-readable detail is in `evidence.json` "
            "(`divergent_pointer_table`, per-candidate `checks`, `controls`).",
        ]
    lines += [
        "",
        "## Falsifier",
        "",
        report["falsifier"],
        "",
        "## Next falsifier",
        "",
        report["next_falsifier"],
        "",
        "## Scope note",
        "",
        "This adjudicates only truthfulness, probe-identity, anchor specificity,",
        "excerpt fidelity and provenance of the staged candidates. It does not choose a",
        "canonical writer and does not apply any patch. If the verdict is",
        "`MULTIPLE_FREEZE_READY_DIVERGENT`, the owner must pick exactly one candidate byte",
        "set before re-freezing; see `evidence.json:divergent_pointer_table`.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n")

    print(json.dumps({
        "verdict": verdict,
        "pins_ok": pins_ok,
        "required_pass": required_ok,
        "record_fidelity_pass": record_ok,
        "freeze_ready": freeze_ok,
        "freeze_ready_hashes": distinct_freeze_hashes,
        "divergent_pointers": len(ptr_table),
        "pairwise_divergent_pointers": pairwise_counts,
        "controls": {n: results[n]["controls_all_caught"] for n in CANDIDATES},
        "exec_failures": {n: len(results[n]["exec_failures"]) for n in CANDIDATES},
        "excerpt_failures": {n: len(results[n]["excerpt_failures"]) for n in CANDIDATES},
        "provenance_gaps": {n: results[n]["provenance_gap_fields"] for n in CANDIDATES},
        "history_rewrites": {n: len(results[n]["history_rewrites"]) for n in CANDIDATES},
        "owner_write_set": (
            {
                "base": owner_write_set["recommended_base"],
                "residual_excerpt_refreshes": [
                    [e["test_id"], e["path"]]
                    for e in owner_write_set["residual_excerpt_refreshes"]],
                "provenance_gaps": owner_write_set["provenance_fields_owner_must_set"],
            } if owner_write_set else None
        ),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
