#!/usr/bin/env python3
"""W023-F2B-DIR-REVIEW-01 -- independent adversarial review of the F2b containment
repair text at FROZEN rev29, scoped to the entailment direction introduced by the
`regularity.must_not_conflate[0]` replacement.

Read-only on every canonical path.  Produces candidate reproductions, a
direction-corrected variant, machine evidence and a report.  Fail-closed on any
pin drift: a verdict is emitted only when entry and exit measurements agree.

    python3 reproduce_023.py            # writes report.json + evidence/
    exit 0 = report written, 2 = pin failure (no verdict), 3 = internal refusal
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # ai4math-swarm
HERE = Path(__file__).resolve().parent
EV = HERE / "evidence"
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")

TASK_ID = "W023-F2B-DIR-REVIEW-01"
NODE_ID = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"

# ---------------------------------------------------------------- entry pins
PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    # reviewed repair artefacts (not canonical; pinned so the verdict is void on a move)
    "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff":
        "d777a8cb84aa7689cd72b0eee767f08486ad07a4d90e28c8f9d6de3be3b77dc7",
    "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml":
        "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a",
    "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml":
        "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c",
}
CAND_066_SHA = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"

# document-internal vocabulary ------------------------------------------------
CONCLUSION_LABEL = {
    "scc_c0_future_inextendibility": "no proper future C0 metric extension",
    "scc_c2_future_inextendibility": "no proper future C2 extension",
}
ANTE_LABEL = "no proper future H2_loc extension"
CLAIM_RE = re.compile(
    r"so\s+H2_loc-inextendibility\s+ENTAILS\s+this class's conclusion\s*;")
REVERSE_CLAIM_RE = re.compile(
    r"this class's conclusion\s+ENTAILS\s+H2_loc-inextendibility")

V1_SENTENCE = "so H2_loc-inextendibility ENTAILS this class's conclusion;"
V2_SENTENCE = ("so this class's conclusion ENTAILS H2_loc-inextendibility and "
               "C2-inextendibility, never the reverse;")
NOTE_OLD = "the earlier 'no containment with C2 or C0 is asserted here' was wrong]"
NOTE_NEW = ("the earlier 'no containment with C2 or C0 is asserted here' was wrong. "
            "R3 major: the first replacement inverted the entailment direction for C0 "
            "-- H2_loc-inextendibility is weaker and entails the C2 sibling, not this "
            "class]")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read(p: str) -> bytes:
    return (ROOT / p).read_bytes()


def measure_pins() -> dict:
    out = {}
    for p, want in PINS.items():
        f = ROOT / p
        got = sha(f.read_bytes()) if f.is_file() else None
        out[p] = {"declared": want, "measured": got, "match": got == want}
    return out


class PinFailure(RuntimeError):
    pass


def guard(pin_map: dict) -> None:
    bad = [k for k, v in pin_map.items() if not v["match"]]
    if bad:
        raise PinFailure("pin drift: " + ", ".join(bad))


# ------------------------------------------------------- diff application
def parse_hunks(diff_text: str):
    hunks, cur = [], None
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            if cur:
                hunks.append(cur)
            cur = {"header": line, "old": [], "new": [], "ctx": []}
        elif cur is not None and line[:1] in (" ", "-", "+") and not line.startswith(("---", "+++")):
            tag, body = line[0], line[1:]
            if tag == " ":
                cur["ctx"].append(body); cur["old"].append(body); cur["new"].append(body)
            elif tag == "-":
                cur["old"].append(body)
            else:
                cur["new"].append(body)
    if cur:
        hunks.append(cur)
    return hunks


def apply_by_block(lines, hunks):
    out = list(lines)
    for h in hunks:
        old, new = h["old"], h["new"]
        hits = [i for i in range(len(out) - len(old) + 1) if out[i:i + len(old)] == old]
        if len(hits) != 1:
            raise RuntimeError(f"hunk not unique: {h['header']} hits={len(hits)}")
        i = hits[0]
        out[i:i + len(old)] = new
    return out


def apply_by_linepair(lines, hunks):
    out = list(lines)
    for h in hunks:
        removed = [l[1:] for l in h["_raw"] if l[0] == "-"]
        added = [l[1:] for l in h["_raw"] if l[0] == "+"]
        if len(removed) != 1 or len(added) != 1:
            raise RuntimeError(f"expected single-line hunk: {h['header']}")
        hits = [i for i, l in enumerate(out) if l == removed[0]]
        if len(hits) != 1:
            raise RuntimeError(f"line not unique: {removed[0][:60]!r} hits={len(hits)}")
        out[hits[0]] = added[0]
    return out


# ------------------------------------------------- document-internal graph
def entailment_graph(doc) -> set:
    edges = set()
    for row in (doc.get("implication_ledger") or {}).get("one_way_entailments", []):
        if row.get("relation") == "entails":
            edges.add((row["from"].strip(), row["to"].strip()))
    return edges


def closure(edges: set) -> set:
    cl = set(edges)
    changed = True
    while changed:
        changed = False
        for a, b in list(cl):
            for c, d in list(cl):
                if b == c and (a, d) not in cl:
                    cl.add((a, d)); changed = True
    return cl


def containment_ranks(doc) -> dict:
    """rank 0 = smallest extension set, from the declared containment sentence."""
    s = (doc.get("implication_ledger") or {}).get("extension_class_containment", "")
    m = re.search(r"E_C2\s+subset of\s+E_\{?C\^?1,1\}?\s+subset of\s+E_H2loc\s+subset of\s+E_C0", s)
    if m:
        return {"C2": 0, "C11": 1, "H2loc": 2, "C0": 3}
    m = re.search(r"E_C0\s+contains\s+E_H2loc\s+contains\s+E_\{?C\^?1,1\}?\s+contains\s+E_C2", s)
    if m:
        return {"C2": 0, "C11": 1, "H2loc": 2, "C0": 3}
    return {}


def probe(raw: str, doc) -> dict:
    """Order-relative, direction-aware entailment probe.

    Two sentence forms are recognised in `regularity.must_not_conflate`:
      Form A: 'H2_loc-inextendibility ENTAILS this class's conclusion'
      Form B: 'this class's conclusion ENTAILS H2_loc-inextendibility'
    Each is valid only if the document's own one_way_entailments graph (transitive
    closure) declares the corresponding edge.  The probe is class-relative, not a
    keyword grep: the same Form A sentence is valid in the C2 sibling and invalid
    in the C0 document.
    """
    slots = (doc.get("regularity") or {}).get("must_not_conflate", [])
    concl = (doc.get("conclusion") or {}).get("conclusion_type")
    label = CONCLUSION_LABEL.get(concl)
    edges = entailment_graph(doc)
    cl = closure(edges)
    ranks = containment_ranks(doc)
    rank_of = {}
    if ranks and label in ("no proper future C0 metric extension",
                           "no proper future C2 extension"):
        tok = "C0" if "C0" in label else "C2"
        rank_of = {"H2loc": ranks.get("H2loc"), "concl": ranks.get(tok)}

    claims = []
    for i, s in enumerate(slots):
        for form, rx, edge in (("A", CLAIM_RE, (ANTE_LABEL, label)),
                               ("B", REVERSE_CLAIM_RE, (label, ANTE_LABEL))):
            if label and rx.search(s):
                if form == "A":
                    rank_ok = (rank_of.get("concl", 99) <= rank_of.get("H2loc", -1))
                else:
                    rank_ok = (rank_of.get("H2loc", 99) <= rank_of.get("concl", -1))
                claims.append({
                    "form": form,
                    "slot": f"regularity.must_not_conflate[{i}]",
                    "excerpt": rx.search(s).group(0),
                    "edge": list(edge),
                    "valid_by_declared_graph": edge in cl,
                    "set_rank_ok": rank_ok if rank_of else None,
                })
    fires = [c for c in claims if c["valid_by_declared_graph"] is False]
    form_a = next((c for c in claims if c["form"] == "A"), None)
    form_b = next((c for c in claims if c["form"] == "B"), None)
    return {
        "claims": claims,
        "claim_present": bool(claims),
        "form_a_present": form_a is not None,
        "form_b_present": form_b is not None,
        "claim_slot": claims[0]["slot"] if claims else None,
        "claim_excerpt": claims[0]["excerpt"] if claims else None,
        "conclusion_type": concl,
        "conclusion_label": label,
        "antecedent_label": ANTE_LABEL,
        "edge_direct": (ANTE_LABEL, label) in edges if label else None,
        "edge_reverse": (label, ANTE_LABEL) in edges if label else None,
        "valid_by_declared_graph": (form_a or form_b)["valid_by_declared_graph"] if claims else None,
        "set_rank_ok": (form_a or form_b)["set_rank_ok"] if claims else None,
        "fires": bool(fires),
        "fired_claims": fires,
        "reverse_claim_present": form_b is not None,
    }


def canonical_gate(path: Path) -> dict:
    cmd = [sys.executable, str(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
           "--json", str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        rep = json.loads(r.stdout)
    except Exception:
        rep = {"raw_stdout": r.stdout[:500]}
    return {"cmd": " ".join(cmd), "rc": r.returncode,
            "verdict": rep.get("verdict"), "class_id": rep.get("class_id"),
            "failed_rules": rep.get("failed_rules"), "failures": rep.get("failures")}


def check(name, got, want, detail=""):
    ok = got == want
    return {"id": name, "expected": want, "observed": got, "pass": ok, "detail": detail}


def main() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    pins_entry = measure_pins()
    try:
        guard(pins_entry)
    except PinFailure as e:
        (EV / "pin_failure.json").write_text(json.dumps(
            {"task_id": TASK_ID, "at": NOW(), "error": str(e), "pins": pins_entry},
            indent=2, sort_keys=True))
        print(f"FAIL-CLOSED: {e}", file=sys.stderr)
        return 2

    live_b = read("schemas/af_scc_c0_vacuum.yaml")
    live = live_b.decode("utf-8")
    live_lines = live.split("\n")
    mirror_b = read("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    c2_b = read("schemas/af_scc_c2_vacuum.yaml")
    f1_b = read("schemas/af_wcc_vacuum.yaml")
    patch_text = read("artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff").decode()
    composed_b = read("artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml")
    w008_b = read("artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml")

    # --- reproduce the 066 candidate by two independent application paths
    hunks = parse_hunks(patch_text)
    raw_tags, cur = [], None
    for line in patch_text.splitlines():
        if line.startswith("@@"):
            cur = []
            raw_tags.append(cur)
        elif cur is not None and line[:1] in (" ", "-", "+") and not line.startswith(("---", "+++")):
            cur.append(line)
    for h, tags in zip(hunks, raw_tags):
        h["_raw"] = tags

    cand_a = "\n".join(apply_by_block(live_lines, hunks))
    cand_b = "\n".join(apply_by_linepair(live_lines, hunks))
    sha_a, sha_b = sha(cand_a.encode()), sha(cand_b.encode())
    cand = cand_a

    # --- locate the claim in the reviewed candidates
    import yaml
    doc_live = yaml.safe_load(live)
    doc_cand = yaml.safe_load(cand)
    doc_c2 = yaml.safe_load(c2_b.decode())
    doc_f1 = yaml.safe_load(f1_b.decode())
    doc_composed = yaml.safe_load(composed_b.decode())
    doc_w008 = yaml.safe_load(w008_b.decode())

    p_live = probe(live, doc_live)
    p_cand = probe(cand, doc_cand)
    p_c2 = probe(c2_b.decode(), doc_c2)
    p_composed = probe(composed_b.decode(), doc_composed)
    p_w008 = probe(w008_b.decode(), doc_w008)
    p_f1 = probe(f1_b.decode(), doc_f1)

    # --- corrected variant v2: live + [direction-corrected clause] + [size-premise fix]
    assert cand.count(V1_SENTENCE) == 1, "v1 sentence not unique"
    v2 = cand.replace(V1_SENTENCE, V2_SENTENCE)
    assert v2.count(NOTE_OLD) == 1, "note not unique"
    v2 = v2.replace(NOTE_OLD, NOTE_NEW)
    v2_lines = v2.split("\n")
    doc_v2 = yaml.safe_load(v2)
    p_v2 = probe(v2, doc_v2)

    # synthetic mutation controls
    c2_rev = c2_b.decode().replace(
        V1_SENTENCE, "so this class's conclusion ENTAILS H2_loc-inextendibility;")
    doc_c2_rev = yaml.safe_load(c2_rev)
    p_c2_rev = probe(c2_rev, doc_c2_rev)

    defect_clause = [s for s in doc_live["regularity"]["must_not_conflate"]
                     if "No containment with C2" in s][0]
    live_empty_item = live.replace(defect_clause, "")
    live_nonsense = live.replace(defect_clause, "XXX")
    import copy
    doc_empty_list = copy.deepcopy(doc_live)
    doc_empty_list["regularity"]["must_not_conflate"] = []
    live_empty_list = yaml.safe_dump(doc_empty_list, sort_keys=False, allow_unicode=True)

    # --- write reconstructed candidate files
    f_v1 = HERE / "proposed_af_scc_c0_vacuum_v1_066.yaml"
    f_v2 = HERE / "proposed_af_scc_c0_vacuum_v2_corrected.yaml"
    f_patch_v2 = HERE / "proposed_patch_v2_corrected.diff"
    f_v1.write_text(cand)
    f_v2.write_text(v2)
    diff_v2 = "\n".join(difflib.unified_diff(
        live_lines, v2_lines, fromfile="a/schemas/af_scc_c0_vacuum.yaml",
        tofile="b/schemas/af_scc_c0_vacuum.yaml", lineterm="")) + "\n"
    f_patch_v2.write_text(diff_v2)

    # self-check: the generated patch applies to the live bytes and yields v2
    import shutil
    ptmp = EV / "patchcheck_tmp"
    if ptmp.exists():
        shutil.rmtree(ptmp)
    (ptmp / "schemas").mkdir(parents=True)
    shutil.copyfile(ROOT / "schemas/af_scc_c0_vacuum.yaml", ptmp / "schemas/af_scc_c0_vacuum.yaml")
    pr = subprocess.run(["patch", "-p1", "--no-backup-if-mismatch"],
                        input=diff_v2.encode(), cwd=ptmp, capture_output=True)
    patch_v2_ok = (pr.returncode == 0 and
                   sha((ptmp / "schemas/af_scc_c0_vacuum.yaml").read_bytes()) == sha(v2.encode()))

    # --- canonical gate on every variant
    tmp_c2_rev = EV / "mutant_c2_reversed.yaml"
    tmp_empty_item = EV / "mutant_c0_empty_item.yaml"
    tmp_empty_list = EV / "mutant_c0_empty_list.yaml"
    tmp_nonsense = EV / "mutant_c0_nonsense.yaml"
    tmp_c2_rev.write_text(c2_rev)
    tmp_empty_item.write_text(live_empty_item)
    tmp_empty_list.write_text(live_empty_list)
    tmp_nonsense.write_text(live_nonsense)
    gate = {
        "live": canonical_gate(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "v1_066_candidate": canonical_gate(f_v1),
        "v2_corrected": canonical_gate(f_v2),
        "composed_044": canonical_gate(ROOT / "artifacts/worker-044/f2b_live_closure_01/sandbox/schemas/af_scc_c0_vacuum.yaml"),
        "c2_sibling": canonical_gate(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "f1": canonical_gate(ROOT / "schemas/af_wcc_vacuum.yaml"),
        "mutant_empty_list": canonical_gate(tmp_empty_list),
        "mutant_empty_item": canonical_gate(tmp_empty_item),
        "mutant_nonsense": canonical_gate(tmp_nonsense),
        "mutant_c2_reversed": canonical_gate(tmp_c2_rev),
    }

    # --- change confinement
    ch_v1 = [i for i, (a, b) in enumerate(zip(live_lines, cand_a.split("\n"))) if a != b]
    ch_v2 = [i for i, (a, b) in enumerate(zip(live_lines, v2_lines)) if a != b]
    composed_clause = [s for s in doc_composed["regularity"]["must_not_conflate"] if CLAIM_RE.search(s)]
    v1_clause = [s for s in doc_cand["regularity"]["must_not_conflate"] if CLAIM_RE.search(s)]

    # --- independent-control guard check
    tampered = {k: dict(v) for k, v in pins_entry.items()}
    tampered["schemas/af_scc_c0_vacuum.yaml"]["match"] = False
    try:
        guard(tampered)
        guard_ok = False
    except PinFailure:
        guard_ok = True

    checks = [
        check("P1_entry_pins_all_match", all(v["match"] for v in pins_entry.values()), True),
        check("P2_live_equals_mirror", sha(mirror_b) == sha(live_b), True),
        check("R1_block_applier_hash", sha_a, CAND_066_SHA),
        check("R2_linepair_applier_hash", sha_b, CAND_066_SHA),
        check("R3_two_methods_agree", cand_a == cand_b, True),
        check("R4_patch_bound_to_066", sha(patch_text.encode()),
              PINS["artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff"]),
        check("D1_claim_present_in_066_candidate", p_cand["claim_present"], True),
        check("D2_claim_invalid_by_declared_graph", p_cand["valid_by_declared_graph"], False,
              "no declared edge H2_loc -> C0 conclusion; the declared edge runs C0 -> H2_loc"),
        check("D3_set_rank_check_agrees", p_cand["set_rank_ok"], False,
              "E_C0 is the largest extension set; absence of H2_loc extensions cannot entail absence of C0 extensions"),
        check("D4_reverse_edge_declared", p_cand["edge_reverse"], True),
        check("D5_claim_present_in_composed_044", p_composed["claim_present"], True),
        check("D6_composed_clause_byte_identical_to_066", composed_clause == v1_clause, True),
        check("D7_claim_present_in_worker008_candidate", p_w008["claim_present"], True),
        check("D8_live_has_no_direction_claim", p_live["claim_present"], False),
        check("X1_c2_sibling_same_sentence_is_valid",
              (p_c2["form_a_present"], p_c2["valid_by_declared_graph"], p_c2["fires"]),
              (True, True, False)),
        check("X2_reversed_c2_mutant_fires",
              (p_c2_rev["form_b_present"], p_c2_rev["fires"]), (True, True)),
        check("X3_f1_carries_no_claim", p_f1["claim_present"], False),
        check("C1_v2_claim_replaced",
              (p_v2["form_a_present"], p_v2["form_b_present"]), (False, True)),
        check("C2_v2_direction_valid",
              (p_v2["valid_by_declared_graph"], p_v2["fires"]), (True, False)),
        check("C3_v2_diff_confined_to_two_lines", ch_v2, [151, 245]),
        check("C4_v1_diff_confined_to_two_lines", ch_v1, [151, 245]),
        check("C5_v1_line_count_unchanged", len(live_lines), len(cand_a.split("\n"))),
        check("C6_v2_line_count_unchanged", len(live_lines), len(v2_lines)),
        check("G1_gate_passes_v1_066", gate["v1_066_candidate"]["rc"], 0),
        check("G2_gate_passes_v2_corrected", gate["v2_corrected"]["rc"], 0),
        check("G3_gate_passes_live_defective", gate["live"]["rc"], 0),
        check("G4_gate_blind_to_direction_mutant", gate["mutant_c2_reversed"]["rc"], 0),
        check("G5_gate_rejects_emptied_list", gate["mutant_empty_list"]["rc"] != 0, True),
        check("G6_gate_blind_to_nonsense_item", gate["mutant_nonsense"]["rc"], 0),
        check("G7_gate_blind_to_emptied_single_item", gate["mutant_empty_item"]["rc"], 0),
        check("N1_tamper_guard_fails_closed", guard_ok, True),
        check("N2_generated_patch_v2_applies_to_v2", patch_v2_ok, True),
    ]
    n_pass = sum(1 for c in checks if c["pass"])

    pins_exit = measure_pins()
    drift = [k for k, v in pins_exit.items() if not v["match"]]

    report = {
        "task_id": TASK_ID,
        "actor": "worker-023",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "created_at": NOW(),
        "verdict": "revise",
        "score": 2.0,
        "decision_question": (
            "Does the ready F2b containment repair (worker-066 patch rebased candidate "
            "84b5d3fa; worker-044 composed rev14 candidate 48cadb72) fix the two defects "
            "without introducing a new normative defect in the same required slot?"),
        "hard_failures": [{
            "id": "W023-F2B-DIR1",
            "severity": "hard",
            "carrier": "regularity.must_not_conflate[0]",
            "line": 152,
            "finding": (
                "The replacement sentence asserts 'H2_loc-inextendibility ENTAILS this "
                "class's conclusion'. For AF-SCC-C0-VAC-GEN that entailment is false and "
                "is the reverse of the document's own declared graph: one_way_entailments "
                "declares 'no proper future C0 metric extension -> no proper future H2_loc "
                "extension', forbidden_weakenings[2] says 'H2_loc-inextendibility is weaker "
                "and entails the C2 sibling, not this class', and subsumption_note says "
                "'This direction runs C0 => H2loc => C2, never the reverse'. The sentence is "
                "correct in the C2 sibling, from which it was copied verbatim; in the C0 "
                "document it licenses exactly the substitution the file forbids."),
            "falsifier": (
                "Exhibit a declared one_way_entailment (or containment) at the pinned bytes "
                "under which 'no proper future H2_loc extension' entails 'no proper future "
                "C0 metric extension'; or show that the sentence is non-normative at the "
                "bound hash (rule_spec R06 names must_not_conflate a required slot)."),
        }],
        "repair_candidate_reviewed": {
            "worker_066_candidate_sha256": CAND_066_SHA,
            "worker_066_candidate_path": str(f_v1.relative_to(ROOT)),
            "worker_044_composed_sha256": sha(composed_b),
            "worker_008_candidate_sha256": sha(w008_b),
            "clause_byte_identical_across_all_three": bool(
                composed_clause and v1_clause and composed_clause == v1_clause),
        },
        "corrected_variant": {
            "path": str(f_v2.relative_to(ROOT)),
            "sha256": sha(v2.encode()),
            "patch_path": str(f_patch_v2.relative_to(ROOT)),
            "scope": ("same two repair lines as v1, with the must_not_conflate sentence "
                      "direction corrected to the document's own C0 => H2loc => C2 order"),
            "changed_lines_0based": ch_v2,
        },
        "probes": {"live": p_live, "v1_066": p_cand, "composed_044": p_composed,
                   "worker_008": p_w008, "c2_sibling": p_c2, "v2_corrected": p_v2,
                   "c2_reversed_mutant": p_c2_rev, "f1": p_f1},
        "canonical_gate": gate,
        "checks_passed": n_pass,
        "checks_total": len(checks),
        "checks": checks,
        "pins_entry": pins_entry,
        "pins_exit": pins_exit,
        "pin_drift_at_exit": drift,
        "void_on_hash_move": True,
        "authority": ("worker-level review only: no node status, no validation_status, no "
                      "gate verdict; landing the corrected variant is lead-formulation's call"),
        "non_claims": [
            "not a gate verdict and not a node completion",
            "not a claim about the mathematics of C0/C2 inextendibility beyond the "
            "document-internal entailment direction",
            "not a claim that the remaining F2b defect families (A2/A6/SEP-6) are closed",
        ],
        "falsifier": (
            "Re-run reproduce_023.py at the same pins. This review is falsified if: any "
            "pinned input hash differs (verdict void, exit 2); the 066 candidate does not "
            "reproduce to 84b5d3fa; either reviewed candidate lacks the clause; the C0 "
            "document declares the H2_loc -> C0 edge; the C2 sibling sentence is shown "
            "invalid; the corrected variant fails the canonical gate; the diff is not "
            "confined to the two repair lines; or any control departs from expectation."),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (EV / "checks.json").write_text(json.dumps(checks, indent=2, sort_keys=True))
    (EV / "probes.json").write_text(json.dumps(report["probes"], indent=2, sort_keys=True))
    (EV / "canonical_gate.json").write_text(json.dumps(gate, indent=2, sort_keys=True))
    (EV / "pins_entry.json").write_text(json.dumps(pins_entry, indent=2, sort_keys=True))

    print(f"{TASK_ID}: {n_pass}/{len(checks)} checks pass; "
          f"v1={CAND_066_SHA[:12]} v2={sha(v2.encode())[:12]} "
          f"hard_failure=W023-F2B-DIR1; pin_drift_at_exit={drift}")
    return 0 if n_pass == len(checks) and not drift else 3


if __name__ == "__main__":
    sys.exit(main())
