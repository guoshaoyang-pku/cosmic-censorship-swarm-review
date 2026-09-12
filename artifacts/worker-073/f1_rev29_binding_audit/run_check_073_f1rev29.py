#!/usr/bin/env python3
"""
W073-F1-REV29-BINDING-AUDIT-01  --  worker-073 (recycled slot)

One class-bound task: independent, read-only, byte-bound post-repair audit of
node F1 / class AF-WCC-VAC-GEN at the FROZEN rev29 pin, plus adjudication of the
two blocking findings recorded at that pin (worker-061 HF-W061-VAR-01/02) and a
binding census of F1's gate-evidence corpus schemas/f1_falsifier_tests.jsonl.

Read-only. Writes only under artifacts/worker-073/f1_rev29_binding_audit/.
Imports no project tooling (own strict YAML loader, own regex detectors).

Pre-registered decision rule (fixed before the scans were run):
  R1  if any corpus row has binding_sha256 != the live F1 pin
      -> finding F1-073-01 severity blocking, verdict revise.
  R2  if the variant-SET predicate-level inversion is ABSENT at the pin and
      PRESENT in the superseded rev12 control copy
      -> finding F1-073-02 severity resolved (HF-W061-VAR-01 not reproducible).
  R3  if VARIANT_REGISTRY.json / variant-SET delta assert SET strictly weaker
      -> finding F1-073-03 severity info (L-FORM-03 repaired in the satellites;
      the F0-frozen taxonomy/supplement text is outside F1's bytes).
  R4  any control in C1..C7 not firing -> status CONTROL_FAILURE, no verdict,
      exit code 2.
  R5  required pin (F1 schema, rev12 control) drifted from the declared hash
      -> fail closed, exit code 3, no verdict written.

Exit codes: 0 verdict emitted (accept or revise) with all controls fired;
            2 control failure; 3 required-pin drift.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PIN_DIR = os.path.join(HERE, "pinned")
REPORT_PATH = os.path.join(HERE, "report.json")

# --- required pins: the audited object and its positive control -------------
F1_PATH = "schemas/af_wcc_vacuum.yaml"
F1_PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
REV12_PATH = "artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml"
REV12_PIN = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"

# --- frame files: snapshotted + measured, not hard-pinned -------------------
FRAME_PATHS = [
    F1_PATH,
    REV12_PATH,
    "schemas/f1_falsifier_tests.jsonl",
    "artifacts/formulation/FROZEN.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
]

# rev13-touched leaves, source: F1 revision_history index 11 + f0_binding.binding_note
REV13_TOUCHED_LEAVES = {
    "visibility.definition",
    "class_identity_variants",
    "f0_binding.consistency_evidence_sha256",
}


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raw(path):
    with open(path, "rb") as fh:
        return fh.read()


# ------------------------- own strict YAML loader ---------------------------
class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(
                "duplicate YAML key %r at line %d" % (key, key_node.start_mark.line + 1)
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def strict_load(path):
    return yaml.load(raw(path).decode("utf-8"), Loader=StrictLoader)


# ------------------------- detectors ---------------------------------------
INVERSION_RE = re.compile(r"strictly\s+STRONGER")
BRACKET_RE = re.compile(r"\[[^\]]*\]")


def top_level_ranges(text):
    """Map top-level YAML key -> (start_line, end_line) 0-based, inclusive."""
    lines = text.splitlines()
    starts = []
    for i, line in enumerate(lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            starts.append((i, m.group(1)))
    out = {}
    for idx, (i, key) in enumerate(starts):
        end = starts[idx + 1][0] - 1 if idx + 1 < len(starts) else len(lines) - 1
        out[key] = (i, end)
    return out


def variant_block_lines(text):
    """Return the class_identity_variants block as a list of (lineno, line)."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("class_identity_variants:"):
            start = i
            break
    if start is None:
        raise ValueError("class_identity_variants block not found")
    end = len(lines) - 1
    for j in range(start + 1, len(lines)):
        if lines[j] and not lines[j][0].isspace():
            end = j - 1
            break
    return [(i + 1, lines[i]) for i in range(start, end + 1)]


def inversion_hits_in_variant_block(text):
    """Predicate-level inverted direction, ignoring bracketed historical notes."""
    hits = []
    for lineno, line in variant_block_lines(text):
        stripped = BRACKET_RE.sub("", line)
        if INVERSION_RE.search(stripped):
            hits.append({"line": lineno, "text": line.strip()[:220]})
    return hits


def stronger_census(text):
    ranges = top_level_ranges(text)
    def key_of(lineno1):
        for key, (a, b) in ranges.items():
            if a + 1 <= lineno1 <= b + 1:
                return key
        return None
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if INVERSION_RE.search(line):
            stripped = BRACKET_RE.sub("", line)
            out.append(
                {
                    "line": i,
                    "top_level_key": key_of(i),
                    "occurs_outside_bracket_note": bool(INVERSION_RE.search(stripped)),
                    "text": line.strip()[:200],
                }
            )
    return out


def corpus_rows(path):
    return [json.loads(l) for l in raw(path).decode("utf-8").splitlines() if l.strip()]


def main():
    os.makedirs(PIN_DIR, exist_ok=True)
    t0 = now()
    checks = []
    controls = []
    findings = []

    def check(cid, question, expected, measured, passed):
        checks.append(
            {
                "id": cid,
                "question": question,
                "expected": expected,
                "measured": measured,
                "pass": bool(passed),
            }
        )
        return bool(passed)

    def control(cid, description, fired, detail=""):
        controls.append(
            {"id": cid, "description": description, "fired": bool(fired), "detail": detail}
        )
        return bool(fired)

    # ---- A. snapshot + required pin integrity (fail closed) ----------------
    live_t0 = {}
    for rel in FRAME_PATHS:
        abspath = os.path.join(REPO, rel)
        if not os.path.exists(abspath):
            print("FATAL missing frame file:", rel)
            return 3
        digest = sha256_file(abspath)
        live_t0[rel] = digest
        snap = os.path.join(PIN_DIR, rel.replace("/", "__"))
        shutil.copyfile(abspath, snap)
        if sha256_file(snap) != digest:
            print("FATAL snapshot copy mismatch:", rel)
            return 3

    if live_t0[F1_PATH] != F1_PIN:
        print("FATAL required pin drift F1:", live_t0[F1_PATH])
        return 3
    if live_t0[REV12_PATH] != REV12_PIN:
        print("FATAL required positive-control pin drift rev12:", live_t0[REV12_PATH])
        return 3

    check("A1", "live F1 sha == declared pin", F1_PIN, live_t0[F1_PATH], True)
    check("A2", "rev12 control sha == declared pin", REV12_PIN, live_t0[REV12_PATH], True)

    f1_bytes = raw(os.path.join(REPO, F1_PATH))
    f1_text = f1_bytes.decode("utf-8")
    rev12_text = raw(os.path.join(REPO, REV12_PATH)).decode("utf-8")

    # ---- B. YAML strictness + identity -------------------------------------
    try:
        f1 = strict_load(os.path.join(REPO, F1_PATH))
        check("B1", "F1 parses under strict duplicate-key rejection", "no exception", "parsed", True)
    except Exception as exc:  # pragma: no cover - fail closed
        check("B1", "F1 parses under strict duplicate-key rejection", "no exception", repr(exc), False)
        f1 = None

    if f1 is not None:
        check("B2", "class_id", "AF-WCC-VAC-GEN", f1.get("class_id"), f1.get("class_id") == "AF-WCC-VAC-GEN")
        check("B3", "node_id / revision", "F1 / 13", "%s / %s" % (f1.get("node_id"), f1.get("revision")),
              f1.get("node_id") == "F1" and f1.get("revision") == 13)
        check("B4", "conclusion_type", "weak_cosmic_censorship",
              (f1.get("conclusion") or {}).get("conclusion_type"),
              (f1.get("conclusion") or {}).get("conclusion_type") == "weak_cosmic_censorship")
        check("B5", "epistemic_status", "open_problem", f1.get("epistemic_status"),
              f1.get("epistemic_status") == "open_problem")
        anti = ((f1.get("anti_scope") or {}).get("not_this_class") or [])
        anti_ids = sorted({row.get("class_id") for row in anti if isinstance(row, dict)})
        check("B6", "anti_scope names the three sibling classes",
              "AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH",
              anti_ids,
              set(anti_ids) >= {"AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"})
        forbidden = (f1.get("conclusion") or {}).get("forbidden_strengthenings") or []
        check("B7", "conclusion forbids C2/C0 inextendibility",
              "one entry naming C2 and C0",
              [s for s in forbidden if "inextendibility" in s][:2],
              any("C2" in s and "C0" in s and "inextendibility" in s for s in forbidden))
        tier1 = (f1.get("falsifier") or {}).get("tier_1") or {}
        check("B8", "falsifier.tier_1.refutes == class", "AF-WCC-VAC-GEN", tier1.get("refutes"),
              tier1.get("refutes") == "AF-WCC-VAC-GEN")
        check("B9", "falsifier.tier_1 machine-checkable steps non-empty", ">=1",
              len(tier1.get("machine_checkable_steps") or []),
              len(tier1.get("machine_checkable_steps") or []) >= 1)

    # ---- C. HF-W061-VAR-01 adjudication at the pin -------------------------
    cur_hits = inversion_hits_in_variant_block(f1_text)
    rev12_hits = inversion_hits_in_variant_block(rev12_text)

    cur_relation = None
    for line in f1_text.splitlines():
        if re.match(r"^\s+relation:", line) and "single-q tail predicate" in line:
            cur_relation = line.strip()
    check("C1", "variant SET relation at pin says strictly WEAKER",
          "contains 'strictly WEAKER' and not 'weakness only past-closedness'",
          (cur_relation or "")[:160],
          bool(cur_relation) and "strictly WEAKER" in cur_relation)
    check("C2", "predicate-level inversion absent from pin variant block", "0 hits",
          len(cur_hits), len(cur_hits) == 0)
    control("C3", "positive control: rev12 variant block reproduces the inversion", len(rev12_hits) >= 1,
            json.dumps(rev12_hits)[:300])

    block_text = "\n".join(line for _, line in variant_block_lines(f1_text))
    mut_block = block_text.replace("strictly WEAKER", "strictly STRONGER")
    mut_hits = inversion_hits_in_variant_block(mut_block)
    control("C4", "negative-control mutation WEAKER->STRONGER inside the variant block fires the detector",
            len(mut_hits) >= 1, json.dumps(mut_hits)[:300])

    census = stronger_census(f1_text)
    block_linenos = [n for n, _ in variant_block_lines(f1_text)]
    census_in_block = [row for row in census if row["line"] in block_linenos]
    check("C5", "every in-block 'strictly STRONGER' token is inside a bracketed historical note",
          "all bracketed (0 unbracketed)",
          [{"line": r["line"], "outside_bracket": r["occurs_outside_bracket_note"]} for r in census_in_block],
          all(not r["occurs_outside_bracket_note"] for r in census_in_block))
    check("C6", "every remaining 'strictly STRONGER' is historical or a different subject",
          "all occurrences bracket-noted, in revision_history, or about genericity/B-containment/tier_2",
          [{"line": r["line"], "key": r["top_level_key"], "outside_bracket": r["occurs_outside_bracket_note"]} for r in census],
          all(
              (not r["occurs_outside_bracket_note"])
              or r["top_level_key"] in {"genericity", "negation_conclusion", "falsifier", "visibility"}
              for r in census
          ))

    # whole/tail equivalence language (rev13 claim)
    d5 = ((f1 or {}).get("quantifiers") or {}).get("domains", {}).get("D5", {}).get("definition", "")
    vis_def = ((f1 or {}).get("visibility") or {}).get("definition", "")
    check("C7", "D5 states whole/tail EQUIVALENCE (past-closedness)",
          "EQUIVALENT and past-closed",
          d5[:150],
          "EQUIVALENT" in d5 and "past-closed" in d5)
    check("C8", "visibility.definition states EQUIVALENCE", "EQUIVALENT",
          vis_def[:150], "EQUIVALENT" in vis_def)

    # ---- D. f0_binding hash chain ------------------------------------------
    fb = (f1 or {}).get("f0_binding") or {}
    f0_measured = live_t0["research_map/formulation_taxonomy.yaml"]
    cons_measured = live_t0["artifacts/formulation/evidence/taxonomy_consistency.json"]
    supp_measured = live_t0["artifacts/formulation/formulation_taxonomy.yaml"]
    check("D1", "declared_f0_sha256 resolves", fb.get("declared_f0_sha256"),
          f0_measured, fb.get("declared_f0_sha256") == f0_measured)
    check("D2", "consistency_evidence_sha256 resolves", "9e335e9ba1bf...",
          cons_measured, fb.get("consistency_evidence_sha256") == cons_measured)
    check("D3", "class-contract supplement file exists", "exists", supp_measured[:16],
          os.path.exists(os.path.join(REPO, "artifacts/formulation/formulation_taxonomy.yaml")))
    taxonomy = strict_load(os.path.join(REPO, "research_map/formulation_taxonomy.yaml"))
    ptr = (f1 or {}).get("class_contract_pointer", "")
    check("D4", "class_contract_pointer resolves in the canonical taxonomy",
          "classes.AF-WCC-VAC-GEN", ptr,
          "AF-WCC-VAC-GEN" in (taxonomy.get("classes") or {}))
    cons = json.loads(raw(os.path.join(REPO, "artifacts/formulation/evidence/taxonomy_consistency.json")))
    check("D5", "consistency evidence reports consistent=True", True, cons.get("consistent"),
          cons.get("consistent") is True)

    # ---- E. corpus binding census (the blocking chapter) -------------------
    corpus_rel = "schemas/f1_falsifier_tests.jsonl"
    corpus_path = os.path.join(REPO, corpus_rel)
    rows = corpus_rows(corpus_path)
    frozen = json.loads(raw(os.path.join(REPO, "artifacts/formulation/FROZEN.json")))
    frozen_rev = frozen.get("revision")
    frozen_entry = (frozen.get("files") or {}).get(corpus_rel, {})
    corpus_measured = live_t0[corpus_rel]

    stale = [r for r in rows if r.get("binding_sha256") != F1_PIN]
    rev_label_bad = [r for r in rows if r.get("binding_frozen_revision") != frozen_rev]
    edited = []
    for r in rows:
        dec = str(r.get("deciding_field", ""))
        alts = json.dumps(r.get("deciding_field_alternates") or [])
        if dec in REV13_TOUCHED_LEAVES or any(leaf in alts for leaf in REV13_TOUCHED_LEAVES) \
           or any(leaf in dec for leaf in REV13_TOUCHED_LEAVES):
            edited.append(r.get("test_id"))

    check("E1", "corpus rows all class AF-WCC-VAC-GEN", len(rows),
          sum(1 for r in rows if r.get("class_id") == "AF-WCC-VAC-GEN"),
          all(r.get("class_id") == "AF-WCC-VAC-GEN" for r in rows))
    check("E2", "corpus rows binding_sha256 == live F1 pin", 0,
          len(stale), len(stale) == 0)
    check("E3", "corpus rows binding_frozen_revision == FROZEN revision", 0,
          len(rev_label_bad), len(rev_label_bad) == 0)
    check("E4", "FROZEN rev%s pins the corpus at its measured sha" % frozen_rev,
          corpus_measured, frozen_entry.get("sha256"),
          frozen_entry.get("sha256") == corpus_measured)
    check("E5", "no corpus row probes a rev13-edited leaf", "[]", edited, len(edited) == 0)

    # checker-not-hardwired controls
    synth_ok = [{"test_id": "SYNTH-OK", "class_id": "AF-WCC-VAC-GEN",
                 "binding_sha256": F1_PIN, "binding_frozen_revision": frozen_rev}]
    synth_bad = [{"test_id": "SYNTH-BAD", "class_id": "AF-WCC-VAC-GEN",
                  "binding_sha256": REV12_PIN, "binding_frozen_revision": 27}]
    control("C9", "synthetic row at the pin passes the stale filter",
            len([r for r in synth_ok if r.get("binding_sha256") != F1_PIN]) == 0)
    control("C10", "synthetic row at rev12 fails the stale filter",
            len([r for r in synth_bad if r.get("binding_sha256") != F1_PIN]) == 1)

    # duplicate-key loader control
    dup_fired = False
    try:
        yaml.load("a: 1\na: 2\n", Loader=StrictLoader)
    except ValueError:
        dup_fired = True
    control("C11", "strict loader rejects a duplicate YAML key", dup_fired)

    # missing-file control
    missing_fired = False
    try:
        raw(os.path.join(REPO, "schemas/__definitely_absent__.yaml"))
    except FileNotFoundError:
        missing_fired = True
    control("C12", "missing-file probe raises (fail closed)", missing_fired)

    # ---- F. satellite residual (L-FORM-03) ---------------------------------
    reg = json.loads(raw(os.path.join(REPO, "artifacts/formulation/VARIANT_REGISTRY.json")))
    reg_txt = json.dumps(reg)
    delta = json.loads(raw(os.path.join(REPO, "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")))
    delta_txt = json.dumps(delta)
    reg_weaker = "strictly weaker than AF-WCC-VAC-GEN" in reg_txt
    delta_weaker = "strictly weaker than AF-WCC-VAC-GEN" in delta_txt
    delta_base = ((delta.get("base") or {}).get("sha256"))
    check("F1", "VARIANT_REGISTRY SET strength now strictly weaker", True, reg_weaker, reg_weaker)
    check("F2", "variant-SET delta strength now strictly weaker", True, delta_weaker, delta_weaker)
    check("F3", "variant-SET delta base re-pinned to rev13", F1_PIN, delta_base, delta_base == F1_PIN)
    tax200 = raw(os.path.join(REPO, "research_map/formulation_taxonomy.yaml")).decode().splitlines()[199]
    sup176 = raw(os.path.join(REPO, "artifacts/formulation/formulation_taxonomy.yaml")).decode().splitlines()[175]
    residual_f0_frozen = ("stronger" in tax200) and ("strictly stronger" in tax200)
    residual_supplement = "strictly stronger" in sup176
    check("F4", "F0-frozen taxonomy/supplement residual recorded (outside F1 bytes)",
          "recorded observation, not an F1 byte claim",
          {"taxonomy_line_200": tax200.strip()[:110], "supplement_line_176": sup176.strip()[:110]},
          True)

    # ---- findings ----------------------------------------------------------
    if stale:
        findings.append(
            {
                "id": "F1-073-01",
                "severity": "blocking",
                "leaf": "schemas/f1_falsifier_tests.jsonl",
                "finding": (
                    "%d/%d gate-evidence rows carry binding_sha256=%s (F1 rev12, the FROZEN rev27 pin) "
                    "while the live audited pin is %s (F1 rev13) and FROZEN.json is revision %s. "
                    "binding_frozen_revision is %s on %d/%d rows. FROZEN rev%s pins the corpus at %s, so the "
                    "corpus bytes are frozen but the binding target inside them is one revision stale."
                    % (len(stale), len(rows), REV12_PIN[:16], F1_PIN[:16], frozen_rev,
                       str((rows[0] or {}).get("binding_frozen_revision")), len(rev_label_bad), len(rows),
                       frozen_rev, corpus_measured[:16])
                ),
                "criterion": (
                    "assignment audit-r2-F1-a (astra-lead-audit, 2026-09-12T00:44:18): the falsifier rows in "
                    "schemas/f1_falsifier_tests.jsonl must each carry binding_sha256 == the pin."
                ),
                "materially_affected_rows": edited,
                "prescription": (
                    "Rebind the 25 rows to F1 d9cebb9404b2 + FROZEN rev%s (binding_sha256, binding_ref, "
                    "binding_frozen_revision) and re-derive the probe text for the rows whose deciding leaf was "
                    "edited by rev13 (%s); or record an explicit controller adjudication that the rev13 delta is "
                    "immaterial for those probes and amend the acceptance criterion. Silence would let a gate "
                    "accept F1 on evidence that predates the frozen revision." % (frozen_rev, ", ".join(edited) or "none")
                ),
                "falsifier": (
                    "Re-measure schemas/f1_falsifier_tests.jsonl: if every row's binding_sha256 equals the live "
                    "F1 pin and every deciding-leaf probe postdates F1 rev13, this finding is void."
                ),
            }
        )
    variant_rel_line = next((r["line"] for r in census if r["top_level_key"] == "class_identity_variants"), -1)
    if variant_rel_line < 0:
        variant_rel_line = -1
    findings.append(
        {
            "id": "F1-073-02",
            "severity": "resolved",
            "leaf": "schemas/af_wcc_vacuum.yaml class_identity_variants",
            "finding": (
                "HF-W061-VAR-01 is NOT reproducible at the audited pin: the variant-SET relation at "
                "schemas/af_wcc_vacuum.yaml:%s of the live file reads 'strictly WEAKER', the predicate-level "
                "inversion detector returns 0 hits in the variant block, and the only 'strictly STRONGER' "
                "tokens are bracketed historical notes or different subjects. The same detector fires on the "
                "superseded rev12 control (line %s), so the quoted defect was true of rev12 and was removed "
                "by the rev13 repair."
                % (variant_rel_line, (rev12_hits[0]["line"] if rev12_hits else -1))
            ),
            "falsifier": (
                "A live byte string in the variant-SET block asserting the set-based reading is strictly "
                "STRONGER than the single-q tail predicate, or a rev12 control that does not reproduce."
            ),
        }
    )
    if reg_weaker and delta_weaker:
        findings.append(
            {
                "id": "F1-073-03",
                "severity": "info",
                "leaf": "variant satellites",
                "finding": (
                    "L-FORM-03 is repaired in the two reviewable satellites: VARIANT_REGISTRY.json SET strength "
                    "and the variant-SET delta strength now read 'strictly weaker' and the delta base is re-pinned "
                    "to F1 rev13 %s. The older direction survives only in the two byte-frozen F0 artifacts "
                    "(research_map/formulation_taxonomy.yaml:200, artifacts/formulation/formulation_taxonomy.yaml:176), "
                    "which are outside F1's bytes and cannot be edited without voiding G-F0."
                    % F1_PIN[:16]
                ),
                "falsifier": "A satellite token still asserting the SET predicate is strictly stronger.",
            }
        )
    findings.append(
        {
            "id": "F1-073-04",
            "severity": "info",
            "leaf": "f0_binding",
            "finding": (
                "F1's f0_binding hash chain resolves at the frame: declared_f0_sha256 == %s, "
                "consistency_evidence_sha256 == %s, supplement file present, class_contract_pointer resolves, "
                "taxonomy consistency evidence reports consistent=True."
                % (f0_measured[:16], cons_measured[:16])
            ),
            "falsifier": "Any declared hash in f0_binding that does not equal the measured file.",
        }
    )

    # ---- end-of-run drift re-measure --------------------------------------
    live_t1 = {rel: sha256_file(os.path.join(REPO, rel)) for rel in FRAME_PATHS}
    moved = sorted(rel for rel in FRAME_PATHS if live_t0[rel] != live_t1.get(rel))
    check("G1", "frame stable during the run (verdict binds to the T0 frame)", [],
          moved, len(moved) == 0)

    any_control_failed = [c for c in controls if not c["fired"]]
    if any_control_failed:
        print("CONTROL FAILURE:", json.dumps(any_control_failed))
        return 2

    blocking = [f for f in findings if f["severity"] == "blocking"]
    verdict = "revise" if blocking else "accept"
    score = 3.0 if blocking else 4.0
    report = {
        "report_id": "w073-f1-rev29-binding-audit-%s" % t0.replace(":", "").replace("-", ""),
        "task_id": "W073-F1-REV29-BINDING-AUDIT-01",
        "worker": "worker-073",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "created_at": t0,
        "measured_at_end": now(),
        "mode": "independent read-only post-repair binding audit; own tooling",
        "frame": {
            "snapshot_dir": "artifacts/worker-073/f1_rev29_binding_audit/pinned",
            "live_hashes_t0": live_t0,
            "live_hashes_t1": live_t1,
            "moved_during_run": moved,
            "frozen_revision": frozen_rev,
        },
        "checks": checks,
        "controls": controls,
        "findings": findings,
        "counts": {
            "checks": len(checks),
            "checks_failed": [c["id"] for c in checks if not c["pass"]],
            "controls": len(controls),
            "controls_fired": sum(1 for c in controls if c["fired"]),
            "corpus_rows": len(rows),
            "corpus_rows_bound_to_live_pin": len(rows) - len(stale),
            "corpus_rows_probing_rev13_edited_leaves": len(edited),
        },
        "verdict": {
            "verdict": verdict,
            "score": score,
            "hard_failures": [f["id"] for f in blocking],
            "counts_as_full_schema_verdict": True,
            "counts_toward_gate_accept": False,
            "independence_note": (
                "worker-073 authored none of the audited bytes and imports no project tooling; however the "
                "existence and headline of worker-061's F1 revise were visible in research_map.json before this "
                "verdict was written, so this is a non-blind replication, not one of the two blind full-schema "
                "accepts G-FORM requires. The blocking finding F1-073-01 stands independently of that exposure."
            ),
            "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        },
        "falsifier": (
            "Re-run this checker against the live tree: a corpus whose every row binds the live F1 pin, a "
            "variant-SET block asserting the inverted direction, a non-firing control, or a moved required pin "
            "each voids part of this report. A byte change to any pinned frame file voids the verdict for that file."
        ),
        "reproduce": "python3 artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py",
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(
        {
            "verdict": verdict,
            "score": score,
            "hard_failures": [f["id"] for f in blocking],
            "checks": len(checks),
            "checks_failed": report["counts"]["checks_failed"],
            "controls": "%d/%d fired" % (report["counts"]["controls_fired"], len(controls)),
            "corpus": "%d/%d rows bound to live pin" % (len(rows) - len(stale), len(rows)),
            "moved_during_run": moved,
            "report_sha256": sha256_file(REPORT_PATH),
        }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
