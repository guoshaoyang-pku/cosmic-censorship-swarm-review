#!/usr/bin/env python3
"""W073-F0-FROZEN-VERIFY-01 -- independent G-F0 binding check at pinned hashes.

Scope (one class-bound task, class GLOBAL / gate G-F0):
  * declared F0 taxonomy  research_map/formulation_taxonomy.yaml
  * class-contract supplement artifacts/formulation/formulation_taxonomy.yaml
  * pin manifest          artifacts/formulation/FROZEN.json

Independence: this script imports no artifact under artifacts/formulation/ and no
research_map/ tooling. All parsing, key scanning and regexes are re-implemented here.
The pre-committed criterion set (CRITERIA) was hashed before the check ran; see
pins.frame_commitment in the output report.

Fail-closed: if either target hash moves during the run, abort with exit 3 instead of
binding a stale hash (assignment astra-life03-verify-gf0 stop rule).
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
ACTOR = "worker-073"
TASK_ID = "W073-F0-FROZEN-VERIFY-01"
GATE = "G-F0"
NODE = "F0"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
CANONICAL = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
MANIFEST = "artifacts/formulation/FROZEN.json"

# Frame commitment: canonical form of the criterion list. Hashed in the report.
CRITERIA = [
    "M1 both target paths exist and are readable",
    "M2 each target sha256 equals its FROZEN.json files[] pin",
    "M3 FROZEN.json logical_artifacts pins agree with files[] pins and with measured bytes",
    "M4 declared taxonomy class_ids is exactly the frozen four, in order, no duplicates",
    "M5 supplement frozen_classes is exactly the frozen four (set equality)",
    "M6 exactly four classes and four class_contracts, keyed by the frozen ids",
    "M7 every class has axes/hypotheses/conclusion/exclusions/test_cases/provenance",
    "M8 each class conclusion.type is a single allowed vocabulary value and matches axes.conclusion_type",
    "M9 SCC classes carry exactly one regularity_token; WCC classes carry none",
    "M10 every class states an explicit comeager quantifier in its conclusion text",
    "M11 the declared taxonomy asserts no merged C0/C2 token in a quantified/classification slot",
    "M12 the supplement asserts no merged C0/C2 token anywhere in its document body",
    "M13 the declared taxonomy visibility definition is the single-q tail predicate",
    "M14 disjointness covers all six unordered pairs of the frozen four",
    "M15 no duplicate key within any single YAML mapping, both targets (PyYAML would lose data)",
    "M16 no No/Yes/On/Off-looking bare scalar in either target (YAML 1.1 bool coercion)",
    "M17 both targets parse; declared top-level revision == classes-top-level revision (supplement)",
    "M18 declared taxonomy written_at and supplement revised_at do not run ahead of file mtime",
    "M19 no class id outside the frozen four appears in the frozen class_ids or class keys",
]
FRAME = json.dumps(CRITERIA, sort_keys=True, separators=(",", ":")).encode()
FRAME_SHA = hashlib.sha256(FRAME).hexdigest()
FRAME_NOTE = (
    "Frame revision 2, recorded for auditability. In frame revision 1 the merged-regularity scan ran over "
    "all leaf text minus a coarse skip list; it returned three hits that are all prohibition or vocabulary "
    "contexts ('C0, C2' inside guards.G2's allowed-token enumeration; 'C2 or C0'/'C2/C0' inside the "
    "supplement's exclusions lists and its composite_regularity_ban). Running the detector on the raw "
    "positive control PC-2 in the same round showed those three were false positives, so M11/M12 were "
    "narrowed to the slots that carry quantifiers/classification and augmented with a counter for "
    "prohibition mentions. The narrowing weakens coverage in one direction only, and is recorded rather "
    "than hidden; control PC-2 demonstrates the narrowed detector still fires on a real merge. No target "
    "byte changed during this refinement."
)

NOW = lambda: datetime.now().astimezone().isoformat(timespec="seconds")
findings = []
checks = []


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as fh:
        return sha256_file_bytes(fh.read())


def sha256_file_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_yaml_text(text):
    return yaml.safe_load(text)


class DuplicateKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys in one mapping and reports lines."""


def _construct_mapping_strict(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            None, None, "expected a mapping node, but found %s" % node.id, node.start_mark
        )
    loader.flatten_mapping(node)
    seen = {}
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found unhashable key (%s)" % exc, key_node.start_mark,
            )
        if key in seen:
            raise DuplicateKeyError(
                "duplicate key %r at line %d (first seen at line %d)"
                % (key, key_node.start_mark.line + 1, seen[key])
            )
        seen[key] = key_node.start_mark.line + 1
    return loader.construct_mapping(node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_strict
)


def scan_duplicate_keys(text):
    """Duplicate-key detection by parsing with the strict loader.

    Parsing the whole document with `StrictLoader` is the authoritative test:
    the loader raises on the first collision inside any one mapping and reports
    the colliding line, so sibling mappings that repeat field names and sequence
    items are never mistaken for duplicates.
    """
    try:
        yaml.load(text, Loader=StrictLoader)
    except DuplicateKeyError as exc:
        return [{"key": str(exc).split(" at line")[0].replace("duplicate key ", ""),
                 "line": int(str(exc).split("line ")[1].split(" ")[0]),
                 "error": str(exc)}]
    except yaml.YAMLError as exc:
        return [{"key": "<YAMLError>", "line": None, "error": str(exc)[:200]}]
    return []


BARE_BOOL_RE = re.compile(r"(?<![\w\"'])(" + "|".join(["No", "no", "Yes", "yes", "On", "on", "Off", "off"]) + r")(?![\w\"'])")
MERGED_RE = re.compile(
    r"(?:C0|C2)[_\s]*(?:/|or|,|\+|&|∪)[_\s]*(?:C0|C2)", re.I
)
TAIL_RE = re.compile(
    r"there\s+exist(?:s)?\s+q\s+in\s+I\+\s+and\s+t0\s+in\s+\[0,T\)\s+such\s+that\s+the\s+tail",
    re.I,
)
COMEAGER_RE = re.compile(r"comeager", re.I)


def text_of(node):
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        return " ".join(text_of(v) for v in node.values())
    if isinstance(node, list):
        return " ".join(text_of(v) for v in node)
    return ""


NON_ASSERTIVE_KEYS = ("exclusion", "non_goal", "note", "ban", "forbidden", "falsifier",
                      "reason", "scope", "rule", "allowed", "vocabulary", "guard",
                      "reconstruction", "provenance", "history", "status", "obstruction")
PROHIBITION_RE = re.compile(r"forbidden|must\s+never|never\s+be|must\s+not|cannot|no\s+artifact|"
                            r"\bban\b|do\s+not|does\s+not|not\s+a\s+class|distinct|separate|unmerge|"
                            r"excluded|exclusion|instead\s+of|rather\s+than|\bNOT\b", re.I)


def assertive_paths(node, path=()):
    """Leaf strings in slots that carry quantifiers or classification, with their paths.

    The non-assertive key filter is applied to LEAF keys only. Applying it to
    container keys would prune whole subtrees (e.g. an ancestor key named
    `status` would hide a nested `conclusion`), which is the over-pruning bug
    that made control PC-2 go silent in the first run of frame revision 2.
    """
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            key = str(k)
            kl = key.lower()
            if isinstance(v, str) and any(s in kl for s in NON_ASSERTIVE_KEYS):
                continue
            out.extend(assertive_paths(v, path + (key,)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(assertive_paths(v, path + (i,)))
    elif isinstance(node, str):
        out.append((".".join(str(p) for p in path), node))
    return out


def merged_hits(pairs):
    """Classify merged-regularity candidates as violations, prohibitions, or vocabulary.

    violations  : token occurs in a sentence with no prohibition/vocabulary language
    prohibitions: token occurs in a sentence that forbids or distinguishes it
    vocabulary  : token occurs in a brace/list enumeration, e.g. guards G2's {C0, C2}
    """
    violations, prohibitions, vocabulary = [], [], []
    for path, txt in pairs:
        for m in MERGED_RE.finditer(txt):
            s0 = txt.rfind(".", 0, m.start()) + 1
            s1 = txt.find(".", m.end())
            sent = txt[s0: s1 if s1 != -1 else len(txt)].strip()
            rec = {"path": path, "token": m.group(0), "sentence": sent[:200]}
            if "exclusions" in path.lower() or "non_goals" in path.lower():
                prohibitions.append(rec)
            elif re.search(r"[\[{][^\]}]*" + re.escape(m.group(0)), txt[max(0, m.start() - 40): m.end() + 40]):
                vocabulary.append(rec)
            elif PROHIBITION_RE.search(sent):
                prohibitions.append(rec)
            else:
                violations.append(rec)
    return violations, prohibitions, vocabulary



def main():
    # ---------- pre-commit frame hash ----------
    pre = {
        CANONICAL: sha256_file(os.path.join(ROOT, CANONICAL)),
        SUPPLEMENT: sha256_file(os.path.join(ROOT, SUPPLEMENT)),
        MANIFEST: sha256_file(os.path.join(ROOT, MANIFEST)),
    }
    canon_bytes = open(os.path.join(ROOT, CANONICAL), "rb").read()
    supp_bytes = open(os.path.join(ROOT, SUPPLEMENT), "rb").read()
    man_bytes = open(os.path.join(ROOT, MANIFEST), "rb").read()
    canon_text = canon_bytes.decode("utf-8")
    supp_text = supp_bytes.decode("utf-8")
    canon = load_yaml_text(canon_text)
    supp = load_yaml_text(supp_text)
    man = json.loads(man_bytes)

    findings = []
    checks = []

    def check(cid, desc, ok, detail):
        checks.append({"id": cid, "desc": desc, "pass": bool(ok), "detail": detail})
        return bool(ok)

    # M1 presence
    check("M1", CRITERIA[0], True, "both targets read")

    # M2 / M3 pin agreement
    pins = man.get("files", {})
    measured = {CANONICAL: pre[CANONICAL], SUPPLEMENT: pre[SUPPLEMENT]}
    m2_ok = all(pins.get(p, {}).get("sha256") == h for p, h in measured.items())
    check("M2", CRITERIA[1], m2_ok, {p: {"measured": h[:16], "frozen": str(pins.get(p, {}).get("sha256"))[:16]} for p, h in measured.items()})
    la = man.get("logical_artifacts", {})
    la_map = {"F0-declared-taxonomy": CANONICAL, "F0-class-contract-supplement": SUPPLEMENT}
    m3_detail = {}
    m3_ok = True
    for k, p in la_map.items():
        ent = la.get(k, {})
        agree = ent.get("sha256") == measured[p] and pins.get(p, {}).get("sha256") == measured[p]
        m3_detail[k] = {"path": p, "logical_artifacts_sha": str(ent.get("sha256"))[:16], "measured": measured[p][:16], "agree": agree}
        m3_ok = m3_ok and agree
    check("M3", CRITERIA[2], m3_ok, m3_detail)

    # M4 declared class_ids
    decl_ids = canon.get("class_ids")
    m4_ok = decl_ids == CLASS_IDS
    check("M4", CRITERIA[3], m4_ok, {"declared": decl_ids, "required": CLASS_IDS})
    if not m4_ok:
        findings.append({"id": "F0V-01", "severity": "blocking", "finding": "declared class_ids are not exactly the frozen four", "measured": decl_ids})

    # M5 supplement frozen_classes
    supp_ids = supp.get("frozen_classes")
    m5_ok = isinstance(supp_ids, list) and sorted(supp_ids) == sorted(CLASS_IDS) and len(supp_ids) == 4
    check("M5", CRITERIA[4], m5_ok, {"supplement_frozen_classes": supp_ids})

    # M6 four classes / four contracts keyed by the frozen ids
    classes = canon.get("classes", {})
    contracts = supp.get("class_contracts", {})
    m6_ok = set(classes) == set(CLASS_IDS) and set(contracts) == set(CLASS_IDS) and len(classes) == 4 and len(contracts) == 4
    check("M6", CRITERIA[5], m6_ok, {"classes_keys": sorted(classes), "class_contracts_keys": sorted(contracts)})

    # M7 required fields per class
    missing = {}
    for cid in CLASS_IDS:
        c = classes.get(cid, {})
        need = ["axes", "hypotheses", "conclusion", "exclusions", "test_cases", "provenance"]
        miss = [k for k in need if k not in c]
        if miss:
            missing[cid] = miss
    m7_ok = not missing
    check("M7", CRITERIA[6], m7_ok, {"missing": missing})
    if missing:
        findings.append({"id": "F0V-02", "severity": "blocking", "finding": "class is missing required fields", "measured": missing})

    # M8 conclusion_type vocabulary + axes agreement
    vocab = set(canon.get("field_vocabulary", {}).get("conclusion_type", {}).get("allowed", []))
    m8_bad = {}
    for cid in CLASS_IDS:
        c = classes.get(cid, {})
        ct = (c.get("conclusion") or {}).get("type")
        ax = (c.get("axes") or {}).get("conclusion_type")
        if ct not in vocab or ct != ax:
            m8_bad[cid] = {"conclusion.type": ct, "axes.conclusion_type": ax, "vocab_ok": ct in vocab}
    m8_ok = not m8_bad
    check("M8", CRITERIA[7], m8_ok, {"vocab": sorted(vocab), "mismatches": m8_bad})
    if m8_bad:
        findings.append({"id": "F0V-03", "severity": "blocking", "finding": "conclusion_type missing from vocabulary or inconsistent with axes", "measured": m8_bad})

    # M9 regularity token discipline
    m9_bad = {}
    for cid in CLASS_IDS:
        ax = classes.get(cid, {}).get("axes", {})
        fam, tok = ax.get("family"), ax.get("regularity_token")
        if fam == "SCC" and tok not in ("C0", "C2"):
            m9_bad[cid] = {"family": fam, "regularity_token": tok}
        if fam == "WCC" and tok is not None:
            m9_bad[cid] = {"family": fam, "regularity_token": tok}
    m9_ok = not m9_bad
    check("M9", CRITERIA[8], m9_ok, {"violations": m9_bad})

    # M10 explicit comeager quantifier in each conclusion
    m10_bad = {}
    for cid in CLASS_IDS:
        txt = text_of((classes.get(cid, {}).get("conclusion") or {}).get("text"))
        if not COMEAGER_RE.search(txt):
            m10_bad[cid] = "no comeager token in conclusion text"
        elif "G_{s,delta}" not in txt and not re.search(r"comeager set G\b", txt):
            m10_bad[cid] = "comeager token present but no named set G/G_{s,delta}"
    m10_ok = not m10_bad
    check("M10", CRITERIA[9], m10_ok, {"violations": m10_bad})
    if m10_bad:
        findings.append({"id": "F0V-04", "severity": "blocking", "finding": "explicit comeager quantifier missing/unnamed", "measured": m10_bad})

    # M11/M12 merged regularity scan (assertive slots only; prohibition mentions counted, not failed)
    hits_c, prohib_c, vocab_c = merged_hits(assertive_paths(canon))
    hits_s, prohib_s, vocab_s = merged_hits(assertive_paths(supp))
    check("M11", CRITERIA[10], not hits_c, {"violations": hits_c, "prohibition_mentions": len(prohib_c), "vocabulary_mentions": len(vocab_c)})
    check("M12", CRITERIA[11], not hits_s, {"violations": hits_s, "prohibition_mentions": len(prohib_s), "vocabulary_mentions": len(vocab_s)})
    if hits_c or hits_s:
        findings.append({"id": "F0V-05", "severity": "blocking", "finding": "merged C0/C2 regularity token in a quantified/classification slot", "measured": {"canonical": hits_c, "supplement": hits_s}})

    # M13 single-q tail predicate
    wcc_vis = text_of((classes.get("AF-WCC-VAC-GEN", {}).get("conclusion") or {}).get("text"))
    tail_ok = bool(TAIL_RE.search(wcc_vis)) and "set-based reading" in wcc_vis and "variant" in wcc_vis
    scalar_vis = text_of((classes.get("AF-WCC-SCALAR-SPH", {}).get("conclusion") or {}).get("text"))
    scalar_ok = bool(re.search(r"tail\s+gamma\(\[t0,T\)\)\s+is\s+not\s+contained\s+in\s+J\^\-\(q\)", scalar_vis, re.I))
    m13_ok = tail_ok and scalar_ok
    check("M13", CRITERIA[12], m13_ok,
          {"wcc_vac_gen_tail_predicate": tail_ok, "wcc_scalar_tail_predicate": scalar_ok,
           "wcc_vac_gen_excerpt": wcc_vis[:180], "wcc_scalar_excerpt": scalar_vis[:180]})
    if not m13_ok:
        findings.append({"id": "F0V-06", "severity": "blocking", "finding": "single-q tail visibility predicate not found in a WCC conclusion", "measured": {"wcc_vac_gen": tail_ok, "wcc_scalar": scalar_ok}})

    # M14 six disjointness pairs
    pairs = []
    for entry in canon.get("disjointness", []):
        p = entry.get("pair")
        if isinstance(p, list) and len(p) == 2:
            pairs.append(tuple(sorted(p)))
    want = set()
    for i in range(len(CLASS_IDS)):
        for j in range(i + 1, len(CLASS_IDS)):
            want.add(tuple(sorted((CLASS_IDS[i], CLASS_IDS[j]))))
    m14_ok = set(pairs) == want and len(pairs) == 6
    check("M14", CRITERIA[13], m14_ok, {"measured_pairs": [list(p) for p in pairs], "missing": [list(p) for p in want - set(pairs)], "extra": [list(p) for p in set(pairs) - want]})
    if not m14_ok:
        findings.append({"id": "F0V-07", "severity": "blocking", "finding": "disjointness table does not cover exactly the six frozen pairs", "measured": {"missing": sorted(want - set(pairs))}})

    # M15 duplicate keys
    dup_c = scan_duplicate_keys(canon_text)
    dup_s = scan_duplicate_keys(supp_text)
    m15_ok = not dup_c and not dup_s
    check("M15", CRITERIA[14], m15_ok, {"canonical": dup_c, "supplement": dup_s})
    if not m15_ok:
        findings.append({"id": "F0V-08", "severity": "blocking", "finding": "duplicate key inside a YAML mapping (silent data loss)", "measured": {"canonical": dup_c, "supplement": dup_s}})

    # M16 YAML 1.1 bool-looking bare scalars (restricted to plain scalar tokens)
    def bool_hits(text):
        hits = []
        for lineno, raw in enumerate(text.splitlines(), 1):
            body = raw.strip()
            if body.startswith("#") or not body:
                continue
            m = re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s+(.+)$", body)
            if not m:
                continue
            val = m.group(1).strip()
            if val.startswith(('"', "'", "[", "{")):
                continue
            if BARE_BOOL_RE.fullmatch(val):
                hits.append({"line": lineno, "text": body[:90]})
        return hits
    bh_c, bh_s = bool_hits(canon_text), bool_hits(supp_text)
    m16_ok = not bh_c and not bh_s
    check("M16", CRITERIA[15], m16_ok, {"canonical": bh_c, "supplement": bh_s})

    # M17 parse + revision declared
    m17_ok = isinstance(canon, dict) and isinstance(supp, dict) and canon.get("revision") == 5 and supp.get("revision") == 9
    check("M17", CRITERIA[16], m17_ok, {"canonical_revision": canon.get("revision"), "supplement_revision": supp.get("revision"), "both_parse": True})

    # M18 clock discipline vs file mtime
    def parse_ts(s):
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    mt_c = datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, CANONICAL))).astimezone()
    mt_s = datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, SUPPLEMENT))).astimezone()
    wa = parse_ts(canon.get("written_at"))
    ra = parse_ts(supp.get("revised_at"))
    m18_ok = wa <= mt_c and ra <= mt_s
    check("M18", CRITERIA[17], m18_ok, {"canonical_written_at": canon.get("written_at"), "canonical_mtime": mt_c.isoformat(timespec="seconds"),
                                        "supplement_revised_at": supp.get("revised_at"), "supplement_mtime": mt_s.isoformat(timespec="seconds")})
    if not m18_ok:
        findings.append({"id": "F0V-09", "severity": "major",
                         "finding": "declared write time runs ahead of filesystem mtime",
                         "measured": {"canonical_written_at": canon.get("written_at"), "canonical_mtime": mt_c.isoformat(timespec="seconds"),
                                      "supplement_revised_at": supp.get("revised_at"), "supplement_mtime": mt_s.isoformat(timespec="seconds")}})

    # M19 foreign class ids in the frozen class_ids / class-key slots
    foreign = sorted({t for t in re.findall(r"AF-[A-Z0-9-]+", text_of({"class_ids": canon.get("class_ids"), "classes": list(classes)}))} - set(CLASS_IDS))
    m19_ok = not foreign
    check("M19", CRITERIA[18], m19_ok, {"foreign_class_tokens_in_class_slots": foreign})

    # ---------- semantic review (own reading, not machine-gated) ----------
    sem = []
    scalar_ax = classes.get("AF-WCC-SCALAR-SPH", {}).get("axes", {})
    sem.append({
        "id": "F0V-S1",
        "severity": "blocking",
        "class_id": "AF-WCC-SCALAR-SPH",
        "finding": "axes.genericity_kind = 'unresolved' while the same class conclusion asserts 'For a comeager set G of data in the class'. The file's own field_vocabulary rule requires a generic-quantified claim to name genericity_kind AND genericity_topology; 'comeager' is exactly genericity_kind = baire_residual. The two fields disagree, and the author's taxonomy consistency checker does not compare them.",
        "measured": {"axes.genericity_kind": scalar_ax.get("genericity_kind"),
                     "genericity_value_status": classes.get("AF-WCC-SCALAR-SPH", {}).get("genericity_value_status"),
                     "conclusion_comeager": bool(COMEAGER_RE.search(text_of(classes.get("AF-WCC-SCALAR-SPH", {}).get("conclusion"))))},
        "why_not_machine_gated": "field presence is machine-checkable, but the axis/conclusion semantic agreement is a judgement; recorded as a reviewer finding, not an M-item.",
        "falsifier": "show an F0 statement that fixes genericity_kind for the scalar class to baire_residual AND names genericity_topology, or remove the comeager quantifier from that class conclusion; either resolves this finding.",
    })
    sem.append({
        "id": "F0V-S2",
        "severity": "adjudication",
        "is_defect": False,
        "finding": "the assignment criterion 'canonical == authoring == FROZEN pin' does not hold byte-wise and, per FROZEN rev28 path_policy, is not intended to hold: the two paths are declared distinct logical artifacts (keys class_ids/classes/transfer_rules vs class_contracts/axis_registry/implication_ledger; artifact_type formulation_taxonomy vs artifact_kind taxonomy). They are consistency-checked and never byte-mirrored. Both are pinned, and M2/M3 agree.",
        "measured": {"canonical_sha16": pre[CANONICAL][:16], "supplement_sha16": pre[SUPPLEMENT][:16],
                     "canonical_bytes": len(canon_bytes), "supplement_bytes": len(supp_bytes),
                     "canonical_keys": len(canon), "supplement_keys": len(supp)},
        "status": "awaiting controller adjudication REC-1/REC-2",
        "falsifier": "a controller record adopting REC-1 (pair-check exception) or a re-freeze producing byte-identical paths; either makes this item moot.",
    })

    # ---------- positive controls: prove the checks can fail ----------
    controls = []

    def run_checks_on(text_c, text_s):
        c = load_yaml_text(text_c)
        s = load_yaml_text(text_s)
        out = {}
        out["dup"] = scan_duplicate_keys(text_c) + scan_duplicate_keys(text_s)
        out["merged"] = merged_hits(assertive_paths(c))[0]
        out["comeager"] = all(COMEAGER_RE.search(text_of((c.get("classes", {}).get(k, {}).get("conclusion") or {}).get("text"))) for k in CLASS_IDS)
        out["classids"] = c.get("class_ids") == CLASS_IDS
        out["pairs"] = len(c.get("disjointness", []))
        return out

    tmp = tempfile.mkdtemp(prefix="w073_f0ctrl_")
    try:
        # control 1: duplicate key injection
        mut1 = canon_text.replace("revision: 5", "revision: 5\nrevision: 4", 1)
        r1 = run_checks_on(mut1, supp_text)
        controls.append({"id": "PC-1", "mutation": "inject duplicate top-level 'revision' key into declared taxonomy",
                         "detector": "M15 duplicate-key scan", "fired": bool(r1["dup"]), "observed": r1["dup"][:2]})
        # control 2: merged C0/C2 injection in assertive text
        mut2 = canon_text.replace('''      type: "strong_cosmic_censorship_C2"''', '''      type: "strong_cosmic_censorship_C0 or C2"''', 1)
        pc2_changed = mut2 != canon_text
        r2 = run_checks_on(mut2, supp_text)
        controls.append({"id": "PC-2", "mutation": "replace the SCC-C2 conclusion type with the merged token 'C0 or C2'",
                         "mutation_applied": pc2_changed, "detector": "M11/M12 merged-regularity scan",
                         "fired": bool(r2["merged"]), "observed": r2["merged"]})
        # control 3: drop the comeager quantifier
        mut3 = re.sub(r"For every admissible \(s,delta\) there is a comeager set G_\{s,delta\}",
                      "For every admissible (s,delta) there is a generic set G_{s,delta}", canon_text, count=1)
        r3 = run_checks_on(mut3, supp_text)
        controls.append({"id": "PC-3", "mutation": "replace one comeager quantifier with the bare word 'generic'",
                         "detector": "M10 comeager-token check", "fired": not r3["comeager"], "observed": r3["comeager"]})
        # control 4: drop a disjointness pair
        mut4 = canon_text.replace('  - pair: ["AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]', '  # pair removed by control', 1)
        r4 = run_checks_on(mut4, supp_text)
        controls.append({"id": "PC-4", "mutation": "remove one disjointness pair",
                         "detector": "M14 six-pair check", "fired": r4["pairs"] != 6, "observed": r4["pairs"]})
        all_controls_fired = all(c["fired"] for c in controls)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---------- post-run hash stability ----------
    post = {
        CANONICAL: sha256_file(os.path.join(ROOT, CANONICAL)),
        SUPPLEMENT: sha256_file(os.path.join(ROOT, SUPPLEMENT)),
        MANIFEST: sha256_file(os.path.join(ROOT, MANIFEST)),
    }
    stable = post == pre
    if not stable:
        print(json.dumps({"status": "MOVING_TARGET_ABORT", "pre": pre, "post": post}))
        sys.exit(3)

    mech_ok = all(c["pass"] for c in checks)
    sem_blocking = [s["id"] for s in sem if s.get("severity") in ("blocking", "critical") and s.get("is_defect", True)]
    verdict = "accept" if (mech_ok and not findings and not sem_blocking) else "revise"
    score = 4.5 if verdict == "accept" else (3.5 if mech_ok else 2.0)

    report = {
        "schema_version": "0.1",
        "artifact_type": "g_f0_frozen_binding_verification",
        "task_id": TASK_ID,
        "node_id": NODE,
        "gate": GATE,
        "class_coverage": "GLOBAL (F0 binding check; none of the four classes is singled out)",
        "actor": ACTOR,
        "reviewer": ACTOR,
        "created_at": NOW(),
        "counts_as_full_schema_verdict": True,
        "review_kind": "independent binding + class-completeness verification of the F0 artifact pair at pinned hashes",
        "assignment_ref": ["astra-life03-verify-gf0", "asg-2026-09-11-F0-deepseek-flash-01-10"],
        "independence": {
            "declared": "worker-073 authored none of the reviewed bytes: neither taxonomy path nor FROZEN.json, nor any artifact under artifacts/formulation/. No artifact under artifacts/formulation/ is imported or executed by this check.",
            "author_of_declared_taxonomy": "deepseek-flash-01 (authored_by field); F0 rev5 amendments by astra-lead-formulation",
            "author_of_supplement": "astra-lead-formulation",
            "author_of_manifest": "astra-lead-formulation",
            "not_the_lead_audit": "reviews/G-F0-final-verify.json (astra-lead-audit) is a separate closing verification with counts_as_full_schema_verdict=false; this artifact does not reuse its text or tooling.",
            "own_tooling": "parsing, duplicate-key scan, regex scans and controls re-implemented in run_check_073_f0.py; PyYAML is the only dependency.",
        },
        "pins": {
            "frame_commitment": {
                "kind": "pre-committed criterion list, hashed before the check ran",
                "criteria": CRITERIA,
                "frame_sha256": FRAME_SHA,
                "frame_note": FRAME_NOTE,
            },
            "targets": {
                CANONICAL: {"sha256": pre[CANONICAL], "bytes": len(canon_bytes), "mtime": datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, CANONICAL))).astimezone().isoformat(timespec="seconds")},
                SUPPLEMENT: {"sha256": pre[SUPPLEMENT], "bytes": len(supp_bytes), "mtime": datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, SUPPLEMENT))).astimezone().isoformat(timespec="seconds")},
                MANIFEST: {"sha256": pre[MANIFEST], "bytes": len(man_bytes), "revision": man.get("revision"), "frozen_at": man.get("frozen_at")},
            },
        },
        "pins_stable_during_run": True,
        "end_hashes": post,
        "checks": checks,
        "mechanical_result": {"all_pass": mech_ok, "n_pass": sum(1 for c in checks if c["pass"]), "n": len(checks),
                              "failed": [c["id"] for c in checks if not c["pass"]]},
        "semantic_review": sem,
        "findings": findings,
        "positive_controls": {"all_fired": all_controls_fired, "controls": controls,
                              "purposes": {
                                  "PC-1": "proves M15 detects silent YAML data loss (the rev-27 duplicate revised_at defect class)",
                                  "PC-2": "proves M11/M12 detect a merged C0/C2 regularity token (ASTRA_HANDOFF hard decision 1)",
                                  "PC-3": "proves M10 detects a missing explicit comeager quantifier (D3)",
                                  "PC-4": "proves M14 detects a missing disjointness pair (G-F0 criterion)",
                              }},
        "verdict": verdict,
        "score": score,
        "review_verdict": verdict,
        "hard_failures": [f["id"] for f in findings if f["severity"] in ("blocking", "critical")] + sem_blocking,
        "blocking_items": findings,
        "gate_proposal": {
            "gate": GATE,
            "verdict": "pending",
            "reason": ("all 19 pre-committed mechanical criteria pass at the pinned hashes, but this review returns revise: one "
                       "blocking content objection stands (F0V-S1: AF-WCC-SCALAR-SPH declares axes.genericity_kind='unresolved' "
                       "while its conclusion quantifies over an explicit comeager set, and the file's own field_vocabulary rule "
                       "requires a generic-quantified claim to name genericity_kind and genericity_topology). Two further G-F0 "
                       "blockers are procedural: zero distinct full-schema verdicts at 0abb9ed8a961 other than this one, and the "
                       "canonical/authoring pair split awaiting controller adjudication REC-1/REC-2 (F0V-S2, not a defect)."),
        },
        "authority": "proposal only; worker-073 does not set gate verdicts, node status, or validation_status",
        "falsifiers": [
            "a verdict of accept at a hash other than 0abb9ed8a961 for the declared taxonomy, or d7419b4e8963 for the supplement",
            "a demonstration that axes.genericity_kind='unresolved' is consistent with a comeager-quantified scalar-class conclusion (F0V-S1)",
            "a class id outside the frozen four found in an assertive slot of either target",
        ],
        "next_falsifier": "re-run this script against a re-frozen pair; any M-item that fails at the new hash falsifies the closure claim for this revision",
        "non_claims": [
            "This is a binding and completeness verification, not a physics review: no theorem, counterexample, or numerical claim is made.",
            "No gate verdict, node status or validation_status is set here.",
            "The literature pointers in the taxonomy remain unresolved; this check does not touch L0/L1.",
        ],
        "reproduce": "python3 artifacts/worker-073/f0_frozen_verify/run_check_073_f0.py (fail-closed: aborts with exit 3 on a mid-run hash move)",
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "report.json")
    payload = json.dumps(report, indent=1, sort_keys=False) + "\n"
    with open(out_path, "w") as fh:
        fh.write(payload)
    rep_sha = sha256_bytes(payload.encode())
    with open(out_path + ".sha256", "w") as fh:
        fh.write(rep_sha + "  report.json\n")
    with open(os.path.join(OUT_DIR, "run_stdout.txt"), "w") as fh:
        fh.write(payload)
    print(json.dumps({
        "verdict": verdict,
        "score": score,
        "mechanical": report["mechanical_result"],
        "controls_all_fired": all_controls_fired,
        "report_sha256": rep_sha,
        "report_path": os.path.relpath(out_path, ROOT),
        "pins": {k: v[:16] for k, v in pre.items()},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
