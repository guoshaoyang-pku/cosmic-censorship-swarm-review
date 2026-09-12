#!/usr/bin/env python3
"""W024-SET-STRENGTH-REPAIR-01 independent verifier (read-only on canonical paths).

Falsifier (pre-registered): the repair claim is false if any of
  (1) a canonical pin moved before or during this run (exit 2, fail-closed);
  (2) the candidate differs from live anywhere outside the three declared sites;
  (3) the finite level model shows the SET variant is NOT class-level stronger than
      AF-WCC-VAC-GEN, or the live label is not the level-mixed defect;
  (4) the original checker does not return VALID on live bytes, or the note-stripped
      original does not return INVALID on live bytes;
  (5) the candidate checker does not return INVALID on live bytes and VALID on candidate;
  (6) check_variant_deltas.py or check_taxonomy_consistency.py regress on the candidate tree;
  (7) repair.patch does not apply cleanly, or patched bytes differ from the candidates;
  (8) any canonical byte changed by this run (G-F0 protection: research_map/formulation_taxonomy.yaml
      must stay at 0abb9ed8a961).

Exit 0 = every assertion held. Exit 1 = an assertion failed. Exit 2 = pin drift.
"""
import hashlib, json, shutil, subprocess, sys
from itertools import combinations
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]

REG = "artifacts/formulation/VARIANT_REGISTRY.json"
DEL = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
CHK = "artifacts/formulation/tools/check_variant_registry.py"
F0C = "research_map/formulation_taxonomy.yaml"
F0S = "artifacts/formulation/formulation_taxonomy.yaml"
FRZ = "artifacts/formulation/FROZEN.json"

EXPECTED = {
    REG: "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    DEL: "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    CHK: "c471da4b7be9a9b0ac884d3722a223c1c7a9fc7dcf5718a0f4707d65e8757f4d",
    F0C: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    F0S: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    FRZ: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

STRENGTH_LIVE_REG = (
    '"strength": "strictly weaker than AF-WCC-VAC-GEN (the parent\'s single-q tail predicate '
    "entails the union reading; the converse fails on the omega-chain witness, "
    "W076-GFORM-STRICTNESS-RECONCILE-06 T4): gamma not contained in the union J^-(I+) implies no "
    "single past J^-(q) contains a tail of gamma, but not conversely "
    "[rev13 direction corrected from 'strictly STRONGER']\","
)
STRENGTH_LIVE_DEL = (
    '"strength": "strictly weaker than AF-WCC-VAC-GEN (the parent\'s single-q tail predicate '
    "entails the union reading; the converse fails on the omega-chain witness, "
    'W076-GFORM-STRICTNESS-RECONCILE-06 T4)",'
)
CHECK_LIVE = '''setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
if "STRONGER" not in setv.get("strength", ""):
    errs.append("variant SET must be marked stronger than its parent")
'''
CHECK_FIXED = '''setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
set_strength = setv.get("strength", "")
while "[" in set_strength and "]" in set_strength:  # strip provenance notes before asserting
    set_strength = set_strength[:set_strength.index("[")] + set_strength[set_strength.index("]") + 1:]
if "STRONGER than AF-WCC-VAC-GEN" not in set_strength:
    errs.append("variant SET must be marked class-level stronger than its parent")
if "class statement" not in set_strength:
    errs.append("variant SET strength must be level-qualified as a class statement")
if "WEAKER than the parent's single-q tail predicate" not in set_strength:
    errs.append("variant SET strength must record the predicate-level weakening")
'''
CHECK_NOTESTRIP = '''setv = by_id.get(("AF-WCC-VAC-GEN", "SET"), {})
_set_s = setv.get("strength", "")
while "[" in _set_s and "]" in _set_s:
    _set_s = _set_s[:_set_s.index("[")] + _set_s[_set_s.index("]") + 1:]
if "STRONGER" not in _set_s:
    errs.append("variant SET must be marked stronger than its parent")
'''

CANDS = {
    REG: OUT / "CANDIDATE_VARIANT_REGISTRY.json",
    DEL: OUT / "CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json",
    CHK: OUT / "CANDIDATE_check_variant_registry.py",
}

results = []
def check(cid, ok, msg, detail=None):
    results.append({"id": cid, "status": "PASS" if ok else "FAIL", "msg": msg, "detail": detail})
    print(("PASS " if ok else "FAIL ") + cid + "  " + msg)
    return ok


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(argv, cwd=None):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout + p.stderr).strip()


def strip_notes(s):
    while "[" in s and "]" in s:
        s = s[:s.index("[")] + s[s.index("]") + 1:]
    return s


def sandbox(name, overrides):
    """Copy the FROZEN input tree into OUT/sandbox_<name> and apply overrides."""
    sb = OUT / f"sandbox_{name}"
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "artifacts").mkdir(parents=True)
    shutil.copytree(ROOT / "artifacts/formulation", sb / "artifacts/formulation")
    shutil.copytree(ROOT / "schemas", sb / "schemas")
    (sb / "research_map").mkdir()
    shutil.copy2(ROOT / F0C, sb / F0C)
    for rel, src in overrides.items():
        (sb / rel).write_bytes(Path(src).read_bytes())
    return sb


def main():
    # ---- 1. entry pins -------------------------------------------------------
    entry = {rel: sha(ROOT / rel) for rel in EXPECTED}
    for rel, exp in EXPECTED.items():
        if entry[rel] != exp:
            print(f"PIN DRIFT at entry: {rel}\n  expected {exp}\n  measured {entry[rel]}")
            print(json.dumps({"verdict": "PIN_DRIFT", "path": rel, "expected": exp,
                              "measured": entry[rel]}, indent=2))
            return 2
    check("P1-ENTRY-PINS", True, "6/6 canonical input pins match the pre-registered hashes")

    live_reg = (ROOT / REG).read_text()
    live_del = (ROOT / DEL).read_text()
    live_chk = (ROOT / CHK).read_text()
    cand_reg = CANDS[REG].read_text()
    cand_del = CANDS[DEL].read_text()
    cand_chk = CANDS[CHK].read_text()

    # ---- 2. candidate minimality (line-diff proof) ---------------------------
    def one_line_diff(live_text, cand_text, lineno, key):
        ll, cl = live_text.splitlines(keepends=True), cand_text.splitlines(keepends=True)
        if len(ll) != len(cl):
            return False, f"line counts differ: {len(ll)} vs {len(cl)}"
        idx = [i for i, (a, b) in enumerate(zip(ll, cl)) if a != b]
        if idx != [lineno - 1]:
            return False, f"changed line indices {[i + 1 for i in idx]} != [{lineno}]"
        if key not in ll[lineno - 1] or key not in cl[lineno - 1]:
            return False, f"changed line is not the {key} site"
        if "".join(ll[:lineno - 1] + ll[lineno:]) != "".join(cl[:lineno - 1] + cl[lineno:]):
            return False, "bytes outside the changed line differ"
        return True, f"exactly line {lineno} changed at the {key} site; all other bytes identical"
    ok, msg = one_line_diff(live_reg, cand_reg, 57, '"strength":')
    check("P2-REG-SITE", ok, "registry candidate: " + msg)
    ok, msg = one_line_diff(live_del, cand_del, 11, '"strength":')
    check("P3-DELTA-SITE", ok, "delta candidate: " + msg)
    ok = (live_chk.count(CHECK_LIVE) == 1 and cand_chk.count(CHECK_FIXED) == 1
          and cand_chk.replace(CHECK_FIXED, "") == live_chk.replace(CHECK_LIVE, "")
          and cand_chk != live_chk)
    check("P4-CHECKER-SITE", ok,
          "checker candidate differs from live only by replacing the SET clause; all other bytes identical")

    # ---- 3. finite level model (independent instrument) ----------------------
    # q1, q2; A_i = J^-(q_i) intersect M. Cells e, m1, m2.
    A1, A2 = {"e", "m1"}, {"e", "m2"}
    union = A1 | A2
    gammas = {"g1": {"e", "m1"}, "g2": {"e", "m1", "m2"}, "g3": {"x"}}
    def P(g):  # single-q TAIL predicate: some q has the geodesic tail inside J^-(q)
        tail = {c for c in gammas[g] if c != "e"}
        return any(tail and tail <= A for A in (A1, A2))
    def S(g):  # SET predicate: whole curve inside the union
        return gammas[g] <= union
    Pset = {g for g in gammas if P(g)}
    Sset = {g for g in gammas if S(g)}
    check("M1-P-IMPLIES-S", Pset <= Sset, f"predicate level: P entails S (P={sorted(Pset)}, S={sorted(Sset)})")
    check("M2-NOT-S-IMPLIES-NOT-P", (set(gammas) - Sset) <= (set(gammas) - Pset),
          "negation: not-S entails not-P")
    check("M3-STRICT-PREDICATE", "g2" in Sset and "g2" not in Pset,
          "witness g2 separates: S-visible while not P-visible (omega-chain shape), so S is strictly weaker as a predicate")
    # class statements: parent = forall gamma not P ; variant SET = forall gamma not S
    strict_ok = True
    for r in range(len(gammas) + 1):
        for Svis in combinations(gammas, r):
            Svis = set(Svis)
            for rp in range(len(Svis) + 1):
                for Pvis in combinations(Svis, rp):  # P subset of S is forced by P=>S
                    parent = not set(Pvis)
                    variant = not Svis
                    if variant and not parent:
                        strict_ok = False
    check("M4-CLASS-LEVEL-STRONGER", strict_ok,
          "class statements: (forall g not S) entails (forall g not P); SET variant is strictly stronger than AF-WCC-VAC-GEN")
    live_label = json.loads(live_reg)["variants"]
    live_set = [v for v in live_label if v.get("variant_id") == "SET"][0]["strength"]
    check("M5-LIVE-LABEL-IS-DEFECT",
          live_set.startswith("strictly weaker than AF-WCC-VAC-GEN") and "class statement" not in live_set,
          "live registry label applies the predicate-level direction to the class subject (level-mixed defect)")
    cand_set = json.loads(cand_reg)["variants"]
    cand_strength = [v for v in cand_set if v.get("variant_id") == "SET"][0]["strength"]
    cand_delta_strength = json.loads(cand_del)["strength"]
    check("M6-CANDIDATE-LEVEL-QUALIFIED",
          cand_strength == cand_delta_strength
          and "STRONGER than AF-WCC-VAC-GEN as a class statement" in cand_strength
          and "WEAKER than the parent's single-q tail predicate" in cand_strength,
          "candidate carries one byte-identical level-qualified label in both artifacts")

    # ---- 4. frozen sibling anchors (repair agrees with F0:94 and F1:235) -----
    f0_lines = (ROOT / F0C).read_text().splitlines()
    f1_lines = (ROOT / "schemas/af_wcc_vacuum.yaml").read_text().splitlines()
    a0 = any("Strictly stronger than the parent class" in l for l in f0_lines)
    a1 = any("strictly WEAKER than this class's single-q tail predicate" in l for l in f1_lines)
    check("M7-FROZEN-ANCHORS", a0 and a1,
          "repair direction agrees with F0:94 (class-level 'Strictly stronger than the parent class') and F1:235 (predicate-level 'strictly WEAKER ... single-q tail predicate')")

    # ---- 5. checker behaviour, five sequential sandboxed runs ----------------
    sb_live = sandbox("live", {})
    sb_cand = sandbox("cand", CANDS)

    def run_on(sb, checker_bytes):
        (sb / CHK).write_bytes(checker_bytes)
        return run([sys.executable, str(sb / CHK)], cwd=sb)

    rc, out = run_on(sb_live, (ROOT / CHK).read_bytes())
    check("V1-ORIG-VALID-ON-LIVE", rc == 0 and out.startswith("VALID:"),
          "original checker returns VALID/exit 0 on live bytes (the false pass)", out.splitlines()[0])
    rc, out = run_on(sb_live, live_chk.replace(CHECK_LIVE, CHECK_NOTESTRIP).encode())
    check("V2-NOTESTRIP-INVALID-ON-LIVE", rc == 1 and "must be marked stronger" in out,
          "note-stripped original returns INVALID/exit 1 on live bytes (reproduces worker-094 F0V-SETDIR-CHECKER)",
          out.splitlines()[-1])
    rc, out = run_on(sb_live, CANDS[CHK].read_bytes())
    check("V3-CAND-INVALID-ON-LIVE", rc == 1 and out.startswith("INVALID:"),
          "candidate checker fails closed on live bytes", out.splitlines()[0])
    rc, out = run_on(sb_cand, CANDS[CHK].read_bytes())
    check("V4-CAND-VALID-ON-CAND", rc == 0 and out.startswith("VALID:"),
          "candidate checker returns VALID/exit 0 on candidate bytes", out.splitlines()[0])
    rc, out = run_on(sb_cand, (ROOT / CHK).read_bytes())
    check("V5-ORIG-VALID-ON-CAND", rc == 0 and out.startswith("VALID:"),
          "original checker still returns VALID on candidate bytes (no regression)", out.splitlines()[0])

    # ---- 6. sibling owner checkers on the candidate tree ---------------------
    rc_f, out_f = run([sys.executable, str(sb_cand / "artifacts/formulation/tools/check_variant_deltas.py")], cwd=sb_cand)
    check("V6-DELTAS-ON-CAND", rc_f == 0 and out_f.startswith("VALID:"),
          "check_variant_deltas.py: VALID on the candidate tree", out_f.splitlines()[0])
    rc_g, out_g = run([sys.executable, str(sb_cand / "artifacts/formulation/tools/check_taxonomy_consistency.py")], cwd=sb_cand)
    check("V7-TAXONOMY-ON-CAND", rc_g == 0 and out_g.startswith("CONSISTENT"),
          "check_taxonomy_consistency.py: CONSISTENT on the candidate tree", out_g.splitlines()[0])

    # ---- 7. patch applies cleanly and reproduces the candidates --------------
    sb_patch = sandbox("patch", {})
    rc_p, out_p = run(["patch", "-p1", "--dry-run", "-i", str(OUT / "repair.patch")], cwd=sb_patch)
    check("P5-PATCH-DRY-RUN", rc_p == 0, "repair.patch applies cleanly with patch -p1 --dry-run", out_p.splitlines()[-1] if out_p else "")
    if rc_p == 0:
        run(["patch", "-p1", "-i", str(OUT / "repair.patch")], cwd=sb_patch)
        same = all((sb_patch / rel).read_bytes() == Path(CANDS[rel]).read_bytes() for rel in CANDS)
        check("P6-PATCH-REPRODUCES", same, "applied patch reproduces all three candidate files byte-for-byte")

    # ---- 8. no canonical write; G-F0 protection ------------------------------
    exit_pins = {rel: sha(ROOT / rel) for rel in EXPECTED}
    drift = [rel for rel in EXPECTED if exit_pins[rel] != entry[rel]]
    check("P7-NO-CANONICAL-WRITE", not drift,
          "all 6 canonical pins unchanged at exit; G-F0 taxonomy 0abb9ed8a961 untouched"
          + ("" if not drift else f" DRIFT: {drift}"))

    verdict = "ALL_PASS" if all(r["status"] == "PASS" for r in results) else "FAIL"
    (OUT / "verify_results.json").write_text(json.dumps({
        "verifier": "W024-SET-STRENGTH-REPAIR-01",
        "verdict": verdict,
        "entry_pins": entry,
        "exit_pins": exit_pins,
        "candidate_sha256": {rel: sha(CANDS[rel]) for rel in CANDS},
        "checks": results,
    }, indent=2, sort_keys=True) + "\n")
    print(f"\nVERDICT: {verdict}  ({sum(r['status']=='PASS' for r in results)}/{len(results)} checks PASS)")
    return 0 if verdict == "ALL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
