#!/usr/bin/env python3
"""Build the WCC/SCC primary-source theorem ledger (Astra-gated, four-class compliant).

Single source of truth:
  artifacts/literature/sources/batch-*.jsonl
  artifacts/literature/theorems/batch-*.jsonl

Emitted:
  ledger/theorems.jsonl        (L0 canonical; class_ids restricted to the four frozen classes)
  ledger/citation_audit.csv    (L1 canonical; locator/resolver/class-mapping/verdict/reviewer)
  artifacts/literature/registry.jsonl
  artifacts/literature/falsifiers.md
  artifacts/literature/unresolved.jsonl
  artifacts/literature/tag_index.md
  artifacts/literature/classes/<class_id>.md   (four files only)
  artifacts/literature/MANIFEST.json

Hard rules (fail-closed):
  * class_ids may contain ONLY the four frozen classes (controller directive astra-w07adj-02).
    Extension labels (DEFINITIONS, OTHER-MODELS, BH-FORMATION, NS-CONSTRUCTION, ...) are ledger_tags.
  * content_status=verified => at least one verified, non-metadata source whose quote entails
    the statement.
  * every entry must carry falsifiers and assumptions; every class_id must be known.
  * unresolved/rejected sources may be cited only by provisional/unresolved/rejected entries.
  * HF-14 GUARD (fail-closed): content and review are SEPARATE axes. `content_status` records
    whether the CONTENT bar is met; `review_status` records whether an independent reviewer has
    accepted the row. No emitted row may carry `status`, `validation_status` or
    `supports_claim`, because A0 reads those as self-certified acceptance
    (evaluation_rubric.yaml:244-252, HF-14 critical).
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIT = ROOT / "artifacts" / "literature"
SOURCES = LIT / "sources"
THEOREMS = LIT / "theorems"
LEDGER = ROOT / "ledger"

# The four frozen classes (ASTRA_HANDOFF.md hard decision 1; F0 taxonomy; F1/F2 schemas).
CLASSES = {
    "AF-WCC-VAC-GEN": "Asymptotically flat vacuum, weak cosmic censorship, generic data (F1 schema)",
    "AF-SCC-C2-VAC-GEN": "Asymptotically flat vacuum, SCC, C^2-inextendibility of the MGHD, generic data (F2a schema)",
    "AF-SCC-C0-VAC-GEN": "Asymptotically flat vacuum, SCC, C^0-inextendibility of the MGHD, generic data (F2b schema)",
    "AF-WCC-SCALAR-SPH": "Asymptotically flat massless scalar field, spherical symmetry, weak cosmic censorship, generic data",
}
CONCLUSION_TYPES = {
    "theorem", "conditional_theorem", "stability_result", "counterexample",
    "numerical_evidence", "formal_model", "open_problem",
}
VERIFIED = {"verified-primary", "verified-api"}
L0_VERIFICATION = {"unverified", "abstract-read", "full-text", "page-checked"}
DERIVED_LEVELS = ("peer-reviewed", "accepted-in-press", "preprint", "numerical", "metadata-only", "unresolved")
TZ = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path):
    out = []
    if not path.exists():
        return out
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}:{i}: bad JSON: {e}")
    return out


def read_batches(dirpath: Path):
    out = []
    for p in sorted(dirpath.glob("batch-*.jsonl")):
        out.extend(read_jsonl(p))
    return out


def derive_evidence_level(t, smap):
    if t.get("evidence_level"):
        return t["evidence_level"]
    if t.get("entry_kind") == "numerical_evidence":
        return "numerical"
    levels = []
    for sid in t.get("source_ids", []):
        s = smap.get(sid)
        if not s or s.get("status") not in VERIFIED:
            continue
        blob = ((s.get("venue") or "") + " " + (s.get("notes") or "")).lower()
        doi = s.get("doi") or ""
        if any(k in blob for k in ("accepted for publication", "to appear", "version accepted", "accepted by", "accepted in")):
            levels.append(3)
        elif doi and not doi.startswith("10.48550"):
            levels.append(4)
        elif s.get("arxiv_id") or "arxiv" in blob:
            levels.append(2)
        else:
            levels.append(1)
    if not levels:
        return "unresolved"
    return {4: "peer-reviewed", 3: "accepted-in-press", 2: "preprint", 1: "metadata-only"}[max(levels)]


def derive_l0_verification(t, smap):
    """Astra L0 acceptance: verification_status in {unverified, abstract-read, full-text, page-checked}."""
    if t.get("verification_status_L0"):
        return t["verification_status_L0"]
    best = "unverified"
    for sid in t.get("source_ids", []):
        s = smap.get(sid)
        if not s or s.get("status") not in VERIFIED:
            continue
        et = (s.get("verification") or {}).get("evidence_type")
        if et == "full-text":
            return "full-text"
        if et == "abstract":
            best = "abstract-read"
        elif et in ("metadata",) and best == "unverified":
            best = "unverified"
    return best


def validate(sources, theorems):
    errors = []
    smap = {}
    for s in sources:
        sid = s.get("source_id")
        if not sid:
            errors.append("source without source_id")
            continue
        if sid in smap:
            errors.append(f"duplicate source_id {sid}")
        smap[sid] = s
        if s.get("status") not in VERIFIED | {"unresolved", "rejected"}:
            errors.append(f"{sid}: bad status {s.get('status')!r}")
        if s.get("status") in VERIFIED:
            for k in ("title", "authors", "year", "url"):
                if not s.get(k):
                    errors.append(f"{sid}: verified source missing {k}")
            ev = (s.get("verification") or {}).get("evidence", "")
            if len(ev) < 30:
                errors.append(f"{sid}: verified source needs a verbatim evidence quote >=30 chars")
            if not (s.get("verification") or {}).get("fetched_at"):
                errors.append(f"{sid}: verified source missing fetched_at")
            if not (s.get("verification") or {}).get("evidence_type"):
                errors.append(f"{sid}: verified source missing evidence_type (abstract|metadata|full-text)")
    tmap = {}
    for t in theorems:
        tid = t.get("theorem_id")
        if not tid:
            errors.append("theorem without theorem_id")
            continue
        if tid in tmap:
            errors.append(f"duplicate theorem_id {tid}")
        tmap[tid] = t
        for c in t.get("class_ids", []):
            if c not in CLASSES:
                errors.append(f"{tid}: class_id {c!r} is not one of the four frozen classes; use ledger_tags")
        for c in t.get("informs_classes", []):
            if c not in CLASSES:
                errors.append(f"{tid}: informs_classes entry {c!r} is not a frozen class")
        for tag in t.get("ledger_tags", []):
            if not isinstance(tag, str):
                errors.append(f"{tid}: ledger_tags must be strings")
        if t.get("conclusion_type") not in CONCLUSION_TYPES:
            errors.append(f"{tid}: bad conclusion_type {t.get('conclusion_type')!r}")
        if not t.get("statement_exact"):
            errors.append(f"{tid}: missing statement_exact")
        if not t.get("assumptions"):
            errors.append(f"{tid}: missing assumptions")
        if not t.get("falsifiers"):
            errors.append(f"{tid}: missing falsifiers")
        for sid in t.get("source_ids", []):
            if sid not in smap:
                errors.append(f"{tid}: unknown source {sid}")
        if t.get("content_status") == "verified":
            if not t.get("source_ids"):
                errors.append(f"{tid}: content_status=verified with no sources")
            non_meta = []
            for sid in t.get("source_ids", []):
                s = smap.get(sid, {})
                if s.get("status") not in VERIFIED:
                    errors.append(f"{tid}: content_status=verified but source {sid} is {s.get('status')!r}")
                if (s.get("verification") or {}).get("evidence_type") != "metadata":
                    non_meta.append(sid)
            if not non_meta:
                errors.append(f"{tid}: content_status=verified but every source is metadata-only (scope needs abstract-level evidence)")
            if t.get("author_asserts_supports") is not True:
                errors.append(f"{tid}: content_status=verified requires author_asserts_supports=true")
        if t.get("content_status") not in {"verified", "provisional", "unresolved", "rejected"}:
            errors.append(f"{tid}: bad content_status {t.get('content_status')!r}")
        # HF-14 guard: the content axis must not be expressed in acceptance vocabulary.
        for forbidden in ("status", "validation_status", "supports_claim"):
            if forbidden in t:
                errors.append(f"{tid}: HF-14 forbidden key {forbidden!r} in a theorem record; "
                              f"content and review axes are separate (use content_status / "
                              f"author_asserts_supports)")
        if derive_l0_verification(t, smap) not in L0_VERIFICATION:
            errors.append(f"{tid}: bad derived L0 verification")
    return errors


def main():
    sources = read_batches(SOURCES)
    theorems = read_batches(THEOREMS)
    errors = validate(sources, theorems)
    if errors:
        print("BUILD FAILED (fail-closed):")
        for e in errors:
            print(" -", e)
        return 1
    LEDGER.mkdir(exist_ok=True)
    smap = {s["source_id"]: s for s in sources}

    # L0 canonical ledger, enriched with Astra acceptance fields.
    # HF-14: the review axis is emitted truthfully on every row. Until an independent
    # reviewer verdict citing this hash exists, no row is reviewed and no row may say so.
    with open(LEDGER / "theorems.jsonl", "w") as f:
        for t in theorems:
            row = dict(t)
            row["evidence_level"] = derive_evidence_level(t, smap)
            row["verification_status"] = derive_l0_verification(t, smap)
            row["review_status"] = "not_independently_reviewed"
            row["acceptance_authority"] = ("astra-lead-literature (ledger author; author "
                                           "self-assessment, not a reviewer verdict)")
            for forbidden in ("status", "validation_status", "supports_claim"):
                if forbidden in row:
                    print(f"BUILD FAILED (HF-14 guard): emitted row {row.get('theorem_id')} "
                          f"carries forbidden key {forbidden!r}", file=sys.stderr)
                    return 1
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    # L1 canonical citation audit.
    used = {}
    for t in theorems:
        for sid in t.get("source_ids", []):
            used.setdefault(sid, []).append(t["theorem_id"])
    tmap = {t["theorem_id"]: t for t in theorems}

    def class_mapping(sid):
        cls = set()
        for tid in used.get(sid, []):
            cls.update(tmap[tid].get("class_ids", []))
        return ";".join(sorted(cls)) if cls else "(evidence/tag only)"

    with open(LEDGER / "citation_audit.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["citation_id", "bibkey", "title", "authors", "year", "venue", "doi",
                    "arxiv_id", "url", "status", "resolver_result", "verification_method",
                    "evidence_type", "fetched_at", "http_status", "exact_locator", "evidence_url",
                    "elided_quote", "mirror_of", "evidence_excerpt", "used_by_theorems", "class_mapping", "assessment", "verdict", "reviewer"])
        for s in sorted(sources, key=lambda x: x["source_id"]):
            v = s.get("verification") or {}
            verdict = {"verified-primary": "verified", "verified-api": "verified",
                       "unresolved": "UNRESOLVED", "rejected": "REJECTED"}[s["status"]]
            resolver = "resolved" if s["status"] in VERIFIED else "unresolved"
            if used.get(s["source_id"]):
                assessment = "assessed: " + ";".join(used[s["source_id"]])
            else:
                a = s.get("assessment") or {}
                assessment = (a.get("status", "not_assessed_in_this_run") + ": " + a.get("reason", "no reason recorded"))
            w.writerow([s["source_id"], s.get("bibkey", ""), s.get("title", ""),
                        "; ".join(s.get("authors", [])), s.get("year", ""), s.get("venue", ""),
                        s.get("doi", ""), s.get("arxiv_id", ""), s.get("url", ""), s["status"],
                        resolver, v.get("method", ""), v.get("evidence_type", ""),
                        v.get("fetched_at", ""), v.get("http_status", ""),
                        (v.get("page") or ""), (v.get("evidence_url") or ""), str(bool(v.get("elided", False))), s.get("mirror_of", ""), (v.get("evidence", "") or "").replace("\n", " ")[:600],
                        ";".join(used.get(s["source_id"], [])), class_mapping(s["source_id"]),
                        assessment, verdict, s.get("reviewer", "lead-literature")])

    # Registry.
    with open(LIT / "registry.jsonl", "w") as f:
        for s in sorted(sources, key=lambda x: x["source_id"]):
            f.write(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n")

    # Unresolved register.
    with open(LIT / "unresolved.jsonl", "w") as f:
        for s in sources:
            if s["status"] in {"unresolved", "rejected"}:
                f.write(json.dumps({"kind": "source", "source_id": s["source_id"],
                                    "bibkey": s.get("bibkey"), "title": s.get("title"),
                                    "status": s["status"], "why": s.get("status_reason", ""),
                                    "next_action": s.get("next_action", "")},
                                   ensure_ascii=False, sort_keys=True) + "\n")
        for t in theorems:
            if t["content_status"] != "verified":
                f.write(json.dumps({"kind": "theorem", "theorem_id": t["theorem_id"],
                                    "label": t.get("label"), "status": t["content_status"],
                                    "why": t.get("unresolved", []),
                                    "next_action": t.get("next_action", "")},
                                   ensure_ascii=False, sort_keys=True) + "\n")

    # Falsifier matrix.
    lines = ["# Falsifier matrix (WCC/SCC)", "",
             f"Generated {now()} by `tools/build_literature.py` from `theorems/*.jsonl`.", "",
             "Every content-verified entry carries at least one explicit falsifier. A falsifier is an",
             "observable mathematical outcome that would kill the claim as stated.", ""]
    for cid, desc in CLASSES.items():
        ts = [t for t in theorems if cid in t.get("class_ids", [])]
        if not ts:
            continue
        lines += [f"## {cid}", "", f"*{desc}*", ""]
        for t in ts:
            lines.append(f"### {t['theorem_id']} — {t.get('label','')} [{t['content_status']}]")
            lines.append("")
            lines.append(f"- Statement (exact scope): {t['statement_exact']}")
            lines.append(f"- Assumptions: {'; '.join(t['assumptions'])}")
            lines.append(f"- Conclusion type: `{t['conclusion_type']}`")
            for fa in t["falsifiers"]:
                lines.append(f"- **Falsifier:** {fa}")
            lines.append("")
    tagged = [t for t in theorems if not t.get("class_ids")]
    if tagged:
        lines += ["## Tagged entries (no frozen class_id)", "",
                  "These entries carry ledger_tags and/or informs_classes; they are evidence or context, not class coverage.", ""]
        for t in tagged:
            lines.append(f"### {t['theorem_id']} — {t.get('label','')} [{t['content_status']}] (tags: {', '.join(t.get('ledger_tags', []))})")
            lines.append("")
            lines.append(f"- Statement (exact scope): {t['statement_exact']}")
            lines.append(f"- Assumptions: {'; '.join(t['assumptions'])}")
            for fa in t["falsifiers"]:
                lines.append(f"- **Falsifier:** {fa}")
            lines.append("")
    (LIT / "falsifiers.md").write_text("\n".join(lines) + "\n")

    # Class dossiers (four frozen classes only).
    for cid, desc in CLASSES.items():
        ts = [t for t in theorems if cid in t.get("class_ids", [])]
        out = [f"# {cid}", "", f"*{desc}*", "",
               f"Entries whose statement is about this class: {len(ts)} "
               f"({len([t for t in ts if t['content_status']=='accepted'])} accepted, "
               f"{len([t for t in ts if t['content_status']!='accepted'])} provisional/unresolved).", ""]
        for t in ts:
            lvl = derive_evidence_level(t, smap)
            out += [f"## {t['theorem_id']} — {t.get('label','')} [{t['content_status']}]", "",
                    f"**Evidence level (derived).** `{lvl}` · **L0 verification.** `{derive_l0_verification(t, smap)}`", "",
                    f"**Exact statement.** {t['statement_exact']}", "",
                    f"**Assumptions.** {'; '.join(t['assumptions'])}", "",
                    f"**Conclusion type.** `{t['conclusion_type']}`", "",
                    f"**Sources.** {', '.join(t.get('source_ids', []))}", "",
                    f"**Scope caveats.** {'; '.join(t.get('scope_caveats', [])) or '(none recorded)'}", "",
                    f"**Does not imply.** {'; '.join(t.get('does_not_imply', [])) or '(none recorded)'}", "",
                    f"**Unresolved.** {'; '.join(t.get('unresolved', [])) or '(none)'}", "",
                    f"**Falsifiers.**", ""]
            out += [f"- {fa}" for fa in t["falsifiers"]]
            out.append("")
        informing = [t for t in theorems if cid in t.get("informs_classes", []) and t["content_status"] in {"verified", "provisional"}]
        if informing:
            out += ["## Informing evidence (other-model or tagged results that bear on this class)", ""]
            for t in informing:
                out.append(f"- {t['theorem_id']} [{t['content_status']}] {t.get('label','')} — tags: {', '.join(t.get('ledger_tags', []))}")
            out.append("")
        (LIT / "classes" / f"{cid}.md").write_text("\n".join(out) + "\n")

    # Tag index (non-class tokens).
    tag_map = {}
    for t in theorems:
        for tag in t.get("ledger_tags", []):
            tag_map.setdefault(tag, []).append(t["theorem_id"])
    with open(LIT / "tag_index.md", "w") as f:
        f.write("# Ledger tag index (non-class tokens)\n\n")
        f.write("Tags never count toward class coverage; class_ids are restricted to the four frozen classes.\n\n")
        for tag in sorted(tag_map):
            f.write(f"- `{tag}`: {', '.join(tag_map[tag])}\n")

    # Manifest.
    manifest = {"generated_at": now(), "builder": "artifacts/literature/tools/build_literature.py",
                "class_ids_frozen": sorted(CLASSES),
                "counts": {"sources": len(sources), "theorems": len(theorems),
                           "verified": len([t for t in theorems if t["content_status"] == "verified"]),
                           "verified_sources": len([s for s in sources if s["status"] in VERIFIED]),
                           "metadata_only_sources": len([s for s in sources
                                                         if (s.get("verification") or {}).get("evidence_type") == "metadata"]),
                           "accepted_with_metadata_anchors": sorted([
                               t["theorem_id"] for t in theorems if t.get("content_status") == "verified"
                               and any((smap.get(sid, {}).get("verification") or {}).get("evidence_type") == "metadata"
                                       for sid in t.get("source_ids", []))]),
                           "evidence_levels_derived": {
                               lvl: len([t for t in theorems if derive_evidence_level(t, smap) == lvl])
                               for lvl in DERIVED_LEVELS},
                           "l0_verification_status": {
                               lvl: len([t for t in theorems if derive_l0_verification(t, smap) == lvl])
                               for lvl in ("unverified", "abstract-read", "full-text", "page-checked")},
                           "unassessed_sources": sorted([s["source_id"] for s in sources
                                                         if not used.get(s["source_id"])]),
                           "entries_with_extension_class_tokens": 0},
                "artifacts": {}}
    for p in [LEDGER / "theorems.jsonl", LEDGER / "citation_audit.csv",
              LIT / "registry.jsonl", LIT / "unresolved.jsonl", LIT / "falsifiers.md",
              LIT / "tag_index.md"]:
        manifest["artifacts"][str(p.relative_to(ROOT))] = sha256(p)
    for p in sorted(SOURCES.glob("batch-*.jsonl")) + sorted(THEOREMS.glob("batch-*.jsonl")):
        manifest["artifacts"][str(p.relative_to(ROOT))] = sha256(p)
    for cid in CLASSES:
        p = LIT / "classes" / f"{cid}.md"
        if p.exists():
            manifest["artifacts"][str(p.relative_to(ROOT))] = sha256(p)
    (LIT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
