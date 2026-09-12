#!/usr/bin/env python3
"""FORM-PROBE-11 / EXEMPT-SURFACE-11 fixture generator (worker-06).

Task: measure the two-stage class-binding pipeline against prose leaks placed in
class-schema surfaces the pipeline does NOT scan by design, at FROZEN rev28.

Method: byte-level single-leaf surgery on the three canonical schemas.
  * each mutant changes exactly ONE leaf (verified by deep diff of the parsed docs);
  * the operative/assertive statement blocks are left byte-identical to canonical;
  * every fixture is re-parsed and asserted to differ from canonical at exactly the
    declared target path.

Surfaces (declared BEFORE any stage run):
  S1 EXEMPT_KEY      -- key subtree the canonical gate marks negative/prescriptive
                        (EXEMPT_KEY in check_class_schema.py), e.g. why_*, *_note,
                        class_change_warning, c0_uniqueness_caveat, forbidden_*.
  S2 UNSCANNED_ASSERT-- non-exempt key, NOT in ASSERTIVE_PATHS: a declarative prose
                        surface that no lexical family rule visits.
  S3 HISTORY_META    -- revision/provenance/status metadata prose.

Fixtures are written ONLY under artifacts/worker-06/exempt11/fixtures/.
Manifest (with sha256 of each fixture) is written BEFORE any stage runs.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
FIX = HERE / "fixtures"
SCHEMAS = {
    "AF-WCC-VAC-GEN": ROOT / "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lines_of(p: Path):
    return p.read_text(encoding="utf-8").split("\n")


def find_key(lines, key, indent, start=0, end=None):
    """Index of the line exactly `' '*indent + key + ':'` (value may follow)."""
    pat = re.compile(r"^" + " " * indent + re.escape(key) + r":")
    end = len(lines) if end is None else end
    for i in range(start, end):
        if pat.match(lines[i]):
            return i
    raise KeyError(f"{key} (indent {indent}) not found in [{start},{end})")


def block_end(lines, i):
    """First line after a mapping value block starting at line i."""
    indent = len(lines[i]) - len(lines[i].lstrip(" "))
    j = i + 1
    while j < len(lines):
        if lines[j].strip() == "":
            j += 1
            continue
        cur = len(lines[j]) - len(lines[j].lstrip(" "))
        if cur <= indent:
            break
        j += 1
    return j


def set_child(lines, parent, key, value, parent_indent=0, child_indent=2):
    pi = find_key(lines, parent, parent_indent)
    pe = block_end(lines, pi)
    ci = find_key(lines, key, child_indent, pi + 1, pe)
    ce = block_end(lines, ci)
    quoted = json.dumps(value, ensure_ascii=False)
    lines[ci:ce] = [" " * child_indent + key + ": " + quoted]
    return lines


def append_list_item(lines, parent, parent_indent, item_indent, value):
    pi = find_key(lines, parent, parent_indent)
    pe = block_end(lines, pi)
    # insert as the first item after the parent key
    lines.insert(pi + 1, " " * item_indent + "- " + json.dumps(value, ensure_ascii=False))
    return lines


def set_revision_note(lines, index, value):
    """Replace notes:[...] of the revision_history entry with this index."""
    ri = find_key(lines, "revision_history", 0)
    re_ = block_end(lines, ri)
    for i in range(ri + 1, re_):
        if re.match(r"^\s*- \{index: " + str(index) + r",", lines[i]):
            new = re.sub(r"notes: \[.*?\]\s*\}",
                         "notes: [" + json.dumps(value, ensure_ascii=False) + "] }", lines[i])
            if new == lines[i]:
                raise ValueError(f"notes list not matched in revision {index}")
            lines[i] = new
            return lines
    raise KeyError(f"revision index {index} not found")


def deep_leaves(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(deep_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(deep_leaves(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = node
    return out


# ---------------------------------------------------------------------------
# Declared corpus.  surface: S1/S2/S3 ; load_bearing: high/medium/low
# family names are leak families, not rule ids.
# ---------------------------------------------------------------------------
MUTANTS = [
    # ---------------- WCC base: inject SCC-family content ----------------
    dict(id="m01", base="AF-WCC-VAC-GEN", path="conclusion.wellformedness_conditions",
         surface="S2", load="high", family="F2-scc-conclusion-in-wcc",
         text=("well-formedness additionally requires that no proper future C2 vacuum extension "
               "of the maximal development exists; otherwise the class is void at the C2 boundary.")),
    dict(id="m02", base="AF-WCC-VAC-GEN", path="known_status.non_transfer_warning",
         surface="S3", load="medium", family="F2-scc-conclusion-in-wcc",
         text=("no ledger entry establishes the C2 inextendibility of generic developments; "
               "strong cosmic censorship remains open and no Cauchy-horizon statement transfers here.")),
    dict(id="m03", base="AF-WCC-VAC-GEN", path="quantifiers.order_note",
         surface="S2", load="medium", family="F9-direction-extension",
         text=("the extension quantifier is a negated existential over proper future C2 extensions "
               "of the given maximal development, and it must follow the data quantifier.")),
    dict(id="m04", base="AF-WCC-VAC-GEN", path="visibility.observability_note",
         surface="S1", load="low", family="F3-iplus-completeness",
         text=("a complete future null infinity is the operative conclusion here; an incomplete "
               "generator of I+ is a statement about the C2-inextendibility class instead.")),
    dict(id="m05", base="AF-WCC-VAC-GEN", path="adjudication_queue.note",
         surface="S3", load="low", family="F5-theorem-promotion",
         text=("the open row is settled: the maximal development is future-inextendible in the "
               "C2 class for a comeager set of one-ended AF vacuum data.")),
    dict(id="m06", base="AF-WCC-VAC-GEN", path="genericity.class_change_warning",
         surface="S1", load="high", family="F4-genericity-transfer",
         text=("the full-measure form of strong cosmic censorship may be substituted for the "
               "comeager form here without loss; the transfer is asserted, not merely recorded.")),
    dict(id="m07", base="AF-WCC-VAC-GEN", path="conclusion.forbidden_strengthenings",
         surface="S1", load="low", family="F2-scc-conclusion-in-wcc", mode="append_item",
         text=("the C2-inextendibility of the maximal development (legitimately forbidden here)")),
    # ---------------- F2a base: inject WCC-family content ----------------
    dict(id="m08", base="AF-SCC-C2-VAC-GEN", path="conclusion.known_obstruction",
         surface="S2", load="high", family="F1-wcc-conclusion-in-scc",
         text=("for exact Kerr data the maximal development contains a visible incomplete causal "
               "geodesic from I+, so the visible-singularity conclusion fails on a non-meager set.")),
    dict(id="m09", base="AF-SCC-C2-VAC-GEN", path="non_vacuity.c2_specific_note",
         surface="S2", load="medium", family="F1-wcc-conclusion-in-scc",
         text=("the class must also exclude a visible singularity; otherwise weak cosmic censorship "
               "is the operative statement and this schema is mislabelled.")),
    dict(id="m10", base="AF-SCC-C2-VAC-GEN", path="extension_predicate.why_future_not_two_sided",
         surface="S1", load="low", family="F1-wcc-conclusion-in-scc",
         text=("a visible incomplete causal geodesic from I+ would refute the statement whenever "
               "the failure set is non-meager; visibility is therefore the operative predicate.")),
    dict(id="m11", base="AF-SCC-C2-VAC-GEN", path="genericity.ambient_space",
         surface="S2", load="high", family="F1-wcc-conclusion-in-scc",
         text=("the ambient space is the set of one-ended AF vacuum data whose maximal development "
               "has a visible incomplete causal geodesic from I+, topologised as in the WCC class.")),
    dict(id="m12", base="AF-SCC-C2-VAC-GEN", path="revision_history[9].notes[0]",
         surface="S3", load="low", family="F6-provenance-status-overclaim", mode="revision_note",
         rev_index=10,
         text=("rev12 delta: republished after the visible-singularity formulation was proved for "
               "this class; the visibility conclusion is now established.")),
    dict(id="m13", base="AF-SCC-C2-VAC-GEN", path="known_status.strongest_caveat",
         surface="S3", load="medium", family="F6-provenance-status-overclaim",
         text=("the strongest published support establishes the visible-singularity statement for "
               "this class; no caveat about preprint-level support survives.")),
    dict(id="m14", base="AF-SCC-C2-VAC-GEN", path="conventions.proof_status",
         surface="S2", load="medium", family="F5-theorem-promotion",
         text=("open_problem no longer applies: the visible-singularity theorem is proved for this "
               "class, so the schema now carries a truth value.")),
    dict(id="m15", base="AF-SCC-C2-VAC-GEN", path="genericity.class_change_warning",
         surface="S1", load="high", family="F4-genericity-transfer",
         text=("the full-measure form is equivalent to the comeager form for this class; weak "
               "cosmic censorship therefore transfers to every data set.")),
    # ---------------- F2b base: inject WCC-family content ----------------
    dict(id="m16", base="AF-SCC-C0-VAC-GEN", path="conclusion.known_obstruction",
         surface="S2", load="high", family="F1-wcc-conclusion-in-scc",
         text=("the Kerr exterior contains a visible incomplete causal geodesic from I+, which is "
               "the operative counterexample to the visible-singularity reading of this class.")),
    dict(id="m17", base="AF-SCC-C0-VAC-GEN", path="non_vacuity.c0_specific_note",
         surface="S2", load="medium", family="F1-wcc-conclusion-in-scc",
         text=("a C2 result on visible singularities is enough for this class; the continuous-"
               "extension conclusion follows from weak cosmic censorship.")),
    dict(id="m18", base="AF-SCC-C0-VAC-GEN", path="extension_predicate.c0_uniqueness_caveat",
         surface="S1", load="low", family="F9-direction-extension",
         text=("a visible incomplete geodesic from I+ is the obstruction used by the proof, so "
               "visibility may be assumed when applying this class.")),
    dict(id="m19", base="AF-SCC-C0-VAC-GEN", path="c0_specifics.conclusion_relation_to_sibling",
         surface="S2", load="high", family="F1-wcc-conclusion-in-scc",
         text=("the sibling class's visible-singularity conclusion is the operative one; the "
               "continuous-extension reading is a separate statement that adds no strength.")),
    dict(id="m20", base="AF-SCC-C0-VAC-GEN", path="known_status.why_this_class_is_not_recorded_as_refuted",
         surface="S1", load="medium", family="F6-provenance-status-overclaim",
         text=("the visible-singularity proof of T-301 settles this class, so the quarantine to "
               "the horizon-localized variant can be lifted and the class recorded as refuted.")),
    dict(id="m21", base="AF-SCC-C0-VAC-GEN", path="provenance.no_progress_claim",
         surface="S1", load="low", family="F6-provenance-status-overclaim",
         text=("the class is refuted by the visible-singularity counterexample, so no further "
               "status claim is needed from L1.")),
    dict(id="m22", base="AF-SCC-C0-VAC-GEN", path="quantifiers.order_note",
         surface="S2", load="medium", family="F1-wcc-conclusion-in-scc",
         text=("the comeager set is chosen after observing the visible singularity, so the "
               "visibility predicate may depend on the data.")),
    # ---------------- explicit calibration positives (expected CAUGHT) ----------------
    dict(id="c01", base="AF-SCC-C2-VAC-GEN", path="i_plus.definition",
         surface="S2", load="high", family="CAL-positive-assertive-field",
         expect="caught", text=("AF structure at future null infinity; a visible incomplete causal "
                                "geodesic from I+ is the conclusion of this class.")),
    dict(id="c02", base="AF-SCC-C0-VAC-GEN", path="conclusion.statement_formal",
         surface="S2", load="high", family="CAL-positive-assertive-field",
         expect="caught", text=("forall r in D0 exists G_r comeager forall D in G_r: there is a "
                                "visible incomplete causal geodesic from I+.")),
    dict(id="c03", base="AF-WCC-VAC-GEN", path="genericity.ambient_space",
         surface="S2", load="high", family="CAL-positive-composite-non-exempt",
         expect="caught", text=("the ambient space is the C0 or C2 extension class of one-ended "
                                "asymptotically flat vacuum data.")),
    # ---------------- legitimate negative controls (expected PASS) ----------------
    dict(id="n01", base="AF-SCC-C2-VAC-GEN", path="visibility.reason",
         surface="S1", load="low", family="CAL-negative-legitimate",
         expect="pass", text=("visibility from I+ is the WCC predicate and is NOT asserted here; a "
                              "visible incomplete causal geodesic is a WCC falsifier and is "
                              "explicitly forbidden as this class's conclusion.")),
    dict(id="n02", base="AF-SCC-C0-VAC-GEN", path="extension_predicate.c0_uniqueness_caveat",
         surface="S1", load="low", family="CAL-negative-legitimate",
         expect="pass", text=("two-sided inextendibility is a different, strictly stronger statement "
                              "and is excluded by construction; this class asserts the future "
                              "direction only.")),
    dict(id="n03", base="AF-WCC-VAC-GEN", path="conclusion.forbidden_strengthenings",
         surface="S1", load="low", family="CAL-negative-legitimate", mode="append_item",
         expect="pass", text=("future C2-inextendibility of the maximal development (forbidden "
                              "strengthening, not this class)")),
]

CANONICAL_CONTROLS = ["p01", "p02", "p03"]


def apply_mutation(base_path: Path, spec: dict):
    lines = lines_of(base_path)
    mode = spec.get("mode", "scalar")
    parent, _, child = spec["path"].partition(".")
    if mode == "scalar":
        # resolve indents by searching the parent block
        pi = find_key(lines, parent, 0)
        pe = block_end(lines, pi)
        # support one extra nesting level (a.b.c)
        rest = spec["path"].split(".")
        cur_start, cur_end, cur_indent = pi + 1, pe, 2
        key = rest[-1]
        for lvl in range(1, len(rest) - 1):
            nxt = rest[lvl]
            ni = find_key(lines, nxt, cur_indent, cur_start, cur_end)
            ne = block_end(lines, ni)
            cur_start, cur_end, cur_indent = ni + 1, ne, cur_indent + 2
        ci = find_key(lines, key, cur_indent, cur_start, cur_end)
        ce = block_end(lines, ci)
        lines[ci:ce] = [" " * cur_indent + key + ": " + json.dumps(spec["text"], ensure_ascii=False)]
    elif mode == "append_item":
        rest = spec["path"].split(".")
        ci = find_key(lines, rest[0], 0)
        ce = block_end(lines, ci)
        indent = 2
        for lvl in range(1, len(rest)):
            ci = find_key(lines, rest[lvl], indent, ci + 1, ce)
            ce = block_end(lines, ci)
            if lvl < len(rest) - 1:
                indent += 2
        lines.insert(ce, " " * (indent + 2) + "- " + json.dumps(spec["text"], ensure_ascii=False))
    elif mode == "revision_note":
        lines = set_revision_note(lines, int(spec["rev_index"]), spec["text"])
    else:
        raise ValueError(mode)
    return "\n".join(lines)


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    manifest = {"artifact": "FORM-PROBE-11-EXEMPT-SURFACE-CORPUS", "generated_by": "worker-06",
                "pins": {}, "fixtures": []}
    for cid, p in SCHEMAS.items():
        manifest["pins"][str(p.relative_to(ROOT))] = sha(p)
    # canonical pass controls
    for i, (cid, p) in enumerate(SCHEMAS.items(), 1):
        fid = f"p0{i}"
        dst = FIX / f"{fid}_{cid.lower().replace('-', '_')}_canonical.yaml"
        dst.write_bytes(p.read_bytes())
        manifest["fixtures"].append(dict(id=fid, kind="canonical_pass_control", base=cid,
                                         path="(none)", surface="P0", load="high",
                                         family="CONTROL-canonical", expect="pass",
                                         file=str(dst.relative_to(ROOT)), sha256=sha(dst)))
    for spec in MUTANTS:
        base = SCHEMAS[spec["base"]]
        text = apply_mutation(base, spec)
        name = spec["path"].replace(".", "_").replace("[", "").replace("]", "")
        dst = FIX / f"{spec['id']}_{spec['base'].lower().replace('-', '_')}_{name}.yaml"
        dst.write_text(text, encoding="utf-8")
        # ---- verify single-leaf mutation ----
        a = deep_leaves(yaml.safe_load(base.read_text(encoding="utf-8")))
        b = deep_leaves(yaml.safe_load(dst.read_text(encoding="utf-8")))
        changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        target = spec["path"]
        ok = all(k == target or k.startswith(target + "[") for k in changed) and changed
        if not ok:
            print(f"FATAL {spec['id']}: mutation touched {changed}", file=sys.stderr)
            sys.exit(3)
        if spec.get("mode") == "append_item":
            ok2 = len([k for k in changed if k.startswith(target)]) == 1
        else:
            ok2 = changed == [target]
        if not ok2:
            print(f"FATAL {spec['id']}: expected exactly [{target}], got {changed}", file=sys.stderr)
            sys.exit(3)
        manifest["fixtures"].append(dict(
            id=spec["id"], kind="mutant" if spec.get("expect") is None else "calibration_control",
            base=spec["base"], path=target, surface=spec["surface"], load=spec["load"],
            family=spec["family"], expect=spec.get("expect", "unchanged_by_design"),
            text=spec["text"], changed_leaves=changed,
            file=str(dst.relative_to(ROOT)), sha256=sha(dst)))
    mpath = HERE / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "manifest.sha256").write_text(sha(mpath) + "  manifest.json\n", encoding="utf-8")
    print(f"wrote {len(manifest['fixtures'])} fixtures; manifest sha256 {sha(mpath)}")


if __name__ == "__main__":
    main()
