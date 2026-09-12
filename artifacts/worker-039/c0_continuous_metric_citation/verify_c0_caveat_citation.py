#!/usr/bin/env python3
"""worker-039: verify the AF-SCC-C0-VAC-GEN `CONVENTION CAVEAT` citation.

Task (class-bound, unclaimed at 2026-09-12T00:18+08:00): the frozen C0 schema
`schemas/af_scc_c0_vacuum.yaml` cites `arXiv:1901.07996` as an UNVERIFIED
worker-supplied pointer supporting the claim that

    "for merely continuous metrics the causal structure can be degenerate and
     chronological futures may fail to be open or may depend on the curve class
     ...; if the causal relation is degenerate, the witness must instead be a
     timelike curve from iota(M) to a point of int(M' minus iota(M))."

This is a *citation verification*, not a theorem.  It checks four things and
fails closed (exit 2) if the schema hash drifted or the fetched raw evidence is
missing/tampered:

  C1  schema hash equals the hash this verification was performed against;
  C2  the quoted claim text is present in the schema;
  C3  a required verbatim quote occurs in the fetched abstract;
  C4  a required verbatim quote occurs in the fetched LaTeX source.

Then it grades the three sub-claims of the caveat (non-openness; curve-class
dependence; the proposed witness remedy).  The remedy grade is the finding:
the paper's only openness guarantee is for the l.u.t./piecewise-C1 curve class
(Lemma 2.2), so "a timelike curve" in the schema is not class-determined for
merely continuous metrics and clause (f) keeps an open proof obligation.

Usage
  python3 verify_c0_caveat_citation.py            # writes verification.json
Exit codes
  0  integrity ok (verdict may still be PARTIAL - that is the scientific result)
  2  integrity failure (hash drift, missing evidence, missing quote)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCHEMA = REPO / "schemas" / "af_scc_c0_vacuum.yaml"
RAW = HERE / "raw"
ABSTRACT = RAW / "arxiv_1901.07996.abs.html"
SOURCE = RAW / "src" / "Future_nopen.tex"
OUT = HERE / "verification.json"
CST = timezone(timedelta(hours=8))

# Hash the verification was performed against (frozen canonical C0 schema).
SCHEMA_SHA256_EXPECTED = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
# Hash of the fetched raw evidence, so tampering/drift is detectable.
ABSTRACT_SHA256_EXPECTED = "97e594378c18afde92fc137364006b963b43150c176658adb52661e750b175f9"
SOURCE_SHA256_EXPECTED = "1e2fd7a7665e47ca2501e39138d67f74388efee425ffea7475422978cc1464a9"

CLASS_ID = "AF-SCC-C0-VAC-GEN"
TASK_ID = "L1-C0-CAVEAT-1901.07996"
ACTOR = "worker-039"

CLAIM_TEXT_REQUIRED = "CONVENTION CAVEAT"
CLAIM_CORE_REQUIRED = (
    "for merely continuous metrics the causal structure can be degenerate and "
    "chronological futures may fail to be open or may depend on the curve class"
)
REMEDY_TEXT_REQUIRED = "if the causal relation is degenerate, the witness must instead be a timelike curve"

# Verbatim quotes that must occur in the fetched evidence for C3/C4 to pass.
QUOTES = [
    (
        "abstract",
        "Most notably, chronological futures (defined naturally using locally "
        "Lipschitz curves) may be non-open, and may differ from the corresponding "
        "sets defined via piecewise $C^1$-curves.",
    ),
    (
        "source:abstract",
        "Most notably, chronological futures (defined naturally using locally "
        "Lipschitz curves) may be non-open, and may differ from the corresponding "
        "sets defined via piecewise $\\mathcal{C}^1$-curves.",
    ),
    (
        "abstract",
        "The phenomena described here are, in particular, relevant for recent "
        "synthetic approaches to low regularity Lorentzian geometry where, in the "
        "absence of a differentiable structure, causality has to be based on "
        "locally Lipschitz curves.",
    ),
    (
        "source:intro",
        "give for the first time examples where the chronological future is not "
        "open and where the chronological future defined via smooth curves and the "
        "one defined via Lipschitz curves differ",
    ),
    (
        "source:lem2.2",
        "\\check I^\\pm(p) = I^\\pm_{\\cinfty}(p) = I^\\pm_{\\copw}(p).",
    ),
    (
        "source:lem2.2",
        "In particular, $I^\\pm_{\\copw}(p)$ is open.",
    ),
    (
        "source:ex3.1",
        "The chronological future of any point with $x < 0$ is not an open subset "
        "of $\\R^2$.",
    ),
    (
        "source:ex3.1",
        "this answers~(\\ref{Q1}) in the negative",
    ),
    (
        "source:sec3-remark",
        "our examples show that in fact all of the pathologies exhibited above "
        "would persist if this definition were adopted",
    ),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_html(t: str) -> str:
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", t)


def collapse(t: str) -> str:
    """Whitespace/typography normalisation for verbatim matching.

    HTML abstracts use a non-breaking hyphen and different case for C^1; LaTeX
    writes (Q1) as (\\ref{Q1}).  Folding those is presentation-only, not content.
    """
    t = t.replace("\u2011", "-").replace("\u2010", "-").replace("\u2013", "-")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"\(\\ref\{([^}]+)\}\)", r"(\1)", t).lower()


@dataclass
class Check:
    checks: list = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append({"check": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    @property
    def ok(self) -> bool:
        return all(c["ok"] for c in self.checks)


def main() -> int:
    ck = Check()

    # ---- integrity -------------------------------------------------------
    if not SCHEMA.is_file():
        ck.add("C1-schema-exists", False, f"missing {SCHEMA}")
        schema_text = ""
    else:
        schema_text = SCHEMA.read_text(encoding="utf-8", errors="replace")
        measured = sha256_file(SCHEMA)
        ck.add(
            "C1-schema-hash",
            measured == SCHEMA_SHA256_EXPECTED,
            f"measured {measured[:16]} expected {SCHEMA_SHA256_EXPECTED[:16]}",
        )

    ck.add(
        "C2-claim-present",
        CLAIM_TEXT_REQUIRED in schema_text and CLAIM_CORE_REQUIRED in schema_text
        and REMEDY_TEXT_REQUIRED in schema_text,
        "quoted caveat + remedy words found in schema" if schema_text else "schema unreadable",
    )

    abstract_raw = ABSTRACT.read_text(encoding="utf-8", errors="replace") if ABSTRACT.is_file() else ""
    source_text = SOURCE.read_text(encoding="utf-8", errors="replace") if SOURCE.is_file() else ""
    ck.add("C3-abstract-present", bool(abstract_raw), str(ABSTRACT))
    ck.add("C4-source-present", bool(source_text), str(SOURCE))
    if abstract_raw:
        ck.add(
            "C3-abstract-hash",
            sha256_file(ABSTRACT) == ABSTRACT_SHA256_EXPECTED,
            f"measured {sha256_file(ABSTRACT)[:16]}",
        )
    if source_text:
        ck.add(
            "C4-source-hash",
            sha256_file(SOURCE) == SOURCE_SHA256_EXPECTED,
            f"measured {sha256_file(SOURCE)[:16]}",
        )

    # ---- required verbatim quotes ---------------------------------------
    haystacks = {
        "abstract": collapse(strip_html(abstract_raw)),
        "source:intro": collapse(source_text),
        "source:lem2.2": collapse(source_text),
        "source:ex3.1": collapse(source_text),
        "source:sec3-remark": collapse(source_text),
        "source:abstract": collapse(source_text),
    }
    quote_rows = []
    for where, q in QUOTES:
        needle = collapse(q)
        found = needle in haystacks.get(where, "")
        quote_rows.append({"where": where, "quote": q, "verbatim_found": found})
        ck.add(f"C5-quote[{where}]", found, q[:70] + ("..." if len(q) > 70 else ""))

    if not ck.ok:
        report = {
            "artifact": "c0_caveat_citation_verification",
            "actor": ACTOR,
            "task_id": TASK_ID,
            "class_id": CLASS_ID,
            "created_at": datetime.now(CST).isoformat(timespec="seconds"),
            "status": "INTEGRITY_FAILURE",
            "checks": ck.checks,
            "verdict": None,
            "falsifier": "Any C-check with ok=false invalidates this verification; re-run after drift.",
        }
        OUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=1, sort_keys=True))
        print("integrity failure", file=sys.stderr)
        return 2

    # ---- grading ---------------------------------------------------------
    # Evidence actually inspected (not the abstract alone):
    #   abs page:   title, authors, dateline, abstract
    #   full text:  LaTeX source of arXiv v2 (e-print), lines cited below
    example_source = next((r for r in quote_rows if r["where"] == "source:ex3.1"), None)
    subclaims = [
        {
            "subclaim": "causal structure can be degenerate / chronology pathologically behaved below Lipschitz",
            "grade": "SUPPORTED",
            "evidence": [
                "raw/arxiv_1901.07996.abs.html: abstract, verbatim",
                "raw/src/Future_nopen.tex:87-93 (intro summary)",
            ],
            "note": "Paper works at C^0 and alpha-Holder (0<alpha<1) regularity, i.e. inside the C0 class.",
        },
        {
            "subclaim": "chronological futures may fail to be open",
            "grade": "SUPPORTED",
            "evidence": [
                "raw/src/Future_nopen.tex:720 (Example 3.1: 'The chronological future of any point with x<0 is not an open subset of R^2' ... 'This answers (Q1) in the negative')",
                "raw/src/Future_nopen.tex:190-191 (intro)",
            ],
            "note": "Example 3.1's metric is alpha-Holder but NOT Lipschitz; the source does not claim "
                    "the example is outside the C0 class (it is inside it).",
        },
        {
            "subclaim": "chronological futures may depend on the curve class",
            "grade": "SUPPORTED",
            "evidence": [
                "raw/arxiv_1901.07996.abs.html: abstract, verbatim ('may differ from the corresponding sets "
                "defined via piecewise C^1-curves')",
                "raw/src/Future_nopen.tex:190-191 (smooth vs Lipschitz futures differ)",
                "raw/src/Future_nopen.tex:340-352 (Lemma 2.2: I^pm_Cinf = I^pm_cpw = check-I^pm, and I^pm_cpw is open)",
            ],
            "note": "The dependence is exactly between the l.u.t./piecewise-C^1 class and the "
                    "locally-Lipschitz/absolutely-continuous class.",
        },
        {
            "subclaim": "remedy: 'if the causal relation is degenerate, the witness must instead be a timelike curve'",
            "grade": "NOT_SUPPORTED_BY_SOURCE",
            "evidence": [
                "raw/src/Future_nopen.tex:340-352 (Lemma 2.2) - the only openness guarantee in the source is for "
                "piecewise-C^1 / locally-uniformly-timelike curves; no theorem makes an arbitrary 'timelike curve' "
                "witness class-determined for a merely continuous metric",
                "raw/src/Future_nopen.tex:722 (Example 3.1 exceptional curve: C^1 with one null point; "
                "not timelike in the piecewise-C^1 sense, is timelike in the absolutely-continuous sense)",
                "raw/src/Future_nopen.tex:819 ('all of the pathologies exhibited above would persist if this "
                "definition were adopted' - i.e. allowing C^1 curves that are timelike except at finitely many "
                "null-tangent points does NOT repair openness)",
                "raw/arxiv_1901.07996.abs.html: abstract (sets 'may differ' by curve class)",
            ],
            "note": "As written, the schema leaves the WITNESS curve class unspecified.  'A timelike curve' is "
                    "ambiguous precisely where the schema needs it not to be; two readers can close the class "
                    "differently.  The source-supported conservative choice is the l.u.t./piecewise-C^1 class, "
                    "under which the witness set is open.",
        },
    ]

    verdict = "PARTIAL"
    report = {
        "artifact": "c0_caveat_citation_verification",
        "actor": ACTOR,
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "status": "INTEGRITY_OK",
        "verdict": verdict,
        "verdict_meaning": "PARTIAL: the caveat's factual core is supported by the cited source; the schema's "
                           "proposed remedy is not, and remains an open proof obligation.",
        "source": {
            "locator_primary": "arXiv:1901.07996v2",
            "locator_resolver": "https://arxiv.org/abs/1901.07996 (HTTP 200)",
            "doi": "10.1007/s11005-019-01213-8",
            "journal": "Letters in Mathematical Physics (2019)",
            "title": "The future is not always open",
            "authors": ["James D. E. Grant", "Michael Kunzinger", "Clemens Saemann", "Roland Steinbauer"],
            "submitted": "2019-01-23",
            "revised": "2019-09-09",
            "fetched": {
                "abstract_html": {
                    "path": "artifacts/worker-039/c0_continuous_metric_citation/raw/arxiv_1901.07996.abs.html",
                    "sha256": ABSTRACT_SHA256_EXPECTED,
                },
                "eprint_tar": {
                    "path": "artifacts/worker-039/c0_continuous_metric_citation/raw/src.tar.gz",
                    "sha256": "bf93d7981ba0efbaa2ff9bcdcb1c07810ae7753005e547389daf0c268fba5d20",
                },
                "latex_source": {
                    "path": "artifacts/worker-039/c0_continuous_metric_citation/raw/src/Future_nopen.tex",
                    "sha256": SOURCE_SHA256_EXPECTED,
                },
            },
        },
        "schema_reference": {
            "path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": SCHEMA_SHA256_EXPECTED,
            "line": 99,
            "field": "extension_predicate.definition",
            "cited_as": "UNVERIFIED",
        },
        "subclaim_grades": subclaims,
        "checks": ck.checks,
        "finding_for_lead": {
            "finding": "C0 clause (f) witness class is not pinned down; the citation's own openness result "
                       "(Lemma 2.2) holds for the l.u.t./piecewise-C^1 class, not for an unqualified "
                       "'timelike curve'.",
            "suggested_disposition": "Either (a) restate clause (f)'s degenerate-case witness as a l.u.t. / "
                                     "piecewise-C^1 timelike curve with a named degeneracy criterion, or "
                                     "(b) mark clause (f) as an open proof obligation with that exact wording. "
                                     "Do not silently mark the citation VERIFIED.",
            "ledger_action": "admissible as a class-bound L1 row for AF-SCC-C0-VAC-GEN with "
                             "verification_status=full-text (LaTeX source inspected) and verdict=PARTIAL; "
                             "must not be recorded as a positive support for the remedy sentence.",
        },
        "falsifier": "Any of: (i) the schema at sha256 1bb78ce9b357 changes the caveat/remedy text or disappears; "
                     "(ii) a source-verbatim passage is produced in which the cited paper makes an unqualified "
                     "timelike-curve witness class-determined for a merely continuous metric (which would "
                     "contradict Lemma 2.2's restriction to piecewise-C^1/l.u.t. curves); (iii) the fetched "
                     "evidence hash changes without re-running this script.  Each invalidates this verification.",
        "limitations": [
            "One source inspected (the cited one); no general literature search for other treatments of C0 causality.",
            "Grade is a reading of the source, not a machine-checked proof of any mathematical statement.",
            "The source's two-dimensional alpha-Holder examples are inside the C0 class but are not "
            "general continuous metrics; the schema's 'merely continuous' scope is broader than the examples.",
        ],
        "reproduce": "python3 artifacts/worker-039/c0_continuous_metric_citation/verify_c0_caveat_citation.py",
    }
    OUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"INTEGRITY_OK verdict={verdict} -> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
