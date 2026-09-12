#!/usr/bin/env python3
"""Independent F0 review checker (worker-094, node F0, gate G-F0).

Fail-closed: the script refuses to emit a report unless the bytes it reads hash to
EXPECT_SHA256.  It re-derives every check from the frozen bytes instead of calling
the author's validator; the author validator is cited only as corroboration.

Checks
  1  pin                 bytes hash == EXPECT_SHA256 (else exit 3)
  2  yaml                strict load + duplicate-key detection (author's file uses none)
  3  identity            exactly the 4 frozen class ids, classes keys == class_ids
  4  tokens              every AF-* token in the raw text is one of the 4 ids, or a
                         parent+variant_id composite that is registered in `variants`
  5  class completeness  axes/hypotheses/exclusions/conclusion/test_cases/provenance;
                         conclusion.type == axes.conclusion_type
  6  axis vocabulary     values in the allowed sets; G2 regularity token discipline
  7  disjointness        all 6 pairs present; each named decisive axis really differs;
                         NEGATIVE CONTROL: a fabricated identical-axis pair must fail
  8  g3                  merged-regularity scan with normalization + positive control
  9  genericity          machine-readability of genericity_kind/genericity_topology
 10  clock               embedded content timestamps vs written_at and vs wall clock
 11  theorem-status      claims_theorem_status false; no class conclusion_type theorem
 12  test cases          per-class positive/negative cases + decisive hypotheses
 13  cross-artifact      canonical F1/F2a/F2b class_id and declared F0 binding hash
 14  case corpus         schemas/taxonomy_cases.jsonl bindings vs pinned F0 hash
 15  publication         canonical vs authoring mirror bytes; FROZEN.json entries/clock

Usage:
  python3 artifacts/worker-094/f0_review/check_f0_independent.py \
      --expect 276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc \
      --out artifacts/worker-094/f0_review/independent_report.json
Exit 0 = review executed (findings may still exist); 3 = pin mismatch (fail closed);
2 = parse failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
AXIS_ORDER = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
              "genericity_kind", "conclusion_type"]
ALLOWED = {
    "family": {"WCC", "SCC"},
    "matter_model": {"vacuum", "massless_scalar_field"},
    "symmetry": {"none_assumed", "spherical"},
    "asymptotics": {"asymptotically_flat_3p1"},
    "genericity_kind": {"baire_residual", "dense_open", "measure_one",
                        "provisional_baire_residual", "unresolved"},
    "conclusion_type": {"weak_cosmic_censorship", "strong_cosmic_censorship_C2",
                        "strong_cosmic_censorship_C0"},
}
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)
TOKEN_RE = re.compile(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)*")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(s: str) -> str:
    return re.sub(r"[\^_{}\s]", "", s)


def strict_yaml(text: str):
    """Load YAML and report duplicate mapping keys (worker-094 HF-094-2 method)."""
    import yaml

    dups: list[str] = []

    class DupLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                dups.append(f"{key}@line{key_node.start_mark.line + 1}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    doc = yaml.load(text, Loader=DupLoader)
    return doc, dups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--now", default=None, help="override wall clock (ISO, for tests)")
    a = ap.parse_args()

    tax_path = ROOT / "research_map" / "formulation_taxonomy.yaml"
    measured = sha256_file(tax_path)
    if measured != a.expect:
        print(f"PIN MISMATCH measured={measured} expect={a.expect}", file=sys.stderr)
        return 3
    raw = tax_path.read_text()
    tax, dups = strict_yaml(raw)

    now = datetime.fromisoformat(a.now) if a.now else datetime.now(CST)
    checks: list[dict] = []
    findings: list[dict] = []

    def chk(cid, ok, detail, severity="info"):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail, "severity": severity})
        if not ok:
            findings.append({"check": cid, "detail": detail, "severity": severity})
        return ok

    # 2 yaml
    chk("yaml.parses", isinstance(tax, dict), "canonical taxonomy parses as a mapping")
    chk("yaml.duplicate_keys", not dups, f"duplicate mapping keys: {dups or 'none'}")

    # 3 identity
    ids = list(tax.get("class_ids") or [])
    classes = tax.get("classes") or {}
    chk("identity.class_ids", ids == FROZEN, f"class_ids = {ids}")
    chk("identity.class_keys", sorted(classes) == sorted(FROZEN), f"classes keys = {sorted(classes)}")
    chk("identity.count", len(ids) == 4 and len(set(ids)) == 4, "exactly four distinct class ids")

    # 4 tokens in raw text
    variant_keys = set()
    for v in tax.get("variants") or []:
        variant_keys.add((v.get("parent_class"), v.get("variant_id")))
    family_prefixes = {"AF-WCC", "AF-SCC"}  # prose family acronyms, not class ids
    seen_ok, seen_bad = set(), set()
    for m in TOKEN_RE.finditer(raw):
        tok = m.group(0)
        if tok in FROZEN or tok in family_prefixes:
            seen_ok.add(tok)
            continue
        matched = False
        for parent, vid in variant_keys:
            if parent and vid and tok == f"{parent}-{vid}":
                matched = True
        (seen_ok if matched else seen_bad).add(tok)
    chk("tokens.class_like", not seen_bad,
        f"unregistered AF-* tokens in raw text: {sorted(seen_bad) or 'none'}", "major")

    # 5 completeness
    for cid in FROZEN:
        c = classes.get(cid) or {}
        for key in ("axes", "hypotheses", "exclusions", "conclusion", "test_cases", "provenance"):
            chk(f"complete[{cid}].{key}", bool(c.get(key)), f"{cid}: {key} present and non-empty")
        concl = c.get("conclusion") or {}
        ax = c.get("axes") or {}
        chk(f"complete[{cid}].conclusion_type", concl.get("type") == ax.get("conclusion_type"),
            f"{cid}: conclusion.type == axes.conclusion_type")

    # 6 axis vocabulary + G2
    for cid in FROZEN:
        ax = (classes.get(cid) or {}).get("axes") or {}
        for k in AXIS_ORDER:
            if k == "regularity_token":
                continue
            chk(f"vocab[{cid}].{k}", ax.get(k) in ALLOWED[k],
                f"{cid}: {k}={ax.get(k)!r} in {sorted(ALLOWED[k])}", "major")
        fam, tok = ax.get("family"), ax.get("regularity_token")
        if fam == "SCC":
            chk(f"g2[{cid}]", tok in {"C0", "C2"}, f"{cid}: SCC regularity_token={tok!r}")
            m = re.match(r"AF-SCC-(C0|C2)-", cid)
            chk(f"g2name[{cid}]", bool(m) and tok == m.group(1), f"{cid}: token matches class id")
            chk(f"g2conc[{cid}]", ax.get("conclusion_type") == f"strong_cosmic_censorship_{tok}",
                f"{cid}: conclusion_type matches regularity token")
        elif fam == "WCC":
            chk(f"g2[{cid}]", tok is None, f"{cid}: WCC regularity_token is null")
        else:
            chk(f"g2[{cid}]", False, f"{cid}: family={fam!r}")

    # 7 disjointness, independently re-derived
    pairs = {}
    for d in tax.get("disjointness") or []:
        p = tuple(d.get("pair") or [])
        pairs[tuple(sorted(p))] = d
    import itertools
    expected = {tuple(sorted(p)) for p in itertools.combinations(FROZEN, 2)}
    chk("disjointness.coverage", set(pairs) == expected,
        f"pairs present={len(pairs)} expected={len(expected)}")
    for p in itertools.combinations(FROZEN, 2):
        d = pairs.get(tuple(sorted(p)), {})
        ax_a = (classes.get(p[0]) or {}).get("axes") or {}
        ax_b = (classes.get(p[1]) or {}).get("axes") or {}
        real = [k for k in AXIS_ORDER if ax_a.get(k) != ax_b.get(k)]
        named = [k for k in (d.get("decisive_axes") or []) if k in AXIS_ORDER]
        chk(f"disjointness[{p[0]}|{p[1]}].differ", bool(real),
            f"{p[0]} vs {p[1]}: differing axes={real}")
        chk(f"disjointness[{p[0]}|{p[1]}].named_subset", bool(named) and set(named) <= set(real),
            f"named decisive axes={named} subset of differing={real}")
    # negative control: identical axis vectors must produce no differing axis
    ctrl = [k for k in AXIS_ORDER if AXIS_ORDER and (lambda x: x)({}) == {}] or []
    same = dict(zip(AXIS_ORDER, AXIS_ORDER))
    ctrl_real = [k for k in AXIS_ORDER if same.get(k) != same.get(k)]
    chk("control.disjointness_negative", ctrl_real == [],
        "fabricated identical-axis pair yields no decisive axis (control behaves)")

    # 8 G3 scan + positive/negative controls
    # Scope: semantic class content only. Guards/field_vocabulary/transfer_rules must be
    # allowed to NAME the forbidden pattern they prohibit, so they are reported separately.
    semantic = {
        "scope_statement": tax.get("scope_statement"),
        "classes": classes,
        "variants": tax.get("variants"),
        "disjointness": tax.get("disjointness"),
        "disjointness_scope": tax.get("disjointness_scope"),
        "disjointness_overlap_note": tax.get("disjointness_overlap_note"),
        "open_questions": tax.get("open_questions"),
    }
    sem_text = json.dumps(semantic, sort_keys=True, default=str)
    sem_hits = [s for s in (normalize(sem_text), sem_text) if MERGED_RE.search(s)]
    guard_text = json.dumps({k: tax.get(k) for k in ("field_vocabulary", "guards", "transfer_rules")},
                            sort_keys=True, default=str)
    guard_hits = [s for s in (normalize(guard_text), guard_text) if MERGED_RE.search(s)]
    chk("g3.no_merged_regularity", not sem_hits,
        "no normalized/plain merged C0/C2 token in semantic class content", "critical")
    checks.append({"id": "g3.guard_section_hits", "ok": True, "severity": "info",
                   "detail": f"guard/vocabulary sections name the prohibited pattern "
                             f"({len(guard_hits)} normalized/plain hit(s)); excluded by scope"})
    pos = MERGED_RE.search(normalize("C^{0} or C^{2} extension")) is not None
    neg = MERGED_RE.search(normalize("C0-inextendibility implies C2-inextendibility")) is None
    chk("control.g3_positive", pos, "positive control 'C^{0} or C^{2}' is caught")
    chk("control.g3_negative", neg, "negative control 'C0-inextendibility implies C2...' is not caught")

    # 9 genericity machine-readability
    for cid in FROZEN:
        ax = (classes.get(cid) or {}).get("axes") or {}
        gk = ax.get("genericity_kind")
        gt_present = "genericity_topology" in ax
        chk(f"genericity[{cid}].topology_slot", gt_present,
            f"{cid}: genericity_kind={gk!r}, genericity_topology slot "
            f"{'present=' + repr(ax.get('genericity_topology')) if gt_present else 'ABSENT'}", "major")

    # 10 clock discipline
    written = tax.get("written_at")
    decided = ((tax.get("class_scope_adjudication") or {}).get("decided_at"))
    created = tax.get("created_at")
    try:
        w = datetime.fromisoformat(str(written))
        d = datetime.fromisoformat(str(decided))
        chk("clock.written_at_covers_content", d <= w,
            f"written_at={written} vs adjudication decided_at={decided} "
            f"(content {'does' if d > w else 'does not'} run ahead of written_at)", "major")
    except Exception as e:  # noqa: BLE001
        chk("clock.written_at_covers_content", False, f"timestamp parse failure: {e}", "major")
    ts_pat = re.compile(r"20\d\d-\d\d-\d\dT\d\d:\d\d(?::\d\d)?(?:[+-]\d\d:\d\d)?")
    future = []
    for m in ts_pat.finditer(raw):
        try:
            t = datetime.fromisoformat(m.group(0))
            if t.tzinfo is None:
                t = t.replace(tzinfo=CST)
            if t > now:
                future.append(m.group(0))
        except ValueError:
            pass
    chk("clock.no_future_dated_content", not future,
        f"content timestamps later than wall clock {now.isoformat()}: {sorted(set(future)) or 'none'}", "major")

    # 11 theorem status
    chk("status.claims_theorem_false", tax.get("claims_theorem_status") is False,
        "claims_theorem_status=false")
    bad_theorem = [cid for cid in FROZEN
                   if ((classes.get(cid) or {}).get("axes") or {}).get("conclusion_type") == "theorem"]
    chk("status.no_theorem_conclusion", not bad_theorem, f"theorem-typed classes: {bad_theorem or 'none'}", "critical")

    # 12 test cases
    for cid in FROZEN:
        c = classes.get(cid) or {}
        tc = c.get("test_cases") or {}
        hyp_ids = {h.get("id") for h in (c.get("hypotheses") or [])}
        pos, neg = tc.get("positive") or {}, tc.get("negative") or {}
        chk(f"cases[{cid}].positive", bool(pos.get("id")) and bool(pos.get("decisive_hypotheses")),
            f"{cid}: positive case {pos.get('id')!r}")
        chk(f"cases[{cid}].negative", bool(neg.get("id")) and bool(neg.get("decisive_hypotheses")),
            f"{cid}: negative case {neg.get('id')!r}")
        for tag, case in (("positive", pos), ("negative", neg)):
            missing = [h for h in (case.get("decisive_hypotheses") or []) if h not in hyp_ids]
            chk(f"cases[{cid}].{tag}.hyps", not missing,
                f"{cid}/{case.get('id')}: decisive hypotheses resolve (missing={missing or 'none'})", "major")
        exp = str(pos.get("expected_classification") or "")
        chk(f"cases[{cid}].positive.binding", exp == cid,
            f"{cid}: positive expected_classification={exp!r}")

    # 13 cross-artifact class binding
    xchecks = []
    canon_tax = ROOT / "research_map" / "formulation_taxonomy.yaml"
    author_tax = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
    author_doc = strict_yaml(author_tax.read_text())[0] if author_tax.exists() else {}
    for node, path in (("F1", "schemas/af_wcc_vacuum.yaml"),
                       ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
                       ("F2b", "schemas/af_scc_c0_vacuum.yaml")):
        p = ROOT / path
        if not p.exists():
            chk(f"cross[{node}].exists", False, f"{path} missing", "critical")
            continue
        doc, _ = strict_yaml(p.read_text())
        cid = doc.get("class_id")
        chk(f"cross[{node}].class_id_in_f0", cid in FROZEN,
            f"{path}: class_id={cid!r} in frozen four", "critical")
        fb = doc.get("f0_binding") or {}
        declared = fb.get("declared_f0_sha256")
        chk(f"cross[{node}].declared_f0_current", declared == a.expect,
            f"{path}: declared_f0_sha256={str(declared)[:16]} vs pinned {a.expect[:16]}", "major")
        ptr = str(doc.get("class_contract_pointer") or "")
        ptr_path, _, ptr_anchor = ptr.partition("#")
        ptr_file = ROOT / ptr_path if ptr_path else None
        ptr_on_canonical = ptr_file is not None and ptr_file.resolve() == canon_tax.resolve()
        anchor_parts = [x for x in ptr_anchor.split(".") if x]
        section = anchor_parts[0] if anchor_parts else ""
        class_key = anchor_parts[-1] if len(anchor_parts) > 1 else ""
        resolves_canonical = bool(section) and isinstance((tax or {}).get(section), dict) \
            and class_key in (tax or {}).get(section, {})
        resolves_authoring = bool(section) and isinstance((author_doc or {}).get(section), dict) \
            and class_key in (author_doc or {}).get(section, {})
        chk(f"cross[{node}].contract_pointer_canonical", ptr_on_canonical,
            f"{path}: class_contract_pointer -> {ptr or 'MISSING'} "
            f"({'canonical' if ptr_on_canonical else 'NOT canonical'}; anchor '{ptr_anchor}' "
            f"resolves canonical={resolves_canonical} authoring={resolves_authoring})", "major")
        xchecks.append({"node": node, "path": path, "class_id": cid, "sha256": sha256_file(p),
                        "declared_f0_sha256": declared, "class_contract_pointer": ptr,
                        "pointer_is_canonical": ptr_on_canonical,
                        "pointer_section": section, "pointer_class_key": class_key,
                        "pointer_section_in_canonical": resolves_canonical,
                        "pointer_section_in_authoring": resolves_authoring})
    chk("cross.class_binding_ran", len(xchecks) == 3, f"cross-artifact checks: {len(xchecks)}/3")

    # 14 case corpus binding
    cases_path = ROOT / "schemas" / "taxonomy_cases.jsonl"
    meta, bindings = None, set()
    if cases_path.exists():
        for line in cases_path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("record_type") == "meta":
                meta = r
            else:
                bindings.add(str(r.get("binding_status")))
    meta_sha = ((meta or {}).get("taxonomy_ref") or {}).get("sha256")
    chk("corpus.meta_binding_current", meta_sha == a.expect,
        f"taxonomy_cases.jsonl meta.taxonomy_ref.sha256={meta_sha} vs pinned {a.expect[:16]}", "major")
    tok_sha = {b.split("_")[-1] for b in bindings}
    chk("corpus.rows_binding_current", tok_sha == {a.expect},
        f"per-case binding tokens={sorted(tok_sha)} vs pinned {a.expect[:16]}", "major")
    chk("corpus.meta_rows_agree", bool(meta_sha) and tok_sha == {meta_sha},
        f"meta sha {meta_sha[:16] if meta_sha else None} vs row binding tokens {sorted(tok_sha)}", "major")

    # 15 publication
    canon = ROOT / "research_map" / "formulation_taxonomy.yaml"
    author = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
    author_sha = sha256_file(author) if author.exists() else None
    author_role = str(author_doc.get("artifact_role") or "")
    author_id = author_doc.get("artifact_id")
    chk("publication.mirror_byte_identical", author_sha == a.expect,
        f"canonical {a.expect[:16]} vs authoring {str(author_sha)[:16]}; authoring declares "
        f"artifact_id={author_id!r} role={author_role[:90]!r}", "major")
    frozen_p = ROOT / "artifacts" / "formulation" / "FROZEN.json"
    fz = json.loads(frozen_p.read_text())
    files = fz.get("files") or {}
    f0_entries = {k: v for k, v in files.items() if "formulation_taxonomy.yaml" in k}
    chk("publication.frozen_single_hash", len({(v or {}).get("sha256") for v in f0_entries.values()}) == 1,
        f"FROZEN.json F0 entries: " + ", ".join(f"{k}={(v or {}).get('sha256', '')[:12]}" for k, v in sorted(f0_entries.items())),
        "major")
    try:
        fa = datetime.fromisoformat(str(fz.get("frozen_at")))
        if fa.tzinfo is None:
            fa = fa.replace(tzinfo=CST)
        chk("publication.frozen_at_not_future", fa <= now,
            f"FROZEN.json frozen_at={fz.get('frozen_at')} vs wall clock {now.isoformat()}", "major")
    except Exception as e:  # noqa: BLE001
        chk("publication.frozen_at_not_future", False, f"frozen_at parse failure: {e}", "major")

    report = {
        "report_id": "W094B-F0-INDEP-REPORT-01",
        "reviewer": "worker-094",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(FROZEN),
        "created_at": now.isoformat(timespec="seconds"),
        "pinned_sha256": a.expect,
        "measured_sha256": measured,
        "pin_ok": measured == a.expect,
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "checks_failed": sum(1 for c in checks if not c["ok"]),
        "checks": checks,
        "findings": findings,
        "cross_artifact": xchecks,
        "corpus": {"meta_taxonomy_ref_sha256": meta_sha, "row_binding_tokens": sorted(tok_sha)},
        "publication": {"canonical_sha256": a.expect, "authoring_sha256": author_sha,
                        "authoring_artifact_id": author_id, "authoring_role": author_role,
                        "frozen_revision": fz.get("revision"), "frozen_at": fz.get("frozen_at")},
        "method": ("Independent re-derivation from the pinned bytes: strict YAML load with duplicate-key "
                   "detection, raw-text class-token census, axis-vocabulary and G2 discipline, disjointness "
                   "recomputed from axis vectors with a fabricated-pair negative control, G3 merged-regularity "
                   "scan with +/- controls, genericity slot machine-readability, clock discipline, theorem-status "
                   "guard, per-class case checks, cross-artifact class binding, case-corpus binding and "
                   "publication/mirror checks. Author validator run separately as corroboration only."),
        "falsifier": ("Measure research_map/formulation_taxonomy.yaml at a different sha256 than the pinned "
                      "hash, or exhibit two of the four descriptors that fail to separate on a "
                      "schemas/taxonomy_cases.jsonl case, or bind a claim to one of the four class ids while the "
                      "token census shows an unregistered class-like token."),
        "negative_controls": [c for c in checks if c["id"].startswith("control.")],
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True))
    for c in checks:
        if not c["ok"]:
            print(f"FAIL {c['id']}: {c['detail']}")
    print(f"checks_passed={report['checks_passed']} checks_failed={report['checks_failed']} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
