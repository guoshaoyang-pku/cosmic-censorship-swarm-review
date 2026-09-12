#!/usr/bin/env python3
"""W080-FORM-SEP-05: re-bind the FORM-SEP-04 containment-inversion hard failure to the
current canonical F2a/F2b hashes.

Read-only. Checks, in order:
  A  hash binding: sha256 of the canonical C2/C0 schemas, canonical-vs-authoring parity,
     sidecar sha256 consistency.
  B  declared containment order parsed from each file's
     implication_ledger.extension_class_containment, and cross-file agreement.
  C  size-premise scan over every string in implication_ledger: a sentence that calls a
     regularity class a "larger/bigger/wider" extension class must agree with the declared
     containment order; the opposite is a hard failure (containment_inversion_in_ledger).
  D  the controller class-separation detector (research_map.class_separation) over both
     parsed documents, recorded as a cross-check only.
  E  counterfactual sensitivity: apply the one-word repair to a copy and re-run C, so a
     FAIL from an always-failing checker is ruled out.

Output: JSON report at the path given by --out (default
artifacts/worker-080/form_sep_05/containment_rebind_report.json). No network, no mutation
of any input. Claims no node completion and no gate verdict.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

CANON = {
    "C2": "schemas/af_scc_c2_vacuum.yaml",
    "C0": "schemas/af_scc_c0_vacuum.yaml",
}
AUTHORING = {
    "C2": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "C0": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
SIDECAR = {
    "C2": "schemas/af_scc_c2_vacuum.yaml.sha256",
    "C0": "schemas/af_scc_c0_vacuum.yaml.sha256",
}
# regularity tokens as they appear in the containment sentences -> canonical label
TOKEN_MAP = {
    "C0": "C0",
    "C^0": "C0",
    "C2": "C2",
    "C^2": "C2",
    "C1,1": "C11",
    "C^1,1": "C11",
    "C^{1,1}": "C11",
    "C11": "C11",
    "H2loc": "H2LOC",
    "H2_loc": "H2LOC",
    "H^2_loc": "H2LOC",
    "H^2_{loc}": "H2LOC",
    "C^infinity": "CINF",
    "C-infinity": "CINF",
    "C1": "C1",
    "C^1": "C1",
}

# v2 fix: brace form captured whole, so E_{C^1,1} is one token "C^1,1" (=C11) and is not
# truncated at the comma into "C^1". The v1 report parsed it as C1; the FAIL verdict was
# unaffected (chain ordering unchanged) but the label was wrong.
E_TOKEN = re.compile(r"E_?(?:\{([^{}]+)\}|([A-Za-z0-9^_\-]+))")
SIZE_ADJ = {
    "larger": +1, "bigger": +1, "wider": +1, "broader": +1,
    "smaller": -1, "narrower": -1,
}
# Predictative size claim only: "<class> is a (strictly) larger/smaller extension class|set".
# Deliberately not a bare adjective match: the containment sentence itself contains the
# generic phrase "the lower the required regularity, the larger the set of admissible
# extensions", which is not a claim about a named class.
PREDICATIVE_SIZE = re.compile(
    r"(?P<subj>C0|C2|C\^?\{?1,1\}?|H2_?loc|H\^2_loc)"
    r"\s*(?:,)?\s*(?:is|denotes|remains|forms|constitutes)\s+(?:a\s+|the\s+)?"
    r"(?P<adj>strictly\s+)?(?P<dir>larger|bigger|wider|broader|smaller|narrower)"
    r"\s+(?P<thing>extension\s+(?:class|set)|class\s+of\s+extensions)",
    re.I,
)
# Informational only: any size adjective in the ledger (not a violation surface).
ADR_RE = re.compile(
    r"(?:strictly\s+)?(?:larger|bigger|wider|broader|smaller|narrower)"
    r"|superset|subset",
    re.I,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk_strings(obj, path=""):
    """Yield (json-pointer, string) for every string leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def parse_chain(sentence: str):
    """Parse a containment sentence into an ordered list of (label, rel) where rel is
    'subset' (each item is a subset of the next) or 'contains' (each item contains the
    next). Returns (labels, rel) or (None, None)."""
    toks = [(m.group(1) or m.group(2)) for m in E_TOKEN.finditer(sentence)]
    labels = [TOKEN_MAP.get(t.strip()) for t in toks]
    rel = None
    if re.search(r"\bsubset\b", sentence, re.I) and re.search(r"contains", sentence, re.I):
        # mixed sentence: decide by position of the first connector
        first_sub = re.search(r"\bsubset\b", sentence, re.I)
        first_con = re.search(r"contains", sentence, re.I)
        rel = "subset" if first_sub.start() < first_con.start() else "contains"
    elif re.search(r"\bsubset\b", sentence, re.I):
        rel = "subset"
    elif re.search(r"contains", sentence, re.I):
        rel = "contains"
    labels = [l for l in labels if l]
    if len(labels) >= 2 and rel:
        return labels, rel
    return None, None


def ranks_from_chain(labels, rel):
    """rank 0 = smallest extension set."""
    if rel == "subset":
        return {lab: i for i, lab in enumerate(labels)}
    # contains: first is largest
    n = len(labels)
    return {lab: n - 1 - i for i, lab in enumerate(labels)}


def scan_size_premises(doc: dict, file_key: str):
    """Return (hits, inversions, unclassified) for predicative size claims under
    implication_ledger. A hit is an inversion iff the claimed size direction contradicts
    the same file's declared containment ranks."""
    ledger = doc.get("implication_ledger") or {}
    own = "C2" if "C2" in str(doc.get("class_id", "")) else (
        "C0" if "C0" in str(doc.get("class_id", "")) else None)
    sibling = "C2" if "C2" in str(doc.get("sibling_disjoint_from", "")) else (
        "C0" if "C0" in str(doc.get("sibling_disjoint_from", "")) else None)
    declared = doc.get("_declared_ranks")
    hits, inversions, unclassified = [], [], []
    for ptr, text in walk_strings(ledger, "implication_ledger"):
        for sent in re.split(r"(?<=[.;])\s+", text):
            for m in PREDICATIVE_SIZE.finditer(sent):
                subj = TOKEN_MAP.get(m.group("subj").strip(), m.group("subj").strip())
                adj = +1 if m.group("dir").lower() in ("larger", "bigger", "wider", "broader") else -1
                # comparator: a second class named in the same clause, else the file's own
                # class when the subject is the sibling, else the sibling.
                others = [TOKEN_MAP.get(t, t) for t in re.findall(
                    r"C0|C2|C\^?\{?1,1\}?|H2_?loc|H\^2_loc", sent)
                    if TOKEN_MAP.get(t, t) != subj]
                if others:
                    comp = others[0]
                elif own is not None and subj != own:
                    comp = own
                else:
                    comp = sibling
                hit = {
                    "path": ptr,
                    "sentence": sent.strip(),
                    "matched_phrase": m.group(0),
                    "subject": subj,
                    "comparator": comp,
                    "size_claim": "larger" if adj > 0 else "smaller",
                    "declared_ranks": declared,
                }
                if comp is None or declared is None or subj not in declared or comp not in declared:
                    unclassified.append(hit)
                    hits.append(hit)
                    continue
                declared_dir = (+1 if declared[subj] > declared[comp]
                                else -1 if declared[subj] < declared[comp] else 0)
                hit["declared_relation"] = ("larger" if declared_dir > 0
                                            else "smaller" if declared_dir < 0 else "equal")
                hit["consistent"] = (declared_dir == adj)
                hits.append(hit)
                if declared_dir != 0 and declared_dir != adj:
                    hit["why_inverted"] = (
                        f"declared order says extension sets of {subj} are "
                        f"{hit['declared_relation']} than {comp}, sentence asserts they are "
                        f"{'larger' if adj > 0 else 'smaller'}"
                    )
                    inversions.append(hit)
    return hits, inversions, unclassified


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "artifacts/worker-080/form_sep_05/"
                                        "containment_rebind_report_v2.json"))
    args = ap.parse_args()

    report = {
        "audit": "W080-FORM-SEP-05",
        "task_id": "W080-FORM-SEP-05-CONTAINMENT-REBIND",
        "artifact_version": 2,
        "supersedes": {
            "report": "artifacts/worker-080/form_sep_05/containment_rebind_report.json",
            "report_sha256": "86e0d3195e8d12fae105cb93e70d746e658c69ea696cff2c97296577fc6635c8",
            "erratum": ("v1 parsed E_{C^1,1} as label 'C1' because the token regex stopped at "
                        "the comma; v2 captures the brace form whole as 'C11'. The FAIL verdict "
                        "and the inversion path/quote are unchanged."),
        },
        "worker": "worker-080",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "scope": {
            "audits": "the FORM-SEP-04 hard failure containment_inversion_in_ledger, re-bound "
                      "to the current canonical F2a/F2b sha256",
            "does_not_audit": ["physical truth", "citation scope",
                               "mathematical correctness of definitions",
                               "C0/C2 class-merge (that is the classsep detector's job)"],
            "read_only": True,
            "claims_no_completion": True,
            "interpretation_owner": "astra-lead-formulation",
        },
        "inputs": {},
        "A_hash_binding": {},
        "B_declared_containment": {},
        "C_size_premise_scan": {},
        "D_classsep_crosscheck": {},
        "E_counterfactual_sensitivity": {},
        "verdict": None,
        "hard_failures": [],
        "falsifier": (
            "Exhibit a reading under which 'C2 is a strictly larger extension class' at "
            "implication_ledger.forbidden_transfers[0].reason is not an extension-set size "
            "premise, or produce a revision whose measured sha256 differs from the bound hash "
            "and in which the sentence agrees with the same file's "
            "extension_class_containment; either voids this finding and requires the rebind to "
            "be re-run at the new hash."
        ),
    }

    docs, hashes = {}, {}
    for key, rel in CANON.items():
        p = ROOT / rel
        h = sha256(p)
        hashes[key] = h
        docs[key] = yaml.safe_load(p.read_text())
        report["inputs"][rel] = h
        side = ROOT / SIDECAR[key]
        side_txt = side.read_text().strip() if side.exists() else None
        side_hash = side_txt.split()[0] if side_txt else None
        auth = ROOT / AUTHORING[key]
        report["A_hash_binding"][key] = {
            "canonical_path": rel,
            "measured_sha256": h,
            "sidecar_path": SIDECAR[key] if side.exists() else None,
            "sidecar_hash": side_hash,
            "sidecar_matches": (side_hash == h) if side_hash else None,
            "authoring_path": AUTHORING[key],
            "authoring_sha256": sha256(auth) if auth.exists() else None,
            "canonical_authoring_byte_parity": (sha256(auth) == h) if auth.exists() else None,
            "class_id": docs[key].get("class_id"),
            "revision": docs[key].get("revision"),
        }

    for key, doc in docs.items():
        sent = (doc.get("implication_ledger") or {}).get("extension_class_containment", "")
        labels, rel = parse_chain(sent)
        doc["_declared_ranks"] = ranks_from_chain(labels, rel) if labels else None
        report["B_declared_containment"][key] = {
            "sentence": sent,
            "parsed_labels": labels,
            "parsed_relation": rel,
            "rank_0_is_smallest": doc["_declared_ranks"],
        }

    r_c2 = (report["B_declared_containment"]["C2"]["rank_0_is_smallest"] or {})
    r_c0 = (report["B_declared_containment"]["C0"]["rank_0_is_smallest"] or {})
    agree = bool(r_c2) and all(r_c2.get(k) == r_c0.get(k) for k in set(r_c2) & set(r_c0))
    report["B_declared_containment"]["cross_file_agree"] = agree
    report["B_declared_containment"]["shared_rank_view"] = {
        k: r_c2.get(k) for k in sorted(set(r_c2) | set(r_c0), key=lambda x: r_c2.get(x, 99))
    }

    all_hits, all_inv, all_unclass = [], [], []
    for key, doc in docs.items():
        hits, inv, unclass = scan_size_premises(doc, key)
        for h in hits:
            h["file"] = CANON[key]
        for h in inv:
            h["file"] = CANON[key]
        for h in unclass:
            h["file"] = CANON[key]
        all_hits += hits
        all_inv += inv
        all_unclass += unclass
    report["C_size_premise_scan"] = {
        "hits": all_hits,
        "inversions": all_inv,
        "unclassified": all_unclass,
        "inversion_count": len(all_inv),
    }

    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import class_separation  # type: ignore
        cs = {key: class_separation.findings(doc, CANON[key])
              for key, doc in docs.items()}
        report["D_classsep_crosscheck"] = {
            "detector": "research_map/class_separation.py",
            "findings": cs,
            "finding_count": sum(len(v) for v in cs.values()),
        }
    except Exception as e:  # pragma: no cover
        report["D_classsep_crosscheck"] = {"error": repr(e)}

    # E: one-word repair sensitivity. Apply the recommended repair to a copy and re-scan.
    repaired = copy.deepcopy(docs["C0"])
    rep_path = "implication_ledger.forbidden_transfers[0].reason"
    original = repaired["implication_ledger"]["forbidden_transfers"][0]["reason"]
    fixed = original.replace("strictly larger extension class", "strictly smaller extension class")
    repaired["implication_ledger"]["forbidden_transfers"][0]["reason"] = fixed
    _, inv2, _ = scan_size_premises(repaired, "C0")
    report["E_counterfactual_sensitivity"] = {
        "repair_path": rep_path,
        "before": original,
        "after": fixed,
        "repair_applied": fixed != original,
        "inversions_after_repair": len(inv2),
        "checker_flips_to_pass": len(inv2) == 0,
        "note": "proves the C failure is specific to the bound text, not an always-failing rule",
    }

    report["hard_failures"] = (
        ["containment_inversion_in_ledger"] if all_inv else []
    )
    report["verdict"] = "FAIL" if all_inv else "PASS"
    report["binding"] = {
        "bound_sha256": hashes,
        "note": "reviewer verdicts bind to these hashes; any revision voids this rebind",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(f"verdict={report['verdict']} hard_failures={report['hard_failures']}")
    for h in all_inv:
        print(f"  INVERTED {h['file']} {h['path']}: {h['sentence']}")
    print(f"report={out} sha256={sha256(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
