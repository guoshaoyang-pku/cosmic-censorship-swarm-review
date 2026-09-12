#!/usr/bin/env python3
"""Worker 09 / P5: build machine-readable findings for the two lead-formulation pointers.

Class bound: AF-SCC-C0-VAC-GEN only (gate G-LIT, assignment asg-2026-09-11-L1-deepseek-flash-09-18).

Every quote is asserted to occur (whitespace-normalised) in the cached extracted text before it
is written, so the JSON cannot carry a paraphrase presented as a quote. Hashes of every raw
source and every derived text file are recorded. Deterministic; stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent            # artifacts/worker-09
SWARM = ROOT.parent.parent                        # repo root
CST = timezone(timedelta(hours=8))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def load_text(name: str) -> str:
    return norm((ROOT / "extracted" / "pointers" / name).read_text())


GRANT = load_text("grant2019.txt")
RENDALL = load_text("rendall2005.txt")

# (quote, source-key) pairs; asserted below.
QUOTES = {
    "grant_abstract": ("We demonstrate the breakdown of several fundamentals of Lorentzian causality theory in low regularity. Most notably, chronological futures (defined naturally using locally Lipschitz curves) may be non-open, and may differ from the corresponding sets defined via piecewise", "grant"),
    "grant_thm210": ("be a continuous and chronological spacetime. Then the following are equivalent:", "grant"),
    "grant_thm210_iii": ("is an achronal Lipschitz-hypersurface", "grant"),
    "grant_thm215": ("There is no internal bubbling", "grant"),
    "grant_ex31": ("The chronological future of any point with x<0x<0 is not an open subset of", "grant"),
    "grant_ex31_q2": ("This answers (Q2) in the negative", "grant"),
    "grant_cor216": ("Any spacetime with a Lipschitz continuous metric is causally plain", "grant"),
    "grant_rec": ("To guarantee openness of chronological futures and pasts and to avoid interior bubbling, set I", "grant"),
    "rendall_ch": ("It may happen that the maximal Cauchy development can be extended to a larger spacetime, which is then of course no longer globally hyperbolic. The boundary of the initial spacetime in the extension is called the Cauchy horizon.", "rendall"),
    "rendall_taub": ("A famous example where this happens is the Taub-NUT spacetime [31]. This is a highly symmetric solution of the Einstein vacuum equations. The extension which is no longer globally hyperbolic contains closed timelike curves.", "rendall"),
    "rendall_generic": ("A way to do this would be to show that this behaviour only occurs for exceptional initial data and that for generic data the maximal globally hyperbolic development is inextendible. This has up to now only been achieved in the simplified context of classes of spacetimes with symmetry. These classes of spacetimes are not generic and so they do not directly say anything about cosmic censorship.", "rendall"),
    "rendall_kerr": ("When the Schwarzschild solution is generalized to include charge or rotation the picture changes dramatically. In the relevant solutions, the Reissner-Nordstr", "rendall"),
}

bad = []
for key, (q, which) in QUOTES.items():
    hay = GRANT if which == "grant" else RENDALL
    if norm(q) not in hay:
        bad.append(key)
if bad:
    raise SystemExit(f"quote(s) not found in cached text: {bad}")

sources = {
    p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
    for p in sorted((ROOT / "sources").glob("*"))
    if p.is_file() and not p.name.startswith(".")
}
extracted = {
    p.name: {"sha256": sha256(p), "bytes": p.stat().st_size}
    for p in sorted((ROOT / "extracted" / "pointers").glob("*"))
    if p.is_file()
}

TARGET = SWARM / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
target_sha = sha256(TARGET)

findings = {
    "phase": "P5",
    "worker": "deepseek-flash-09",
    "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
    "gate": "G-LIT",
    "class_ids": ["AF-SCC-C0-VAC-GEN"],
    "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
    "task": ("Adjudicate, with primary sources, the two quarantined pointers the formulation lead "
             "recorded on the AF-SCC-C0-VAC-GEN side: Grant et al. arXiv:1901.07996 (C0 causal "
             "structure convention caveat in extension clause (f)) and Rendall arXiv:gr-qc/0503112 "
             "(extendible maximal Cauchy developments / Cauchy horizons)."),
    "target_artifact": {
        "path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "sha256": target_sha,
        "field_in_scope": "extension_predicate.definition clause (f) CONVENTION CAVEAT",
        "field_status_on_disk": "cited with 'worker-supplied pointer, UNVERIFIED'; clause (f) also carries '[R2 major, recorded not fully resolved]'",
    },
    "rows": [
        {
            "finding_id": "W09-P5-001",
            "bibkey": "grant2019future",
            "source": "J. D. E. Grant, M. Kunzinger, C. Saemann, R. Steinbauer, 'The future is not always open'",
            "arxiv_id": "1901.07996",
            "arxiv_version_read": "v2 (Mon, 9 Sep 2019); verified against both the official arXiv HTML v2 and the ar5iv rendering",
            "published": "Letters in Mathematical Physics 110 (2020), no. 1, 83-103; DOI 10.1007/s11005-019-01213-8",
            "doi_resolver": "Crossref 10.1007/s11005-019-01213-8 -> title 'The future is not always open', vol 110, pages 83-103",
            "evidence_level": "full-text / theorem-level (numbered results read from the v2 HTML)",
            "pointer_claim_under_test": ("for merely continuous metrics the causal structure can be degenerate and "
                                         "chronological futures may fail to be open or may depend on the curve class"),
            "verdict": "supported_with_wording_correction",
            "theorem_level_locators": [
                "Theorem 2.10 (openness of I^+- iff achronality/Lipschitz-hypersurface property of its boundary)",
                "Theorem 2.15 (I_C-infinity = I_C1_pw = I_Lipschitz = I_AC for all p iff no internal bubbling)",
                "Corollary 2.16 + the causally-plain equivalence (internal+external bubbling absent)",
                "Example 3.1 (alpha-Hoelder, non-Lipschitz metric; I^+(p) not open; I^+(p) != I-check^+(p))",
                "Lemma 2.9 (for continuous metrics, I_AC = I_Lipschitz)",
            ],
            "exact_quotes": [
                QUOTES["grant_abstract"][0] + " C^1-curves.",
                "Theorem 2.10: 'Let (M,g) be a continuous and chronological spacetime. Then the following are equivalent: (i) For all p in M, I^+- (p) is open. ... (iii) ... is an achronal Lipschitz-hypersurface.'",
                "Theorem 2.15: '(ii) There is no internal bubbling, i.e., B_int^+- (p,U) = empty for every p and every cylindrical neighbourhood U.'",
                "Example 3.1: 'The chronological future of any point with x<0 is not an open subset of R^2.'; 'This answers (Q2) in the negative.'",
                "'Any spacetime with a Lipschitz continuous metric is causally plain' (text after Corollary 2.16).",
            ],
            "class_binding": {
                "supports": ("the convention caveat itself: in the frozen C0 regularity the chronological future used in "
                             "extension clause (f) is not automatically open and is definition-sensitive; a C0 witness "
                             "must fix its curve class explicitly."),
                "does_not_prove": [
                    "nothing about the AF-SCC-C0-VAC-GEN conclusion: the paper has no Einstein equation, no 4-dimensional AF data, no genericity claim; its examples are 2-dimensional non-vacuum metrics.",
                    "it does not establish that the extension's fallback witness (a timelike curve from iota(M) to int(M' minus iota(M))) is equivalent to the I^+ witness; that equivalence is the lead's inference.",
                    "it does not show that every C0 spacetime is pathological: Lipschitz metrics are causally plain (Corollary 2.16), and the schema's extension metric is only assumed continuous, so pathologies are possible, not forced.",
                ],
                "wording_correction": ("the schema parenthetical says 'the causal structure can be degenerate'. The source "
                                       "does not say the causal structure is degenerate - the metric is continuous and "
                                       "Lorentzian (nondegenerate) throughout. What can fail is causal plainness: there may "
                                       "be (internal/external) bubbling, I^+ may be non-open, and I^+ may depend on the "
                                       "curve class. Recommend replacing 'degenerate' with 'not causally plain (may exhibit "
                                       "bubbling)'."),
            },
            "metadata_correction_for_lead": ("the R2 review bibliography gives 'Lett. Math. Phys. 109 (2019) 83-91'; the "
                                             "version of record is Lett. Math. Phys. 110 (2020) 83-103, DOI "
                                             "10.1007/s11005-019-01213-8 (arXiv v2 2019-09-09). Use the corrected locator."),
            "falsifier": ("a page-check of the published version showing Theorem 2.10/2.15 or Example 3.1 was renumbered "
                          "or restated, or a continuous-non-Lipschitz 4-dimensional AF vacuum example in which I^+ is open "
                          "and curve-class independent (then the caveat would be unnecessary, though still harmless)."),
            "source_files": ["sources/abs_1901.07996.html", "sources/full5_1901.07996.html",
                             "sources/full5b_1901.07996v2.html", "sources/crossref_1901_07996_correct.json",
                             "extracted/pointers/grant2019.txt"],
        },
        {
            "finding_id": "W09-P5-002",
            "bibkey": "rendall2005nature",
            "source": "A. D. Rendall, 'The nature of spacetime singularities'",
            "arxiv_id": "gr-qc/0503112",
            "arxiv_version_read": "v1 (2005-03-29)",
            "published": ("in '100 Years of Relativity: Space-Time Structure: Einstein and Beyond' (A. Ashtekar, ed.), "
                          "World Scientific, 2005, pp. 76-92; DOI 10.1142/9789812700988_0003"),
            "doi_resolver": "Crossref 10.1142/9789812700988_0003 -> 'THE NATURE OF SPACETIME SINGULARITIES', pages 76-92",
            "evidence_level": "full-text / survey-level (no numbered theorem; expository statements in Sections 2 and 3)",
            "pointer_claim_under_test": ("extendible maximal Cauchy developments and Cauchy horizons (Taub-NUT; Kerr/RN); "
                                         "the ambiguity of SCC under the regularity/equation choice of extension"),
            "verdict": "supported_survey_level_with_non_transfer_clause",
            "theorem_level_locators": [
                "Section 2 'Cosmological singularities', paragraph after the Eardley-Moncrief formulation of SCC (definition of extendibility, Cauchy horizon, Taub-NUT example)",
                "Section 2, following paragraph (generic data inextendible; symmetry results say nothing directly about cosmic censorship)",
                "Section 3 'Black hole singularities' (Reissner-Nordstroem and Kerr: Schwarzschild singularity replaced by a Cauchy horizon)",
            ],
            "exact_quotes": [
                QUOTES["rendall_ch"][0],
                QUOTES["rendall_taub"][0],
                QUOTES["rendall_generic"][0],
                QUOTES["rendall_kerr"][0] + "om and Kerr solutions, the Schwarzschild singularity is replaced by a Cauchy horizon.",
            ],
            "class_binding": {
                "supports": [
                    "the vocabulary used by the frozen class: 'maximal Cauchy development', 'extendible', 'Cauchy horizon' (Section 2).",
                    "non-vacuity of the C0 extension predicate in the vacuum case: Taub-NUT is an explicit Einstein-vacuum solution whose maximal Cauchy development admits a proper extension (the extension is smooth, hence also C0; it is no longer globally hyperbolic and contains closed timelike curves).",
                    "why the class needs its genericity quantifier: Taub-NUT is 'highly symmetric', i.e. outside any generic (comeager) set of AF data; the survey states that symmetry-class results 'do not directly say anything about cosmic censorship'.",
                ],
                "does_not_prove": [
                    "no theorem in this source establishes the AF-SCC-C0-VAC-GEN conclusion, positively or negatively.",
                    "no statement that exact Kerr/Reissner-Nordstroem AF Cauchy data have an extendible maximal development is proved here; Section 3 is survey prose ('the Schwarzschild singularity is replaced by a Cauchy horizon'), and the later blue-shift discussion shows the mechanism is not a simple extendibility theorem.",
                    "no statement about the regularity of the extension: the Taub-NUT extension discussed is smooth, so it cannot discriminate C0 from C2 or H2_loc, and it must not be used as a C0-specific or C2-specific witness.",
                    "no evidence that genericity is needed to make the class true; 'exceptional' is used informally, not as a meagreness statement.",
                ],
            },
            "unresolved_leadform_question": ("The formulation lead's highest-value open item - whether ANY proper future "
                                             "extension of an AF development must cross a Cauchy horizon - is NOT settled by "
                                             "this source. The C0 extension predicate (a)-(f) contains no Cauchy-horizon "
                                             "condition, so no separation claim should be made to depend on that premise "
                                             "until a primary theorem is located. Status: unresolved."),
            "falsifier": ("a primary (numbered-theorem) source showing that exact Kerr or Reissner-Nordstroem AF initial "
                          "data have an inextendible maximal development would falsify the class-motivating use of the "
                          "Kerr/RN sentence; a statement in Rendall's text that Taub-NUT data are generic AF data would "
                          "falsify the non-transfer clause."),
            "source_files": ["sources/abs_grqc0503112.html", "sources/full5_grqc0503112.html",
                             "sources/crossref_grqc0503112_correct.json", "extracted/pointers/rendall2005.txt"],
        },
        {
            "finding_id": "W09-P5-CTRL-1",
            "kind": "method_control",
            "description": ("Guessed-journal DOI control. The DOI 10.1007/s11005-018-1110-z was fetched as a candidate "
                            "for Grant et al.; Crossref returned 'M-theory from the superpoint' (Lett. Math. Phys. 108, "
                            "2695-2727, 2018). The candidate was rejected and replaced by the DOI printed on the arXiv "
                            "abstract page (10.1007/s11005-019-01213-8), which resolves to the correct title."),
            "expected": "a wrong DOI resolves to a different work",
            "observed": "different work",
            "control_passed": True,
            "source_files": ["sources/crossref_1901_07996.json"],
        },
    ],
    "unresolved": [
        "whether every proper future extension of an AF development must cross a Cauchy horizon (no source verified here proves it).",
        "the schema's fallback-witness equivalence (timelike-curve witness vs I^+ witness) has no primary source; it remains the lead's inference.",
    ],
    "hashes": {"sources": sources, "extracted": extracted, "target": {"path": str(TARGET.relative_to(SWARM)), "sha256": target_sha}},
}

out = ROOT / "extracted" / "p5_findings.json"
out.write_text(json.dumps(findings, indent=1))
print("wrote", out, "sha256", sha256(out))
print("quotes asserted:", len(QUOTES), "| target sha", target_sha[:16])
