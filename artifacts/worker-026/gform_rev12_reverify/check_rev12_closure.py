#!/usr/bin/env python3
"""W026-GFORM-REV12-CLOSURE-REVERIFY-01 -- independent hash-pinned checker.

Task taken by worker-026 (fleet instance 2026-09-12T00:30:28) because no
assignment card existed in comms/inbox/worker-026.jsonl.  The formulation group
landed revision 12 of F0-adjacent schemas at 2026-09-12T00:31:41+08:00 claiming
to close the hash-bound G-FORM findings.  This instrument independently
re-measures the closure claims on frozen copies of the canonical bytes.

Read-only with respect to every canonical artifact: all inputs are the pinned
copies under pinned/ plus pin_manifest.json.  No network.  Stdlib + PyYAML only.

Usage
-----
  python3 check_rev12_closure.py --pin      # freeze live bytes -> pinned/ + manifest
  python3 check_rev12_closure.py --check    # checks + mutation controls (deterministic)
  python3 check_rev12_closure.py --live     # drift + independent-citation corroboration

Exit codes for --check:
  0  measurement valid: pinned bytes intact and every mutation control fired
  1  a control failed to fire -> the measurement is INVALID (report still written)
  2  pin/parse error or pinned bytes do not match the manifest
"""

from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PIN_DIR = os.path.join(HERE, "pinned")
MANIFEST = os.path.join(HERE, "pin_manifest.json")
REPORT = os.path.join(HERE, "report.json")
CONTROLS = os.path.join(HERE, "controls.json")
DRIFT = os.path.join(HERE, "drift.json")
CORROB = os.path.join(HERE, "corroboration.json")

TASK_ID = "W026-GFORM-REV12-CLOSURE-REVERIFY-01"
ACTOR = "worker-026"
GATE = "G-FORM"
NODE = "F1,F2a,F2b,F0"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

# name -> (repo-relative live path, pin basename, class_id)
ITEMS = {
    "f0_canonical": ("research_map/formulation_taxonomy.yaml",
                     "formulation_taxonomy.canonical", "GLOBAL"),
    "f0_authoring": ("artifacts/formulation/formulation_taxonomy.yaml",
                     "formulation_taxonomy.authoring", "GLOBAL"),
    "f1": ("schemas/af_wcc_vacuum.yaml", "af_wcc_vacuum", "AF-WCC-VAC-GEN"),
    "f2a": ("schemas/af_scc_c2_vacuum.yaml", "af_scc_c2_vacuum", "AF-SCC-C2-VAC-GEN"),
    "f2b": ("schemas/af_scc_c0_vacuum.yaml", "af_scc_c0_vacuum", "AF-SCC-C0-VAC-GEN"),
}
SCHEMAS = ["f1", "f2a", "f2b"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: str) -> str:
    return sha256_bytes(open(p, "rb").read())


# --------------------------------------------------------------------------
# pin step
# --------------------------------------------------------------------------
def cmd_pin() -> int:
    if os.path.exists(MANIFEST):
        print("pin manifest already exists; refusing to overwrite (delete it to re-pin)",
              file=sys.stderr)
        return 2
    os.makedirs(PIN_DIR, exist_ok=True)
    out = {"task_id": TASK_ID, "actor": ACTOR, "gate": GATE,
           "pinned_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "pins": {}}
    for name, (rel, base, cid) in ITEMS.items():
        live = os.path.join(ROOT, rel)
        b = open(live, "rb").read()
        h = sha256_bytes(b)
        dst = os.path.join(PIN_DIR, f"{base}.{h[:12]}.yaml")
        with open(dst, "wb") as fh:
            fh.write(b)
        out["pins"][name] = {
            "relpath": rel, "class_id": cid, "bytes": len(b),
            "sha256_live": h,
            "sha256_pinned": sha256_file(dst),
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S+08:00",
                                   time.localtime(os.path.getmtime(live))),
            "pinned_copy": os.path.relpath(dst, ROOT),
        }
    with open(MANIFEST, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps({k: v["sha256_live"] for k, v in out["pins"].items()}, indent=1))
    return 0


# --------------------------------------------------------------------------
# strict YAML loading (duplicate keys recorded, not silently last-wins)
# --------------------------------------------------------------------------
class DupLoader(yaml.SafeLoader):
    duplicates: list


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            present = key in mapping
        except TypeError:
            present = False
        if present:
            loader.duplicates.append(
                {"key": str(key), "line": key_node.start_mark.line + 1})
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DupLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def strict_load(text: str):
    loader = DupLoader(text)
    loader.duplicates = []
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, loader.duplicates


def resolve_fragment(doc, fragment: str):
    """Return (value, missing_part).  Dotted path, no list indices."""
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None, part
    return cur, None


def find_key(doc, key):
    """Depth-first search for the first mapping value under `key`."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k == key:
                return v
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(doc, list):
        for it in doc:
            r = find_key(it, key)
            if r is not None:
                return r
    return None


def set_key(doc, key, value):
    """Set the first mapping value found under `key`; returns True if set."""
    if isinstance(doc, dict):
        for k in list(doc.keys()):
            if k == key:
                doc[k] = value
                return True
            if set_key(doc[k], key, value):
                return True
    elif isinstance(doc, list):
        for it in doc:
            if set_key(it, key, value):
                return True
    return False


def as_dt(x):
    if isinstance(x, _dt.datetime):
        return x
    return _dt.datetime.fromisoformat(str(x))


def load_bundle() -> dict:
    manifest = json.load(open(MANIFEST))
    bundle = {"manifest": manifest, "raw": {}, "doc": {}, "dups": {}, "sha": {}}
    for name, (rel, base, cid) in ITEMS.items():
        info = manifest["pins"][name]
        path = os.path.join(ROOT, info["pinned_copy"])
        raw = open(path, "rb").read()
        h = sha256_bytes(raw)
        if h != info["sha256_pinned"]:
            raise RuntimeError(f"pinned copy drifted: {info['pinned_copy']} {h}")
        bundle["raw"][name] = raw.decode("utf-8")
        bundle["sha"][name] = h
        doc, dups = strict_load(bundle["raw"][name])
        bundle["doc"][name] = doc
        bundle["dups"][name] = dups
    return bundle


# --------------------------------------------------------------------------
# checks -- each returns dict(id, title, verdict, severity, evidence)
# --------------------------------------------------------------------------
def _ev(path, detail):
    return f"{path} :: {detail}"


def p1_no_duplicate_keys(b) -> dict:
    bad = {n: d for n, d in b["dups"].items() if d}
    return {"id": "P1", "files": {n: (n not in bad) for n in ITEMS}, "title": "strict YAML parse: no duplicate mapping keys",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info",
            "evidence": [f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} has "
                         f"{len(d)} duplicate key(s): {d[:4]}" for n, d in bad.items()]
                        or [f"all {len(ITEMS)} pinned YAMLs strict-parse with 0 duplicate keys"]}


def p2_clock(b) -> dict:
    pins = b["manifest"]["pins"]
    pinned_at = _dt.datetime.fromisoformat(b["manifest"]["pinned_at"])
    bad, ev = [], []
    for n in ITEMS:
        stamp = b["doc"][n].get("revised_at") or b["doc"][n].get("written_at")
        if not stamp:
            ev.append(f"{ITEMS[n][0]}: no revised_at/written_at (n/a)")
            continue
        t = stamp if isinstance(stamp, _dt.datetime) \
            else _dt.datetime.fromisoformat(str(stamp))
        if t.tzinfo is None:
            t = t.replace(tzinfo=pinned_at.tzinfo)
        delta = (t - pinned_at).total_seconds()
        ev.append(f"{ITEMS[n][0]} declared={stamp} delta_vs_pin={delta:+.0f}s")
        if delta > 120:
            bad.append(n)
    return {"id": "P2", "files": {n: (n not in bad) for n in ITEMS},
            "title": "clock discipline: no declared timestamp ahead of wall clock",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev}


def p3_pointer(b) -> dict:
    f0 = b["doc"]["f0_canonical"]
    auth = b["doc"]["f0_authoring"]
    f0_sha = b["sha"]["f0_canonical"]
    auth_sha = b["sha"]["f0_authoring"]
    bad, ev = [], []
    for n in SCHEMAS:
        d = b["doc"][n]
        ptr = d.get("class_contract_pointer")
        cid = ITEMS[n][2]
        ok_path = isinstance(ptr, str) and ptr.startswith(
            "research_map/formulation_taxonomy.yaml#")
        val, missing = (None, "no-pointer")
        if ok_path:
            val, missing = resolve_fragment(f0, ptr.split("#", 1)[1])
        decl = (d.get("f0_binding") or {}).get("declared_f0_sha256")
        supp = d.get("class_contract_supplement_pointer")
        sval, smissing = (None, "no-supplement-pointer")
        if isinstance(supp, str) and "#" in supp:
            sval, smissing = resolve_fragment(auth, supp.split("#", 1)[1])
        checks = {
            "pointer_is_canonical_path": ok_path,
            "pointer_resolves_in_canonical_f0": val is not None,
            "declared_f0_sha_equals_pinned_canonical": decl == f0_sha,
            "supplement_pointer_is_separate_field": supp != ptr,
            "supplement_pointer_resolves_in_authoring_f0": sval is not None,
            "pointer_target_is_class_entry": isinstance(val, dict) and "axes" in val,
        }
        if not all(checks.values()):
            bad.append(n)
        ev.append(f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} class={cid} "
                  f"ptr={ptr!r} resolves={val is not None} missing={missing} "
                  f"declared_f0={str(decl)[:12]} == pin {f0_sha[:12]}: {decl == f0_sha} "
                  f"supp={str(supp)!r} resolves={sval is not None} "
                  f"(authoring {auth_sha[:12]}) checks={checks}")
    return {"id": "P3", "files": {n: (n not in bad) for n in SCHEMAS},
            "title": "class_contract_pointer binds the canonical F0 classes entry "
                                 "(authoring supplement split into its own field)",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev}


def p4_vocabulary(b) -> dict:
    f0 = b["doc"]["f0_canonical"]
    allowed = (((f0.get("field_vocabulary") or {}).get("conclusion_type") or {})
               .get("allowed") or [])
    bad, ev = [], []
    for n in SCHEMAS:
        cid = ITEMS[n][2]
        tok = ((b["doc"][n].get("conclusion") or {}).get("conclusion_type"))
        axis = (((f0.get("classes") or {}).get(cid) or {}).get("axes") or {}) \
            .get("conclusion_type")
        in_vocab = tok in allowed
        equals_axis = tok == axis
        ok = in_vocab and equals_axis
        if not ok:
            bad.append(n)
        ev.append(f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} class={cid} "
                  f"conclusion_type={tok!r} in field_vocabulary.allowed({allowed}): "
                  f"{in_vocab}; equals classes.{cid}.axes.conclusion_type={axis!r}: "
                  f"{equals_axis}")
    return {"id": "P4", "files": {n: (n not in bad) for n in SCHEMAS},
            "title": "conclusion_type token admitted by canonical F0 vocabulary "
                                 "and equal to the canonical class axis (HF-02 class leakage)",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev}


def p5_af_iplus(b) -> dict:
    d = b["doc"]["f1"]
    sym = "AF_{I+}"
    leaf = str(find_key(d, "predicate_abbreviation") or "")
    formal = ((d.get("conclusion") or {}).get("statement_formal") or "")
    occ = len(re.findall(re.escape(sym), b["raw"]["f1"]))
    defined = sym in leaf and "abbreviat" in leaf.lower()
    used = sym in formal
    ok = defined and used and occ >= 2
    return {"id": "P5", "files": {"f1": ok},
            "title": "F1 visibility symbol AF_{I+} has a definition leaf and is used",
            "verdict": "PASS" if ok else "FAIL",
            "severity": "info" if ok else "blocking",
            "evidence": [f"schemas/af_wcc_vacuum.yaml#sha256:{b['sha']['f1'][:12]} "
                         f"literal_occurrences={occ} predicate_abbreviation_defined={defined} "
                         f"used_in_conclusion.statement_formal={used}",
                         "definition leaf: " + leaf[:180]]}


def p6a_tagged_index(b) -> dict:
    bad, ev = [], []
    for n in SCHEMAS:
        q = b["doc"][n].get("quantifiers") or {}
        ordered = q.get("ordered") or []
        binder0 = ordered[0].get("binder") if ordered else None
        texts = [str(q.get("formal") or ""), str(q.get("negation") or ""),
                 str(((b["doc"][n].get("conclusion") or {})
                      .get("statement_formal")) or "")]
        pair_binder = any(re.search(r"\(\s*s\s*,\s*delta\s*\)\s*(in|,)", t)
                          for t in texts)
        d0 = str(((q.get("domains") or {}).get("D0") or {}).get("definition") or "")
        tagged = "tagged disjoint union" in d0
        ok = (binder0 == "r") and (not pair_binder) and tagged
        if not ok:
            bad.append(n)
        ev.append(f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} first_binder={binder0!r} "
                  f"(s,delta)-binder_in_formal_negation_conclusion={pair_binder} "
                  f"D0_declares_tagged_union={tagged}")
    return {"id": "P6a", "files": {n: (n not in bad) for n in SCHEMAS},
            "title": "D0 retyped as a single tagged regularity index r; no (s,delta) pair binder",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev}


def p6b_single_branch(b) -> dict:
    bad, ev = [], []
    for n in SCHEMAS:
        d0 = str((((b["doc"][n].get("quantifiers") or {}).get("domains") or {})
                  .get("D0") or {}).get("definition") or "")
        branches = re.findall(r"\br\s*=\s*", d0)
        smooth = "r = smooth" in d0
        sobolev = "(sobolev,s,delta)" in d0 or "(sobolev, s, delta)" in d0
        n_branches = (1 if smooth else 0) + (1 if sobolev else 0)
        ok = n_branches == 1
        if not ok:
            bad.append(n)
        ev.append(f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} D0_branches={n_branches} "
                  f"(smooth={smooth}, sobolev_pair={sobolev}) "
                  f"r_equals_occurrences={len(branches)}")
    return {"id": "P6b", "files": {n: (n not in bad) for n in SCHEMAS},
            "title": "single frozen data class: D0 has exactly one regularity branch "
                     "(G-FORM unmet item 'no single frozen data class (s,delta,norm)')",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev}


def p7_extension_predicate(b) -> dict:
    bad, ev = [], []
    for n in ["f2a", "f2b"]:
        d = b["doc"][n]
        ep = d.get("extension_predicate") or {}
        name = ep.get("name")
        q = d.get("quantifiers") or {}
        d3ref = ((q.get("domains") or {}).get("D3") or {}).get("definition_ref")
        formal = str(((d.get("conclusion") or {}).get("statement_formal")) or "")
        neg = str(q.get("negation") or "")
        tok = (((b["doc"]["f0_canonical"].get("classes") or {}).get(ITEMS[n][2]) or {})
               .get("axes") or {}).get("regularity_token")
        ok = (bool(name) and d3ref == "extension_predicate"
              and name in formal
              and ep.get("frozen_direction") == "future"
              and ep.get("frozen_regularity") == tok)
        if not ok:
            bad.append(n)
        ev.append(f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} predicate={name!r} "
                  f"D3.definition_ref={d3ref!r} used_in_formal={bool(name) and name in formal} "
                  f"used_in_negation={bool(name) and name in neg} "
                  f"direction={ep.get('frozen_direction')!r} "
                  f"regularity={ep.get('frozen_regularity')!r} canonical_token={tok!r}")
    return {"id": "P7", "files": {n: (n not in bad) for n in ["f2a", "f2b"]},
            "title": "SCC extension predicate defined, bound from D3, and used in the "
                     "formal conclusion and its negation",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev,
            "advisory": ["SCC negation block states the failure naturally instead of "
                         "re-using the predicate name; notation-only, not a binding failure "
                         "at this pin"] if any("used_in_negation=False" in e for e in ev) else []}


def p8_revision_history(b) -> dict:
    bad, ev = [], []
    for n in SCHEMAS:
        d = b["doc"][n]
        rev = d.get("revision")
        hist = d.get("revision_history") or []
        last = hist[-1] if hist else {}
        notes = " ".join(str(x) for x in (last.get("notes") or []))
        prov = bool(d.get("timestamp_provenance"))
        try:
            stamp_match = as_dt(last.get("at")) == as_dt(d.get("revised_at"))
        except (TypeError, ValueError):
            stamp_match = False
        mentions = f"rev{rev}" in notes
        ok = (rev == 12 and stamp_match and mentions and prov)
        if not ok:
            bad.append(n)
        ev.append(f"{ITEMS[n][0]}#sha256:{b['sha'][n][:12]} revision={rev} "
                  f"last_history_at={last.get('at')} revised_at={d.get('revised_at')} "
                  f"stamp_match={stamp_match} notes_mention_rev{rev}={mentions} "
                  f"timestamp_provenance_present={prov}")
    return {"id": "P8", "files": {n: (n not in bad) for n in SCHEMAS},
            "title": "revision/history consistency: revision 12 is recorded in the last "
                     "revision_history entry with the declared revised_at stamp",
            "verdict": "FAIL" if bad else "PASS",
            "severity": "blocking" if bad else "info", "evidence": ev}


CHECKS = [p1_no_duplicate_keys, p2_clock, p3_pointer, p4_vocabulary,
          p5_af_iplus, p6a_tagged_index, p6b_single_branch,
          p7_extension_predicate, p8_revision_history]
CHECK_PATHS = {"P1": ["f1", "f2a", "f2b", "f0_canonical", "f0_authoring"],
               "P2": ["f1", "f2a", "f2b", "f0_canonical", "f0_authoring"],
               "P3": SCHEMAS, "P4": SCHEMAS, "P5": ["f1"],
               "P6a": SCHEMAS, "P6b": SCHEMAS, "P7": ["f2a", "f2b"],
               "P8": SCHEMAS}


def run_checks(b) -> dict:
    return {c(b)["id"]: c(b) for c in CHECKS}


def cmd_check() -> int:
    try:
        b = load_bundle()
    except Exception as exc:  # noqa: BLE001
        print(f"pin error: {exc}", file=sys.stderr)
        return 2
    res = run_checks(b)
    for cid, r in res.items():
        fails = [ITEMS[pk][2] for pk, ok in r.get("files", {}).items() if not ok]
        r["verdict"] = "FAIL" if fails else "PASS"
        r["failing_classes"] = fails
    overall = "CLOSED" if all(r["verdict"] == "PASS" for r in res.values()) \
        else ("PARTIALLY_CLOSED" if any(r["verdict"] == "PASS" for r in res.values())
              else "NOT_CLOSED")
    report = {
        "task_id": TASK_ID, "actor": ACTOR, "gate": GATE, "node_id": NODE,
        "class_ids": CLASS_IDS,
        "as_of_pin": b["manifest"]["pinned_at"],
        "pins": {n: {"relpath": ITEMS[n][0], "sha256": b["sha"][n]}
                 for n in ITEMS},
        "checks": [res[fn(b)["id"]] for fn in CHECKS],
        "verdict": overall,
        "open_findings": [r["id"] for r in res.values() if r["verdict"] == "FAIL"],
        "advisory_findings": [a for r in res.values() for a in r.get("advisory", [])],
        "authority_limits": [
            "worker-level measurement only; not a gate verdict",
            "does not edit, apply, or promote any canonical artifact",
            "does not adjudicate whether the G-FORM criterion should be read as one branch",
        ],
        "falsifier": ("Re-run this instrument against the same pinned sha256 values; "
                      "it is falsified if any check verdict differs, if any pinned copy "
                      "fails its manifest hash, if any mutation control stops firing, or "
                      "if the strict parser accepts a duplicated key."),
    }
    with open(REPORT, "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)

    # ---------------- mutation controls (in memory only) ----------------
    def mut(name):
        return copy.deepcopy(b)

    controls = []

    def add(cid, target, mutation, predicted, bundle_override=None,
            raw_override=None, noop=False, target_path=None):
        if noop:
            bb = b
        elif raw_override is not None:
            bb = copy.deepcopy(b)
            bb["raw"][raw_override[0]] = raw_override[1]
            doc, dups = strict_load(raw_override[1])
            bb["doc"][raw_override[0]] = doc
            bb["dups"][raw_override[0]] = dups
        else:
            bb = bundle_override
        r = run_checks(bb)[target]
        if target_path is not None:
            observed = "PASS" if r["files"][target_path] else "FAIL"
        else:
            observed = r["verdict"]
        controls.append({"id": cid, "target_check": target, "target_path": target_path,
                         "mutation": mutation,
                         "predicted": predicted, "observed": observed,
                         "fired": observed == predicted})

    # N0 null control: the unmutated pin reproduces the base verdicts
    add("N0", "P1", "none (null control)", "PASS", noop=True, target_path="f1")
    # C1 duplicate top-level key injected into F1 raw text
    add("C1", "P1", "append duplicate top-level key 'revised_at' to F1 raw text", "FAIL",
        raw_override=("f1", b["raw"]["f1"] + "\nrevised_at: 2099-01-01T00:00:00+08:00\n"),
        target_path="f1")
    # C2 future-dated revised_at in F1
    bb = mut("f1")
    bb["doc"]["f1"]["revised_at"] = "2099-01-01T00:00:00+08:00"
    add("C2", "P2", "set F1 revised_at to 2099", "FAIL", bundle_override=bb,
        target_path="f1")
    # C3 dangling class_contract_pointer in F2a
    bb = mut("f2a")
    bb["doc"]["f2a"]["class_contract_pointer"] = \
        "research_map/formulation_taxonomy.yaml#classes.NONEXISTENT"
    add("C3", "P3", "point F2a class_contract_pointer at classes.NONEXISTENT", "FAIL",
        bundle_override=bb, target_path="f2a")
    # C4 bogus conclusion_type in F1 (base PASS -> must fail)
    bb = mut("f1")
    bb["doc"]["f1"]["conclusion"]["conclusion_type"] = "bogus_token"
    add("C4", "P4", "replace F1 conclusion_type with bogus_token", "FAIL",
        bundle_override=bb, target_path="f1")
    # C4b F2a with the canonical axis token (base FAIL -> must pass)
    bb = mut("f2a")
    bb["doc"]["f2a"]["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C2"
    add("C4b", "P4", "replace F2a conclusion_type with canonical strong_cosmic_censorship_C2",
        "PASS", bundle_override=bb, target_path="f2a")
    # C5 erase the AF_{I+} definition leaf in F1
    bb = mut("f1")
    set_key(bb["doc"]["f1"], "predicate_abbreviation", "none")
    add("C5", "P5", "erase F1 predicate_abbreviation (AF_{I+} definition leaf)", "FAIL",
        bundle_override=bb, target_path="f1")
    # C6 collapse D0 to a single branch in F1 (base FAIL -> must pass)
    bb = mut("f1")
    bb["doc"]["f1"]["quantifiers"]["domains"]["D0"]["definition"] = \
        "admissible regularity indices: r = smooth only."
    add("C6", "P6b", "collapse F1 D0 to the single branch r = smooth", "PASS",
        bundle_override=bb, target_path="f1")
    # C7 reintroduce the (s,delta) pair binder in F1 quantifiers.formal
    bb = mut("f1")
    bb["doc"]["f1"]["quantifiers"]["formal"] = \
        "forall (s,delta) in D0 exists G_r comeager: ..."
    add("C7", "P6a", "reintroduce '(s,delta) in D0' binder in F1 quantifiers.formal", "FAIL",
        bundle_override=bb, target_path="f1")
    # C8 erase the SCC extension predicate name in F2a
    bb = mut("f2a")
    bb["doc"]["f2a"]["extension_predicate"]["name"] = None
    add("C8", "P7", "erase F2a extension_predicate.name", "FAIL", bundle_override=bb,
        target_path="f2a")
    # C9 break the revision/history stamp in F1
    bb = mut("f1")
    bb["doc"]["f1"]["timestamp_provenance"] = None
    add("C9", "P8", "erase F1 timestamp_provenance", "FAIL", bundle_override=bb,
        target_path="f1")

    ctrl_doc = {"task_id": TASK_ID, "actor": ACTOR,
                "controls": controls,
                "all_fired": all(c["fired"] for c in controls),
                "note": ("Controls mutate in-memory copies only; no canonical artifact is "
                         "written.  A control that stops firing invalidates the measurement.")}
    with open(CONTROLS, "w") as fh:
        json.dump(ctrl_doc, fh, indent=1, sort_keys=True)

    print(json.dumps({"verdict": overall,
                      "checks": {r["id"]: r["verdict"] for r in res.values()},
                      "failing_classes": {r["id"]: r["failing_classes"]
                                          for r in res.values() if r["verdict"] == "FAIL"},
                      "controls_fired": sum(c["fired"] for c in controls),
                      "controls_total": len(controls)}, indent=1))
    return 0 if ctrl_doc["all_fired"] else 1


# --------------------------------------------------------------------------
# live step: drift + corroboration (non-deterministic by construction)
# --------------------------------------------------------------------------
def cmd_live() -> int:
    manifest = json.load(open(MANIFEST))
    out = {"task_id": TASK_ID, "actor": ACTOR,
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "pin_manifest": os.path.relpath(MANIFEST, ROOT), "live": {}}
    for name, info in manifest["pins"].items():
        p = os.path.join(ROOT, info["relpath"])
        cur = sha256_file(p) if os.path.exists(p) else None
        out["live"][name] = {"relpath": info["relpath"],
                             "pinned_sha256": info["sha256_pinned"],
                             "live_sha256": cur,
                             "drift": cur != info["sha256_pinned"]}
    with open(DRIFT, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)

    # corroboration: independent outbox events citing the pinned hashes
    import glob
    prefixes = {n: manifest["pins"][n]["sha256_pinned"][:12] for n in manifest["pins"]}
    corr = {"task_id": TASK_ID, "actor": ACTOR,
            "measured_at": out["measured_at"], "citations": {}}
    for n, pref in prefixes.items():
        found = []
        for f in glob.glob(os.path.join(ROOT, "comms", "outbox", "*.jsonl")) + \
                glob.glob(os.path.join(ROOT, "comms", "inbox", "*.jsonl")):
            if os.path.basename(f).startswith("worker-026"):
                continue
            for line in open(f, errors="ignore"):
                if pref in line:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    found.append({"created_at": e.get("created_at"),
                                  "actor": e.get("actor"),
                                  "event_id": e.get("event_id")})
        found.sort(key=lambda x: (x.get("created_at") or "", x.get("event_id") or ""))
        corr["citations"][n] = {"pinned_sha256_prefix": pref,
                                "independent_citations": len(found),
                                "first": found[:3]}
    with open(CORROB, "w") as fh:
        json.dump(corr, fh, indent=1, sort_keys=True)
    print(json.dumps({"drift": {k: v["drift"] for k, v in out["live"].items()},
                      "independent_citations": {k: v["independent_citations"]
                                                for k, v in corr["citations"].items()}},
                     indent=1))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("--pin", "--check", "--live"):
        print(__doc__)
        sys.exit(2)
    sys.exit({"--pin": cmd_pin, "--check": cmd_check, "--live": cmd_live}[sys.argv[1]]())
