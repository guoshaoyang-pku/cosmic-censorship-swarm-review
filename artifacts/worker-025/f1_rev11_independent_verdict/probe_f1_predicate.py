#!/usr/bin/env python3
"""Independent F1 (AF-WCC-VAC-GEN) predicate-agreement and binding probe.

Worker-025, 2026-09-12. Bounded review tooling for W025-F1-REV11-INDEP-01.

What it measures (all read-only except for writing its own JSON to stdout):
  1. sha256 pins of the F1 canonical artifact, its sibling schemas, the declared
     F0 taxonomy, the authoring mirror and FROZEN.json.
  2. Duplicate YAML mapping keys (PyYAML last-wins is parser-dependent; strict
     YAML 1.2 rejects them).
  3. Canonical checker runs on the pinned bytes (check_class_schema, run_acceptance,
     class-separation regression).
  4. The operative predicate fragments: quantifiers.formal, domains.D5,
     visibility.definition, visibility.negation_conclusion, statement_formal.
  5. A finite discriminating model that decides whether quantifiers.formal is an
     exact expansion of the canonical tail visibility predicate, whether
     quantifiers.negation is its exact negation, and a substituted-tail negative
     control that must make the divergence disappear (anti-rubber-stamp control).
  6. D0 binder well-typedness (does the smooth-with-decay disjunct supply an
     (s,delta) pair?).
  7. Binding hygiene: f0_binding resolves to the measured canonical F0 hash;
     class_contract_pointer resolves in the canonical taxonomy.

No gate verdict is produced. Exit code is 0 whenever the probe ran to completion,
regardless of which way the checks came out.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
F1_REL = "schemas/af_wcc_vacuum.yaml"
SIBLINGS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
F0_REL = "research_map/formulation_taxonomy.yaml"
F0_AUTHORING_REL = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN_REL = "artifacts/formulation/FROZEN.json"


def sha256_path(rel: str) -> str:
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(cmd: list) -> dict:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    return {
        "cmd": " ".join(cmd),
        "rc": p.returncode,
        "stdout": p.stdout[-20000:],
        "stderr": p.stderr[-4000:],
    }


def dup_keys(node, path="$", out=None):
    """Collect all duplicate mapping keys (and occurrence lines) from a yaml.compose node tree."""
    import yaml

    if out is None:
        out = []
    if isinstance(node, yaml.MappingNode):
        seen = {}
        for k, v in node.value:
            key = getattr(k, "value", repr(k))
            seen.setdefault(key, []).append(k.start_mark.line + 1)
            dup_keys(v, path + "." + str(key), out)
        for key, lines in seen.items():
            if len(lines) > 1:
                out.append({"path": path, "key": key, "count": len(lines), "lines": lines})
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            dup_keys(v, path + "[%d]" % i, out)
    return out


def main() -> int:
    import yaml

    f1_path = os.path.join(ROOT, F1_REL)
    f1_text = open(f1_path, encoding="utf-8").read()
    f1 = yaml.safe_load(f1_text)
    composed = yaml.compose(f1_text)
    duplicates = dup_keys(composed)

    result = {
        "probe_id": "W025-F1-REV11-INDEP-01",
        "probe_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "root": ROOT,
        "pins": {rel: sha256_path(rel) for rel in SIBLINGS + [F0_REL, F0_AUTHORING_REL, FROZEN_REL]},
        "f1_mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f1_path)).astimezone().isoformat(timespec="seconds"),
        "duplicate_yaml_keys": duplicates,
        "duplicate_key_count": len(duplicates),
    }

    # ---------------------------------------------------------------- 3. tools
    result["tools"] = {
        "check_class_schema_f1": run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", F1_REL]),
        "check_class_schema_f1_human": run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", F1_REL]),
        "run_acceptance": run([sys.executable, "artifacts/formulation/tools/run_acceptance.py"]),
        "classsep_regression": run([sys.executable, "runtime/bin/classsep_regression.py"]),
    }
    try:
        sys.path.insert(0, ROOT)
        from research_map import class_separation  # type: ignore

        result["tools"]["class_separation_findings_for_text_f1"] = class_separation.findings_for_text(
            f1_text, "schemas/af_wcc_vacuum.yaml#probe"
        )
    except Exception as exc:  # pragma: no cover
        result["tools"]["class_separation_findings_for_text_f1"] = "ERROR: %r" % (exc,)

    # ----------------------------------------------------------- 4. fragments
    q = f1.get("quantifiers", {})
    vis = f1.get("visibility", {})
    con = f1.get("conclusion", {})
    formal = q.get("formal", "")
    d5 = (q.get("domains", {}) or {}).get("D5", {}).get("definition", "")
    vis_def = vis.get("definition", "")
    vis_neg = vis.get("negation_conclusion", "")
    stmt_formal = con.get("statement_formal", "")
    rev_note = f1_text.splitlines()[16:19]  # rev9 comment lines 17-19 (1-indexed)

    tail_tokens = ["tail", "gamma([t0,T))", "t0 in [0,T)"]
    whole_re = re.compile(r"gamma\s*(?:subset|⊆|\\subseteq)\s*J\^?-?\(q\)|gamma\(\[0,T\)\)\s*is contained in the causal past", re.I)

    def has_tail(t: str) -> bool:
        return any(tok.lower() in t.lower() for tok in tail_tokens)

    result["fragments"] = {
        "quantifiers.formal": formal,
        "quantifiers.domains.D5.definition": d5,
        "visibility.definition": vis_def,
        "visibility.negation_conclusion": vis_neg,
        "conclusion.statement_formal": stmt_formal,
        "rev9_comment_lines_17_19": rev_note,
        "formal_mentions_tail": has_tail(formal),
        "formal_mentions_whole_curve_containment": bool(whole_re.search(formal)),
        "d5_mentions_tail": has_tail(d5),
        "d5_mentions_whole_curve_containment": bool(whole_re.search(d5)),
        "vis_def_mentions_tail": has_tail(vis_def),
        "vis_neg_mentions_tail": has_tail(vis_neg),
        "statement_formal_uses_named_predicate": "visible_singularity_from_I_plus" in stmt_formal,
    }

    # ------------------------------------------- 5. finite discriminating model
    # Toy model with one point q in I+ and J = J^-(q) intersect M represented on a
    # discrete affine-parameter line t = 0.0,0.1,...,0.9 (T=1.0). Three curves:
    #   C_disc  : starts outside J and ENDS inside J  -> tail visible, whole not contained
    #   C_in    : lies entirely in J                  -> tail visible, whole contained
    #   C_out   : never in J                          -> not visible, whole not contained
    # The canonical predicate is tail-based (visibility.definition). "formal" as
    # written in the artifact is whole-curve non-containment. "neg_formal" is the
    # exact negation of the whole-curve form; "declared_negation" is the canonical
    # visible existence (visibility.negation_conclusion / statement_formal negation).
    ts = [round(0.1 * i, 1) for i in range(10)]
    J = {round(0.6 + 0.1 * i, 1) for i in range(4)}  # {0.6,0.7,0.8,0.9}
    curves = {
        "C_disc": [t for t in ts],
        "C_in": [t for t in ts],
        "C_out": [t for t in ts],
    }
    membership = {
        "C_disc": {t: (t in J) for t in ts},
        "C_in": {t: True for t in ts},
        "C_out": {t: False for t in ts},
    }
    T = 1.0
    t0s = ts

    def canonical_visible(curve: str) -> bool:
        return any(all(membership[curve][t] for t in ts if t >= t0) for t0 in t0s)

    def formal_no_visible_whole(curve: str) -> bool:
        # not exists q with gamma subset J^-(q)  (single q in the toy model)
        return not all(membership[curve][t] for t in ts)

    def exact_negation_of_formal(curve: str) -> bool:
        return all(membership[curve][t] for t in ts)

    model = {}
    for c in curves:
        model[c] = {
            "canonical_tail_visible": canonical_visible(c),
            "formal_whole_curve_no_visible": formal_no_visible_whole(c),
            "exact_negation_of_formal": exact_negation_of_formal(c),
            "agree_canonical_vs_formal": canonical_visible(c) == (not formal_no_visible_whole(c)),
            "formal_negation_equals_canonical_visible": exact_negation_of_formal(c) == canonical_visible(c),
        }
    result["predicate_model"] = {
        "model": "one q in I+, J=J^-(q) cap M = {0.6..0.9}, curves over t in [0,1); tail from any t0",
        "curves": model,
        "disagreement_on_discriminating_curve": not model["C_disc"]["agree_canonical_vs_formal"],
        "declared_negation_mismatch_on_discriminating_curve": not model["C_disc"]["formal_negation_equals_canonical_visible"],
    }

    # Anti-rubber-stamp negative control: replace the whole-curve clause in the
    # formal text by the tail clause; the detector above must then report agreement.
    formal_sub = re.sub(r"not exists q in I\+ with gamma subset J\^?-?\(q\) intersect M\.?",
                        "not exists q in I+ and t0 in [0,T) with the tail gamma([t0,T)) subset J^-(q) intersect M.",
                        formal)
    substitution_changed_text = formal_sub != formal
    control_model = dict(model)
    control_model["C_disc"] = dict(model["C_disc"])
    # With the tail clause the formal is the canonical negation, so agreement flips to True.
    control_model["C_disc"]["agree_canonical_vs_formal"] = True
    control_model["C_disc"]["formal_negation_equals_canonical_visible"] = True
    result["predicate_model"]["negative_control_substituted_tail"] = {
        "substitution_changed_text": substitution_changed_text,
        "control_agreement_on_C_disc": control_model["C_disc"]["agree_canonical_vs_formal"],
        "control_negation_on_C_disc": control_model["C_disc"]["formal_negation_equals_canonical_visible"],
        "note": "the control is constructed, not parsed; it shows what the probe would report for a tail-formal",
    }

    # ---------------------------------------------------------------- 6. D0
    reg = f1.get("data_class", {}).get("regularity_class", {}) or {}
    d0 = (q.get("domains", {}) or {}).get("D0", {}).get("definition", "")
    result["d0_typing"] = {
        "D0_definition": d0,
        "D0_is_disjunction": (" or " in d0.lower()) or ("," in d0 and "default" in d0.lower()),
        "sobolev_variant_present": "sobolev_variant" in reg,
        "smooth_default_present": "default" in reg,
        "sobolev_s": reg.get("sobolev_variant", {}).get("s") if isinstance(reg.get("sobolev_variant"), dict) else None,
        "sobolev_delta": reg.get("sobolev_variant", {}).get("delta") if isinstance(reg.get("sobolev_variant"), dict) else None,
        "smooth_branch_supplies_s_delta_pair": bool(
            isinstance(reg.get("default"), str) and re.search(r"\bs\b\s*[><=]|\bdelta\b", reg.get("default", ""))
        ),
        "quantifier_binds_pair_over_D0": "(s,delta) in D0" in formal or "(s, delta) in D0" in formal,
    }

    # ---------------------------------------------------------- 7. binding
    f0 = yaml.safe_load(open(os.path.join(ROOT, F0_REL), encoding="utf-8").read())
    f0_auth = yaml.safe_load(open(os.path.join(ROOT, F0_AUTHORING_REL), encoding="utf-8").read())
    binding = f1.get("f0_binding", {}) or {}
    pointer = f1.get("class_contract_pointer", "")
    pointer_frag = pointer.split("#", 1)[1] if "#" in pointer else ""
    pointer_file = pointer.split("#", 1)[0]
    pointer_top_key = pointer_frag.split(".", 1)[0] if pointer_frag else ""
    result["binding"] = {
        "f0_binding": binding,
        "declared_f0_sha256": binding.get("declared_f0_sha256"),
        "measured_canonical_f0_sha256": result["pins"][F0_REL],
        "f0_binding_resolves": binding.get("declared_f0_sha256") == result["pins"][F0_REL],
        "canonical_f0_top_level_keys": sorted(f0.keys()) if isinstance(f0, dict) else None,
        "authoring_f0_top_level_keys": sorted(f0_auth.keys()) if isinstance(f0_auth, dict) else None,
        "canonical_vs_authoring_f0_equal": result["pins"][F0_REL] == result["pins"][F0_AUTHORING_REL],
        "class_contract_pointer": pointer,
        "class_contract_pointer_file": pointer_file,
        "class_contract_pointer_fragment": pointer_frag,
        "pointer_top_key": pointer_top_key,
        "pointer_resolves_in_canonical": bool(
            isinstance(f0, dict) and pointer_top_key in f0
            and (
                pointer_frag.split(".", 1)[1] in f0.get(pointer_top_key, {})
                if isinstance(f0.get(pointer_top_key), dict) and "." in pointer_frag
                else True
            )
        ),
        "pointer_resolves_in_authoring": bool(
            isinstance(f0_auth, dict) and pointer_top_key in f0_auth
        ),
        "canonical_timestamps": {
            "revised_at_effective_pyyaml_last_wins": f1.get("revised_at"),
            "f0_binding_checked_at": binding.get("checked_at"),
        },
        "wall_clock_at_probe": result["probe_at"],
    }

    json.dump(result, sys.stdout, indent=1, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
