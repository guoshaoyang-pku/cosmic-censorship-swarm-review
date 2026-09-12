#!/usr/bin/env python3
"""W035-REV14-CONFORMANCE-PRECHECK-01 (worker-035, node F2b, class AF-SCC-C0-VAC-GEN).

Read-only, deterministic pre-registered checker for the F2b C0 schema, written for the
REC-36 rev14 / FROZEN rev30 window. It is an INSTRUMENT, not a verdict: it flags; it never
authors and never writes outside its own output path.

Scope: `schemas/af_scc_c0_vacuum.yaml` (canonical) or any `--file` copy. Every check carries
its own falsifier and every blocking check has a labeled fixture in `fixtures/` (see
`make_fixtures.py` / `controls.json`) whose mutation flips exactly that check, plus a positive
fixture where the live bytes fail. The instrument's own self-falsifier: a fixture whose
observed status differs from `fixtures/expected.json`.

Usage:
  python3 precheck.py --file schemas/af_scc_c0_vacuum.yaml --out report.json
  python3 precheck.py --file fixtures/F3_both_fixed.yaml --c2 schemas/af_scc_c2_vacuum.yaml

Exit codes: 0 = all blocking checks PASS, 2 = >=1 blocking FAIL, 3 = instrument error/drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CANON = "schemas/af_scc_c0_vacuum.yaml"
CANON_ABS = os.path.join(ROOT, CANON)
C2_CANON = "schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
ENTRY_HASHES = "entry_hashes.json"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
REG_TOKEN = "C0"
SIBLING = "AF-SCC-C2-VAC-GEN"

# extension-set order, outer (largest set) -> inner (smallest set)
CHAIN_TOKENS = [
    ("E_C0", "C0"),
    ("E_H2loc", "H2loc"),
    (r"E_\{C\^1,1\}", "C11"),
    ("E_C2", "C2"),
]
CLASS_WORD = re.compile(r"\b(C0|C2|H2_loc|H2loc|C\^\{?1,1\}?)\b")


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def walk_strings(obj, key=None):
    """Yield (key, str) for every string leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v, key)
    elif isinstance(obj, str):
        yield key, obj


def collect_key(doc, target_key):
    out = []

    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == target_key and isinstance(v, list):
                    out.extend([x for x in v if isinstance(x, str)])
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)

    rec(doc)
    return out


REL_PAT = re.compile(
    r"(E_\{C\^1,1\}|E_C0|E_H2loc|E_C2)\s+(contains|is\s+a\s+subset\s+of|subset\s+of)\s+"
    r"(?=(E_\{C\^1,1\}|E_C0|E_H2loc|E_C2))"
)
TOKEN_LABEL = {"E_C0": "C0", "E_H2loc": "H2loc", "E_{C^1,1}": "C11", "E_C2": "C2"}


def parse_chain(text: str) -> list[str]:
    """Return the extension sets ordered outer (largest set) -> inner (smallest set).

    Reads explicit binary relations (`A contains B`, `A subset of B`) and topologically
    orders them, so the result is comparable across phrasings and connectives.
    """
    pairs = []
    for a, rel, b in REL_PAT.findall(text):
        bigger, smaller = (a, b) if rel == "contains" else (b, a)
        pairs.append((TOKEN_LABEL[bigger], TOKEN_LABEL[smaller]))
    nodes = []
    for x, y in pairs:
        for t in (x, y):
            if t not in nodes:
                nodes.append(t)
    if not pairs:
        # fallback: first-occurrence order of the known tokens
        found = sorted(
            ((m.start(), tok) for pat, tok in CHAIN_TOKENS for m in [re.search(pat, text)] if m),
        )
        return [t for _, t in found]
    # Kahn: edge bigger -> smaller, emit larger sets first
    indeg = {n: 0 for n in nodes}
    adj = {n: [] for n in nodes}
    for x, y in pairs:
        adj[x].append(y)
        indeg[y] += 1
    order, ready = [], sorted([n for n in nodes if indeg[n] == 0], key=nodes.index)
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
                ready.sort(key=nodes.index)
    return order if len(order) == len(nodes) else [t for t in nodes]


def normalize_word(w: str) -> str:
    w = w.strip()
    if w in ("H2_loc", "H2loc"):
        return "H2loc"
    if w.startswith("C^"):
        return "C11"
    return w


def node(status, cid, name, severity, detail, evidence, falsifier, **extra):
    d = {
        "id": cid,
        "name": name,
        "severity": severity,
        "status": status,
        "detail": detail,
        "evidence": evidence,
        "falsifier": falsifier,
    }
    d.update(extra)
    return d


def check_identity(doc, target, measured, mirror_path):
    ev = [f"{target}#sha256:{measured[:12]}"]
    problems = []
    cid = doc.get("class_id")
    if cid != CLASS_ID:
        problems.append(f"class_id={cid!r} != {CLASS_ID!r}")
    comps = doc.get("class_components") or {}
    if comps.get("regularity_token") != REG_TOKEN:
        problems.append(f"class_components.regularity_token={comps.get('regularity_token')!r}")
    sib = doc.get("sibling_disjoint_from")
    if isinstance(sib, str):
        sib = [sib]
    if not sib or SIBLING not in sib:
        problems.append(f"sibling_disjoint_from does not name {SIBLING}")
    st = "FAIL" if problems else "PASS"
    return node(
        st,
        "P01",
        "class_identity_and_separation",
        "blocking",
        "; ".join(problems) if problems else "class_id, regularity token and sibling disjointness are the C0 values; no C2/C0 merge at the identity fields",
        ev,
        "an edit that asserts another class id or drops the C2 sibling separation flips this to FAIL (fixture F5_identity_leak)",
    )


def check_f0_chain(doc, target, measured):
    fb = doc.get("f0_binding") or {}
    rows, problems = [], []
    pairs = [
        ("declared_f0_sha256", "declared_f0_artifact"),
        ("consistency_evidence_sha256", "consistency_evidence"),
    ]
    # any other *_sha256 leaf under f0_binding
    extra = [k for k in fb if isinstance(k, str) and k.endswith("_sha256") and k not in dict(pairs)]
    for k in extra:
        pairs.append((k, k[: -len("_sha256")]))
    for hk, pk in pairs:
        declared = fb.get(hk)
        if not isinstance(declared, str):
            continue
        p = fb.get(pk)
        if not p:
            rows.append({"field": hk, "declared": declared, "path": None, "status": "unresolved_referent"})
            problems.append(f"{hk}: no declared path")
            continue
        hp = p if os.path.isabs(p) else os.path.join(ROOT, p)
        meas = sha256_file(hp)
        if meas is None:
            rows.append({"field": hk, "declared": declared, "path": p, "status": "unresolved_path"})
            problems.append(f"{hk}: path {p} missing")
        elif meas == declared:
            rows.append({"field": hk, "declared": declared, "path": p, "measured": meas, "status": "resolved"})
        else:
            rows.append({"field": hk, "declared": declared, "path": p, "measured": meas, "status": "mismatch"})
            problems.append(f"{hk}: declared {declared[:12]} != measured {meas[:12]} at {p}")
    st = "FAIL" if problems else "PASS"
    return node(
        st,
        "P02",
        "f0_binding_declared_hashes_resolve",
        "blocking",
        "; ".join(problems) if problems else f"all {len(rows)} declared sha256 field(s) resolve to measured bytes",
        [f"{target}#sha256:{measured[:12]}"] + [f"{r['path']}#sha256:{(r.get('measured') or r['declared'])[:12]}" for r in rows if r.get("path")],
        "corrupting one declared hash by one hex character flips this to FAIL (fixture F4_chain_corrupt); a refreshed binding with all declared values equal to measured bytes flips it back to PASS",
        rows=rows,
    )


def check_refresh(doc, target, measured):
    fb = doc.get("f0_binding") or {}
    declared = fb.get("declared_f0_sha256")
    p = fb.get("declared_f0_artifact")
    hp = os.path.join(ROOT, p) if p and not os.path.isabs(p) else p
    meas = sha256_file(hp) if hp else None
    if meas is None or not isinstance(declared, str):
        st, detail = "OBS", "declared F0 artifact not measurable; refresh rule not evaluable"
    elif meas == declared:
        st, detail = "PASS", "declared F0 hash equals measured F0 bytes; the binding's own refresh trigger is not active"
    else:
        st, detail = "FAIL", f"declared F0 {declared[:12]} != measured {meas[:12]}; binding refresh owed before any gate verdict"
    return node(
        st,
        "P03",
        "f0_binding_refresh_rule_satisfied",
        "blocking",
        detail,
        [f"{p}#sha256:{(meas or 'missing')[:12]}", f"{target}#sha256:{measured[:12]}"],
        "a byte move of research_map/formulation_taxonomy.yaml without refreshing declared_f0_sha256 flips this to FAIL",
        declared_f0_sha256=declared,
        measured_f0_sha256=meas,
        checked_at=fb.get("checked_at"),
        rule=fb.get("rule"),
    )


def check_d1(doc, target, measured, chain_order):
    entries = collect_key(doc, "must_not_conflate")
    denial = re.compile(
        r"no\s+containment\s+(with|between)|not\s+contained\s+in|is\s+not\s+contained|incomparable\s+with",
        re.I,
    )
    # Metalinguistic mentions are not assertions: bracketed revision notes and quoted spans
    # are stripped before matching, and reported separately (CF-16 pattern).
    mention = re.compile(r"\[.*?\]|'[^']*'|\"[^\"]*\"")
    hits, mentions = [], []
    for e in entries:
        asserted = mention.sub(" ", e)
        if denial.search(e) and CLASS_WORD.search(e):
            if denial.search(asserted) and CLASS_WORD.search(asserted):
                hits.append(e)
            else:
                mentions.append(e)
    chain_asserts = len(chain_order) >= 2
    if hits and chain_asserts:
        st = "FAIL"
        detail = (f"{len(hits)} must_not_conflate entr(y/ies) deny containment in asserted text while "
                  f"implication_ledger.extension_class_containment asserts {' contains '.join(chain_order)}: {hits[0][:160]}")
    elif hits and not chain_asserts:
        st = "OBS"
        detail = "containment denial asserted but the ledger chain does not parse; cannot adjudicate (see P05)"
    else:
        st = "PASS"
        detail = (f"no asserted containment-denial entry among {len(entries)} must_not_conflate entries; "
                  f"ledger chain {' contains '.join(chain_order) if chain_order else 'unparsed'}"
                  + (f"; {len(mentions)} quoted/bracketed historical mention(s) ignored" if mentions else ""))
    return node(
        st,
        "P04",
        "D1_must_not_conflate_containment_denial",
        "blocking",
        detail,
        [f"{target}#sha256:{measured[:12]}"],
        "re-adding 'No containment with C2 or C0 is asserted here' as asserted (unquoted, unbracketed) text flips this to FAIL (fixtures F0_baseline, F9_unquoted_denial); quoting it inside a revision note flips it back to PASS (fixture F8_rev14_actual)",
        hits=hits,
        mentions_ignored=[m[:120] for m in mentions],
        must_not_conflate_count=len(entries),
    )


def check_d2(doc, target, measured, chain_order):
    led = doc.get("implication_ledger") or {}
    rows = led.get("forbidden_transfers") or []
    own = ((doc.get("class_components") or {}).get("regularity_token")) or "C0"
    problems = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        reason = str(r.get("reason", ""))
        m = re.search(r"([A-Za-z0-9_^{},\s]+?)\s+is\s+a\s+strictly\s+(larger|smaller)\s+extension\s+class", reason)
        if not m:
            continue
        raw, direction = m.group(1), m.group(2)
        words = [normalize_word(w) for w in CLASS_WORD.findall(raw)]
        words = [w for w in words if w in chain_order]
        if not words:
            continue
        x = words[-1]
        if own not in chain_order:
            continue
        # 'this class' target is the file's own class
        target_word = own
        to = str(r.get("to", ""))
        if to != "this class":
            tw = [normalize_word(w) for w in CLASS_WORD.findall(to)]
            tw = [w for w in tw if w in chain_order]
            if tw:
                target_word = tw[-1]
        ix, it = chain_order.index(x), chain_order.index(target_word)
        # outer rank < inner rank; a "larger" class must be outer of the target
        ok = (ix < it) if direction == "larger" else (ix > it)
        if not ok:
            problems.append(
                f"forbidden_transfers reason asserts {x} strictly {direction} than {target_word}, "
                f"but the chain has {' contains '.join(chain_order)} (rank {ix} vs {it}): {reason[:120]}"
            )
    st = "FAIL" if problems else ("OBS" if not chain_order else "PASS")
    detail = "; ".join(problems) if problems else (
        f"no forbidden_transfers reason contradicts the chain {' contains '.join(chain_order)}"
        if chain_order else "chain unparsed; no size-direction adjudication possible"
    )
    return node(
        st,
        "P05",
        "D2_forbidden_transfer_size_direction",
        "blocking",
        detail,
        [f"{target}#sha256:{measured[:12]}"],
        "changing the reason to 'C2 is a strictly larger extension class' against the live chain flips this to FAIL (fixture F2_d2_inversion_fixed is the reverse)",
        rows_checked=len(rows),
    )


def check_revhist(doc, target, measured):
    fb = doc.get("f0_binding") or {}
    live = fb.get("declared_f0_sha256") or ""
    rows = doc.get("revision_history") or []
    named = [
        r.get("index")
        for r in rows
        if isinstance(r, dict) and not r.get("unused") and live[:12] and live[:12] in " ".join(r.get("notes") or [])
    ]
    unused_notes = [r.get("index") for r in rows if isinstance(r, dict) and r.get("unused") and (r.get("notes") or [])]
    ts = [(r.get("index"), r.get("at")) for r in rows if isinstance(r, dict)]
    mono, prev = True, None
    for _, t in ts:
        if not t:
            continue
        if prev is not None and str(t) < str(prev):
            mono = False
        prev = t
    problems = []
    if not named:
        problems.append(f"no non-unused revision_history row names the live declared F0 {live[:12]}")
    if not mono:
        problems.append("revision_history timestamps are not monotone by index")
    if unused_notes:
        problems.append(f"unused row(s) {unused_notes} carry delta notes")
    st = "PASS" if not problems else "FAIL"
    return node(
        st,
        "P06",
        "revision_history_binding_monotone",
        "advisory",
        "; ".join(problems) if problems else f"newest row(s) {named} name the live F0 hash; timestamps monotone; no unused delta rows",
        [f"{target}#sha256:{measured[:12]}"],
        "adding a row that names the live declared F0 hash with a later timestamp flips this to PASS (fixture F7_revhist_fix)",
        rows_naming_live_f0=named,
        timestamps_monotone=mono,
        unused_rows_with_notes=unused_notes,
    )


def check_sidepins(target, measured, is_canon):
    if not is_canon:
        return node("OBS", "P07", "sidecar_and_entry_hash_pins", "advisory",
                    "non-canonical target; side pins are evaluated only for the canonical path",
                    [f"{target}#sha256:{measured[:12]}"], "n/a for fixtures")
    rows = []
    side = os.path.join(ROOT, CANON + ".sha256")
    if os.path.exists(side):
        toks = open(side).read().split()
        tok = toks[0] if toks else None
        rows.append({"pin": CANON + ".sha256", "declared": tok, "status": "resolved" if tok == measured else "mismatch"})
    else:
        rows.append({"pin": CANON + ".sha256", "declared": None, "status": "absent"})
    try:
        eh = json.load(open(os.path.join(ROOT, ENTRY_HASHES)))
        tok = eh.get(CANON)
        rows.append({"pin": ENTRY_HASHES, "declared": tok, "status": ("resolved" if tok == measured else ("mismatch" if tok else "absent"))})
    except Exception as e:  # pragma: no cover
        rows.append({"pin": ENTRY_HASHES, "declared": None, "status": f"unreadable: {e}"})
    bad = [r for r in rows if r["status"] == "mismatch"]
    st = "FAIL" if bad else ("PASS" if rows else "OBS")
    return node(st, "P07", "sidecar_and_entry_hash_pins", "advisory",
                "; ".join(f"{r['pin']}: {r['status']}" for r in rows),
                [f"{CANON}#sha256:{measured[:12]}"],
                "refreshing both side pins to the measured hash flips this to PASS (F-035-02 repair)",
                rows=rows)


def check_review_status(doc, target, measured):
    rs = doc.get("review_status") or {}
    revs = rs.get("independent_reviewers")
    verdict = rs.get("verdict")
    ok = bool(revs) and verdict not in (None, "pending")
    return node("PASS" if ok else "FAIL", "P08", "review_status_block_freshness", "advisory",
                f"independent_reviewers={revs!r}, verdict={verdict!r}",
                [f"{target}#sha256:{measured[:12]}"],
                "a revision whose review_status lists the bound reviewers and a decided verdict flips this to PASS (HF-W035-AA-03 repair)",
                independent_reviewers=revs, verdict=verdict)


def check_crossfile(doc, target, measured, c2_path, chain_order):
    """Compare the C0 chain order with the C2 sibling's own containment statement."""
    if not os.path.exists(c2_path):
        return node("OBS", "P09", "sibling_chain_consistency", "blocking",
                    f"C2 sibling {c2_path} missing", [f"{target}#sha256:{measured[:12]}"], "n/a")
    c2 = load_yaml(c2_path)
    text = ((c2.get("implication_ledger") or {}).get("extension_class_containment")) or ""
    c2_order = parse_chain(text)
    c2_sha = sha256_file(c2_path)
    shared = [t for t in chain_order if t in c2_order]
    ok = len(shared) >= 2 and [t for t in chain_order if t in shared] == [t for t in c2_order if t in shared]
    st = "PASS" if ok else "FAIL"
    return node(st, "P09", "sibling_chain_consistency", "blocking",
                f"C0 chain {' contains '.join(chain_order)} vs C2 chain {' subset-of '.join(c2_order)}: {'consistent' if ok else 'ORDER DISAGREES'}",
                [f"{target}#sha256:{measured[:12]}", f"{c2_path}#sha256:{(c2_sha or 'missing')[:12]}"],
                "flipping the C2 chain order flips this to FAIL (fixture F6_crossfile_flip pairs a clean C0 with a mutated C2)",
                c0_order=chain_order, c2_order=c2_order)


def check_frozen(target, measured, is_canon):
    if not is_canon:
        return node("OBS", "P10", "frozen_rev30_pin", "blocking", "non-canonical target; FROZEN pin checked only for the canonical path",
                    [f"{target}#sha256:{measured[:12]}"], "n/a for fixtures")
    try:
        fr = json.load(open(os.path.join(ROOT, FROZEN)))
    except Exception as e:
        return node("FAIL", "P10", "frozen_rev30_pin", "blocking", f"FROZEN.json unreadable: {e}",
                    [FROZEN], "a FROZEN manifest that declares this artifact at the measured hash flips this to PASS")
    files = fr.get("files") or {}
    rows = [{"declared_path": k, "declared": v.get("sha256") if isinstance(v, dict) else None}
            for k, v in files.items() if k.endswith("af_scc_c0_vacuum.yaml")]
    hit = [r for r in rows if r["declared"] == measured]
    st = "PASS" if hit else "FAIL"
    return node(st, "P10", "frozen_rev30_pin", "blocking",
                f"FROZEN rev{fr.get('revision')} declares {[r['declared_path'] for r in rows]} at "
                f"{[ (r['declared'] or '')[:12] for r in rows]} vs measured {measured[:12]}",
                [f"{FROZEN}#sha256:{(sha256_file(os.path.join(ROOT, FROZEN)) or '')[:12]}", f"{target}#sha256:{measured[:12]}"],
                "regenerating FROZEN with the live artifact hash flips this to PASS; a byte move of the artifact without FROZEN regeneration flips it to FAIL",
                declared=rows)


def check_mirror(target, measured, is_canon):
    mirror = os.path.join(ROOT, "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    if not is_canon:
        return node("OBS", "P11", "double_tree_mirror_align", "advisory", "non-canonical target; mirror checked only for the canonical path",
                    [f"{target}#sha256:{measured[:12]}"], "n/a for fixtures")
    m = sha256_file(mirror)
    st = "PASS" if m == measured else ("FAIL" if m else "OBS")
    return node(st, "P11", "double_tree_mirror_align", "advisory",
                f"mirror artifacts/formulation/schemas/af_scc_c0_vacuum.yaml sha256 {(m or 'missing')[:12]} vs canonical {measured[:12]}",
                [f"artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#sha256:{(m or 'missing')[:12]}"],
                "a divergent mirror pair flips this to FAIL; the double-tree rule requires canonical == mirror == FROZEN pin")


def run(file_path, c2_path, canon_mode):
    target = os.path.relpath(os.path.abspath(file_path), ROOT)
    start = sha256_file(file_path)
    doc = load_yaml(file_path)
    measured = sha256_file(file_path)
    drift = start != measured
    chain_text = ((doc.get("implication_ledger") or {}).get("extension_class_containment")) or ""
    chain = parse_chain(chain_text)
    checks = [
        check_identity(doc, target, measured, None),
        check_f0_chain(doc, target, measured),
        check_refresh(doc, target, measured),
        check_d1(doc, target, measured, chain),
        check_d2(doc, target, measured, chain),
        check_revhist(doc, target, measured),
        check_sidepins(target, measured, canon_mode),
        check_review_status(doc, target, measured),
        check_crossfile(doc, target, measured, c2_path, chain),
        check_frozen(target, measured, canon_mode),
        check_mirror(target, measured, canon_mode),
    ]
    if drift:
        checks.append(node("FAIL", "P00", "target_stable_during_read", "blocking",
                           f"sha256 changed during read: {start} -> {measured}",
                           [f"{target}#sha256:{measured[:12]}"],
                           "a stable file cannot drift; any change means re-run on the new bytes"))
    blocking_fail = [c["id"] for c in checks if c["severity"] == "blocking" and c["status"] == "FAIL"]
    advisory_fail = [c["id"] for c in checks if c["severity"] == "advisory" and c["status"] == "FAIL"]
    return {
        "instrument": "W035-REV14-CONFORMANCE-PRECHECK-01",
        "instrument_sha256": sha256_file(os.path.abspath(__file__)),
        "generated_at": now_iso(),
        "target": {"path": target, "sha256_start": start, "sha256_end": measured, "revision": doc.get("revision"),
                   "class_id": doc.get("class_id"), "node_id": doc.get("node_id")},
        "c2_reference": {"path": os.path.relpath(os.path.abspath(c2_path), ROOT), "sha256": sha256_file(c2_path)},
        "chain_order_outer_to_inner": chain,
        "checks": checks,
        "summary": {
            "blocking_pass": [c["id"] for c in checks if c["severity"] == "blocking" and c["status"] == "PASS"],
            "blocking_fail": blocking_fail,
            "advisory_fail": advisory_fail,
            "verdict": "BLOCKING_FAIL" if blocking_fail else "NO_BLOCKING_FAIL",
            "note": "instrument only; this is not a gate verdict and not a class verdict (worker event authority)",
        },
        "self_falsifier": "any fixture in fixtures/ whose observed check status differs from fixtures/expected.json falsifies this instrument",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=CANON_ABS)
    ap.add_argument("--c2", default=os.path.join(ROOT, C2_CANON))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    canon_mode = os.path.abspath(a.file) == CANON_ABS
    rep = run(a.file, a.c2, canon_mode)
    text = json.dumps(rep, indent=1, ensure_ascii=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 2 if rep["summary"]["blocking_fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
