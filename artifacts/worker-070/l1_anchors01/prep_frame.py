#!/usr/bin/env python3
"""W070-L1-ANCHORS-01 pre-registration.

Writes frame.json BEFORE any live fetch. The frame fixes:
  - the pinned input hashes (L1 citation_audit.csv, L0 theorems.jsonl, three class schemas),
  - the exact set of unanchored provenance rows to be judged (derived from the pinned schema
    bytes, not retyped),
  - one deterministic ledger-match rule per row, over the pinned L1 ledger,
  - the candidate primary locators to resolve live for rows with no ledger match,
  - the classification labels and the controls.

Nothing here asserts that a candidate work entails a schema field; the deliverable is a
coverage/pointer census for the literature owner to bind or reject.
"""
import hashlib
import json
import re
import sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT = f"{ROOT}/artifacts/worker-070/l1_anchors01/frame.json"

PINS = {
    "ledger/citation_audit.csv": None,
    "ledger/theorems.jsonl": None,
    "schemas/af_wcc_vacuum.yaml": None,
    "schemas/af_scc_c2_vacuum.yaml": None,
    "schemas/af_scc_c0_vacuum.yaml": None,
}

SCHEMAS = [
    ("schemas/af_wcc_vacuum.yaml", "AF-WCC-VAC-GEN", "F1"),
    ("schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN", "F2a"),
    ("schemas/af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN", "F2b"),
]

# ---------------------------------------------------------------- item registry
# id -> ledger-match rule. Rules are deterministic over the pinned L1 CSV.
# k: title_all = every token must occur in normalized title
#    title_any = at least one phrase must occur in normalized title
#    author_all = every token must occur in normalized "authors" field
#    doi_equal  = exact DOI equality (case-normalized)
#    arxiv_equal= exact arXiv id equality (version stripped)
ITEMS = {
    "F1-P1": {
        "rule": {"any_of": [
            {"title_all": ["mass", "asymptotically", "flat", "manifold"]},
            {"author_all": ["choquet bruhat", "york"]},
            {"title_all": ["boost", "problem", "general", "relativity"]},
        ]},
        "candidates": ["CBY1980", "BARTNIK1986", "COM1981"],
    },
    "F1-P2": {
        "rule": {"any_of": [
            {"doi_equal": "10.1007/BF01645389"},
            {"title_all": ["global", "aspects", "cauchy", "problem"]},
        ]},
        "candidates": ["CBG1969"],
    },
    "F1-P3": {
        "rule": {"any_of": [
            {"title_all": ["positive", "mass"]},
            {"author_all": ["schoen", "yau"]},
            {"title_all": ["mass", "asymptotically", "flat", "manifold"]},
        ]},
        "candidates": ["SY1979", "SY1981", "WITTEN1981", "BARTNIK1986"],
    },
    "F1-P4": {
        "rule": {"any_of": [
            {"title_any": ["predictab"]},
            {"title_all": ["cosmic", "censorship"]},
            {"author_all": ["hawking", "ellis"]},
        ]},
        "candidates": ["HE1973", "CHRIST1999", "WALD1984"],
    },
    "F1-P5": {  # needed_for: "no status claim is made by this schema" (informational)
        "rule": {"any_of": [{"title_all": ["cosmic", "censorship"]}]},
        "candidates": ["CHRIST1999"],
        "informational": True,
    },
    "F2a-C1": {
        "rule": {"any_of": [
            {"doi_equal": "10.1007/BF01645389"},
            {"title_all": ["global", "aspects", "cauchy", "problem"]},
        ]},
        "candidates": ["CBG1969"],
    },
    "F2a-C2": {
        "rule": {"any_of": [
            {"title_any": ["strong cosmic censorship", "inextendib"]},
            {"title_all": ["strong", "cosmic", "censorship"]},
        ]},
        "candidates": ["SB2007", "SBIERSKI2018", "DAFERMOSLUK2025"],
    },
    "F2a-C3": {
        "rule": {"any_of": [{"title_any": ["kerr"]}]},
        "candidates": ["CARTER1968"],
    },
    "F2b-C1": {
        "rule": {"any_of": [
            {"doi_equal": "10.1007/BF01645389"},
            {"title_all": ["global", "aspects", "cauchy", "problem"]},
        ]},
        "candidates": ["CBG1969"],
    },
    "F2b-C2": {
        "rule": {"any_of": [{"title_any": ["inextendib"]}]},
        "candidates": ["SBIERSKI2018", "SB2007", "DAFERMOSLUK2025"],
    },
    "F2b-C3": {
        "rule": {"any_of": [{"title_any": ["kerr"]}]},
        "candidates": ["CARTER1968"],
    },
    "F2b-C4": {
        "rule": {"any_of": [{"title_any": ["holonomy"]}]},
        "candidates": ["SB2007"],
    },
}

# ------------------------------------------------------------- candidate registry
CANDIDATES = {
    "CBG1969": {"kind": "doi", "id": "10.1007/BF01645389",
                "expect_title_tokens": ["global", "aspects", "cauchy", "problem"]},
    "CBY1980": {"kind": "crossref_query",
                "query": "The Cauchy problem Choquet-Bruhat York General Relativity and Gravitation",
                "expect_title_tokens": ["cauchy", "problem"],
                "expect_author_any": ["choquet"]},
    "BARTNIK1986": {"kind": "doi", "id": "10.1002/cpa.3160390505",
                    "expect_title_tokens": ["mass", "asymptotically", "flat", "manifold"]},
    "COM1981": {"kind": "crossref_query",
                "query": "The boost problem in general relativity Christodoulou O Murchadha",
                "expect_title_tokens": ["boost", "problem"],
                "expect_author_any": ["christodoulou", "murchadha"]},
    "SY1979": {"kind": "doi", "id": "10.1007/BF01940959",
               "expect_title_tokens": ["positive", "mass"]},
    "SY1981": {"kind": "doi", "id": "10.1007/BF01942093",
               "expect_title_tokens": ["positive", "mass"]},
    "WITTEN1981": {"kind": "doi", "id": "10.1007/BF01208277",
                   "expect_title_tokens": ["positive", "mass"]},
    "CHRIST1999": {"kind": "doi", "id": "10.1088/0264-9381/16/12A/302",
                   "expect_title_tokens": ["global", "initial", "value", "problem"]},
    "HE1973": {"kind": "doi", "id": "10.1017/CBO9780511524646",
               "expect_title_tokens": ["large", "scale", "structure", "space"]},
    "WALD1984": {"kind": "doi", "id": "10.1017/CBO9780511815960",
                 "expect_title_tokens": ["general", "relativity"]},
    "CARTER1968": {"kind": "doi", "id": "10.1103/PhysRev.174.1559",
                   "expect_title_tokens": ["kerr"]},
    "SBIERSKI2018": {"kind": "arxiv", "id": "1507.00601",
                     "expect_title_tokens": ["inextendibility", "schwarzschild"]},
    "SB2007": {"kind": "arxiv", "id": "2007.12049",
               "expect_title_tokens": ["holonomy"]},
    "DAFERMOSLUK2025": {"kind": "arxiv", "id": "2408.05257",
                        "expect_title_tokens": ["extend"]},
}

CONTROLS = {
    "positive_doi": {"kind": "doi", "id": "10.1007/BF01645389",
                     "expect_title_tokens": ["global", "aspects", "cauchy", "problem"]},
    "negative_doi": {"kind": "doi", "id": "10.9999/does-not-exist-w070",
                     "expect_title_tokens": []},
    "positive_arxiv": {"kind": "arxiv", "id": "1711.11380",
                       "expect_title_tokens": ["inextendibility", "schwarzschild"]},
    "parser_fixture": {"fixture": {"title": "Fixture: global aspects of the Cauchy problem",
                                   "authors": "A. Fixture", "year": 1969, "doi": "fixture",
                                   "arxiv_id": "", "venue": "fixture"}},
}

LABELS = [
    "LEDGER_ROW_EXISTS",
    "CANDIDATE_RESOLVED_NOT_IN_LEDGER",
    "CANDIDATE_UNRESOLVED",
    "NO_CANDIDATE_REGISTERED",
]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def extract_items():
    """Derive the unanchored provenance rows from the pinned schema bytes."""
    out = []
    pat = re.compile(r'-\s*\{concept:\s*"(?P<concept>[^"]+)",\s*identifier:\s*null,\s*status:\s*(?P<status>\w+),\s*needed_for:\s*"(?P<needed>[^"]+)"\}')
    for rel, cls, node in SCHEMAS:
        txt = open(f"{ROOT}/{rel}").read()
        for m in pat.finditer(txt):
            out.append({
                "schema": rel, "class_id": cls, "node": node,
                "concept": m.group("concept"), "status": m.group("status"),
                "needed_for": m.group("needed"),
            })
    return out


def main():
    for rel in PINS:
        PINS[rel] = sha256_file(f"{ROOT}/{rel}")
    rows = extract_items()
    print(f"derived {len(rows)} unanchored provenance rows from pinned schemas", file=sys.stderr)
    # sanity: the registry must cover exactly the derived rows
    frame = {
        "schema_version": "w070-anchors-frame-1",
        "task_id": "w070-l1-anchors-01",
        "actor": "worker-070",
        "node_id": "L1",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-LIT",
        "question": ("At the pinned hashes, for every provenance source row declared "
                     "identifier:null/status:unresolved in the three class schemas: does the "
                     "pinned L1 ledger already contain a row satisfying the pre-registered "
                     "match rule, and if not, does a pre-registered candidate primary locator "
                     "resolve live? Coverage/pointer census only; entails nothing about the "
                     "schema fields."),
        "pins": PINS,
        "derived_rows": rows,
        "item_registry": ITEMS,
        "candidate_registry": CANDIDATES,
        "controls": CONTROLS,
        "labels": LABELS,
        "match_semantics": {
            "normalize": "casefold; replace every run of non-alphanumeric characters with a single space; strip",
            "title_all": "every token appears in normalized title field",
            "title_any": "at least one phrase appears as a substring of normalized title field",
            "author_all": "every token appears in normalized authors field",
            "doi_equal": "casefold(doi) equality",
            "arxiv_equal": "arXiv id equality after stripping a trailing vN",
            "row_matches": "row satisfies at least one predicate in the item's any_of list",
        },
        "decision_rules": {
            "LEDGER_ROW_EXISTS": ">=1 pinned L1 row matches the item rule; report all matching citation_ids",
            "CANDIDATE_RESOLVED_NOT_IN_LEDGER": "0 matching rows AND >=1 registered candidate resolves live with expected title tokens",
            "CANDIDATE_UNRESOLVED": "0 matching rows AND candidates registered but none resolves with expected tokens",
            "NO_CANDIDATE_REGISTERED": "0 matching rows AND no candidate registered",
            "informational_rows": "F1-P5 has needed_for='no status claim is made by this schema'; its class is reported but it is not a blocking anchor",
        },
        "drift_policy": ("any pin sha256 change between frame write and report write voids the run; "
                         "it does not falsify it. A re-run at the same pins is the falsification test."),
        "limits": [
            "A matching ledger row is a pointer candidate, not proof that the row entails the schema field.",
            "Candidate resolution verifies metadata only (title/authors/year); content entailment needs a page-check by the literature owner.",
            "Crossref/arXiv metadata can change; resolved entries are bound to the raw response hashes.",
        ],
    }
    with open(OUT, "w") as f:
        json.dump(frame, f, indent=1, sort_keys=False)
    print(sha256_file(OUT), OUT)


if __name__ == "__main__":
    main()
