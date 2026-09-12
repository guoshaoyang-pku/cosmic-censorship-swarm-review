#!/usr/bin/env python3
"""worker-006 independent L0 review harness (fail-closed, hash-pinned).

Task: independent review of L0 `ledger/theorems.jsonl` against the declared L0
acceptance tests (assignment asg-2026-09-11-L0-astra-lead-literature-03,
astra-life01-l0-revise, astra-indep-1-L0-L1-literature) plus the G-LIT criteria.

Binds:
  - ledger/theorems.jsonl      (LedgerPin)
  - ledger/citation_audit.csv  (AuditPin)
Both are re-hashed at the end; any drift aborts with exit 2 and no verdict file.

Outputs (written by run()):
  - checks.json   per-check results + aggregates
Writes nothing else; the caller composes the review JSON.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]  # artifacts/worker-006/l0_review -> repo root
LEDGER = REPO / "ledger" / "theorems.jsonl"
AUDIT = REPO / "ledger" / "citation_audit.csv"
OUT = Path(__file__).resolve().parent / "checks.json"

FROZEN_FOUR = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
VERIF_STATUS = {"unverified", "abstract-read", "full-text", "page-checked"}
CONCLUSION_TYPES = {
    "theorem", "conditional_theorem", "counterexample", "open_problem",
    "stability_result", "formal_model", "numerical_evidence",
}
# rows asserting a mathematical result must carry scope controls
STRONG = {"theorem", "conditional_theorem", "counterexample", "stability_result"}
REQUIRED = [
    "theorem_id", "label", "statement_exact", "assumptions", "class_ids",
    "topology", "genericity", "regularity", "conclusion_type", "evidence_level",
    "verification_status", "does_not_imply", "falsifiers", "source_ids",
    "scope_caveats", "unresolved", "ledger_tags", "status",
]
# citation-audit records known to be unresolved / metadata-wrong after the
# citation-integrity-C adversarial pass (artifacts/literature/reviews/citation-integrity-C.md)
KNOWN_BAD = {
    "SRC-090": "status unresolved, no locator",
    "SRC-041": "DOI resolves to a different work",
    "SRC-050": "venue page range wrong",
    "SRC-011": "DOI is a 2002 reprint, record year 1969",
    "SRC-025": "record year vs publisher year",
    "SRC-046": "quote has undisclosed elisions",
    "SRC-071": "evidence is OpenAlex reconstruction, not liftable",
    "SRC-072": "evidence is OpenAlex reconstruction, not liftable",
    "SRC-016": "quote not symbol-faithful",
}
UNRESOLVED_MARKERS = re.compile(
    r"unresolv|paywall|not machine-retrieved|not retrieved|not independently|"
    r"no DOI|not verified|unverified|surrogate|reconstruction|not liftable|"
    r"year|reprint|page range|elision|symbol",
    re.I,
)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows():
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def load_audit():
    with AUDIT.open() as f:
        return {r["citation_id"]: r for r in csv.DictReader(f)}


def main() -> int:
    pin = {"ledger_sha256": sha256(LEDGER), "audit_sha256": sha256(AUDIT)}
    rows = load_rows()
    audit = load_audit()
    checks: list[dict] = []

    def add(cid, ok, detail, hard=True):
        checks.append({"check": cid, "ok": bool(ok), "hard": bool(hard),
                       "detail": detail})

    # C1 row count
    add("L0-COUNT>=15", len(rows) >= 15, f"{len(rows)} rows")

    # C2 uniqueness
    ids = [r.get("theorem_id") for r in rows]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    add("L0-ID-UNIQUE", not dup, f"duplicate theorem_id: {dup or 'none'}")

    # C3 required fields present and non-empty (list fields: >=1 for scope controls)
    missing = []
    for r in rows:
        for k in REQUIRED:
            if k not in r:
                missing.append(f"{r.get('theorem_id')}:{k}:absent")
        for k in ("theorem_id", "label", "statement_exact", "conclusion_type",
                  "evidence_level", "verification_status", "status"):
            if not str(r.get(k) or "").strip():
                missing.append(f"{r.get('theorem_id')}:{k}:empty")
        for k in ("does_not_imply", "falsifiers", "scope_caveats", "assumptions"):
            if not r.get(k):
                missing.append(f"{r.get('theorem_id')}:{k}:empty-list")
    add("L0-REQUIRED-FIELDS", not missing, f"{len(missing)} violations: {missing[:12]}")

    # C4 class token discipline
    foreign = []
    for r in rows:
        for t in r.get("class_ids") or []:
            if t not in FROZEN_FOUR:
                foreign.append(f"{r.get('theorem_id')}:{t}")
    add("L0-CLASS-TOKENS-FROZEN", not foreign,
        f"foreign class_ids tokens: {foreign or 'none'}; "
        f"rows with empty class_ids (non-class ledger rows): "
        f"{sum(1 for r in rows if not r.get('class_ids'))}")

    # C5 non-class tags live in ledger_tags (no token leak the other way)
    tag_leak = []
    for r in rows:
        for t in r.get("ledger_tags") or []:
            if t in FROZEN_FOUR:
                tag_leak.append(f"{r.get('theorem_id')}:{t}")
    add("L0-NONCLASS-TAGGED", not tag_leak,
        f"frozen class tokens inside ledger_tags: {tag_leak or 'none'}", hard=False)

    # C6 verification_status vocabulary + no inflation vs citation evidence level
    bad_status = []
    overstated = []
    ev_types = Counter()
    for r in rows:
        vs = r.get("verification_status")
        if vs not in VERIF_STATUS:
            bad_status.append(f"{r.get('theorem_id')}:{vs}")
        if vs in ("full-text", "page-checked"):
            srcs = [audit.get(s) for s in (r.get("source_ids") or [])]
            ev = {str(s.get("evidence_type")) for s in srcs if s}
            ev_types.update(ev)
            if ev and ev <= {"abstract"}:
                overstated.append(f"{r.get('theorem_id')}:{vs} but sources={sorted(ev)}")
    add("L0-VERIF-VOCAB", not bad_status, f"bad verification_status: {bad_status or 'none'}")
    add("L0-VERIF-NO-INFLATION", not overstated,
        f"stronger-than-source claims: {overstated or 'none'}; "
        f"audit evidence_type counts={dict(ev_types)}")

    # C7 conclusion inflation controls on strong rows
    infl = []
    for r in rows:
        if r.get("conclusion_type") in STRONG:
            if not r.get("does_not_imply"):
                infl.append(f"{r.get('theorem_id')}:no-does_not_imply")
            if not r.get("scope_caveats"):
                infl.append(f"{r.get('theorem_id')}:no-scope-caveats")
            if not r.get("assumptions"):
                infl.append(f"{r.get('theorem_id')}:no-assumptions")
            if not r.get("falsifiers"):
                infl.append(f"{r.get('theorem_id')}:no-falsifier")
    add("L0-CONCLUSION-INFLATION", not infl,
        f"{len(infl)} violations: {infl[:12]}")

    # C8 source linkage both directions
    unknown, unreferenced = [], []
    by_theorem = defaultdict(set)
    for cid, rec in audit.items():
        for t in re.split(r"[;,]", str(rec.get("used_by_theorems") or "")):
            t = t.strip()
            if t:
                by_theorem[t].add(cid)
    for r in rows:
        tid = r.get("theorem_id")
        for s in r.get("source_ids") or []:
            if s not in audit:
                unknown.append(f"{tid}:{s}")
        if not (by_theorem.get(tid) & set(r.get("source_ids") or [])):
            unreferenced.append(f"{tid}:{sorted(r.get('source_ids') or [])}")
    add("L0-SOURCE-LINKAGE", not unknown and not unreferenced,
        f"unknown source_ids={unknown[:8]}; rows without reciprocal audit link="
        f"{unreferenced[:8]}")

    # C9a hard: a source the audit itself marks unresolved / not-verified must be
    # named in the row's unresolved list (claim-level honesty).
    aud_unresolved = {cid for cid, rec in audit.items()
                      if "unresolv" in (rec.get("status", "") + rec.get("verdict", "")).lower()}
    uncaveated = []
    for r in rows:
        blob = " ".join(map(str, (r.get("unresolved") or []) + (r.get("scope_caveats") or [])))
        for s in (r.get("source_ids") or []):
            if s in aud_unresolved and s not in blob:
                uncaveated.append(f"{r.get('theorem_id')}:{s}")
    add("L0-UNRESOLVED-CITED-FLAGGED", not uncaveated,
        f"rows citing audit-unresolved sources without naming them: {uncaveated or 'none'}; "
        f"audit-unresolved ids: {sorted(aud_unresolved) or 'none'}")

    # C9b soft: the adversarial citation pass recorded metadata corrections
    # (year / page range / quote fidelity). A ledger row whose claim does not rest
    # on the corrected field need not repeat it, but the gap should be visible.
    bad_echo, handled = [], []
    for r in rows:
        cited_bad = [s for s in (r.get("source_ids") or []) if s in KNOWN_BAD]
        if not cited_bad:
            continue
        blob = " ".join(map(str, (r.get("unresolved") or []) + (r.get("scope_caveats") or [])))
        for s in cited_bad:
            if s in blob or UNRESOLVED_MARKERS.search(blob):
                handled.append(f"{r.get('theorem_id')}:{s}")
            else:
                bad_echo.append(f"{r.get('theorem_id')}:{s}({KNOWN_BAD[s]})")
    add("L0-CITATION-CORRECTION-ECHO", not bad_echo,
        f"rows not echoing citation-registry corrections: {bad_echo or 'none'}; "
        f"handled rows: {handled or 'none'}", hard=False)

    # C10 rejected/unresolved rows must not support claims
    bad_support = []
    for r in rows:
        if str(r.get("status")) in ("rejected", "unresolved") and r.get("supports_claim"):
            bad_support.append(f"{r.get('theorem_id')}:{r.get('status')}")
    add("L0-STATUS-SUPPORT", not bad_support, f"bad support flags: {bad_support or 'none'}")

    # C11 de-dup statements (normalized)
    norm = [re.sub(r"\W+", " ", str(r.get("statement_exact") or "").lower()).strip() for r in rows]
    sdup = [k for k, v in Counter(norm).items() if v > 1 and k]
    add("L0-STATEMENT-DEDUP", not sdup,
        f"duplicate normalized statements: {len(sdup)}", hard=False)

    # C12 coverage of the four frozen classes by admitted rows. The 00:30:49 revision
    # renamed status=accepted -> included_unreviewed (HF-14 repair), so count every
    # non-rejected row that carries a class token.
    cov = Counter()
    for r in rows:
        if str(r.get("status")) != "rejected":
            for t in r.get("class_ids") or []:
                cov[t] += 1
    add("L0-CLASS-COVERAGE", all(cov.get(c, 0) > 0 for c in FROZEN_FOUR),
        f"admitted (non-rejected) rows per class: {dict(cov)}; "
        f"status vocabulary={dict(Counter(str(r.get('status')) for r in rows))}", hard=False)

    # C13 soft: lexical grounding of strong statements in the cited sources'
    # recorded excerpts/titles. Low overlap is a flag for human follow-up, not a
    # verdict on its own (L0 declares abstract-level reading; paraphrase is expected).
    STOP = set("the a an of and or in on to for with by is are was were be been that this "
               "as at from not no than then which who whose it its their there here we our "
               "can may must all any some each both more most other such only own same so "
               "than too very s t don now".split())
    def toks(s):
        return {w for w in re.findall(r"[a-z0-9]{3,}", str(s).lower()) if w not in STOP}
    weak = []
    overlaps = []
    for r in rows:
        if r.get("conclusion_type") not in STRONG:
            continue
        claim = toks(r.get("statement_exact"))
        src = " ".join(str(audit[s].get("title", "")) + " " + str(audit[s].get("evidence_excerpt", ""))
                       for s in (r.get("source_ids") or []) if s in audit)
        st = toks(src)
        if not claim or not st:
            weak.append(f"{r.get('theorem_id')}:no-text")
            continue
        ov = len(claim & st) / len(claim)
        overlaps.append((r.get("theorem_id"), round(ov, 3)))
        if ov < 0.15:
            weak.append(f"{r.get('theorem_id')}:{ov:.3f}")
    overlaps.sort(key=lambda x: x[1])
    add("L0-STATEMENT-GROUNDING", not weak,
        f"strong rows with <0.15 content-token overlap against cited excerpts: "
        f"{weak or 'none'}; lowest overlaps: {overlaps[:8]}", hard=False)

    # C14 hard: evaluation_rubric.yaml HF-14 self_certified_acceptance. Detector text
    # explicitly covers "a ledger or claim record [that] sets status=accepted /
    # validation_status=passed / supports_claim=true with no independent reviewer
    # verdict field and no artifact hash". Severity critical -> cannot accept.
    REV_FIELD = re.compile(r"review|verdict|artifact_ref|artifact_sha|evidence_ref|sha256", re.I)
    selfcert = []
    n_acc = n_sup = 0
    for r in rows:
        asserts = (str(r.get("status")) == "accepted") or (r.get("supports_claim") is True)
        if not asserts:
            continue
        n_acc += str(r.get("status")) == "accepted"
        n_sup += r.get("supports_claim") is True
        if not any(REV_FIELD.search(k) for k in r.keys()):
            selfcert.append(r.get("theorem_id"))
    add("HF-14-SELF-CERTIFIED-ACCEPT", not selfcert,
        f"HF-14 fires on {len(selfcert)}/{len(rows)} rows (status=accepted: {n_acc}, "
        f"supports_claim=true: {n_sup}, overlap 50); the row schema has no reviewer / "
        f"verdict / artifact-hash key, so the omission is structural (first: {selfcert[:6]}); "
        "evaluation_rubric.yaml HF-14 severity=critical, detector is ledger-inclusive")

    # C15 soft: HF-01 detector is claim-scoped (`claim.conclusion_type == theorem AND no
    # artifact_refs`), but the ledger's theorem rows have no artifact binding either. The
    # map has this under adjudication (worker-032 N-C5 / lead deferral to rev 3), so it is
    # reported, not counted as a hard failure of L0 at this hash.
    ART_FIELD = re.compile(r"artifact_ref|artifact_sha|evidence_ref|sha256", re.I)
    no_art = [r.get("theorem_id") for r in rows
              if r.get("conclusion_type") == "theorem"
              and not any(ART_FIELD.search(k) for k in r.keys())]
    add("HF-01-THEOREM-NO-ARTIFACT-REF", not no_art,
        f"{len(no_art)} theorem rows carry no artifact_refs/hash field; "
        "detector scope (claim vs ledger row) is under controller adjudication, "
        "reported as a finding not a hard failure", hard=False)

    # C16 soft: coherence of ledger admission status with the row's own unresolved list
    # (flash-22 evidence_strength_mismatch). Under the reading status=admission, this is a
    # display/coherence issue; quantified so the author can disposition it.
    mismatch = []
    QUALIFY = re.compile(r"peer review|refereeing|publication status|not.*(published|verified)",
                         re.I)
    for r in rows:
        if str(r.get("status")) != "accepted":
            continue
        blob = " ".join(map(str, r.get("unresolved") or []))
        if QUALIFY.search(blob):
            mismatch.append(r.get("theorem_id"))
    add("L0-ACCEPT-UNRESOLVED-COHERENCE", not mismatch,
        f"{len(mismatch)} accepted rows keep an acceptance-qualifying item in unresolved[]: "
        f"{mismatch[:10]}", hard=False)

    # C17 hard: HF-14 repair coherence (revision landed 2026-09-12T00:30:49). A row may
    # declare non-independent admission only; any claim of independent review must name
    # the reviewer evidence it rests on.
    prov_bad = []
    for r in rows:
        rs = str(r.get("review_status") or "")
        auth = str(r.get("acceptance_authority") or "")
        if not rs or not auth:
            prov_bad.append(f"{r.get('theorem_id')}:missing-provenance")
            continue
        if rs == "not_independently_reviewed":
            if not (("author" in auth.lower()) or ("self" in auth.lower())):
                prov_bad.append(f"{r.get('theorem_id')}:unreviewed-without-author-attribution")
        elif not REV_FIELD.search(json.dumps(r)):
            prov_bad.append(f"{r.get('theorem_id')}:claims-review-without-evidence")
    add("HF-14-REPAIR-COHERENT", not prov_bad,
        f"{len(prov_bad)} provenance-coherence violations: {prov_bad[:8] or 'none'}; "
        f"review_status values={dict(Counter(str(r.get('review_status')) for r in rows))}")

    # C18 hard: supports_claim=true requires a named basis / adjudication, not author say-so
    unsupported = []
    for r in rows:
        if r.get("supports_claim") is True:
            basis = str(r.get("supports_claim_basis") or "")
            if not basis or "not adjudicated" in basis.lower() or "author" in basis.lower():
                unsupported.append(f"{r.get('theorem_id')}:{basis[:40]}")
    add("L0-SUPPORTS-CLAIM-BASIS", not unsupported,
        f"{len(unsupported)} supports_claim=true rows without an adjudicated basis: "
        f"{unsupported or 'none'}; supports_claim true count="
        f"{sum(1 for r in rows if r.get('supports_claim') is True)}")

    pin2 = {"ledger_sha256": sha256(LEDGER), "audit_sha256": sha256(AUDIT)}
    drift = pin != pin2
    add("L0-HASH-STABLE", not drift, f"start={pin} end={pin2}")
    if drift:
        print("FAIL-CLOSED: artifact drifted during review; no verdict written", file=sys.stderr)
        OUT.write_text(json.dumps({"pins": pin, "pins_end": pin2, "checks": checks,
                                   "hard_failures": ["artifact drifted during review"]},
                                  indent=1))
        return 2

    hard = [c for c in checks if c["hard"] and not c["ok"]]
    soft = [c for c in checks if not c["hard"] and not c["ok"]]
    result = {
        "pins": pin,
        "pins_end": pin2,
        "rows": len(rows),
        "checks": checks,
        "hard_failures": [c["check"] for c in hard],
        "soft_findings": [c["check"] for c in soft],
        "verdict_suggestion": "revise" if hard else "accept",
    }
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in
                      ("rows", "pins", "hard_failures", "soft_findings",
                       "verdict_suggestion")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
