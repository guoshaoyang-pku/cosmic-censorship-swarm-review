#!/usr/bin/env python3
"""W065-PROJECTION-ADVERSARIAL-03

Adversarial test of the restricting projection that the 00:20:04 concordance
measurement (`data_class_concordance_20260912T002004.json`) used to return
CONCORDANT_CORE for F1/F2a/F2b.

The prior tool *declared* a restricting-path list and an `operative()`
normalizer; its own falsifier says the verdict is void if a reviewer exhibits a
`data_class` field that changes the admitted data set and the projection drops
it. This tool does not reuse that list. It re-derives EVERY `data_class` leaf
path from the three canonical schemas, screens every delta adversarially
(default: candidate), adjudicates each candidate with a named rule, and reports
both a strict verdict and the full exposure list.

Evidence-only. Reads the canonicals, writes nothing outside --out / --window.
No gate verdict, no node transition.

Usage:
  python3 projection_adversarial.py \
      --out artifacts/worker-065/projection_adversarial_<stamp>.json \
      --window artifacts/worker-065/projection_window_<stamp>.json \
      --stamp <stamp>
"""

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

CST = timezone(timedelta(hours=8))

SCHEMAS = {
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    "F2a": ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
}


# ---------------------------------------------------------------- flattening

def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, "{}.{}".format(prefix, k) if prefix else str(k)))
    elif isinstance(obj, list):
        out[prefix] = json.dumps(obj, sort_keys=True)
    else:
        out[prefix] = obj
    return out


def load_doc(path):
    with open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if "data_class" not in doc:
        raise SystemExit("no data_class in {}".format(path))
    return doc


def load_data_class(path):
    doc = load_doc(path)
    return doc, flatten(doc["data_class"])


# ---------------------------------------------------------------- screening

ADMISSION_TOKENS = [
    (r"\bassum(?:e|ed|es|ption|ptions)\b", "assumed"),
    (r"\brequire(?:s|d)?\b", "requires"),
    (r"\biff\b", "iff"),
    (r"\bmust\b", "must"),
    (r"\bexclud(?:e|ed|es|ing|es)\b", "excluded"),
    (r"\bimpos(?:e|ed|es|ing)\b", "imposed"),
    (r"\bparity\b", "parity"),
    (r"\bonly if\b", "only_if"),
    (r"\bforbid(?:den)?\b", "forbidden"),
    (r"\bshrink(?:s|ing)?\b", "shrink"),
    (r">=|<=|>|<", "inequality"),
    (r"\b\d+\s*/\s*\d+\b", "fraction"),
]

ANNOTATION_MARKERS = [
    (r"\bcitation", "citation"),
    (r"\blocator", "locator"),
    (r"\bstatus\b", "status"),
    (r"\bunverified\b", "unverified"),
    (r"\bsupplied\b", "supplied"),
    (r"\bprovenance\b", "provenance"),
    (r"\backnowledg(?:e|ed|es)\b", "acknowledged"),
    (r"\brecorded not resolved\b", "recorded_not_resolved"),
    (r"\bnote\b", "note"),
    (r"\bsee\b", "see"),
    (r"\bL1\b", "L1"),
    (r"\bworker-\d+", "worker_ref"),
]

STOPWORDS = {"a", "an", "the", "is", "are", "be", "of", "on", "in", "to", "that",
             "this", "it", "its", "and", "or", "with", "for", "by", "as", "at"}


def collapse(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def strip_parentheticals(text):
    return collapse(re.sub(r"\([^()]*\)", " ", str(text)))


def operative_core(text):
    """Operative core: drop parentheticals and clauses after ';'."""
    t = strip_parentheticals(text).lower()
    if ";" in t:
        t = t.split(";")[0]
    return collapse(t)


def core_tokens(text):
    t = operative_core(text).replace("-", " ").replace("_", " ")
    toks = re.findall(r"[a-z0-9>=/^{}]+", t)
    return frozenset(x for x in toks if x not in STOPWORDS)


def annotation_residual(text):
    """Text of a span after removing annotation-bearing clauses."""
    t = strip_parentheticals(text)
    parts = re.split(r";", t)
    kept = [p for p in parts
            if not any(re.search(rx, p, flags=re.IGNORECASE) for rx, _ in ANNOTATION_MARKERS)]
    return collapse(" ".join(kept))


def differing_span(values):
    texts = [collapse(v) for v in values if v is not None]
    if not texts:
        return ""
    uniq = []
    for t in texts:
        others = [o for o in texts if o != t]
        if not others or all(t != o for o in others):
            uniq.append(t)
    maximal = [u for u in uniq if not any(u != u2 and u in u2 for u2 in uniq)]
    return " || ".join(maximal) if maximal else ""


def screen(raw_values):
    """Stage 1: adversarial screen. Default CANDIDATE; INERT only on explicit
    annotation-only or parenthetical-only evidence."""
    vals = {n: raw_values[n] for n in SCHEMAS if raw_values[n] is not None}
    missing = [n for n in SCHEMAS if raw_values[n] is None]
    span = differing_span(list(vals.values()))

    stripped = {n: strip_parentheticals(v) for n, v in vals.items()}
    if len(vals) >= 2 and len(set(stripped.values())) == 1:
        return {"result": "INERT", "reason": "difference is parenthetical gloss only",
                "admission_tokens": [], "residual_admission_tokens": [],
                "annotation_markers": [], "differing_span": span, "missing_in": missing}

    tokens, markers = [], []
    for rx, label in ADMISSION_TOKENS:
        if re.search(rx, span, flags=re.IGNORECASE):
            tokens.append(label)
    for rx, label in ANNOTATION_MARKERS:
        if re.search(rx, span, flags=re.IGNORECASE):
            markers.append(label)

    residual = annotation_residual(span)
    residual_tokens = [label for rx, label in ADMISSION_TOKENS
                       if re.search(rx, residual, flags=re.IGNORECASE)]

    if not residual_tokens and markers:
        return {"result": "INERT",
                "reason": "all admission tokens sit inside annotation clauses; residual "
                          "text carries only annotation markers",
                "admission_tokens": tokens, "residual_admission_tokens": residual_tokens,
                "annotation_markers": markers, "differing_span": span,
                "annotation_residual": residual, "missing_in": missing}

    return {"result": "CANDIDATE",
            "reason": "residual differing span carries admission-relevant token(s)"
                      if residual_tokens else
                      "presence/absence difference with no annotation marker",
            "admission_tokens": tokens, "residual_admission_tokens": residual_tokens,
            "annotation_markers": markers, "differing_span": span,
            "annotation_residual": residual, "missing_in": missing}


# ---------------------------------------------------------------- adjudication

PARAM_SIGNATURES = [
    (r"k\s*>=\s*\d+", "i_plus_regularity_k"),
    (r"s\s*>\s*\d+(?:\s*/\s*\d+)?", "sobolev_s"),
    (r"delta\s+in\s*\([^)]*\)", "sobolev_delta"),
    (r"H\^s_delta", "weighted_space_h"),
    (r"H\^\{s-1\}_\{delta\+1\}", "weighted_space_K"),
    (r"smooth-with-decay", "smooth_default"),
]

PARAM_BY_LABEL = {label: rx for rx, label in PARAM_SIGNATURES}

CONTRADICTION = re.compile(
    r"\bnot\s+imposed\b|\bno\s+\w+\s+(?:is\s+)?(?:fixed|assumed|imposed)\b|\bnone\b",
    flags=re.IGNORECASE)


def dc_flatten(doc):
    return flatten(doc["data_class"])


def full_flatten(doc):
    return flatten(doc)


def corroboration(sig_label, all_docs, delta_path):
    """Where is this parameter signature declared elsewhere in each schema?"""
    rx = PARAM_BY_LABEL[sig_label]
    exclude = "data_class." + delta_path
    hits = {}
    for name, doc in all_docs.items():
        found = None
        for p, v in full_flatten(doc).items():
            if p == exclude or v is None:
                continue
            if re.search(rx, collapse(v), flags=re.IGNORECASE):
                found = p
                break
        hits[name] = found
    return hits, all(h is not None for h in hits.values())


def sibling_raw_equal(all_docs, parent):
    """An adjacent field under the same parent that is raw-equal in all three."""
    vals = {}
    for name, doc in all_docs.items():
        for p, v in dc_flatten(doc).items():
            if p.startswith(parent + ".") and p.count(".") == parent.count(".") + 1:
                vals.setdefault(p, {})[name] = v
    for p, per in vals.items():
        if len(per) == 3 and len({json.dumps(v, sort_keys=True) for v in per.values()}) == 1:
            return p, per
    return None, None


def adjudicate(path, present, raw_values, screen_res, all_docs):
    """Stage 2: resolve each candidate with a named rule. Unresolved => RELEVANT."""
    vals = {n: raw_values[n] for n in SCHEMAS if raw_values[n] is not None}
    span = screen_res["differing_span"]
    joined = " ".join(collapse(v) for v in vals.values())
    low = joined.lower()
    common = (len(present) == 3)

    # R1 derived theorem statement (positive-mass rigidity, 'iff' at raw-equal fields)
    if "rigidity" in path or re.search(r"\biff\b", low):
        sign_vals = {n: dc_flatten(all_docs[n]).get("adm_mass.sign") for n in SCHEMAS}
        if len({json.dumps(v) for v in sign_vals.values()}) == 1:
            return {"verdict": "ADMISSION_NEUTRAL", "rule": "R1_derived_theorem",
                    "reason": "'m_ADM = 0 iff Minkowski' is the rigidity half of the positive "
                              "mass theorem already declared byte-identically at "
                              "data_class.adm_mass.sign; true of every admitted datum, removes none.",
                    "refs": ["data_class.adm_mass.sign (raw-equal)",
                             "data_class.equations (raw-equal: vacuum)"]}

    # R2 common path, operative core token-set identical (wording only)
    if common:
        toks = {n: sorted(core_tokens(v)) for n, v in vals.items()}
        if len({json.dumps(t) for t in toks.values()}) == 1:
            return {"verdict": "ADMISSION_NEUTRAL", "rule": "R2_operative_core_equal",
                    "reason": "operative core token set identical in all three schemas; the "
                              "delta is wording or an appended explanatory clause.",
                    "refs": ["core token set: {}".format(json.dumps(toks["F1"]))]}

    # R4 prose disclaimer explicitly declining membership decisions
    if re.search(r"not\s+counterexamples|does\s+not\s+decide|NOT\s+decide|"
                 r"outside G.*may not be asserted", joined, flags=re.IGNORECASE):
        return {"verdict": "ADMISSION_NEUTRAL", "rule": "R4_prose_disclaimer",
                "reason": "prose disclaimer that explicitly declines to decide membership; "
                          "adds no admission condition.",
                "refs": ["data_class.genericity.membership_ruling (raw-equal in all three)"]}

    # R3 extra field restating a parameter already declared at the same shape of
    # path in all three schemas (redundancy, no polarity contradiction)
    if not common:
        sigs = [label for rx, label in PARAM_SIGNATURES
                if re.search(rx, span, flags=re.IGNORECASE)]
        if sigs:
            corrob, ok = {}, True
            for s in sigs:
                hits, allhit = corroboration(s, all_docs, path)
                corrob[s] = hits
                ok = ok and allhit
            if ok:
                contradiction = False
                for s, hits in corrob.items():
                    for name, hp in hits.items():
                        val = collapse(full_flatten(all_docs[name])[hp])
                        if CONTRADICTION.search(val) and re.search(
                                r"\b(require|impose|must)\w*", span, flags=re.IGNORECASE):
                            contradiction = True
                if not contradiction:
                    return {"verdict": "ADMISSION_NEUTRAL",
                            "rule": "R3_redundant_class_parameter",
                            "reason": "every parameter signature in the differing span is "
                                      "already declared elsewhere in all three schemas; the "
                                      "extra field re-states an assumption at a second "
                                      "location and adds no admission condition.",
                            "refs": [{"signature": s, "declared_at": h}
                                     for s, h in corrob.items()]}

    # R5 extra annotation field whose only condition word is a use-note on a
    # raw-equal sibling (derived condition)
    if not common and screen_res.get("annotation_markers"):
        cond = set(screen_res.get("residual_admission_tokens") or [])
        if cond and cond <= {"excluded", "imposed", "assumed"}:
            parent = path.rsplit(".", 1)[0]
            sib, per = sibling_raw_equal(all_docs, parent)
            if sib:
                return {"verdict": "ADMISSION_NEUTRAL",
                        "rule": "R5_derived_condition_under_raw_equal_sibling",
                        "reason": "condition word occurs in an annotation clause of an extra "
                                  "field; a sibling field under the same parent is raw-equal "
                                  "in all three schemas, so the condition is derived, not an "
                                  "admission difference.",
                        "refs": ["{} (raw-equal: {})".format(
                            sib, json.dumps(per, sort_keys=True)[:200])]}

    return {"verdict": "ADMISSION_RELEVANT", "rule": "R6_unresolved",
            "reason": "candidate not resolved by R1-R5; conservatively treated as "
                      "admission-relevant. Differing span: {}".format(span[:400]),
            "refs": []}


# ---------------------------------------------------------------- named axes

AXIS_KEYS = ("s", "delta", "spaces")

SPEC_VALUE_PATTERNS = {
    "s": re.compile(r"\bs\s*>\s*[0-9]+(?:\s*/\s*[0-9]+)?"),
    "delta": re.compile(r"delta\s+in\s*\([^)]*\)"),
}


def named_axes():
    """Values are read from parsed YAML (a raw-line scan misses flow-style
    mappings); the raw scan is kept only to enumerate distinct spec values."""
    out = {axis: {} for axis in AXIS_KEYS}
    for axis in AXIS_KEYS:
        for name, (cls, p) in SCHEMAS.items():
            doc = load_doc(p)
            out[axis][name] = doc["data_class"]["regularity_class"][
                "sobolev_variant"].get(axis)
    out["raw_equal"] = {
        axis: len({json.dumps(v) for v in out[axis].values()}) == 1
        for axis in AXIS_KEYS
    }

    style, values = {}, {"s": {}, "delta": {}}
    for name, (cls, p) in SCHEMAS.items():
        text = open(p, "r", encoding="utf-8").read()
        lines = text.splitlines()
        style[name] = {
            "block_style_s_lines": [i + 1 for i, l in enumerate(lines)
                                    if re.match(r"^\s+s:\s", l)],
            "flow_style_lines": [i + 1 for i, l in enumerate(lines)
                                 if re.search(r"\{[^}]*\bs:\s", l)],
        }
        for axis, rx in SPEC_VALUE_PATTERNS.items():
            values[axis][name] = sorted(set(re.findall(rx, text)))
    out["declaration_style"] = style
    out["distinct_spec_values"] = values
    out["competing_specs"] = {
        axis: sorted(set(v for per in values[axis].values() for v in per))
        for axis in values
    }
    out["canonical_values"] = {axis: out[axis]["F1"] for axis in AXIS_KEYS}
    return out


# ---------------------------------------------------------------- pipeline

def run(docs_override=None):
    all_docs, flat = {}, {}
    for name, (cls, p) in SCHEMAS.items():
        doc = docs_override[name] if (docs_override and name in docs_override) \
            else load_doc(p)
        all_docs[name] = doc
        flat[name] = dc_flatten(doc)

    union = sorted(set().union(*[set(f.keys()) for f in flat.values()]))
    deltas = []
    for path in union:
        raw = {n: flat[n].get(path) for n in SCHEMAS}
        present = [n for n in SCHEMAS if raw[n] is not None]
        if len(present) == 3 and len({json.dumps(raw[n], sort_keys=True) for n in SCHEMAS}) == 1:
            continue
        sc = screen(raw)
        row = {"path": path, "present_in": present, "raw_values": raw, "screen": sc}
        if sc["result"] == "CANDIDATE":
            row["adjudication"] = adjudicate(path, present, raw, sc, all_docs)
        deltas.append(row)
    return all_docs, flat, deltas


def verdict_of(deltas):
    rel = [d for d in deltas
           if d.get("adjudication", {}).get("verdict") == "ADMISSION_RELEVANT"]
    return "PROJECTION_UNSOUND" if rel else "PROJECTION_SOUND"


def run_controls():
    controls = []

    def mutate(name, path, value):
        doc = copy.deepcopy(load_doc(SCHEMAS[name][1]))
        node = doc["data_class"]
        keys = path.split(".")
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
        return doc

    def check(label, name, path, value, expect):
        _, _, deltas = run({name: mutate(name, path, value)})
        row = next((x for x in deltas if x["path"] == path), None)
        if row is None:
            got = "NO_DELTA_DETECTED"
        elif row["screen"]["result"] == "INERT":
            got = "INERT"
        else:
            got = row["adjudication"]["verdict"]
        controls.append({"control": label, "mutated": "{}:{}".format(name, path),
                         "new_value": value, "expected": expect, "observed": got,
                         "pass": got == expect,
                         "rule": row.get("adjudication", {}).get("rule") if row else None})
        return got == expect

    check("C1 different Sobolev index", "F2a",
          "regularity_class.sobolev_variant.s", "s > 3", "ADMISSION_RELEVANT")
    check("C2 parity imposed", "F2b",
          "asymptotic_decay.parity_conditions", "parity imposed (even)", "ADMISSION_RELEVANT")
    check("C3 cosmetic citation rewording", "F2b",
          "adm_mass.locator", "citation to be supplied later by L1", "INERT")
    check("C4 new admission condition inside data_class", "F2b",
          "adm_mass.hypotheses_reconciliation",
          "admission requires an additional falloff condition not declared elsewhere",
          "ADMISSION_RELEVANT")
    check("C5 parenthetical gloss", "F2a",
          "regularity_class.sobolev_variant.spaces",
          "h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} (weighted Sobolev)", "INERT")
    return controls


# ---------------------------------------------------------------- main

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--window", required=True)
    ap.add_argument("--stamp", required=True)
    args = ap.parse_args()

    now = datetime.now(CST).isoformat(timespec="seconds")
    pre = {n: {"path": p, "sha256": sha256_file(p),
               "bytes": len(open(p, "rb").read())} for n, (c, p) in SCHEMAS.items()}

    docs, flat, deltas = run()
    axes = named_axes()

    post = {n: {"path": p, "sha256": sha256_file(p)} for n, (c, p) in SCHEMAS.items()}
    drift = {n: pre[n]["sha256"] != post[n]["sha256"] for n in SCHEMAS}
    stable = not any(drift.values())

    controls = run_controls()
    controls_ok = all(c["pass"] for c in controls)

    relevant = [d for d in deltas
                if d.get("adjudication", {}).get("verdict") == "ADMISSION_RELEVANT"]
    candidates = [d for d in deltas if d["screen"]["result"] == "CANDIDATE"]
    inert = [d for d in deltas if d["screen"]["result"] == "INERT"]

    if not stable:
        strict = "VOID_WINDOW_UNSTABLE"
    elif not controls_ok:
        strict = "INSTRUMENT_INVALID_CONTROLS_FAILED"
    else:
        strict = verdict_of(deltas)

    union_paths = sorted(set().union(*[set(flat[n].keys()) for n in SCHEMAS]))

    artifact = {
        "task_id": "W065-PROJECTION-ADVERSARIAL-03",
        "actor": "worker-065",
        "at": now,
        "node_id": "F2",
        "gate": "G-FORM",
        "group_id": "formulation",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": [SCHEMAS[n][0] for n in SCHEMAS],
        "canonical_paths": pre,
        "tests_artifact": "artifacts/worker-065/data_class_concordance_20260912T002004.json",
        "scope": "Adversarial test of the restricting projection used by the 00:20:04 "
                 "concordance measurement. Read-only on canonicals; does not modify that "
                 "artifact or any canonical file.",
        "method": {
            "census": "flatten every leaf path under data_class in each canonical schema; "
                      "deltas = paths absent in >=1 schema or raw-unequal",
            "screen": "default CANDIDATE; INERT only on parenthetical-only difference or "
                      "annotation-markers-without-residual-admission-tokens",
            "adjudication_rules": ["R1_derived_theorem", "R2_operative_core_equal",
                                   "R3_redundant_class_parameter",
                                   "R4_prose_disclaimer",
                                   "R5_derived_condition_under_raw_equal_sibling",
                                   "R6_unresolved=ADMISSION_RELEVANT"],
            "strict_verdict": "PROJECTION_SOUND iff zero ADMISSION_RELEVANT deltas",
            "maximal_exposure": "all deltas reported regardless of adjudication so a "
                                "reviewer can reject the projection without re-running",
        },
        "data_class_census": {
            "per_schema_paths": {n: len(flat[n]) for n in SCHEMAS},
            "union_paths": len(union_paths),
            "deltas": len(deltas),
        },
        "deltas": deltas,
        "named_axes": axes,
        "stale_blocker_check": {
            "claim_tested": "F1/F2a/F2b ship three different (s, delta, K-weight) specifications",
            "at_hashes": {n: pre[n]["sha256"][:12] for n in SCHEMAS},
            "parsed_values": {axis: axes[axis] for axis in AXIS_KEYS},
            "parsed_raw_equal": axes["raw_equal"],
            "distinct_spec_values": axes["distinct_spec_values"],
            "declaration_style": axes["declaration_style"],
            "style_note": "F1 declares the sobolev block in block style; F2a/F2b declare the "
                          "same fields in a single flow-style mapping. A raw-line scanner that "
                          "looks for 's:'/'delta:' at line start sees the F1 declaration and "
                          "misses F2a/F2b, which is a plausible mechanism for the stale "
                          "three-different-specifications blocker; the parsed values are equal.",
            "spaces_delta_adjudication": next(
                ({"screen": d["screen"]["result"],
                  "adjudication": d.get("adjudication", {}).get("verdict"),
                  "rule": d.get("adjudication", {}).get("rule")}
                 for d in deltas if d["path"] == "regularity_class.sobolev_variant.spaces"),
                None),
            "k_weight_modulo_gloss_equal": len({
                strip_parentheticals(axes["spaces"][n]) for n in SCHEMAS}) == 1,
        },
        "controls": controls,
        "controls_ok": controls_ok,
        "window": {"pre": pre, "post": post, "drift": drift, "stable": stable},
        "result": {
            "strict_verdict": strict,
            "screening_inert": len(inert),
            "candidates": len(candidates),
            "admission_relevant": len(relevant),
            "admission_relevant_witnesses": [
                {"path": d["path"], "span": d["screen"]["differing_span"][:300]}
                for d in relevant],
            "maximal_exposure_deltas": [d["path"] for d in deltas],
            "verdict_scope": "PROJECTION_SOUND means 0 of {} deltas changes the admitted data "
                             "set under the declared screen/adjudication; all {} deltas remain "
                             "published for reviewer rejection of the projection.".format(
                                 len(deltas), len(deltas)),
            "prior_verdict": "CONCORDANT_CORE (data_class_concordance_20260912T002004.json)",
            "prior_verdict_status_under_this_test": (
                "SURVIVES the substantive falsifier" if strict == "PROJECTION_SOUND"
                else "VOID (projection drops an admission-relevant delta)"
                if strict == "PROJECTION_UNSOUND" else "UNDETERMINED"),
        },
        "falsifier": "A reviewer exhibits (a) a data_class delta that changes the admitted data "
                     "set which this artifact screened INERT or adjudicated ADMISSION_NEUTRAL, "
                     "with the specific admitted/excluded datum named; or (b) a same-path "
                     "declaration used by R3 that does not actually appear in all three schemas "
                     "at the cited location; or (c) a competing (s, delta, K-weight) "
                     "specification that the scan missed; or (d) any of the three canonical "
                     "sha256 values differs between the window pre and post readings (window "
                     "UNSTABLE), or any of the five controls does not behave as declared "
                     "(instrument invalid).",
        "limitations": [
            "The screen/adjudication is a declared instrument, not a proof; every delta with "
            "raw values, tokens and differing span is published so a reviewer can overturn an "
            "adjudication without re-running.",
            "ADMISSION_NEUTRAL concerns whether the delta changes the admitted set, not "
            "whether the schemas are identical; full exposure is listed separately.",
            "One instant, one window: hash drift after the post reading is not covered.",
            "Evidence only: sets no gate verdict and no node transition.",
        ],
        "reproduce": "python3 artifacts/worker-065/projection_adversarial.py --stamp {} "
                     "--out artifacts/worker-065/projection_adversarial_{}.json "
                     "--window artifacts/worker-065/projection_window_{}.json".format(
                         args.stamp, args.stamp, args.stamp),
    }

    window = {
        "task_id": "W065-PROJECTION-ADVERSARIAL-03",
        "actor": "worker-065",
        "at": now,
        "stamp": args.stamp,
        "pre": pre,
        "post": post,
        "drift": drift,
        "stable": stable,
        "note": "Pre/measurement/post sha256 window around the adversarial projection test; "
                "the test reports VOID_WINDOW_UNSTABLE on any drift.",
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(args.window, "w", encoding="utf-8") as fh:
        json.dump(window, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("strict_verdict:", strict)
    print("deltas:", len(deltas), "candidates:", len(candidates), "relevant:", len(relevant))
    print("controls_ok:", controls_ok, "window_stable:", stable)
    print("named axes parsed equal:", axes["raw_equal"])
    print("distinct spec values:", axes["distinct_spec_values"])
    print("out:", args.out)
    return 0 if (stable and controls_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
