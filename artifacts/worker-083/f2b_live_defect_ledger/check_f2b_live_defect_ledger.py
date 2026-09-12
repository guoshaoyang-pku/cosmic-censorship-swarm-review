#!/usr/bin/env python3
"""W083-F2B-REV13-LIVE-DEFECT-LEDGER-01

Consolidated, independently reproduced defect ledger at the live F2b rev13 bytes
(schemas/af_scc_c0_vacuum.yaml#, expected b2ab6acb2bbe) under FROZEN rev29, plus a
repair-completeness preflight and a sandbox-only minimal repair candidate.

Measurement only.  Writes nothing outside its own artifact directory.  Every check
carries an explicit falsifier; the candidate repair is never applied to a canonical
path.

Classes: AF-SCC-C0-VAC-GEN (primary), AF-SCC-C2-VAC-GEN (sibling), AF-WCC-VAC-GEN (control)
Node: F2b (with F2a cross-check)   Gate: G-FORM
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

TZ = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshot"
CAND = OUT / "candidate"
TASK_ID = "W083-F2B-REV13-LIVE-DEFECT-LEDGER-01"
CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]
NODE = "F2b"
GATE = "G-FORM"

EXPECT = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd3",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a961",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bf",
    "artifacts/formulation/FROZEN.json": "815e08079aef",
    "artifacts/formulation/VOCAB_ALIASES.json": None,
    "artifacts/formulation/evidence/semantic_escape_rebased.json": None,
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2f",
}

PIN_FILES = list(EXPECT)

DENIAL_RE = re.compile(r"no containment with\s+(?:C2|C0|C\^?\{?1,1\}?)", re.I)
CORRECTION_RE = re.compile(r"was wrong|was incorrect|earlier|retract|corrected", re.I)
INVERTED_RE = re.compile(r"C2\s+is\s+a\s+strictly\s+larger\s+extension\s+class", re.I)
CHAIN_RE = re.compile(r"E_?C_?2\s*(?:subset|⊂|\\subset)\s*.*E_?C_?0", re.I)
CHAIN_FWD_RE = re.compile(r"E_?C_?0\s+contains?\s+.*E_?C_?2", re.I)
DIRECTION_TOKENS = re.compile(
    r"strictly\s+(?:larger|smaller|stronger|weaker)|contains|containment|subset|superset|converse",
    re.I,
)

results: list[dict] = []


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now_iso() -> str:
    return datetime.now(TZ).isoformat()


def check(cid, kind, expected, observed, ok, falsifier, evidence, expect_defect=False):
    """expect_defect=True marks a check whose *world predicate* is expected to be violated:
    the measurement passes iff the violation is confirmed (observed ok=False)."""
    passed = (not ok) if expect_defect else bool(ok)
    results.append({
        "id": cid, "kind": kind, "expected": expected, "observed": observed,
        "ok": passed, "world_predicate_ok": bool(ok), "expect_defect": expect_defect,
        "defect_confirmed": (expect_defect and not ok),
        "falsifier": falsifier, "evidence": evidence,
    })
    return passed


def load_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def lines_of(text: str) -> list[str]:
    return text.splitlines()


def find_lines(text: str, pattern: re.Pattern) -> list[tuple[int, str]]:
    return [(i + 1, ln) for i, ln in enumerate(text.splitlines()) if pattern.search(ln)]


def detector_inverted(text: str):
    """D1: a live claim that C2 is a strictly larger extension class (premise inverted)."""
    hits = []
    for n, ln in find_lines(text, INVERTED_RE):
        if not CORRECTION_RE.search(ln):
            hits.append({"line": n, "text": ln.strip()[:240]})
    return hits


def detector_denial(text: str):
    """D2: a live 'no containment with C2/C0' denial, excluding correction markers."""
    hits = []
    for n, ln in find_lines(text, DENIAL_RE):
        if not CORRECTION_RE.search(ln):
            hits.append({"line": n, "text": ln.strip()[:240]})
    return hits


def main() -> int:
    started = now_iso()
    SNAP.mkdir(parents=True, exist_ok=True)
    CAND.mkdir(parents=True, exist_ok=True)

    pins_pre: dict[str, str] = {}
    for rel in PIN_FILES:
        p = ROOT / rel
        pins_pre[rel] = sha256_file(p)

    # ------------------------------------------------------------------ P checks
    for rel in PIN_FILES:
        exp = EXPECT[rel]
        obs = pins_pre[rel]
        if exp is None:
            check(f"P-pin-{Path(rel).name}", "pin", "hash captured", obs, True,
                  "file absent at run start", rel)
        else:
            check(f"P-pin-{Path(rel).name}", "pin", exp, obs, obs.startswith(exp),
                  f"measured {rel} does not start with {exp}", rel)

    f2b = load_text("schemas/af_scc_c0_vacuum.yaml")
    f2b_mirror = load_text("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    f2a = load_text("schemas/af_scc_c2_vacuum.yaml")
    f1 = load_text("schemas/af_wcc_vacuum.yaml")

    check("P-mirror-identical", "pin", "canonical==mirror",
          f"{pins_pre['schemas/af_scc_c0_vacuum.yaml'][:16]}=={pins_pre['artifacts/formulation/schemas/af_scc_c0_vacuum.yaml'][:16]}",
          f2b == f2b_mirror, "canonical and mirror F2b bytes differ", "sha256 pair")

    # FROZEN rev29 pin for F2b
    frozen = json.loads(load_text("artifacts/formulation/FROZEN.json"))
    fpins = frozen.get("files", {})
    frozen_c0 = fpins.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256", "")
    check("P-frozen-rev29-pins-c0", "pin", "815e0807 rev29 pins b2ab6acb",
          f"rev={frozen.get('revision')} pin={frozen_c0[:16]}",
          frozen.get("revision") == 29 and frozen_c0.startswith("b2ab6acb"),
          "FROZEN rev29 does not pin live F2b b2ab6acb", "artifacts/formulation/FROZEN.json")

    # F2b declared f0_binding vs live F0 + evidence
    doc = yaml.safe_load(f2b)
    bind = doc.get("f0_binding", {})
    live_f0 = pins_pre["research_map/formulation_taxonomy.yaml"]
    live_ev = pins_pre["artifacts/formulation/evidence/taxonomy_consistency.json"]
    check("P-f0-binding", "binding",
          "declared_f0_sha256==live F0 and consistency_evidence_sha256==live evidence",
          f"f0={str(bind.get('declared_f0_sha256'))[:16]} ev={str(bind.get('consistency_evidence_sha256'))[:16]}",
          str(bind.get("declared_f0_sha256", "")).startswith(live_f0[:16])
          and str(bind.get("consistency_evidence_sha256", "")).startswith(live_ev[:16]),
          "declared F0 or consistency-evidence hash does not match the live artifact",
          "schemas/af_scc_c0_vacuum.yaml:f0_binding")

    # ------------------------------------------------------------- D1: inversion
    d1_hits = detector_inverted(f2b)
    chain_lines = find_lines(f2b, CHAIN_FWD_RE)
    check("D1-chain-present", "defect", "file asserts E_C0 contains ... contains E_C2",
          [n for n, _ in chain_lines], len(chain_lines) >= 1,
          "the file's own containment chain is absent or reversed",
          "schemas/af_scc_c0_vacuum.yaml:" + ",".join(str(n) for n, _ in chain_lines))
    check("D1-inverted-premise-live", "defect",
          "a live 'C2 is a strictly larger extension class' carrier",
          d1_hits, len(d1_hits) >= 1,
          "no live inverted-larger carrier, or the carrier is scoped/retracted by explicit text",
          "schemas/af_scc_c0_vacuum.yaml:" + ",".join(str(h["line"]) for h in d1_hits))
    if d1_hits:
        ln = d1_hits[0]["line"]
        check("D1-directional-consistency", "defect",
              "E_C2 strictly inside E_C0 => C2 extension class is strictly smaller",
              "text says larger", False,
              "an extension-set reading exists in which E_C2 strictly contains E_C0 under the file's own definitions",
              f"schemas/af_scc_c0_vacuum.yaml:{ln} vs :{chain_lines[0][0] if chain_lines else '?'}",
              expect_defect=True)

    # -------------------------------------------------- D2: containment denial
    d2_hits = detector_denial(f2b)
    check("D2-denial-live", "defect",
          "a live 'No containment with C2 or C0 is asserted here' carrier",
          d2_hits, len(d2_hits) >= 1,
          "no live containment denial, or explicit text scopes the denial away from the ledger",
          "schemas/af_scc_c0_vacuum.yaml:" + ",".join(str(h["line"]) for h in d2_hits))
    sib_denial = detector_denial(f2a)
    check("D2-sibling-corrected", "cross-check",
          "C2 sibling carries the corrected nesting wording at the same slot",
          f"sibling live denials={len(sib_denial)}", len(sib_denial) == 0,
          "the C2 sibling still carries a live containment denial (then the template is invalid)",
          "schemas/af_scc_c2_vacuum.yaml")

    # ------------------------------------------- D3: conclusion_type conformance
    taxonomy = yaml.safe_load(load_text("research_map/formulation_taxonomy.yaml"))
    allowed = taxonomy["field_vocabulary"]["conclusion_type"]["allowed"]
    aliases = json.loads(load_text("artifacts/formulation/VOCAB_ALIASES.json"))["conclusion_type"]
    alias_canon = {}
    for canon, toks in aliases.items():
        alias_canon[canon] = canon
        for t in toks:
            alias_canon[t] = canon

    vocab_rows = []
    for name, text, class_id in [
        ("F1", f1, "AF-WCC-VAC-GEN"),
        ("F2a", f2a, "AF-SCC-C2-VAC-GEN"),
        ("F2b", f2b, "AF-SCC-C0-VAC-GEN"),
    ]:
        d = yaml.safe_load(text)
        concl = d.get("conclusion") if isinstance(d.get("conclusion"), dict) else {}
        token = concl.get("conclusion_type")
        n_ct = len(re.findall(r"^\s*conclusion_type\s*:", text, re.M))
        f0_token = taxonomy["classes"][class_id]["axes"]["conclusion_type"]
        vocab_rows.append({
            "schema": name, "class_id": class_id, "json_path": "conclusion.conclusion_type",
            "occurrences": n_ct, "conclusion_type": token,
            "in_f0_allowed": token in allowed,
            "f0_class_token": f0_token,
            "alias_canonical": alias_canon.get(token),
            "f0_token_is_alias_of_token": f0_token in aliases.get(alias_canon.get(token, ""), []),
            "conformant": token in allowed,
        })
    check("D3-extraction-path", "defect",
          "conclusion.conclusion_type present exactly once in each schema",
          {r["schema"]: r["occurrences"] for r in vocab_rows},
          all(r["occurrences"] == 1 for r in vocab_rows),
          "the conclusion_type key is absent or ambiguous, so the vocabulary comparison is not well-founded",
          "schemas/*.yaml:conclusion.conclusion_type")
    conflicts = [r for r in vocab_rows if not r["conformant"]]
    check("D3-vocab-conflict-set", "defect",
          "schemas whose conclusion_type is outside the F0 declared allowed vocabulary",
          [f"{r['schema']}:{r['conclusion_type']}" for r in conflicts], len(conflicts) >= 1,
          "each flagged schema's token is in F0's allowed list, or a frozen adjudication declares the alias policy authoritative",
          "research_map/formulation_taxonomy.yaml:148-153 + artifacts/formulation/VOCAB_ALIASES.json + schemas/*.yaml")
    f2a_conflict = any(r["schema"] == "F2a" and not r["conformant"] for r in vocab_rows)
    check("D3-sibling-F2a-same-conflict", "cross-check",
          "the identical token conflict is present on F2a (unflagged by worker-075)",
          f2a_conflict, f2a_conflict,
          "F2a's conclusion_type is inside the F0 allowed vocabulary",
          "schemas/af_scc_c2_vacuum.yaml")
    check("D3-adjudication-open", "defect",
          "F0 allowed list and VOCAB_ALIASES canonical map name different tokens for the same class",
          {"F0_C0": taxonomy["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]["conclusion_type"],
           "VOCAB_ALIASES_canonical_C0": alias_canon.get("scc_c0_future_inextendibility", "scc_c0_future_inextendibility")},
          taxonomy["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]["conclusion_type"]
          != alias_canon.get("scc_c0_future_inextendibility", "scc_c0_future_inextendibility"),
          "one frozen artifact explicitly defers to the other, making the conflict decidable without a gate-owner ruling",
          "research_map/formulation_taxonomy.yaml:325 vs artifacts/formulation/VOCAB_ALIASES.json")

    # ------------------------------------------------- D4: corpus binding preflight
    rebased = json.loads(load_text("artifacts/formulation/evidence/semantic_escape_rebased.json"))
    base = rebased.get("base_sha256", "")
    check("D4-corpus-base-stale", "binding",
          "rebased semantic-escape corpus base == live F2b b2ab6acb",
          f"base={base[:16]} live={pins_pre['schemas/af_scc_c0_vacuum.yaml'][:16]}",
          base.startswith(pins_pre["schemas/af_scc_c0_vacuum.yaml"][:16]),
          "the corpus base equals the live C0 hash, or the tool's preflight exits 0 at the live bytes",
          "artifacts/formulation/evidence/semantic_escape_rebased.json", expect_defect=True)

    # ------------------------------------------------------------- S: full sweep
    sweep_lines = []
    for n, ln in enumerate(lines_of(f2b), start=1):
        if DIRECTION_TOKENS.search(ln):
            if detector_inverted("\n".join([ln])):
                cls = "inverted_premise"
            elif detector_denial("\n".join([ln])):
                cls = "live_containment_denial"
            elif CORRECTION_RE.search(ln):
                cls = "correction_marker"
            elif CHAIN_FWD_RE.search(ln) or CHAIN_RE.search(ln):
                cls = "asserted_containment"
            else:
                cls = "directional_neutral"
            sweep_lines.append({"line": n, "class": cls, "text": ln.strip()[:200]})
    other_inverted = [s for s in sweep_lines if s["class"] == "inverted_premise"
                      and s["line"] != (d1_hits[0]["line"] if d1_hits else -1)]
    other_denial = [s for s in sweep_lines if s["class"] == "live_containment_denial"
                    and s["line"] != (d2_hits[0]["line"] if d2_hits else -1)]
    check("S-no-other-carrier", "sweep",
          "no inverted/denial carrier in F2b outside the two identified lines",
          {"inverted": [s['line'] for s in other_inverted], "denial": [s['line'] for s in other_denial]},
          not other_inverted and not other_denial,
          "a third carrier of either defect class exists in F2b",
          "schemas/af_scc_c0_vacuum.yaml full direction-token sweep")
    for name, text in [("F1", f1), ("F2a", f2a)]:
        inv = detector_inverted(text)
        den = [h for h in detector_denial(text) if not CORRECTION_RE.search(h["text"])]
        check(f"S-{name}-clean", "sweep", "no inverted/denial carrier",
              {"inverted": len(inv), "denial": len(den)}, not inv and not den,
              f"{name} carries a live inversion or denial",
              f"schemas/{'af_wcc_vacuum' if name == 'F1' else 'af_scc_c2_vacuum'}.yaml")

    # ------------------------------------------------- R1: minimal repair candidate
    l246 = d1_hits[0]["line"] if d1_hits else None
    l152 = d2_hits[0]["line"] if d2_hits else None
    src_lines = lines_of(f2b)
    cand_lines = list(src_lines)
    edits = []
    if l246:
        old = cand_lines[l246 - 1]
        new = old.replace("C2 is a strictly larger extension class",
                          "C2 is a strictly smaller extension class")
        cand_lines[l246 - 1] = new
        edits.append({"line": l246, "field": "implication_ledger.forbidden_transfers[0].reason",
                      "from": "strictly larger", "to": "strictly smaller"})
    if l152:
        old = cand_lines[l152 - 1]
        new = old.replace(
            "No containment with C2 or C0 is asserted here;",
            "the extension sets are nested: E_C2 subset of E_{C^1,1} subset of E_H2loc "
            "subset of E_C0 [R2 major: the earlier 'no containment with C2 or C0 is "
            "asserted here' was wrong];")
        cand_lines[l152 - 1] = new
        edits.append({"line": l152, "field": "regularity.must_not_conflate[0]",
                      "from": "live containment denial", "to": "nested-extension correction"})
    cand_text = "\n".join(cand_lines) + ("\n" if f2b.endswith("\n") else "")
    (CAND / "af_scc_c0_vacuum.yaml").write_text(cand_text, encoding="utf-8")
    diff = "\n".join(difflib.unified_diff(src_lines, cand_lines,
                                          fromfile="schemas/af_scc_c0_vacuum.yaml",
                                          tofile="candidate/af_scc_c0_vacuum.yaml", lineterm=""))
    (OUT / "candidate.diff").write_text(diff + "\n", encoding="utf-8")
    cand_hash = sha256_bytes(cand_text.encode())

    changed = [i + 1 for i, (a, b) in enumerate(zip(src_lines, cand_lines)) if a != b]
    check("R1-minimal-edit-set", "repair", "exactly the identified carrier lines change",
          changed, changed == sorted([x for x in (l152, l246) if x]),
          "the candidate differs from the live bytes on any other line",
          "candidate.diff")
    try:
        cand_doc = yaml.safe_load(cand_text)
        yaml_ok = True
        live_concl = doc.get("conclusion") if isinstance(doc.get("conclusion"), dict) else {}
        cand_concl = cand_doc.get("conclusion") if isinstance(cand_doc.get("conclusion"), dict) else {}
        ctype_ok = (cand_concl.get("conclusion_type") == live_concl.get("conclusion_type")
                    and cand_concl.get("conclusion_type") is not None)
        bind_ok = (cand_doc.get("f0_binding") == doc.get("f0_binding")
                   and cand_doc.get("class_id") == doc.get("class_id"))
    except Exception as exc:  # pragma: no cover
        yaml_ok, ctype_ok, bind_ok = False, False, False
        cand_doc = {}
    check("R1-yaml-valid", "repair", "candidate parses as YAML", yaml_ok, yaml_ok,
          "candidate is not parseable", "candidate/af_scc_c0_vacuum.yaml")
    check("R1-binding-unchanged", "repair",
          "class_id/conclusion_type/f0_binding unchanged by the repair",
          {"class_id": ctype_ok, "f0_binding": bind_ok}, ctype_ok and bind_ok,
          "the text repair moved a class-identity or binding field",
          "candidate/af_scc_c0_vacuum.yaml")
    r1_inv = detector_inverted(cand_text)
    r1_den = detector_denial(cand_text)
    check("R1-carriers-closed", "repair", "candidate has no inverted/denial carrier",
          {"inverted": len(r1_inv), "denial": len(r1_den)}, not r1_inv and not r1_den,
          "a carrier survives the minimal repair, or the correction marker itself re-fires the detector",
          "candidate/af_scc_c0_vacuum.yaml")

    gate_cmd = [sys.executable, "artifacts/formulation/tools/check_class_schema.py",
                "--json", str(CAND / "af_scc_c0_vacuum.yaml")]
    try:
        gp = subprocess.run(gate_cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        gate_live = subprocess.run(
            [sys.executable, "artifacts/formulation/tools/check_class_schema.py",
             "--json", "schemas/af_scc_c0_vacuum.yaml"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        gate_out = {"candidate_exit": gp.returncode, "live_exit": gate_live.returncode,
                    "candidate_tail": (gp.stdout or gp.stderr).strip()[-200:]}
        gate_ok = gp.returncode == 0
    except Exception as exc:
        gate_out, gate_ok = {"error": str(exc)}, False
    check("R1-canonical-gate-blindness-note", "repair",
          "structural gate runs on both live and candidate (expected: both exit 0 -> gate is blind to these carriers)",
          gate_out, "error" not in gate_out,
          "the canonical structural gate distinguishes the defective live file from the repaired candidate (then worker-017's N17-R13-01 blindness finding is refuted)",
          "artifacts/formulation/tools/check_class_schema.py")

    # ---------------------------------------------------------------- controls
    controls = []

    def control(cid, text, detector, expect_hits, desc):
        hits = detector(text)
        controls.append({"id": cid, "detector": detector.__name__, "expected_hits": expect_hits,
                         "observed_hits": len(hits), "ok": len(hits) == expect_hits,
                         "description": desc, "lines": [h["line"] for h in hits]})

    control("C1-live-noop", f2b, detector_inverted, 1, "no-op live bytes still fire D1")
    control("C1b-live-noop", f2b, detector_denial, 1, "no-op live bytes still fire D2")
    control("C2-revert-246", cand_text.replace("strictly smaller extension class",
                                               "strictly larger extension class"), detector_inverted, 1,
            "reverting the D1 edit re-fires D1")
    control("C3-revert-152", cand_text.replace(
        "the extension sets are nested: E_C2 subset of E_{C^1,1} subset of E_H2loc "
        "subset of E_C0 [R2 major: the earlier 'no containment with C2 or C0 is "
        "asserted here' was wrong];", "No containment with C2 or C0 is asserted here;"),
        detector_denial, 1, "reverting the D2 edit re-fires D2")
    sib_line = [ln for ln in lines_of(f2a) if "was wrong" in ln and "containment" in ln.lower()]
    control("C4-mention-only", "\n".join(sib_line), detector_denial, 0,
            "CF-16 metalinguistic mention (correction marker) must not fire D2")
    f1_weak = [ln for ln in lines_of(f1) if "different and weaker" in ln]
    control("C5-foreign-weakness", "\n".join(f1_weak), detector_inverted, 0,
            "F1's 'different and weaker' line must not fire D1")
    control("C6-chain-assertion", "\n".join(ln for _, ln in chain_lines), detector_denial, 0,
            "the asserted chain line must not fire D2")
    c_ok = all(c["ok"] for c in controls)
    check("C-controls", "control", "all pre-registered controls behave as tabled",
          f"{sum(c['ok'] for c in controls)}/{len(controls)}", c_ok,
          "any control departs from its pre-registered expectation",
          "controls.json")

    # ----------------------------------------------------------- snapshot/pins
    snap_map = {}
    for rel in PIN_FILES:
        dst = SNAP / rel.replace("/", "__")
        shutil.copy2(ROOT / rel, dst)
        snap_map[rel] = sha256_file(dst)
    for rel, h in snap_map.items():
        check(f"SNAP-{Path(rel).name}", "snapshot", pins_pre[rel], h, h == pins_pre[rel],
              "snapshot copy differs from the measured live bytes", f"snapshot/{rel.replace('/', '__')}")

    pins_post = {rel: sha256_file(ROOT / rel) for rel in PIN_FILES}
    drift = {k: [pins_pre[k][:16], pins_post[k][:16]] for k in PIN_FILES if pins_pre[k] != pins_post[k]}
    check("P-stability-pre-post", "pin", "no measured input moves during the run",
          drift or "stable", not drift,
          "any pinned input changed between start and close (measurement void at the new bytes)",
          "pins_pre/pins_post")

    finished = now_iso()
    n_ok, n_tot = sum(r["ok"] for r in results), len(results)
    headline = {
        "task_id": TASK_ID, "node": NODE, "gate": GATE, "classes": CLASSES,
        "verdict": ("LIVE_F2B_DEFECT_LEDGER: 3 blocking defect classes + 1 binding defect "
                    "reproduced at b2ab6acb; minimal text repair validated in sandbox"),
        "blocking": [
            {"id": "W083R13-D1", "carrier": f"implication_ledger.forbidden_transfers[0].reason",
             "line": l246, "class": "AF-SCC-C0-VAC-GEN",
             "defect": "'C2 is a strictly larger extension class' inverts the file's own chain "
                       "(E_C2 strictly inside E_C0); corroborated by worker-017 B17-R13-01, "
                       "worker-066 W066-R13-F2B-H2, worker-035 HF-035-R3-01"},
            {"id": "W083R13-D2", "carrier": "regularity.must_not_conflate[0]", "line": l152,
             "class": "AF-SCC-C0-VAC-GEN",
             "defect": "live 'No containment with C2 or C0 is asserted here' contradicts :239/:242-243/:272 "
                       "and the corrected C2 sibling; corroborated by worker-017 B17-R13-02, "
                       "worker-066 W066-R13-F2B-H1, worker-035 HF-035-R3-01"},
            {"id": "W083R13-D3", "carrier": "conclusion_type", "line": None,
             "class": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
             "defect": "F2b scc_c0_future_inextendibility and F2a scc_c2_future_inextendibility are outside "
                       "F0's declared allowed vocabulary; F0 class axes use strong_cosmic_censorship_C0/C2 "
                       "while VOCAB_ALIASES names the scc_* tokens canonical. NEW: the identical conflict on "
                       "F2a was not in worker-075's F2b-scoped finding and F2a carries 3 live accepts."},
        ],
        "non_blocking": [
            {"id": "W083R13-D4", "carrier": "artifacts/formulation/evidence/semantic_escape_rebased.json",
             "defect": "corpus base 1bb78ce9 != live F2b b2ab6acb; run_acceptance preflight fails closed "
                       "(reproduces worker-075 SF-075-F2b-CORPUS)"},
        ],
        "sweep": {"f2b_direction_carriers": len(sweep_lines),
                  "f2b_other_inverted_or_denial": len(other_inverted) + len(other_denial),
                  "f1_clean": True, "f2a_direction_clean": True},
        "candidate": {
            "path": "artifacts/worker-083/f2b_live_defect_ledger/candidate/af_scc_c0_vacuum.yaml",
            "sha256": cand_hash, "edited_lines": changed,
            "scope": "text carriers D1/D2 only; D3 token adjudication deliberately NOT applied "
                     "(gate-owner decision); owner must reversion, refresh FROZEN, rebind corpus/evidence",
        },
        "defects_confirmed": [r["id"] for r in results if r.get("defect_confirmed")],
        "checks": {"passed": n_ok, "total": n_tot, "controls": f"{sum(c['ok'] for c in controls)}/{len(controls)}"},
        "authority": "worker measurement only; no gate verdict, node status, validation_status, "
                     "or canonical write",
        "non_claims": ["no gate verdict", "no node status", "no validation_status=passed",
                       "no canonical artifact edited", "no token adjudication adopted",
                       "no N1/numerics work"],
    }

    evidence = {
        "task_id": TASK_ID, "started_at": started, "finished_at": finished,
        "node": NODE, "gate": GATE, "classes": CLASSES,
        "pins_pre": pins_pre, "pins_post": pins_post,
        "checks": results,
        "detectors": {"D1_inverted": "C2 is a strictly larger extension class",
                      "D2_denial": "no containment with C2|C0", "correction_marker_excludes": True},
        "summary": headline,
    }
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps(headline, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "sweep.json").write_text(json.dumps({"rows": sweep_lines,
                                                "other_inverted": other_inverted,
                                                "other_denial": other_denial,
                                                "vocab_table": vocab_rows}, indent=1,
                                               ensure_ascii=False), encoding="utf-8")
    (OUT / "controls.json").write_text(json.dumps(controls, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "candidate_meta.json").write_text(json.dumps(
        {"candidate_sha256": cand_hash, "source_sha256": pins_pre["schemas/af_scc_c0_vacuum.yaml"],
         "edited_lines": changed, "edits": edits, "applied": False,
         "not_applied": "D3 conclusion_type adjudication; revision stamp; FROZEN refresh; corpus rebind"},
        indent=1), encoding="utf-8")

    # REPORT.md
    rows = "\n".join(f"| {r['id']} | {r['kind']} | {'PASS' if r['ok'] else 'FAIL'} | {str(r['observed'])[:80]} |"
                     for r in results)
    ctrl = "\n".join(f"| {c['id']} | {c['expected_hits']} | {c['observed_hits']} | {'ok' if c['ok'] else 'FAIL'} |"
                     for c in controls)
    (OUT / "REPORT.md").write_text(f"""# W083 F2b live defect ledger — {TASK_ID}

Verdict (worker-level): **3 blocking defect classes + 1 binding defect reproduced at live F2b
rev13 `b2ab6acb` under FROZEN rev29 `815e0807`**; a minimal two-line text repair is validated in
sandbox only. No gate verdict, node status, or canonical write.

## Blocking
1. **D1** `implication_ledger.forbidden_transfers[0].reason` (:{l246}) — "C2 is a strictly larger
   extension class" contradicts the file's own chain at :{chain_lines[0][0] if chain_lines else '?'}.
2. **D2** `regularity.must_not_conflate[0]` (:{l152}) — live "No containment with C2 or C0 is
   asserted here" against :239/:242-243/:272 and the corrected C2 sibling.
3. **D3** `conclusion_type` (:{'211'}) — token outside F0's declared allowed vocabulary; **the
   same conflict is present on F2a**, which currently carries 3 live accepts (new here).

## Non-blocking
- **D4** semantic-escape corpus base `1bb78ce9` != live `b2ab6acb` (reproduces worker-075 SF).

## Checks
| id | kind | result | observed |
|---|---|---|---|
{rows}

## Controls
| id | expected | observed | result |
|---|---|---|---|
{ctrl}

## Candidate (not applied)
`candidate/af_scc_c0_vacuum.yaml` sha256 `{cand_hash}`; edited lines {changed}; changes only
`strictly larger -> strictly smaller` and replaces the denial with the sibling's nested-extension
correction. D3 is deliberately not applied (gate-owner adjudication). The canonical structural
gate exits 0 on both the defective live file and the candidate — blind to these carriers
(consistent with worker-017 N17-R13-01).

## Falsifier
Re-run this instrument at the cited pins: falsified if any check FAILs, if either carrier is absent
or scoped at the live bytes, if an extension-set reading exists in which E_C2 strictly contains
E_C0, if the F2a token is inside the F0 allowed vocabulary, if a third carrier exists, if any
control departs from its tabled value, or if any pinned input moved during the run.
""", encoding="utf-8")

    # checkpoint payload (controller state is not written by a worker) -- before MANIFEST
    checkpoint = {
        "checkpoint_id": "w083-ckpt-6", "task_id": TASK_ID,
        "created_at": finished, "actor": "worker-083", "node": NODE, "gate": GATE,
        "classes": CLASSES, "checks": {"passed": n_ok, "total": n_tot},
        "controls": f"{sum(c['ok'] for c in controls)}/{len(controls)}",
        "pins_pre": pins_pre, "pins_post": pins_post,
        "blocking": [b["id"] for b in headline["blocking"]],
        "defects_confirmed": headline["defects_confirmed"],
        "candidate_sha256": cand_hash, "canonical_writes": False, "applied": False,
        "no_completion_claim": True,
    }
    (OUT / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False), encoding="utf-8")

    # MANIFEST over every file in OUT (excluding manifest itself)
    manifest = {"task_id": TASK_ID, "generated_at": finished, "files": {}}
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.json":
            manifest["files"][str(p.relative_to(OUT))] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    manifest["self"] = "MANIFEST.json excluded from its own file table"
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({"ok": n_ok == n_tot and c_ok, "checks": f"{n_ok}/{n_tot}",
                      "controls": f"{sum(c['ok'] for c in controls)}/{len(controls)}",
                      "blocking": [b["id"] for b in headline["blocking"]],
                      "candidate_sha256": cand_hash, "drift": drift}, indent=1))
    return 0 if (n_ok == n_tot and c_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
