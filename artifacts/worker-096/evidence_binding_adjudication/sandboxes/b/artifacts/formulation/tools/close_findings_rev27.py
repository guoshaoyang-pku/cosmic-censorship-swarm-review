#!/usr/bin/env python3
"""rev27 closure of the hash-bound findings in astra-life03-close-findings.

Findings addressed (each is hash-bound to a review at a pinned sha256):
  (a) duplicate top-level YAML keys `revised_at` x7/x8 and `revised_at_unused` x1-2, and
      future-dated machine-readable timestamps  -> F1-review-090 HF, F1-review-094 HF-094-2,
      F1-review-19 F-5, F2b-review-034 F-034-3, F1-review-lead-audit-r2 BLOCKING(clock)
  (b) class_contract_pointer targets artifacts/formulation/** and its fragment does not resolve
      in the canonical taxonomy -> F1-review-090 HF, F2b-review-034 HF-034-2,
      F1-review-19 F-3, F1-review-lead-audit-r2 BLOCKING(binding)
  (c) undefined AF_{I+} in conclusion.statement_formal
      -> F1-review-090 HF, F1-review-19 HF-06
  (d) quantifier-domain defects:
      d1 whole-curve vs tail visibility clause -> F1-review-19 HF-06 (critical),
         independently confirmed by worker-037 W037V2-F1 and worker-078 W078-F1-QUANT-ADJ-01
      d2 D0 mixes pair-indexed Sobolev data with the smooth-with-decay default while the binder
         is (s,delta) -> F1-review-19 F-2 (major), F2b-review-034 HF-034-1
  (e) evidence not hash-bound: taxonomy_consistency.json carries no tree hashes
      -> F1-review-090 F090-05, F1-review-19 F-4

Plus the F0-side findings in F0-review-lead-audit-r2:
  (f) the demoted set-based (variant SET) visibility wording survives in the
      AF-WCC-SCALAR-SPH conclusion -> B-16F0-1 / W082-F-01
  (g) resolved_divergences[D3] claims the comeager quantifier is standardised for each class
      but was not discharged for AF-WCC-SCALAR-SPH -> B-16F0-2 / W082-F-02
  (h) C2/C0 provenance.schema_owner pointers name a legacy non-class artifact and the
      superseded node name F2 -> B-16F0-3

NOT changed here (recorded as a disposition, not looped on):
  the F0 dual-tree "divergence" reported by research_map/audit_evidence.py::MIRRORS. The two
  paths are DIFFERENT logical artifacts (declared taxonomy vs class-contract supplement), not
  two trees of one artifact; forcing byte-identity would be destructive. Byte-level evidence is
  re-measured and recorded in artifacts/formulation/evidence/f0_mirror_disposition.json.

Usage:
  python3 artifacts/formulation/tools/close_findings_rev27.py --dry-run
  python3 artifacts/formulation/tools/close_findings_rev27.py --apply --at 2026-09-12T01:05:00+08:00
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
SCHEMAS = {
    "AF-WCC-VAC-GEN": (
        ROOT / "schemas/af_wcc_vacuum.yaml",
        ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    ),
    "AF-SCC-C2-VAC-GEN": (
        ROOT / "schemas/af_scc_c2_vacuum.yaml",
        ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    ),
    "AF-SCC-C0-VAC-GEN": (
        ROOT / "schemas/af_scc_c0_vacuum.yaml",
        ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    ),
}


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def sub_once(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    n = text.count(old)
    if n != count:
        raise SystemExit(
            f"ASSERT FAIL [{label}]: expected {count} occurrence(s), found {n}\n  pattern: {old[:200]!r}"
        )
    return text.replace(old, new)


# --------------------------------------------------------------------------------------
# F0: declared taxonomy (canonical). The authoring supplement is a DIFFERENT artifact and
# is deliberately not touched.
# --------------------------------------------------------------------------------------
F0_SET_BASED_TEXT = """      text: >-
        For generic data in the class, the MGHD admits I+ and every future-inextendible causal
        geodesic contained in J-(I+) is complete; equivalently, the singularities that form are
        hidden behind an event horizon and no singularity is visible from I+."""

F0_TAIL_TEXT = """      text: >-
        For a comeager set G of data in the class, chosen before and independently of the data,
        every member's MGHD admits I+ and there is NO visible singularity from I+: for every
        future-inextendible causal geodesic gamma of finite affine length, for every q in I+ and
        every t0 in [0,T), the tail gamma([t0,T)) is not contained in J^-(q) intersect M. The
        singularities that form are hidden behind an event horizon and no singularity is visible
        from I+. [rev5: D1/D3 discharge for this class. The superseded set-based wording
        contained-in-J-(I+) is the variant SET predicate and is NOT this class's predicate.]"""


def repair_f0(text: str, now: str) -> str:
    text = sub_once(text, F0_SET_BASED_TEXT, F0_TAIL_TEXT, "F0 scalar-sph conclusion")
    text = sub_once(
        text,
        '      resolution: "the comeager quantifier is now stated explicitly in each class conclusion text and bound before the data"',
        '      resolution: "the comeager quantifier is now stated explicitly in each class conclusion text and bound before the data; confirmed discharged for ALL FOUR classes, including AF-WCC-SCALAR-SPH, whose conclusion text carried the demoted set-based wording until rev5 (worker-16 B-16F0-2 / worker-082 W082-F-02)"',
        "F0 D3 resolution",
    )
    text = sub_once(
        text,
        '      schema_owner: "F2 (artifact schemas/af_scc_regularities.yaml, section C2)"',
        '      schema_owner: "F2a (artifact schemas/af_scc_c2_vacuum.yaml)"',
        "F0 C2 schema_owner",
    )
    text = sub_once(
        text,
        '      schema_owner: "F2 (artifact schemas/af_scc_regularities.yaml, section C0)"',
        '      schema_owner: "F2b (artifact schemas/af_scc_c0_vacuum.yaml)"',
        "F0 C0 schema_owner",
    )
    text = sub_once(text, 'written_at: "2026-09-11T23:34:00+08:00"', f'written_at: "{now}"', "F0 written_at")
    text = sub_once(text, "revision: 4\n", "revision: 5\n", "F0 revision")
    text = sub_once(
        text,
        "revision_note_rev4: >-\n",
        "revision_note_rev5: >-\n"
        "  rev5 closes the content-bearing F0-review-lead-audit-r2 blocking findings: (f) the\n"
        "  AF-WCC-SCALAR-SPH conclusion no longer carries the demoted set-based visibility reading;\n"
        "  it now states the single-q tail predicate with the comeager set bound before the data\n"
        "  (worker-16 B-16F0-1 / worker-082 W082-F-01); (g) the D3 resolution is confirmed\n"
        "  discharged for the scalar class (B-16F0-2 / W082-F-02); (h) C2/C0 provenance.schema_owner\n"
        "  pointers now name the canonical class schemas and the F2a/F2b node ids instead of the\n"
        "  legacy schemas/af_scc_regularities.yaml and the superseded node name F2 (B-16F0-3).\n"
        "  No class id added; class_ids unchanged.\n"
        "revision_note_rev4: >-\n",
        "F0 rev5 note",
    )
    return text


# --------------------------------------------------------------------------------------
# Schema header repair: collapse duplicate revised_at / revised_at_unused into one
# revised_at plus a machine-readable revision_history.
# --------------------------------------------------------------------------------------
HEADER_START = "revised_at:"
HEADER_END = "timestamp_provenance:"


def repair_header(text: str, now: str, rev_delta: str, next_rev: int) -> str:
    start = text.index(HEADER_START)
    end = text.index(HEADER_END, start)
    block = text[start:end]
    entries = []
    pending = []
    for line in block.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            pending.append(s.lstrip("# ").strip())
            continue
        m = re.match(r"^(revised_at|revised_at_unused):\s*\"?([^\"]+?)\"?\s*$", s)
        if not m:
            raise SystemExit(f"ASSERT FAIL [header parse]: unexpected line {s!r}")
        entries.append({"key": m.group(1), "at": m.group(2), "notes": pending})
        pending = []
    if pending:
        entries[-1]["notes"].extend(pending)
    if not entries:
        raise SystemExit("ASSERT FAIL [header]: no revised_at entries found")

    lines = [f'revised_at: "{now}"', "revision_history:"]
    for i, e in enumerate(entries, start=1):
        unused = "true" if e["key"] == "revised_at_unused" else "false"
        lines.append(
            f"  - {{index: {i}, at: {json.dumps(e['at'])}, unused: {unused}, notes: {json.dumps(e['notes'])} }}"
        )
    lines.append(
        f"  - {{index: {len(entries)+1}, at: {json.dumps(now)}, unused: false, notes: {json.dumps([rev_delta])} }}"
    )
    text = text[:start] + "\n".join(lines) + "\n" + text[end:]
    text = sub_once(text, f"revision: {next_rev - 1}\n", f"revision: {next_rev}\n", "schema revision bump")
    return text


# --------------------------------------------------------------------------------------
# Common quantifier-domain repair: D0 becomes a tagged regularity index.
# --------------------------------------------------------------------------------------
D0_LONG_OLD = (
    '      definition: "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1), or the '
    "smooth-with-decay default; the class is fixed at these values and does not range over 'suitable' regularity\""
)
D0_SHORT_OLD = (
    '      definition: "admissible regularity pairs: Sobolev variant s > 5/2 and delta in (1/2,1), or the '
    'smooth-with-decay default"'
)
D0_NEW = (
    '      definition: "admissible regularity indices, a tagged disjoint union: r = smooth (the smooth-with-decay '
    "default) or r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1). X^r_vac(AF) is the corresponding "
    "one-ended AF vacuum constraint manifold (Frechet for r = smooth; weighted Sobolev product "
    "H^s_delta x H^{s-1}_{delta+1} for r = (sobolev,s,delta)). The index r ranges over exactly D0, so the "
    "smooth branch is no longer typed as a pair and the class does not range over 'suitable' regularity. "
    '[rev12 F-2 well-typedness repair: F1-review-19 F-2, F2b-review-034 HF-034-1]"'
)

COMMON = [
    ("forall (s,delta) in D0", "forall r in D0", 2),
    (
        "exists G_{s,delta} subset X^{s,delta}_vac(AF) with G_{s,delta} comeager",
        "exists G_r subset X^r_vac(AF) with G_r comeager",
        1,
    ),
    ("forall (Sigma,h,K) in G_{s,delta}", "forall (Sigma,h,K) in G_r", 1),
    ('binder: "(s,delta)", domain_id: D0', 'binder: "r", domain_id: D0', 1),
    ('binder: "G_{s,delta}", domain_id: D1', 'binder: "G_r", domain_id: D1', 1),
    ("there exists (s,delta) in D0", "there exists r in D0", 1),
    ("for every comeager G subset X^{s,delta}_vac(AF)", "for every comeager G_r subset X^r_vac(AF)", 1),
    ("(Sigma,h,K) in G whose", "(Sigma,h,K) in G_r whose", 1),
    ('"{ (s,delta) in D0 :', '"{ r in D0 :', 1),
]

D1_LONG_OLD = (
    'definition: "comeager (residual) subsets of X^r_vac(AF): G = intersection over n >= 1 of U_n with each '
    'U_n open and dense in the named topology; equivalently X minus G is meager"'
)
D1_LONG_NEW = (
    'definition: "comeager (residual) subsets of X^r_vac(AF): G_r = intersection over n >= 1 of U_n with each '
    'U_n open and dense in the named topology; equivalently X^r_vac(AF) minus G_r is meager"'
)
D1_SHORT_OLD = (
    'definition: "comeager (residual) subsets of X^r_vac(AF) in the named topology; complement meager"'
)
D1_SHORT_NEW = (
    'definition: "comeager (residual) subsets of X^r_vac(AF) in the named topology; X^r_vac(AF) minus G_r is meager"'
)


def repair_common_quantifiers(text: str, class_id: str) -> str:
    for old, new, n in COMMON:
        text = sub_once(text, old, new, f"{class_id} common:{old[:40]}", count=n)
    text = text.replace("X^{s,delta}_vac(AF)", "X^r_vac(AF)")
    text = text.replace("G_{s,delta}", "G_r")
    if class_id == "AF-WCC-VAC-GEN":
        text = sub_once(text, D1_LONG_OLD, D1_LONG_NEW, "F1 D1")
        text = sub_once(
            text,
            "with each U_n open and dense in X^r_vac(AF); equivalently the complement is meager (first category); G is non-empty because X_vac is Baire",
            "with each U_n open and dense in X^r_vac(AF); equivalently the complement is meager (first category); G_r is non-empty because X_vac is Baire",
            "F1 generic_set G_r",
        )
    else:
        text = sub_once(text, D1_SHORT_OLD, D1_SHORT_NEW, f"{class_id} D1")
    if "X^{s,delta}_vac" in text or "G_{s,delta}" in text:
        raise SystemExit("ASSERT FAIL: residual pair-indexed tokens remain")
    return text


def repair_f1_specific(text: str) -> str:
    text = sub_once(
        text,
        "    not exists q in I+ with gamma subset J^-(q) intersect M.",
        "    not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
        "F1 tail formal",
    )
    text = sub_once(
        text,
        '    - {kind: not_exists, binder: "q", domain_id: D5}',
        '    - {kind: not_exists, binder: "(q,t0)", domain_id: D5}',
        "F1 D5 binder",
    )
    text = sub_once(
        text,
        '      definition: "points q of I+ such that gamma([0,T)) is contained in the causal past J^-(q) intersected with M"',
        '      definition: "pairs (q,t0) with q a point of I+ and t0 in [0,T) such that the tail gamma([t0,T)) is '
        "contained in the causal past J^-(q) intersected with M. Whole-curve containment gamma([0,T)) subset J^-(q) "
        "is strictly STRONGER and is NOT the predicate of this class [rev12: F1-review-19 HF-06 critical, "
        'independently confirmed by worker-037 W037V2-F1 and worker-078 W078-F1-QUANT-ADJ-01]"',
        "F1 D5 definition",
    )
    text = sub_once(
        text,
        '  definition: "conformal completion of (M,g) at future null infinity: an embedding into (Mtilde,gtilde) with Omega > 0 on M, Omega = 0 and dOmega != 0 on I+, gtilde = Omega^2 g of class C^k Lorentzian on Mtilde = M union I+, I+ a null hypersurface diffeomorphic to R x S^2, with the conformal Einstein equations holding near I+ to the order required by k"\n',
        '  definition: "conformal completion of (M,g) at future null infinity: an embedding into (Mtilde,gtilde) with Omega > 0 on M, Omega = 0 and dOmega != 0 on I+, gtilde = Omega^2 g of class C^k Lorentzian on Mtilde = M union I+, I+ a null hypersurface diffeomorphic to R x S^2, with the conformal Einstein equations holding near I+ to the order required by k"\n'
        '  predicate_abbreviation: "AF_{I+}(M) abbreviates the existence predicate of i_plus.definition: M admits a '
        "conformal completion (Mtilde,gtilde,Omega) at future null infinity with the regularity assumed in "
        "i_plus_regularity. It introduces no assumption beyond that leaf and is the only reading of the symbol in "
        "this schema. [rev12: F1-review-090 HF and F1-review-19 HF-06 - the symbol was previously undefined; "
        'grep AF_{I+} matched conclusion.statement_formal only]"\n',
        "F1 AF_{I+} definition",
    )
    text = sub_once(
        text,
        "    future-inextendible causal geodesic of finite affine length is visible from I+.",
        "    future-inextendible causal geodesic of finite affine length has a tail visible from I+.",
        "F1 negation prose",
    )
    return text


def class_id_of(text: str) -> str:
    m = re.search(r"^class_id:\s*(\S+)\s*$", text, re.M)
    if not m:
        raise SystemExit("ASSERT FAIL: class_id not found")
    return m.group(1)


def repair_f0_binding(text: str, class_id: str, f0_sha: str, consistency_sha: str, now: str) -> str:
    old = re.search(r"f0_binding: \{declared_f0_artifact: [^}]*\}", text)
    if not old:
        raise SystemExit("ASSERT FAIL: f0_binding line not found")
    new = (
        "f0_binding: {declared_f0_artifact: research_map/formulation_taxonomy.yaml, declared_f0_sha256: \""
        + f0_sha
        + '", class_contract_supplement: artifacts/formulation/formulation_taxonomy.yaml, '
        'class_contract_supplement_pointer: "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.'
        + class_id
        + '", consistency_evidence: artifacts/formulation/evidence/taxonomy_consistency.json, '
        'consistency_evidence_sha256: "'
        + consistency_sha
        + '", checked_at: "'
        + now
        + '", rule: "if the declared F0 artifact changes hash, this binding must be refreshed and the consistency '
        'check re-run before any gate verdict", binding_note: "rev12: refreshed to the rev5 declared-F0 hash after '
        "the F0 scalar-class conclusion repair; class_contract_pointer resolves in the canonical taxonomy (key "
        "`classes`) and the supplement pointer is a separately named field, so the declared taxonomy and the "
        'class-contract supplement are never conflated"}'
    )
    return text.replace(old.group(0), new)


def repair_pointer(text: str, class_id: str) -> str:
    old = f"class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.{class_id}\n"
    new = (
        f"class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.{class_id}\n"
        f"class_contract_supplement_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.{class_id}\n"
    )
    return sub_once(text, old, new, f"pointer {class_id}")


REV_DELTA = (
    "rev12 delta: closes the hash-bound findings of astra-life03-close-findings - duplicate revised_at keys "
    "collapsed into revision_history, revised_at stamped with wall-clock, class_contract_pointer repointed at "
    "the canonical taxonomy (key `classes`) with the supplement pointer split into its own field, D0 retyped as "
    "a tagged regularity index `r`, and (F1 only) the visibility clause repaired from whole-curve to the "
    "canonical tail predicate and AF_{I+} defined."
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--at", default=None, help="publish wall-clock, ISO8601 with offset")
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        ap.error("pass --dry-run or --apply")
    now = args.at or dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    report = {"at": now, "phase": "dry-run" if args.dry_run else "apply", "files": {}}

    # 1. F0 canonical declared taxonomy
    f0_text = F0_CANON.read_text()
    f0_new = repair_f0(f0_text, now)
    f0_sha = sha_bytes(f0_new.encode())
    if args.apply:
        F0_CANON.write_text(f0_new)
    report["files"]["research_map/formulation_taxonomy.yaml"] = {
        "sha256": f0_sha,
        "changed": f0_new != f0_text,
        "revision": 5,
    }

    # 2. consistency evidence: hash-bound to the two logical F0 artifacts (no schema dependency)
    cons = json.loads(CONSISTENCY.read_text())
    cons_old = json.dumps(cons, sort_keys=True)
    cons["map_taxonomy_sha256"] = f0_sha
    cons["lead_contract_sha256"] = sha(F0_SUPP)
    cons["binding_rule"] = (
        "map_taxonomy and lead_contract are DIFFERENT logical artifacts: the declared F0 taxonomy "
        "(keys class_ids/classes/transfer_rules) and the class-contract supplement (keys "
        "class_contracts/axis_registry/implication_ledger). They are not mirror trees and are not "
        "required to be byte-identical. [rev12: F1-review-090 F090-05, F1-review-19 F-4]"
    )
    cons["measured_at"] = now
    cons_bytes = (json.dumps(cons, indent=2) + "\n").encode()
    cons_sha = sha_bytes(cons_bytes)
    if args.apply:
        CONSISTENCY.write_bytes(cons_bytes)
    report["files"]["artifacts/formulation/evidence/taxonomy_consistency.json"] = {
        "sha256": cons_sha,
        "changed": json.dumps(cons, sort_keys=True) != cons_old,
    }

    # 3. three class schemas, published byte-identically to canonical + authoring mirror
    for class_id, (canon, author) in SCHEMAS.items():
        text = canon.read_text()
        orig = text
        text = repair_header(text, now, REV_DELTA, 12)
        text = repair_pointer(text, class_id)
        text = sub_once(
            text,
            D0_LONG_OLD if class_id == "AF-WCC-VAC-GEN" else D0_SHORT_OLD,
            D0_NEW,
            f"{class_id} D0",
        )
        text = repair_common_quantifiers(text, class_id)
        if class_id == "AF-WCC-VAC-GEN":
            text = repair_f1_specific(text)
        text = repair_f0_binding(text, class_id, f0_sha, cons_sha, now)
        new_sha = sha_bytes(text.encode())
        if args.apply:
            canon.write_text(text)
            author.write_text(text)
        report["files"][str(canon.relative_to(ROOT))] = {"sha256": new_sha, "changed": text != orig, "revision": 12}
        report["files"][str(author.relative_to(ROOT))] = {"sha256": new_sha, "mirror_identical": True}

    out = ROOT / "artifacts/formulation/evidence/close_findings_rev27_report.json"
    if args.apply:
        out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
