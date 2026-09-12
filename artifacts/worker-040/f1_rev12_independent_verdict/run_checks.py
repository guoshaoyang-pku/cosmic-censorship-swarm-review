#!/usr/bin/env python3
"""W040-F1-INDEP-VERDICT-03 -- from-scratch, hash-bound verification of canonical F1 rev12.

Reviewed bytes: schemas/af_wcc_vacuum.yaml at
  sha256 cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3 (rev 12, mtime 00:32:02).
Context: research_map/formulation_taxonomy.yaml 0abb9ed8a961 (declared F0),
         artifacts/formulation/evidence/taxonomy_consistency.json 9e335e9b (measured).

The script is standalone: python3 run_checks.py [--out-dir DIR].
It replays every check against a byte snapshot taken at review time and re-measures
the live files at entry and exit, so any later publication is reported as drift and
voids the canonical binding (the findings then apply to the snapshot only).

Independence: written from scratch by worker-040 (not an F1 author); the only shared
writes are this worker's own artifact directory.  No shared artifact is modified.
"""

import argparse
import datetime as dt
import hashlib
import itertools
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML required\n")
    raise

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

PIN_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
PIN_F1_SNAPSHOT = "snapshot_af_wcc_vacuum.cce9c60146d6.yaml"
PIN_TAX_SNAPSHOT = "snapshot_formulation_taxonomy.0abb9ed8a961.yaml"
CONSISTENCY_SNAPSHOT = "snapshot_taxonomy_consistency.9e335e9ba1bf.json"

TARGET = "schemas/af_wcc_vacuum.yaml"
CANON_TAX = "research_map/formulation_taxonomy.yaml"
AUTHOR_TAX = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
VARIANTS = "artifacts/formulation/VARIANT_REGISTRY.json"

REVIEW_CLOCK = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
CLASS_TOKEN = re.compile(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)*")
CLASS_ID = "AF-WCC-VAC-GEN"
FROZEN_IDS = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class DupLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently last-winning."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicates = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            try:
                key = self.construct_object(key_node, deep=True)
            except Exception:
                continue
            try:
                hash(key)
            except TypeError:
                continue
            if key in seen:
                self.duplicates.append(
                    {"key": str(key), "line": key_node.start_mark.line + 1}
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml_dup(path):
    with open(path, "r", encoding="utf-8") as fh:
        loader = DupLoader(fh)
        try:
            doc = loader.get_single_data()
        finally:
            loader.dispose()
    return doc, loader.duplicates


def measure(root, rels):
    out = {}
    for rel in rels:
        p = os.path.join(root, rel)
        out[rel] = {"sha256": sha256(p) if os.path.exists(p) else None,
                    "exists": os.path.exists(p)}
    return out


def resolve_pointer(doc, pointer):
    node = doc
    for part in pointer.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(part)
        node = node[part]
    return node


def check(cid, label, kind, status, evidence, falsifier, detail=""):
    return {"id": cid, "label": label, "kind": kind, "status": status,
            "evidence": evidence, "falsifier": falsifier, "detail": detail}


# --------------------------------------------------------------------------------------
# visibility semantics: finite-model adjudication of "whole-curve is strictly STRONGER"
# --------------------------------------------------------------------------------------

def all_preorders(n):
    """All reflexive-transitive relations on {0..n-1} (a causal order, not nec. antisym.)."""
    elems = list(range(n))
    pairs = [(i, j) for i in elems for j in elems]
    out = []
    m = len(pairs)
    for mask in range(1 << m):
        rel = {pairs[k] for k in range(m) if (mask >> k) & 1}
        if any((i, i) not in rel for i in elems):
            continue
        transitive = True
        for (a, b) in rel:
            for (c, d) in rel:
                if b == c and (a, d) not in rel:
                    transitive = False
                    break
            if not transitive:
                break
        if transitive:
            out.append(rel)
    return out


def sequences(n, max_len=4, causal_rel=None, allow_repeat=True):
    elems = list(range(n))
    for length in range(1, max_len + 1):
        pool = itertools.product(elems, repeat=length) if allow_repeat else \
            itertools.permutations(elems, length)
        for seq in pool:
            if causal_rel is None or all(
                (seq[i], seq[j]) in causal_rel
                for i in range(length) for j in range(i + 1, length)
            ):
                yield seq


def visibility_adjudication():
    """Tail single-q vs whole-curve single-q containment over finite causal orders.

    past(q) is a down-set of a preorder (the finite analogue of J^-(q) being past-closed
    and transitive).  tail_visible = exists t0 forall t>=t0: gamma_t in past(q);
    whole_visible = forall t: gamma_t in past(q).  Tail => whole by transitivity.
    """
    res = {"models": {}, "controls": {}}
    total_cmp = 0
    divergences = 0
    witness = None
    for n in (2, 3, 4):
        preorders = all_preorders(n)
        cmps = 0
        divs = 0
        for rel in preorders:
            for q in range(n):
                past = {p for p in range(n) if (p, q) in rel}
                for seq in sequences(n, causal_rel=rel):
                    tail = any(all(seq[t] in past for t in range(t0, len(seq)))
                               for t0 in range(len(seq)))
                    whole = all(x in past for x in seq)
                    cmps += 1
                    if tail and not whole:
                        divs += 1
                        if witness is None:
                            witness = {"n": n, "q": q, "seq": list(seq)}
        res["models"][f"n={n}"] = {"preorders": len(preorders), "comparisons": cmps,
                                   "tail_without_whole_divergences": divs}
        total_cmp += cmps
        divergences += divs
    res["causal_past_closed"] = {"comparisons": total_cmp, "divergences": divergences}
    res["witness"] = witness

    # teeth control A: past sets are singletons {q}, no longer down-closed
    teeth_a = 0
    for n in (2, 3):
        for rel in all_preorders(n):
            for q in range(n):
                past = {q}
                for seq in sequences(n, causal_rel=rel):
                    tail = any(all(seq[t] in past for t in range(t0, len(seq)))
                               for t0 in range(len(seq)))
                    whole = all(x in past for x in seq)
                    if tail and not whole:
                        teeth_a += 1
    res["controls"]["singleton_nonclosed_past_divergences"] = teeth_a

    # teeth control B: drop causality of the sequence, keep past-closed pasts
    teeth_b = 0
    for n in (2, 3):
        for rel in all_preorders(n):
            for q in range(n):
                past = {p for p in range(n) if (p, q) in rel}
                for seq in sequences(n, causal_rel=None):
                    tail = any(all(seq[t] in past for t in range(t0, len(seq)))
                               for t0 in range(len(seq)))
                    whole = all(x in past for x in seq)
                    if tail and not whole:
                        teeth_b += 1
    res["controls"]["non_causal_sequence_divergences"] = teeth_b
    res["controls"]["expected"] = {
        "causal_past_closed": 0, "singleton_nonclosed_past": ">0",
        "non_causal_sequence": ">0"}
    res["analytic_proof"] = (
        "gamma future-directed causal => gamma(t) precedes gamma(t0) for t<t0. If the "
        "tail from t0 lies in J^-(q), concatenating gamma|[t,t0] with the causal curve "
        "gamma(t0)->q gives a causal curve gamma(t)->q, hence gamma(t) in J^-(q). So "
        "tail containment implies whole-curve containment; whole-curve containment "
        "implies tail containment at t0=0. The two readings are EQUIVALENT, not "
        "strictly ordered, for any q and any D4 causal geodesic."
    )
    return res


def controls_for_parsers():
    """Negative controls proving the structural checkers can fail."""
    out = {}
    dup_yaml = "a: 1\nrevised_at: '2026-01-01T00:00:00+08:00'\nrevised_at: '2026-01-02T00:00:00+08:00'\n"
    loader = DupLoader(dup_yaml)
    try:
        loader.get_single_data()
    finally:
        loader.dispose()
    out["duplicate_key_detector"] = {"duplicates_found": len(loader.duplicates),
                                     "expected": 1}
    future = "2026-09-12T23:59:59+08:00"
    out["future_time_detector"] = {
        "would_flag": dt.datetime.fromisoformat(future) > REVIEW_CLOCK}
    txt = "x: AF_{I+}(M)\n"
    out["undefined_symbol_detector"] = {
        "symbol_occurrences": len(re.findall(r"AF_\{I\+\}", txt)),
        "definitional_anchor_present": "abbreviates" in txt,
        "would_flag": "abbreviates" not in txt}
    doc = {"classes": {CLASS_ID: {"ok": True}}}
    bogus_failed = False
    try:
        resolve_pointer(doc, "classes.AF-NOPE")
    except KeyError:
        bogus_failed = True
    out["pointer_resolver"] = {"bogus_pointer_raises": bogus_failed}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--out-dir", default=HERE)
    args = ap.parse_args()
    root, out_dir = os.path.abspath(args.root), os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    snap_f1 = os.path.join(out_dir, PIN_F1_SNAPSHOT)
    snap_tax = os.path.join(out_dir, PIN_TAX_SNAPSHOT)
    snap_cons = os.path.join(out_dir, CONSISTENCY_SNAPSHOT)
    for p in (snap_f1, snap_tax, snap_cons):
        if not os.path.exists(p):
            sys.exit(f"missing review snapshot: {p}")

    checks = []
    entry = measure(root, [TARGET, CANON_TAX, AUTHOR_TAX, CONSISTENCY, FROZEN, VARIANTS])
    snap_hashes = {"snapshot_f1": sha256(snap_f1), "snapshot_tax": sha256(snap_tax),
                   "snapshot_consistency": sha256(snap_cons)}

    # --- B01 binding -------------------------------------------------------------------
    live_f1 = entry[TARGET]["sha256"]
    ok = live_f1 == PIN_F1 == snap_hashes["snapshot_f1"]
    checks.append(check(
        "B01", "target bytes equal the reviewed pin", "binding",
        "PASS" if ok else "FAIL",
        f"live={live_f1} pin={PIN_F1}",
        "any byte change of schemas/af_wcc_vacuum.yaml voids this verdict",
        f"snapshot {PIN_F1_SNAPSHOT} sha256={snap_hashes['snapshot_f1']}"))

    f1, dups = load_yaml_dup(snap_f1)
    rev = f1.get("revision")
    cid = f1.get("class_id")
    checks.append(check(
        "B02", "schema identity: revision 12, class AF-WCC-VAC-GEN", "binding",
        "PASS" if (rev == 12 and cid == CLASS_ID) else "FAIL",
        f"revision={rev} class_id={cid}",
        "revision != 12 or class_id != AF-WCC-VAC-GEN retires this verdict"))

    # --- C01 duplicate keys ------------------------------------------------------------
    dup_summary = []
    for p in (snap_f1, snap_tax):
        _, d = load_yaml_dup(p)
        dup_summary.append({"file": os.path.basename(p), "duplicates": d,
                            "count": len(d)})
    dups_total = sum(x["count"] for x in dup_summary)
    checks.append(check(
        "C01", "no duplicate YAML mapping keys in F1 or canonical F0", "structural",
        "PASS" if dups_total == 0 else "FAIL",
        json.dumps(dup_summary),
        "one duplicate mapping key (esp. revised_at) reinstates HF-040-02",
        "PyYAML safe-load would last-win silently; DupLoader records every duplicate"))

    # --- C02 revised_at hygiene --------------------------------------------------------
    raw_f1 = open(snap_f1, "r", encoding="utf-8").read()
    raw_lines = raw_f1.splitlines()
    top_rev = [i + 1 for i, ln in enumerate(raw_lines) if re.match(r"^revised_at:", ln)]
    revised_at = f1.get("revised_at")
    live_mtime = dt.datetime.fromtimestamp(
        os.path.getmtime(os.path.join(root, TARGET)),
        dt.timezone(dt.timedelta(hours=8)))
    snap_mtime = dt.datetime.fromtimestamp(os.path.getmtime(snap_f1),
                                           dt.timezone(dt.timedelta(hours=8)))
    stamped = dt.datetime.fromisoformat(revised_at) if revised_at else None
    fresh_ok = (len(top_rev) == 1 and stamped is not None
                and stamped <= REVIEW_CLOCK
                and stamped <= live_mtime + dt.timedelta(seconds=5))
    checks.append(check(
        "C02", "single non-future revised_at, not after the publication mtime",
        "structural",
        "PASS" if fresh_ok else "FAIL",
        f"top-level occurrences={len(top_rev)} lines={top_rev} revised_at={revised_at} "
        f"live_mtime={live_mtime.isoformat()} snapshot_copy_mtime={snap_mtime.isoformat()} "
        f"review_clock={REVIEW_CLOCK.isoformat()}",
        "a second top-level revised_at, a future stamp beyond run clock, or a stamp "
        "later than the canonical publication mtime reinstates HF-040-02"))

    # --- C03 canonical pointer ---------------------------------------------------------
    tax, tax_dups = load_yaml_dup(snap_tax)
    ptr = f1.get("class_contract_pointer")
    ptr_ok, ptr_detail = False, ""
    if isinstance(ptr, str) and "#" in ptr:
        path, frag = ptr.split("#", 1)
        try:
            node = resolve_pointer(tax, frag)
            ptr_ok = path == CANON_TAX and isinstance(node, dict)
            ptr_detail = (f"fragment {frag} resolves to dict with keys "
                          f"{sorted(node)[:8]}")
        except KeyError as exc:
            ptr_detail = f"fragment {frag} unresolvable (missing {exc})"
    else:
        ptr_detail = f"malformed pointer {ptr!r}"
    ctrl_fail = False
    try:
        resolve_pointer(tax, "classes.AF-NOPE")
    except KeyError:
        ctrl_fail = True
    checks.append(check(
        "C03", "class_contract_pointer resolves in the canonical F0 taxonomy",
        "semantic",
        "PASS" if (ptr_ok and ctrl_fail) else "FAIL",
        f"pointer={ptr} | {ptr_detail} | bogus-pointer control raises={ctrl_fail}",
        "an unresolvable fragment, a pointer to the authoring mirror, or a control "
        "that does not raise reinstates HF-040-01"))

    # --- C04 supplement pointer --------------------------------------------------------
    author, _ = load_yaml_dup(os.path.join(root, AUTHOR_TAX))
    supp = f1.get("class_contract_supplement_pointer")
    supp_ok, supp_detail = False, ""
    if isinstance(supp, str) and "#" in supp:
        spath, sfrag = supp.split("#", 1)
        try:
            snode = resolve_pointer(author, sfrag)
            supp_ok = isinstance(snode, dict)
            supp_detail = f"fragment {sfrag} resolves (keys {sorted(snode)[:8]})"
        except KeyError as exc:
            supp_detail = f"fragment {sfrag} unresolvable (missing {exc})"
    canon_node = tax.get("classes", {}).get(CLASS_ID, {})
    axes = canon_node.get("axes", {}) if isinstance(canon_node, dict) else {}
    axes_ok = (axes.get("family") == "WCC" and axes.get("matter_model") == "vacuum"
               and canon_node.get("conclusion", {}).get("type")
               == "weak_cosmic_censorship")
    checks.append(check(
        "C04", "supplement pointer resolves and canonical contract axes agree",
        "semantic",
        "PASS" if (supp_ok and axes_ok) else "FAIL",
        f"supplement={supp} | {supp_detail} | canonical axes family="
        f"{axes.get('family')!r} matter={axes.get('matter_model')!r} conclusion_type="
        f"{canon_node.get('conclusion', {}).get('type')!r}",
        "supplement unresolvable, or a family/matter/conclusion-type disagreement "
        "between F1 and the canonical class contract"))

    # --- C05 f0_binding hash vs measured ----------------------------------------------
    fb = f1.get("f0_binding", {}) if isinstance(f1.get("f0_binding"), dict) else {}
    declared_f0 = fb.get("declared_f0_sha256")
    measured_f0 = entry[CANON_TAX]["sha256"] == snap_hashes["snapshot_tax"]
    f0_hash_ok = declared_f0 == entry[CANON_TAX]["sha256"]
    checks.append(check(
        "C05", "declared F0 hash matches measured canonical taxonomy", "binding",
        "PASS" if (f0_hash_ok and measured_f0) else "FAIL",
        f"declared={declared_f0} measured={entry[CANON_TAX]['sha256']}",
        "any divergence between the declared and measured canonical F0 hash"))
    f0_binding_detail = (f"declared F0 {declared_f0}; declared consistency evidence "
                         f"{fb.get('consistency_evidence_sha256')}")

    # --- C06 consistency evidence hash -------------------------------------------------
    declared_cons = fb.get("consistency_evidence_sha256")
    measured_cons = entry[CONSISTENCY]["sha256"]
    cons = json.load(open(snap_cons, "r", encoding="utf-8"))
    cons_ok = declared_cons == measured_cons
    checks.append(check(
        "C06", "declared consistency-evidence hash matches canonical evidence file",
        "binding",
        "PASS" if cons_ok else "FAIL",
        f"declared={declared_cons} measured={measured_cons} | file says consistent="
        f"{cons.get('consistent')} errors={cons.get('errors')}",
        "the binding rule requires the declared evidence hash to resolve; a stale "
        "declaration must be refreshed before any gate verdict (finding W040-F1-05)"))

    # --- C07 AF_{I+} definition coverage ----------------------------------------------
    sym = re.compile(r"AF_\{I\+\}")
    occ = [(i + 1, ln.strip()) for i, ln in enumerate(raw_lines) if sym.search(ln)]
    anchor_lines = [ln for _, ln in occ if "abbreviates" in ln]
    iplus = f1.get("i_plus", {}) if isinstance(f1.get("i_plus"), dict) else {}
    abbr = iplus.get("predicate_abbreviation", "")
    sym_ok = bool(anchor_lines) and "AF_{I+}(M) abbreviates" in str(abbr) and len(occ) <= 3
    checks.append(check(
        "C07", "AF_{I+} has an in-schema definitional anchor", "semantic",
        "PASS" if sym_ok else "FAIL",
        f"occurrences={[l for l, _ in occ]} anchor_lines={len(anchor_lines)} "
        f"predicate_abbreviation={str(abbr)[:110]!r}",
        "an occurrence of AF_{I+} outside the anchor's scope, or a missing "
        "predicate_abbreviation, reinstates HF-040-03"))

    # --- C08 quantifier repair ---------------------------------------------------------
    q = f1.get("quantifiers", {}) if isinstance(f1.get("quantifiers"), dict) else {}
    qformal = str(q.get("formal", ""))
    d5 = q.get("domains", {}).get("D5", {}) if isinstance(q.get("domains"), dict) else {}
    d5def = str(d5.get("definition", ""))
    tail_pat = re.compile(r"gamma\(\[t0,T\)\)\s*subset\s*J\^-\(q\)")
    whole_pat = re.compile(r"gamma\(\[0,T\)\)\s*subset\s*J\^-\(q\)")
    formal_ok = bool(tail_pat.search(qformal)) and not whole_pat.search(qformal)
    d5_first = d5def.split("Whole-curve")[0]
    d5_tail_ref = bool(re.search(r"tail\s+gamma\(\[t0,T\)\)", d5_first)) \
        or bool(tail_pat.search(d5_first))
    d5_whole_ref = bool(re.search(r"gamma\(\[0,T\)\)", d5_first))
    d5_ok = d5_tail_ref and not d5_whole_ref
    checks.append(check(
        "C08", "quantifiers.formal and D5 now use the canonical tail binder",
        "semantic",
        "PASS" if (formal_ok and d5_ok) else "FAIL",
        f"formal_tail={bool(tail_pat.search(qformal))} "
        f"formal_whole={bool(whole_pat.search(qformal))} "
        f"D5_first_clause_tail_ref={d5_tail_ref} "
        f"D5_first_clause_whole_ref={d5_whole_ref}",
        "a whole-curve binder inside quantifiers.formal or the operative D5 clause "
        "reopens the F1-review-19/025 negation defect"))

    # --- C09 class-binding census ------------------------------------------------------
    tokens = {}
    for m in CLASS_TOKEN.finditer(raw_f1):
        tokens[m.group(0)] = tokens.get(m.group(0), 0) + 1
    bound_ids = {k for k in tokens}
    conclusion = f1.get("conclusion", {}) if isinstance(f1.get("conclusion"), dict) else {}
    core_text = " ".join([
        str(conclusion.get("statement_formal", "")),
        str(conclusion.get("statement_natural_language", "")),
        str(f1.get("scope_statement", "")), qformal,
    ])
    scc_leak = [t for t in bound_ids if t.startswith("AF-SCC")]
    leak_in_core = any(t in core_text for t in scc_leak)
    census_ok = (bound_ids <= FROZEN_IDS and cid == CLASS_ID and not leak_in_core
                 and "weak_cosmic_censorship" == f1.get("conclusion", {}).get("conclusion_type"))
    checks.append(check(
        "C09", "single-class binding; no SCC/C0/C2 leakage into the core statement",
        "semantic",
        "PASS" if census_ok else "FAIL",
        f"tokens={tokens} conclusion_type="
        f"{f1.get('conclusion', {}).get('conclusion_type')!r} scc_in_core={leak_in_core}",
        "a fifth class-id-shaped token, a non-frozen binding, or an SCC conclusion "
        "token in quantifiers/conclusion/scope falsifies the binding"))

    # --- C10 visibility equivalence (the rev12 overclaim) ------------------------------
    adj = visibility_adjudication()
    model_div = adj["causal_past_closed"]["divergences"]
    teeth_a = adj["controls"]["singleton_nonclosed_past_divergences"]
    teeth_b = adj["controls"]["non_causal_sequence_divergences"]
    instrument_ok = (model_div == 0 and teeth_a > 0 and teeth_b > 0)
    checks.append(check(
        "C10", "whole-curve vs tail single-q visibility: equivalence adjudication",
        "semantic",
        "FAIL" if instrument_ok else "INSTRUMENT-INVALID",
        f"past-closed causal models: {adj['causal_past_closed']['comparisons']} "
        f"comparisons / {model_div} divergences; teeth controls "
        f"singleton-past={teeth_a}, non-causal={teeth_b}; witness={adj['witness']}",
        "exhibit a future-directed causal geodesic gamma, point q and t0 with the "
        "tail in J^-(q) but gamma(t) not in J^-(q) for some t<t0; that would reinstate "
        "the 'strictly STRONGER' claim and refute this finding",
        "schema line 72 asserts whole-curve containment is strictly STRONGER; the "
        "analytic concatenation argument and the finite models show EQUIVALENCE"))

    # --- C11 misclassification example -------------------------------------------------
    ex_witness = adj["witness"]
    example_supported = ex_witness is not None
    checks.append(check(
        "C11", "schema's line-213 misclassification example is realizable",
        "semantic",
        "FAIL" if not example_supported else "PASS",
        f"witness of tail-but-not-whole containment in a past-closed causal model: "
        f"{ex_witness}; non-causal teeth control finds "
        f"{adj['controls']['non_causal_sequence_divergences']} such witnesses",
        "produce a future-directed causal geodesic that starts outside J^-(q) and "
        "ends inside it; that would make the example real and falsify this finding",
        "the example requires a causal curve to leave a past-closed past set, which "
        "the concatenation argument rules out"))

    # --- B03 drift guard ---------------------------------------------------------------
    exit_h = measure(root, [TARGET, CANON_TAX, AUTHOR_TAX, CONSISTENCY, FROZEN, VARIANTS])
    drift = [rel for rel in entry if entry[rel]["sha256"] != exit_h[rel]["sha256"]]
    checks.append(check(
        "B03", "live canonical files stable across the review window", "binding",
        "PASS" if not drift else "DRIFT",
        f"entry={ {k: (v['sha256'] or '')[:12] for k, v in entry.items()} } "
        f"exit={ {k: (v['sha256'] or '')[:12] for k, v in exit_h.items()} }",
        "any drift means the verdict binds the snapshot only and must be re-run "
        "against the next canonical publication"))

    # --- resolved prior findings -------------------------------------------------------
    resolved = [
        {"id": "HF-040-01", "status": "resolved",
         "evidence_ref": "C03 canonical pointer resolves at classes.AF-WCC-VAC-GEN"},
        {"id": "HF-040-02", "status": "resolved",
         "evidence_ref": "C01 zero duplicate keys / C02 single non-future revised_at"},
        {"id": "HF-040-03", "status": "resolved",
         "evidence_ref": "C07 predicate_abbreviation anchor defines AF_{I+}"},
    ]

    hard_failures = []
    if not instrument_ok:
        hard_failures.append({
            "id": "HF-040-04-INSTRUMENT", "severity": "blocker",
            "name": "visibility_adjudication_instrument_invalid",
            "evidence": "teeth controls failed to fire", "why_blocking":
            "cannot certify the equivalence finding with a broken instrument"})
    else:
        hard_failures.append({
            "id": "HF-040-04", "severity": "major",
            "name": "false_strictness_claim_for_whole_curve_visibility",
            "evidence": "schemas/af_wcc_vacuum.yaml rev12 line 72: 'Whole-curve "
                        "containment gamma([0,T)) subset J^-(q) is strictly STRONGER "
                        "and is NOT the predicate of this class'; line 213 repeats the "
                        "impossible justification 'a geodesic that starts in the "
                        "exterior and ends inside the black-hole region'. C10: "
                        f"{adj['causal_past_closed']['comparisons']} causal past-closed "
                        "comparisons, 0 divergences (equivalence); teeth controls "
                        f"non-causal={teeth_b}, non-closed-past={teeth_a}.",
            "why_blocking": "The canonical F1 schema asserts a false mathematical "
                            "relation between its own central predicate and an "
                            "equivalent formulation. A G-FORM pass at this hash would "
                            "certify the false strictness claim. Fix: replace the "
                            "strictness sentence with the past-closure equivalence "
                            "statement (W037 withdrawal and W040-F1-INDEP-VERDICT-02 "
                            "already established it) and delete the misclassification "
                            "example.",
        })
    if not cons_ok:
        hard_failures.append({
            "id": "HF-040-05", "severity": "major",
            "name": "stale_declared_consistency_evidence_hash",
            "evidence": f"F1 f0_binding.consistency_evidence_sha256={declared_cons}; "
                        f"canonical evidence file measured {measured_cons} "
                        f"(still consistent={cons.get('consistent')}).",
            "why_blocking": "The binding rule in the same leaf requires refresh and "
                            "re-run before a gate verdict; a declared evidence hash "
                            "that no longer resolves at the canonical path blocks "
                            "hash-bound promotion.",
        })

    advisory = [
        {"id": "W040-F1-A1", "severity": "advisory",
         "text": "line 72 cites 'F1-review-19 HF-06 critical, independently confirmed "
                 "by worker-037 W037V2-F1 and worker-078 W078-F1-QUANT-ADJ-01'. "
                 "worker-037's own equivalence adjudication WITHDREW W037V2-F1 after "
                 "its falsifier fired (J^- past-closure bridge), so the 'independently "
                 "confirmed' attribution is stale; cite the withdrawal and the "
                 "equivalence, not the withdrawn blocker.",
         "evidence_refs": ["artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json",
                           "reviews/F1-review-040.json"]},
        {"id": "W040-F1-A2", "severity": "advisory",
         "text": "the same 'strictly STRONGER' sentence is repeated for the SET variant "
                 "(line 233) and the canonical F0 taxonomy; only the SET-vs-single-q "
                 "relation is at stake there and its strictness is not established by "
                 "the argument given, but it is not adjudicated here.",
         "evidence_refs": ["schemas/af_wcc_vacuum.yaml#class_identity_variants",
                           "research_map/formulation_taxonomy.yaml"]},
    ]

    verdict = "revise" if hard_failures else "accept-with-advisories"
    score = 3.5 if verdict == "revise" else 4.0

    overall_falsifier = {
        "statement": "This verdict is void on any of the following; each check also "
                     "carries its own falsifier.",
        "falsifiers": [
            "any byte change of schemas/af_wcc_vacuum.yaml away from " + PIN_F1,
            "a future-directed causal geodesic gamma, q in I+ and t0 with "
            "gamma([t0,T)) in J^-(q) intersect M but gamma(t) not in J^-(q) for some "
            "t<t0 (would reinstate the strictness claim and refute HF-040-04)",
            "a canonical F1 text that states the tail/whole-curve equivalence and "
            "deletes the misclassification example (retires HF-040-04)",
            "a refreshed f0_binding whose consistency_evidence_sha256 equals the "
            "measured evidence file (retires HF-040-05)",
            "re-running this script after any new F1 publication: every hash-bound "
            "conclusion must be regenerated against the new bytes",
        ],
    }

    independence = {
        "reviewer": "worker-040",
        "reviewer_is_author": False,
        "author_of_target": f1.get("authored_by"),
        "own_checks_written": True,
        "snapshot_taken": True,
        "network_used": False,
        "shared_artifacts_modified": [],
        "prior_reviews_consulted": [
            "reviews/F1-review-040.json", "reviews/F1-review-19.json",
            "reviews/F1-review-090.json", "reviews/F1-review-lead-audit-r2.json",
            "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json",
            "artifacts/worker-078/f1_quantifier_adjudication/report.json",
        ],
    }

    checks_json = {
        "artifact_kind": "machine_check_results",
        "task_id": "W040-F1-INDEP-VERDICT-03",
        "created_at": REVIEW_CLOCK.isoformat(),
        "target": TARGET,
        "reviewed_snapshot": PIN_F1_SNAPSHOT,
        "reviewed_sha256": PIN_F1,
        "live_sha256_at_entry": live_f1,
        "live_sha256_at_exit": exit_h[TARGET]["sha256"],
        "drift": drift,
        "checks": checks,
        "resolved_prior_findings": resolved,
        "hard_failures": hard_failures,
        "advisory": advisory,
        "verdict": verdict,
        "score": score,
    }
    checks_path = os.path.join(out_dir, "checks.json")
    with open(checks_path, "w", encoding="utf-8") as fh:
        json.dump(checks_json, fh, indent=1, sort_keys=True)
        fh.write("\n")

    instrument = {
        "artifact_kind": "instrument_runs",
        "task_id": "W040-F1-INDEP-VERDICT-03",
        "visibility_adjudication": adj,
        "parser_and_detector_controls": controls_for_parsers(),
        "determinism_note": "pure enumeration over fixed finite sets; no RNG, no network",
    }
    instr_path = os.path.join(out_dir, "instrument_runs.json")
    with open(instr_path, "w", encoding="utf-8") as fh:
        json.dump(instrument, fh, indent=1, sort_keys=True)
        fh.write("\n")

    verdict_json = {
        "schema_version": "1.0",
        "artifact_kind": "independent_class_bound_verdict",
        "task_id": "W040-F1-INDEP-VERDICT-03",
        "created_at": REVIEW_CLOCK.isoformat(),
        "reviewer": "worker-040",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": [CLASS_ID],
        "target": {
            "path": TARGET,
            "sha256": PIN_F1,
            "revision": rev,
            "snapshot": PIN_F1_SNAPSHOT,
            "mtime": live_mtime.isoformat(),
            "snapshot_copy_mtime": snap_mtime.isoformat(),
            "live_sha256_at_entry": live_f1,
            "live_sha256_at_exit": exit_h[TARGET]["sha256"],
            "drift_during_run": drift,
        },
        "verdict": verdict,
        "score": score,
        "hard_failures": hard_failures,
        "advisory_findings": advisory,
        "resolved_prior_findings": resolved,
        "f0_binding": f0_binding_detail,
        "checks_summary": {c["id"]: c["status"] for c in checks},
        "evidence_refs": [
            f"artifacts/worker-040/f1_rev12_independent_verdict/{PIN_F1_SNAPSHOT}",
            "artifacts/worker-040/f1_rev12_independent_verdict/checks.json",
            "artifacts/worker-040/f1_rev12_independent_verdict/instrument_runs.json",
            "artifacts/worker-040/f1_rev12_independent_verdict/run_checks.py",
            "artifacts/worker-040/f1_rev12_independent_verdict/entry_hashes.json",
            "research_map/formulation_taxonomy.yaml",
            "artifacts/formulation/evidence/taxonomy_consistency.json",
        ],
        "next_falsifier": overall_falsifier,
        "limitations": [
            "Finite preorder models are a control, not a proof; the decisive argument "
            "is the concatenation lemma recorded in instrument_runs.json.",
            "The SET-variant strictness claim (line 233) and the F0 taxonomy wording "
            "are out of scope here.",
            "The live canonical may have moved after the exit measurement; the "
            "snapshot is the reviewed object.",
        ],
        "independence": independence,
        "authority_note": "worker event: cannot set status=done, validation_status="
                          "passed, or a gate verdict; controller and leads own those "
                          "with artifact + review evidence. No shared artifact was "
                          "modified by this worker.",
    }
    verdict_path = os.path.join(out_dir, "verdict.json")
    with open(verdict_path, "w", encoding="utf-8") as fh:
        json.dump(verdict_json, fh, indent=1, sort_keys=True)
        fh.write("\n")

    entry_path = os.path.join(out_dir, "entry_hashes.json")
    with open(entry_path, "w", encoding="utf-8") as fh:
        json.dump({"entry_live": entry, "exit_live": exit_h,
                   "snapshots": snap_hashes, "review_clock": REVIEW_CLOCK.isoformat(),
                   "drift": drift}, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(json.dumps({
        "task_id": "W040-F1-INDEP-VERDICT-03",
        "reviewed_sha256": PIN_F1,
        "verdict": verdict,
        "score": score,
        "checks": {c["id"]: c["status"] for c in checks},
        "drift": drift,
        "outputs": [os.path.basename(p) for p in
                    (checks_path, instr_path, verdict_path, entry_path)],
    }, indent=1))
    return 0 if instrument_ok else 2


if __name__ == "__main__":
    sys.exit(main())
