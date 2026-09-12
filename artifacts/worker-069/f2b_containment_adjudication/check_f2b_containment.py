#!/usr/bin/env python3
"""Independent containment-wording checker for the F2b class schema.

Task: W069-F2B-CONTAINMENT-ADJ-01   (class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM)

Read-only. Given one YAML file (canonical bytes or a mutation control) this emits a JSON
object with per-check results about:

  C1  hash/pin integrity of the canonical target (skipped for controls)
  C2  the extension-class containment chain declared by the file
  C3  the forbidden-transfer reason "C2 is a strictly larger extension class" versus that chain
  C4  the `regularity.must_not_conflate` sentence "No containment with C2 or C0 is asserted here"
      versus the ledger's containment assertions (scoped vs file-wide reading; ambiguity flag)
  C5  the operative forbidden direction, re-derived from the set relations independently
  C6  duplicate top-level YAML mapping keys (parser hygiene; strict compose, last-wins load)
  C7  consistency of the chain string with the one_way_entailments rows

The checker is written from the file bytes and the class-containment definition; it uses no
reviewer's conclusion as an input. It is deliberately narrow: it does not re-review the schema.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

CANONICAL_SHA256 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
CANONICAL_PATH = "schemas/af_scc_c0_vacuum.yaml"
CHAIN_RE = re.compile(
    r"E_(?P<a>\w+|\{[^}]+\})\s+contains\s+E_(?P<b>\w+|\{[^}]+\})"
    r"(?:\s+contains\s+E_(?P<c>\w+|\{[^}]+\}))?"
    r"(?:\s+contains\s+E_(?P<d>\w+|\{[^}]+\}))?"
)
LARGER_RE = re.compile(r"C2 is a strictly (larger|smaller) extension class")
WEAKER_RE = re.compile(r"C2-inextendibility is strictly (weaker|stronger)")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_duplicate_top_level_keys(text: str) -> dict:
    """Return {key: count} for duplicate mapping keys anywhere, using strict compose."""
    dups: list[dict] = []

    class DupLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        keys = [str(loader.construct_object(k, deep=deep)) for k, _ in node.value]
        counts = collections.Counter(keys)
        d = {k: c for k, c in counts.items() if c > 1}
        if d:
            dups.append(d)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    DupLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    yaml.load(text, Loader=DupLoader)  # noqa: S506 (local file, strict-compose probe only)
    merged: dict[str, int] = {}
    for d in dups:
        for k, c in d.items():
            merged[k] = max(merged.get(k, 0), c)
    return merged


def chain_from_text(chain_text: str) -> list[str]:
    m = CHAIN_RE.search(chain_text)
    if not m:
        return []
    order = [m.group("a"), m.group("b"), m.group("c"), m.group("d")]
    return [f"E_{x}" for x in order if x]


def line_of(text: str, needle: str) -> int | None:
    for i, ln in enumerate(text.splitlines(), start=1):
        if needle in ln:
            return i
    return None


def run(path: Path, *, expect_canonical: bool, canonical_pin: str = CANONICAL_SHA256) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    measured = hashlib.sha256(raw).hexdigest()
    doc = yaml.safe_load(text) or {}

    checks: dict[str, dict] = {}

    # ---- C1 hash integrity -------------------------------------------------
    if expect_canonical:
        c1_ok = measured == canonical_pin
        checks["C1_canonical_hash_matches_pin"] = {
            "ok": c1_ok,
            "measured_sha256": measured,
            "pinned_sha256": canonical_pin,
            "note": "drift voids the binding, not the wording checks",
        }
    else:
        checks["C1_canonical_hash_matches_pin"] = {
            "ok": None,
            "measured_sha256": measured,
            "note": "control copy: canonical pin not applicable",
        }

    # ---- C2 containment chain ---------------------------------------------
    ledger = doc.get("implication_ledger") or {}
    chain_text = str(ledger.get("extension_class_containment") or "")
    chain = chain_from_text(chain_text)
    chain_ok = chain[:4] == ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]
    checks["C2_chain_declared"] = {
        "ok": chain_ok,
        "measured_chain": chain,
        "expected_chain": ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"],
        "line": line_of(text, "extension_class_containment:"),
        "text": chain_text[:400],
    }

    # ---- C3 forbidden-transfer reason -------------------------------------
    fts = ledger.get("forbidden_transfers") or []
    ft0 = fts[0] if fts and isinstance(fts[0], dict) else {}
    ft0_reason = str(ft0.get("reason") or "")
    lm = LARGER_RE.search(ft0_reason)
    wm = WEAKER_RE.search(ft0_reason)
    size_word = lm.group(1) if lm else None
    # E_C2 is a strict subset of E_C0 (chain above), so "larger" is false and "smaller" is true.
    contradiction = bool(size_word == "larger" and chain_ok)
    checks["C3_forbidden_transfer_reason"] = {
        "ok": not contradiction,
        "line": line_of(text, "C2 is a strictly"),
        "from": ft0.get("from"),
        "to": ft0.get("to"),
        "reason": ft0_reason,
        "class_size_word": size_word,
        "consequent_word": wm.group(1) if wm else None,
        "contradiction": contradiction,
        "derivation": (
            "chain C2 asserts E_C2 is a strict subset of E_C0; therefore the C2 extension set is "
            "strictly smaller, and the phrase 'C2 is a strictly larger extension class' is false "
            "on the file's own containment"
        ),
    }

    # ---- C4 must_not_conflate denial vs ledger ----------------------------
    mnc = (doc.get("regularity") or {}).get("must_not_conflate") or []
    denial = next((str(x) for x in mnc if "No containment with C2 or C0" in str(x)), "")
    entail = ledger.get("one_way_entailments") or []
    ledger_has_containment = bool(entail) or "contains E_" in chain_text
    checks["C4_must_not_conflate_denial"] = {
        "ok": None,  # ambiguity: neither pass nor proven contradiction; adjudicated below
        "line": line_of(text, "No containment with C2 or C0"),
        "sentence": denial,
        "ledger_asserts_containment": ledger_has_containment,
        "contradiction_filewide_reading": bool(denial and ledger_has_containment),
        "contradiction_scoped_reading": False,
        "classification": "scoped-wording-ambiguity" if denial else "sentence-absent",
        "note": (
            "the bullet's subject is the H2_loc regularity-axis entry and the scope word is 'here'; "
            "read file-wide it contradicts the ledger's one-way entailments, read in place it does "
            "not. The defect is that the scope is not explicit."
        ),
    }

    # ---- C5 operative direction re-derived independently -------------------
    # E_C2 strict subset E_C0  =>  (no C0 extension) entails (no C2 extension);
    # so P_C2 is strictly weaker and the transfer P_C2 -> P_C0 must be forbidden.
    expected_forbidden = "no proper future C2 extension"
    decl_from = str(ft0.get("from") or "")
    direction_ok = (
        expected_forbidden in decl_from
        and str(ft0.get("to") or "") in ("this class", "no proper future C0 metric extension")
    ) or ("C2" in decl_from and "C0" in str(ft0.get("to") or ""))
    checks["C5_operative_direction"] = {
        "ok": bool(direction_ok and chain_ok),
        "declared_from": decl_from,
        "declared_to": ft0.get("to"),
        "expected_forbidden_transfer": "P_C2 -> P_C0 (weaker -> stronger)",
        "note": (
            "the prohibition is correct independently of the reason's class-size premise; the "
            "defect is confined to that premise"
        ),
    }

    # ---- C6 duplicate top-level keys --------------------------------------
    dups = strict_duplicate_top_level_keys(text)
    checks["C6_duplicate_top_level_keys"] = {
        "ok": not dups,
        "duplicates": dups,
        "note": "strict-compose duplicate enumeration; yaml.safe_load is last-wins",
    }

    # ---- C7 chain vs entailment rows --------------------------------------
    def rows_ok() -> tuple[bool, list[str]]:
        got: list[str] = []
        for row in entail:
            if not isinstance(row, dict):
                continue
            r = str(row.get("reason") or "")
            f = str(row.get("from") or "")
            t = str(row.get("to") or "")
            if "E_H2loc subset of E_C0" in r:
                got.append("E_H2loc subset E_C0")
            elif "E_C2 subset of E_H2loc" in r:
                got.append("E_C2 subset E_H2loc")
            if "C0" in f and "C2" in t and "transitivity" in r:
                got.append("E_C2 subset E_C0 (transitive)")
        need = {"E_H2loc subset E_C0", "E_C2 subset E_H2loc", "E_C2 subset E_C0 (transitive)"}
        return need.issubset(set(got)), got

    rows_pass, rows_got = rows_ok()
    checks["C7_entailment_rows_consistent_with_chain"] = {
        "ok": bool(rows_pass and chain_ok),
        "rows_derived": rows_got,
        "note": "the one_way_entailments rows assert the same strict subset relations as the chain",
    }

    blocking = [k for k, v in checks.items() if v.get("ok") is False and k in ("C3_forbidden_transfer_reason", "C5_operative_direction", "C7_entailment_rows_consistent_with_chain")]
    ambiguous = [k for k, v in checks.items() if v.get("ok") is None and k == "C4_must_not_conflate_denial"]
    hygiene = [k for k, v in checks.items() if v.get("ok") is False and k == "C6_duplicate_top_level_keys"]

    return {
        "checker": "check_f2b_containment.py",
        "checker_sha256": sha256_file(Path(__file__)),
        "target_path": str(path),
        "target_sha256": measured,
        "target_bytes": len(raw),
        "checks": checks,
        "summary": {
            "blocking_checks_failed": blocking,
            "ambiguity_checks": ambiguous,
            "hygiene_checks_failed": hygiene,
            "containment_contradiction": checks["C3_forbidden_transfer_reason"]["contradiction"],
            "must_not_conflate_ambiguity": bool(denial),
            "operative_transfer_correct": checks["C5_operative_direction"]["ok"],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--control", action="store_true", help="control copy; skip canonical pin")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out = run(Path(a.path), expect_canonical=not a.control)
    if a.json:
        print(json.dumps(out, indent=1, sort_keys=True))
    else:
        print(json.dumps(out["summary"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
