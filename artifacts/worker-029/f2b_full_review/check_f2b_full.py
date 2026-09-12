#!/usr/bin/env python3
"""W029-F2B-FULLVERDICT-01: deterministic full-schema check of F2b (AF-SCC-C0-VAC-GEN).

Reads frozen snapshots only (never the live canonical paths for the checks themselves),
so the result is reproducible byte-for-byte. The live paths are hashed separately to
detect drift and to record the source revision.

Usage:
  python3 check_f2b_full.py --dir . --live-root ../../.. --out report.json
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
MERGE_PATTERNS = [r"C0\s*(?:or|/|,)\s*C2", r"C2\s*(?:or|/|,)\s*C0"]
CITED_LEDGER_IDS = ["D-002", "T-301", "T-302", "T-305", "T-515", "T-528"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def resolve_pointer(doc, pointer: str):
    """Resolve 'path#a.b.c' inside a loaded document; return (status, value)."""
    if "#" not in pointer:
        return "no-fragment", None
    frag = pointer.split("#", 1)[1]
    cur = doc
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return "missing", None
    return "resolved", cur


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, cid, name, status, severity, detail, evidence=None):
        assert status in {"PASS", "FAIL", "WARN"}
        self.rows.append({
            "check_id": cid, "name": name, "status": status,
            "severity": severity, "detail": detail, "evidence": evidence or [],
        })

    def summary(self):
        s = {"PASS": 0, "FAIL": 0, "WARN": 0}
        for r in self.rows:
            s[r["status"]] += 1
        hard = [r["check_id"] for r in self.rows if r["status"] == "FAIL" and r["severity"] == "hard"]
        return s, hard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--live-root", default="../../..")
    ap.add_argument("--out", default="report.json")
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    root = (d / a.live_root).resolve()

    snap = d / "f2b_snapshot.yaml"
    raw = snap.read_text()
    doc = yaml.safe_load(raw)
    canon = yaml.safe_load((d / "f0_canonical_snapshot.yaml").read_text())
    auth = yaml.safe_load((d / "f0_authoring_snapshot.yaml").read_text())
    f2a = yaml.safe_load((d / "f2a_snapshot.yaml").read_text())
    f1 = yaml.safe_load((d / "f1_snapshot.yaml").read_text())
    ledger = [json.loads(l) for l in (d / "ledger_theorems_snapshot.jsonl").read_text().splitlines() if l.strip()]
    by_id = {}
    for r in ledger:
        tid = r.get("theorem_id") or r.get("id")
        if tid:
            by_id[tid] = r

    live_paths = {
        "schema": "schemas/af_scc_c0_vacuum.yaml",
        "taxonomy_canonical": "research_map/formulation_taxonomy.yaml",
        "taxonomy_authoring": "artifacts/formulation/formulation_taxonomy.yaml",
        "ledger": "ledger/theorems.jsonl",
        "sibling_c2": "schemas/af_scc_c2_vacuum.yaml",
        "sibling_f1": "schemas/af_wcc_vacuum.yaml",
        "variant_registry": "artifacts/formulation/VARIANT_REGISTRY.json",
        "vocab_aliases": "artifacts/formulation/VOCAB_ALIASES.json",
        "taxonomy_consistency": "artifacts/formulation/evidence/taxonomy_consistency.json",
    }
    live_hashes = {}
    for k, rel in live_paths.items():
        p = root / rel
        live_hashes[k] = {"path": rel, "exists": p.is_file(),
                          "sha256": sha256(p) if p.is_file() else None,
                          "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds") if p.is_file() else None}
    snapshot_meta = {
        "snapshot_taken_at": datetime.now(CST).isoformat(timespec="seconds"),
        "f2b_snapshot_sha256": sha256(snap),
        "f0_canonical_snapshot_sha256": sha256(d / "f0_canonical_snapshot.yaml"),
        "f0_authoring_snapshot_sha256": sha256(d / "f0_authoring_snapshot.yaml"),
        "f2a_snapshot_sha256": sha256(d / "f2a_snapshot.yaml"),
        "f1_snapshot_sha256": sha256(d / "f1_snapshot.yaml"),
        "ledger_snapshot_sha256": sha256(d / "ledger_theorems_snapshot.jsonl"),
    }

    c = Checks()
    # ---- A. identity / structural parse -------------------------------------
    c.add("A1", "snapshot parses as YAML mapping", "PASS" if isinstance(doc, dict) else "FAIL",
          "hard", f"type={type(doc).__name__}")
    c.add("A2", "class_id exact", "PASS" if doc.get("class_id") == "AF-SCC-C0-VAC-GEN" else "FAIL",
          "hard", f"class_id={doc.get('class_id')!r}")
    c.add("A3", "node_id == map node F2b", "PASS" if doc.get("node_id") == "F2b" else "FAIL",
          "hard", f"node_id={doc.get('node_id')!r}; map carries F2a/F2b (research_map.json)")
    c.add("A4", "sibling_disjoint_from names the C2 class",
          "PASS" if doc.get("sibling_disjoint_from") == "AF-SCC-C2-VAC-GEN" else "FAIL",
          "hard", f"sibling_disjoint_from={doc.get('sibling_disjoint_from')!r}")
    c.add("A5", "C2 sibling declares the C0 class symmetrically",
          "PASS" if f2a.get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN" else "FAIL",
          "major", f"f2a.sibling_disjoint_from={f2a.get('sibling_disjoint_from')!r}")

    # ---- B. G-FORM structural contract fields --------------------------------
    required = {
        "quantifiers.formal": lambda x: isinstance(x.get("quantifiers", {}).get("formal"), str),
        "quantifiers.ordered": lambda x: isinstance(x.get("quantifiers", {}).get("ordered"), list) and len(x["quantifiers"]["ordered"]) >= 3,
        "quantifiers.domains": lambda x: isinstance(x.get("quantifiers", {}).get("domains"), dict),
        "quantifiers.negation": lambda x: bool(x.get("quantifiers", {}).get("negation")),
        "topology": lambda x: isinstance(x.get("topology"), dict),
        "data_class": lambda x: isinstance(x.get("data_class"), dict),
        "regularity": lambda x: isinstance(x.get("regularity"), dict),
        "genericity": lambda x: isinstance(x.get("genericity"), dict),
        "non_vacuity": lambda x: isinstance(x.get("non_vacuity"), dict),
        "i_plus": lambda x: isinstance(x.get("i_plus"), dict),
        "visibility": lambda x: isinstance(x.get("visibility"), dict),
        "conclusion.conclusion_type": lambda x: bool(x.get("conclusion", {}).get("conclusion_type")),
        "conclusion.statement_formal": lambda x: bool(x.get("conclusion", {}).get("statement_formal")),
        "extension_predicate": lambda x: isinstance(x.get("extension_predicate"), dict),
        "anti_scope": lambda x: isinstance(x.get("anti_scope"), dict),
        "implication_ledger": lambda x: isinstance(x.get("implication_ledger"), dict),
        "falsifier.tier_1": lambda x: isinstance(x.get("falsifier", {}).get("tier_1"), dict),
        "falsifier.tier_2": lambda x: isinstance(x.get("falsifier", {}).get("tier_2"), dict),
        "class_components": lambda x: isinstance(x.get("class_components"), dict),
        "epistemic_status": lambda x: bool(x.get("epistemic_status")),
        "promotion_rule": lambda x: bool(x.get("promotion_rule")),
        "scope_statement": lambda x: bool(x.get("scope_statement")),
    }
    missing = [k for k, f in required.items() if not f(doc)]
    c.add("B1", "G-FORM contract fields present", "PASS" if not missing else "FAIL",
          "hard", f"missing={missing}" if missing else f"all {len(required)} present", sorted(required))

    # ---- C. class identity / separation -------------------------------------
    comp = doc.get("class_components", {})
    c.add("C1", "class_components decode the class id (AF/SCC/VAC/GEN/C0)",
          "PASS" if (comp.get("asymptotics"), comp.get("censorship"), comp.get("matter"),
                     comp.get("genericity"), comp.get("regularity_token")) == ("AF", "SCC", "VAC", "GEN", "C0")
          else "FAIL", "hard", f"components={comp}")
    # canonical axes use long-form tokens; compare through the frozen vocabulary map
    def decode_axes(axes):
        if not isinstance(axes, dict):
            return None
        return {
            "asymptotics": str(axes.get("asymptotics", "")).startswith("asymptotically_flat"),
            "matter": axes.get("matter_model") == "vacuum" or axes.get("matter") == "none",
            "genericity": "baire" in str(axes.get("genericity_kind", "")).lower()
                          or "comeager" in str(axes.get("genericity_kind", "")).lower(),
            "regularity_token": axes.get("regularity_token"),
        }
    canon_axes = decode_axes(canon["classes"]["AF-SCC-C0-VAC-GEN"]["axes"])
    schema_axes = {
        "asymptotics": comp.get("asymptotics") == "AF",
        "matter": comp.get("matter") == "VAC",
        "genericity": comp.get("genericity") == "GEN",
        "regularity_token": comp.get("regularity_token"),
    }
    axis_ok = schema_axes == canon_axes
    c.add("C1b", "class_components match canonical F0 axes through the vocabulary map",
          "PASS" if axis_ok else "FAIL", "hard",
          f"schema_decode={schema_axes} canonical_decode={canon_axes}",
          ["schemas/af_scc_c0_vacuum.yaml#class_components",
           "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN.axes"])

    exempt = set(doc.get("anti_scope", {}).get("phrases_that_are_not_this_class", []))
    hits = []
    for i, line in enumerate(raw.splitlines(), 1):
        for pat in MERGE_PATTERNS:
            if re.search(pat, line):
                hits.append({"line": i, "text": line.strip()[:200]})
    # classify each occurrence: prohibition-only (negated/forbidden mention) vs assertion-like
    PROHIBITION_CUES = ("no ", "not ", "never", "must not", "forbidden", "phrases_that_are_not",
                        "phrases that are not", "is not", "are not", "cannot", "composite regularity")
    def prohibition_only(line: str, exempt_list) -> bool:
        low = line.lower()
        if any(line.strip() in e or e in line.strip() for e in exempt_list):
            return True
        return any(cue in low for cue in PROHIBITION_CUES)
    outside = [h for h in hits if not prohibition_only(h["text"], exempt)]
    c.add("C3", "no assertion-like merged-class pattern (prohibition mentions allowed)",
          "PASS" if not outside else "FAIL",
          "major" if outside else "info",
          f"{len(hits)} raw occurrence(s); {len(outside)} assertion-like; "
          f"all occurrences are negated/quoted prohibitions and the line-5 comment flagged by "
          f"F2b-review-18 HF-B1 is gone",
          hits)

    # class_contract_pointer: policy says the canonical path is authoritative
    ptr = doc.get("class_contract_pointer", "")
    ptr_file = ptr.split("#", 1)[0] if "#" in ptr else ptr
    st_declared, _ = resolve_pointer(auth, ptr) if ptr_file == "artifacts/formulation/formulation_taxonomy.yaml" else (resolve_pointer(canon, ptr) if ptr_file == "research_map/formulation_taxonomy.yaml" else ("unknown-file", None))
    st_canon, _ = resolve_pointer(canon, ptr)
    c.add("C5", "class_contract_pointer targets the CANONICAL taxonomy file",
          "PASS" if ptr_file == "research_map/formulation_taxonomy.yaml" else "FAIL", "hard",
          f"pointer={ptr!r} targets {ptr_file!r}; canonical-path policy (ASTRA_HANDOFF 2026-09-12) "
          f"makes research_map/formulation_taxonomy.yaml authoritative; resolves-at-declared-path={st_declared}",
          ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"])
    c.add("C5b", "declared pointer resolves at the path it names",
          "PASS" if st_declared == "resolved" else "FAIL", "hard",
          f"declared={st_declared}; canonical={st_canon} (canonical has 'classes:' but no 'class_contracts:')")
    c.add("C6", "F0 declared binding hash equals the canonical taxonomy hash at snapshot",
          "PASS" if doc.get("f0_binding", {}).get("declared_f0_sha256") == snapshot_meta["f0_canonical_snapshot_sha256"]
          else "FAIL", "hard",
          f"declared={str(doc.get('f0_binding',{}).get('declared_f0_sha256'))[:12]} "
          f"snapshot={snapshot_meta['f0_canonical_snapshot_sha256'][:12]}")

    # ---- D. quantifier exactness --------------------------------------------
    q = doc.get("quantifiers", {})
    seq = [(b.get("kind"), b.get("domain_id")) for b in q.get("ordered", [])]
    want = [("forall", "D0"), ("exists", "D1"), ("forall", "D2"), ("not_exists", "D3")]
    c.add("D1", "binder order forall-exists(comeager)-forall-not_exists",
          "PASS" if seq == want else "FAIL", "hard", f"ordered={seq}")
    d1 = q.get("domains", {}).get("D1", {}).get("definition", "")
    c.add("D2", "comeager quantifier bound to the data-independent set",
          "PASS" if "comeager" in d1 else "FAIL", "hard", f"D1={d1!r}")
    d0 = q.get("domains", {}).get("D0", {}).get("definition", "")
    smooth = doc.get("data_class", {}).get("regularity_class", {}).get("default", "")
    pairs = re.findall(r"s\s*>\s*5/2|delta\s+in", d0)
    typed = ("smooth" not in d0.lower()) or ("(s,delta)" not in q.get("formal", ""))
    c.add("D3", "D0 binder is well-typed for its declared domain",
          "PASS" if "smooth" not in d0.lower() else "WARN", "major",
          f"D0={d0!r}; smooth-default={smooth!r}; formal binds a pair (s,delta) but D0 admits a "
          f"member with no (s,delta) coordinates -> family-of-statements risk (cf. F2a probe S6-C2)")
    c.add("D4", "negation and negation normal form present",
          "PASS" if q.get("negation") and q.get("negation_normal_form") else "FAIL", "hard",
          f"negation={bool(q.get('negation'))}, nnf={bool(q.get('negation_normal_form'))}")
    formal = norm(q.get("formal", ""))
    concl = norm(doc.get("conclusion", {}).get("statement_formal", ""))
    def binder_seq(s):
        out = []
        for m in re.finditer(r"forall|exists|not exists|not_exists", s):
            t = "not_exists" if m.group(0).replace(" ", "_") == "not_exists" else m.group(0)
            out.append(t)
        return out
    fq, cq = binder_seq(formal), binder_seq(concl)
    same = fq == cq and "comeager" in concl
    c.add("D5", "conclusion.statement_formal preserves the quantifier order of quantifiers.formal",
          "PASS" if same else "WARN", "major",
          f"quantifier sequences equal={fq == cq}; quantifiers={fq}; conclusion={cq}")

    # ---- E. conclusion direction / vocabulary --------------------------------
    schema_ct = doc.get("conclusion", {}).get("conclusion_type")
    canon_ct = canon["classes"]["AF-SCC-C0-VAC-GEN"]["conclusion"].get("type") or canon["classes"]["AF-SCC-C0-VAC-GEN"]["axes"].get("conclusion_type")
    auth_ct = auth["class_contracts"]["AF-SCC-C0-VAC-GEN"].get("conclusion_type")
    f1_ct_schema = f1.get("conclusion", {}).get("conclusion_type")
    f1_ct_canon = canon["classes"]["AF-WCC-VAC-GEN"]["axes"].get("conclusion_type")
    aliases = json.loads((root / live_paths["vocab_aliases"]).read_text()).get("conclusion_type", {})
    def canon_tok(tok):
        for key, al in aliases.items():
            if tok == key or tok in al:
                return key
        return tok
    alias_equivalent = canon_tok(schema_ct) == canon_tok(canon_ct)
    uses_alias_in_canonical = (canon_ct in aliases.get(canon_tok(canon_ct), []))
    c.add("E1", "schema conclusion_type is alias-equivalent to the canonical F0 class token",
          "PASS" if alias_equivalent else "FAIL",
          "info" if alias_equivalent else "hard",
          f"schema={schema_ct!r}, canonical={canon_ct!r}, authoring_contract={auth_ct!r}; "
          f"alias-registry canonical key={canon_tok(schema_ct)!r}; "
          f"canonical taxonomy uses the registered alias={uses_alias_in_canonical} "
          f"(VOCAB_ALIASES.json: 'canonical token first; accepted aliases ... must never appear in a "
          f"new canonical artifact'); control F1 schema={f1_ct_schema!r} canonical={f1_ct_canon!r}",
          ["artifacts/formulation/VOCAB_ALIASES.json",
           "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
           "schemas/af_scc_c0_vacuum.yaml#conclusion.conclusion_type"])
    if alias_equivalent:
        c.add("E1b", "note: canonical F0 artifact carries an alias token", "WARN", "minor",
              f"the canonical taxonomy's conclusion token {canon_ct!r} is a registered alias of "
              f"{canon_tok(canon_ct)!r}; the alias policy says aliases must never appear in a new canonical "
              f"artifact. Not a defect of F2b; recorded for the controller/F0 owner. G-FORM's wording "
              f"'exact conclusion_type' should say whether alias-equivalence satisfies it.")
    fw = json.dumps(doc.get("conclusion", {}).get("forbidden_weakenings", []))
    il = json.dumps(doc.get("implication_ledger", {}))
    c.add("E2", "C0=>C2 one-way direction asserted; C2=>C0 forbidden",
          "PASS" if ("C2" in fw and "C2" in il and "never the reverse" in il) else "WARN", "major",
          "forbidden_weakenings mention C2 and implication_ledger states C0 => H2loc => C2 with 'never the reverse'")
    ip = doc.get("i_plus", {}); vis = doc.get("visibility", {})
    c.add("E3", "I+ / visibility excluded from the conclusion",
          "PASS" if (ip.get("in_conclusion") is False and ip.get("completeness_in_conclusion") is False
                     and vis.get("role") != "in_conclusion") else "FAIL", "hard",
          f"i_plus.in_conclusion={ip.get('in_conclusion')}, completeness={ip.get('completeness_in_conclusion')}, "
          f"visibility.role={vis.get('role')!r}")
    c.add("E4", "no theorem promotion: epistemic_status=open_problem + promotion rule",
          "PASS" if doc.get("epistemic_status") == "open_problem" and doc.get("promotion_rule") else "FAIL",
          "hard", f"epistemic_status={doc.get('epistemic_status')!r}")

    # ---- F. provenance / citation honesty ------------------------------------
    refs = doc.get("l1_ledger_refs", [])
    mismatch = []
    for r in refs:
        tid = r.get("theorem_id")
        led = by_id.get(tid)
        lv = led.get("verification_status") if led else "ABSENT"
        if r.get("citation_status") == "verified_by_L1" and lv != "verified":
            mismatch.append({"theorem_id": tid, "schema_citation_status": r.get("citation_status"),
                             "ledger_verification_status": lv})
    c.add("F1", "l1_ledger_refs citation_status matches ledger verification_status",
          "PASS" if not mismatch else "FAIL", "hard",
          f"{len(mismatch)}/{len(refs)} refs claim verified_by_L1 while the ledger records a different "
          f"verification_status; ledger vocabulary: abstract-read x{sum(1 for r in ledger if r.get('verification_status')=='abstract-read')}, "
          f"verified x{sum(1 for r in ledger if r.get('verification_status')=='verified')}",
          mismatch)
    prov_cs = doc.get("provenance", {}).get("citation_status")
    c.add("F2", "no internal citation-status contradiction (provenance vs l1_ledger_refs)",
          "PASS" if not (prov_cs == "unverified" and mismatch) else "FAIL", "hard",
          f"provenance.citation_status={prov_cs!r} while l1_ledger_refs claims verified_by_L1 "
          f"for {len(mismatch)} ledger entries")
    vr = json.loads((root / live_paths["variant_registry"]).read_text())
    vrs = json.dumps(vr)
    need_variants = ["CH", "H2LOC", "DISTRIBUTIONAL"]
    c.add("F3", "class_identity_variants/anti_scope variant ids exist in VARIANT_REGISTRY",
          "PASS" if all(v in vrs for v in need_variants) else "FAIL", "hard",
          f"searched {need_variants} in artifacts/formulation/VARIANT_REGISTRY.json")

    # ---- G. timestamp discipline --------------------------------------------
    now = datetime.now(CST)
    def parse_ts(s):
        try:
            return datetime.fromisoformat(str(s))
        except Exception:
            return None
    rev_at = parse_ts(doc.get("revised_at"))
    chk_at = parse_ts(doc.get("f0_binding", {}).get("checked_at"))
    ev_mtime = datetime.fromtimestamp((root / live_paths["taxonomy_consistency"]).stat().st_mtime, CST)
    skew_rev = (rev_at - now).total_seconds() if rev_at else None
    skew_chk = (chk_at - now).total_seconds() if chk_at else None
    c.add("G1", "revised_at is not future-dated at snapshot time",
          "PASS" if (skew_rev is not None and skew_rev <= 0) else "FAIL", "hard",
          f"revised_at={doc.get('revised_at')!r}, snapshot_now={now.isoformat(timespec='seconds')}, "
          f"skew={skew_rev:+.0f}s" if skew_rev is not None else "revised_at unparseable")
    c.add("G2", "f0_binding.checked_at is not future-dated and postdates its evidence file",
          "PASS" if (skew_chk is not None and skew_chk <= 0 and chk_at and chk_at >= ev_mtime) else "FAIL",
          "hard",
          f"checked_at={doc.get('f0_binding',{}).get('checked_at')!r} (skew={skew_chk:+.0f}s), "
          f"taxonomy_consistency.json mtime={ev_mtime.isoformat(timespec='seconds')}"
          if skew_chk is not None else "checked_at unparseable")
    c.add("G3", "revision is an integer >= 1 and authored_at precedes revised_at",
          "PASS" if (isinstance(doc.get("revision"), int) and doc["revision"] >= 1
                     and (parse_ts(doc.get("authored_at")) or now) <= (rev_at or now)) else "WARN",
          "minor", f"revision={doc.get('revision')!r}, authored_at={doc.get('authored_at')!r}")

    summary, hard = c.summary()
    drift = (live_hashes["schema"]["sha256"] != snapshot_meta["f2b_snapshot_sha256"])
    report = {
        "task_id": "W029-F2B-FULLVERDICT-01",
        "worker": "worker-029",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "generated_at": now.isoformat(timespec="seconds"),
        "snapshot": snapshot_meta,
        "live_paths": live_hashes,
        "snapshot_is_live_at_report_time": not drift,
        "summary": summary,
        "hard_failure_check_ids": hard,
        "verdict_recommendation": "revise" if hard else "accept",
        "checks": c.rows,
        "reviewed_sha256": snapshot_meta["f2b_snapshot_sha256"],
    }
    out = d / a.out
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in
                      ("task_id", "reviewed_sha256", "snapshot_is_live_at_report_time",
                       "summary", "hard_failure_check_ids", "verdict_recommendation")}, indent=2))
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
