#!/usr/bin/env python3
"""W083-REV13-REPAIR-PACKET-01 — build and validate an apply-ready repair packet.

Read-only on every canonical path. All writes are confined to this artifact directory
(PKT/sandbox*). Two independently-adjudicated repairs are integrated:

  L-FORM-01  F2b (schemas/af_scc_c0_vacuum.yaml + authoring mirror): one-word inverted
             premise, "strictly larger" -> "strictly smaller" (worker-058 HF-1,
             corroborated by worker-060 CS-01 / worker-096 R09).
  L-FORM-02  consistency-evidence binding: all three schemas declare
             f0_binding.consistency_evidence_sha256 = 675a99d0..., while the canonical
             path holds the checker's summary 9e335e9b. Repair via worker-096 O3:
             patch check_taxonomy_consistency.py to write only under --write and to
             emit the two tree hashes + measured_at, then restore the existing ENRICHED
             bytes 675a99d0 at the canonical path. No class-schema hash moves for F1/F2a,
             so their rev12 verdicts survive; F2b moves (L-FORM-01) and its verdicts void.

Outputs: evidence.json, packet.json, diffs/*.diff. Exit 0 iff every control passes and
all canonical hashes are unchanged at exit.
"""
from __future__ import annotations

import datetime
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
PKT = Path(__file__).resolve().parent
SANDBOX = PKT / "sandbox"
PRISTINE = PKT / "sandbox_pristine"
DIFFS = PKT / "diffs"

HELD = {
    "FROZEN": "artifacts/formulation/FROZEN.json",
    "F0_canonical": "research_map/formulation_taxonomy.yaml",
    "F0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "F2b_mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "EVIDENCE": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "CHECKER": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "GATE": "artifacts/formulation/tools/check_class_schema.py",
    "FREEZER": "artifacts/formulation/tools/regenerate_frozen.py",
    "VERIFIER": "artifacts/formulation/tools/verify_frozen.py",
}
REV28_FROZEN_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
ENRICHED_SRC = ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
ENRICHED_SHA = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LF01_OLD = "C2 is a strictly larger extension class"
LF01_NEW = "C2 is a strictly smaller extension class"

CHECKS: list[dict] = []


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check(check_id, ok, expected, observed, falsifier, locator=""):
    CHECKS.append({
        "check_id": check_id, "ok": bool(ok), "expected": expected,
        "observed": observed, "falsifier": falsifier, "locator": locator,
    })
    return bool(ok)


def run(cmd, cwd):
    p = subprocess.run([sys.executable, *cmd] if cmd[0].endswith(".py") else cmd,
                       cwd=str(cwd), capture_output=True, text=True, timeout=600)
    return {"cmd": " ".join(str(c) for c in cmd), "exit": p.returncode,
            "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}


# --------------------------------------------------------------------------- mirror
def build_mirror(dst: Path):
    man = json.loads((ROOT / HELD["FROZEN"]).read_text())
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for rel in list(man["files"]) + [HELD["FROZEN"]]:
        src = ROOT / rel
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    return man


def copy_work(tag: str) -> Path:
    w = PKT / f"work_{tag}"
    if w.exists():
        shutil.rmtree(w)
    shutil.copytree(PRISTINE, w)
    return w


# ------------------------------------------------------------------- directional audit
def _norm(tok: str) -> str:
    return tok.strip().replace("^", "").replace("{", "").replace("}", "").replace(",", "_").replace(" ", "")


def parse_chain(text: str):
    """Parse the containment clause of the ledger into (superset, subset) pairs."""
    clause = re.split(r"[;.]", str(text))[0]
    pairs = []
    if re.search(r"\bsubset\b", clause):
        for m in re.finditer(r"E_([A-Za-z0-9^,_{}]+)\s+subset(?:\s+of)?\s+E_([A-Za-z0-9^,_{}]+)", clause):
            pairs.append((_norm(m.group(2)), _norm(m.group(1))))
    else:
        toks = re.findall(r"E_([A-Za-z0-9^,_{}]+)", clause)
        pairs = [(_norm(a), _norm(b)) for a, b in zip(toks, toks[1:])]
    return pairs


def _descends(sup: str, sub: str, pairs, seen=None) -> bool:
    if sup == sub:
        return True
    seen = seen or set()
    for a, b in pairs:
        if a == sup and b not in seen:
            seen.add(b)
            if b == sub or _descends(b, sub, pairs, seen):
                return True
    return False


def directional_findings(schema: dict) -> list[dict]:
    """Flag reason-strings whose stated direction contradicts the file's own chain."""
    led = schema.get("implication_ledger") or {}
    pairs = parse_chain(str(led.get("extension_class_containment", "")))
    own = {"AF-SCC-C0-VAC-GEN": "C0", "AF-SCC-C2-VAC-GEN": "C2"}.get(schema.get("class_id"))
    out = []
    if not own:
        return out

    def relation(x: str) -> str:
        if _descends(own, x, pairs):
            return "smaller"          # E_own contains E_x  => x is the smaller extension set
        if _descends(x, own, pairs):
            return "larger"
        return "incomparable"

    def audit(rows, field):
        for i, row in enumerate(rows or []):
            r = str(row.get("reason", ""))
            m = re.search(r"([A-Za-z0-9^,]+)\s+is\s+a\s+strictly\s+(larger|smaller)\s+extension\s+class", r)
            if m:
                x, asserted = _norm(m.group(1)), m.group(2)
                rel = relation(x)
                if rel == "incomparable":
                    out.append({"rule": "DIR-3", "field": f"{field}[{i}]", "subject": x,
                                "asserted": asserted, "chain_says": "incomparable",
                                "text": r[:160],
                                "falsifier": f"exhibit a chain clause ordering E_{own} against E_{x}, or a reading where the premise is well-posed"})
                elif rel != asserted:
                    out.append({"rule": "DIR-1", "field": f"{field}[{i}]", "subject": x,
                                "asserted": asserted, "chain_says": rel,
                                "text": r[:160],
                                "falsifier": f"exhibit an extension-set reading under which E_{x} is strictly {asserted} than E_{own}"})
            m2 = re.search(r"([A-Za-z0-9^,]+)-inextendibility is strictly (weaker|stronger)", r)
            if m2:
                x, asserted = _norm(m2.group(1)), m2.group(2)
                rel = relation(x)
                implied = {"smaller": "weaker", "larger": "stronger"}.get(rel)
                if implied and implied != asserted:
                    out.append({"rule": "DIR-2", "field": f"{field}[{i}]", "subject": x,
                                "asserted": asserted, "chain_says": implied,
                                "text": r[:160],
                                "falsifier": f"exhibit a reading where E_{x} {rel} makes {x}-inextendibility {asserted}"})
    audit(led.get("one_way_entailments"), "one_way_entailments")
    audit(led.get("forbidden_transfers"), "forbidden_transfers")
    return out


def mirror_equality(root: Path):
    a = root / "schemas/af_scc_c0_vacuum.yaml"
    b = root / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    return sha(a) == sha(b), {"canonical": sha(a), "mirror": sha(b)}


# --------------------------------------------------------------------- checker patch
def patched_checker_text(orig: str) -> str:
    head_old = ("import json, sys, yaml\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[3]\n")
    head_new = ("import argparse, datetime, hashlib, json, sys, yaml\nfrom pathlib import Path\n"
                "ROOT = Path(__file__).resolve().parents[3]\n"
                "_ap = argparse.ArgumentParser(description=\"taxonomy consistency check; writes only with --write\")\n"
                "_ap.add_argument(\"--write\", action=\"store_true\", help=\"write the evidence file (default: dry-run, no write)\")\n"
                "_args = _ap.parse_args()\n"
                "def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()\n")
    tail_old = ('       "alias_policy": AL["policy"]}\nout = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
                'out.write_text(json.dumps(rep, indent=2)+"\\n")\n')
    tail_new = ('       "alias_policy": AL["policy"],\n'
                '       "map_taxonomy_sha256": _sha(ROOT/"research_map/formulation_taxonomy.yaml"),\n'
                '       "lead_contract_sha256": _sha(ROOT/"artifacts/formulation/formulation_taxonomy.yaml"),\n'
                '       "measured_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}\n'
                'out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
                'payload = json.dumps(rep, indent=2)+"\\n"\n'
                'if _args.write:\n'
                '    out.write_text(payload)\n'
                '    print(f"WROTE {out.relative_to(ROOT)} ({len(payload)} bytes)")\n'
                'else:\n'
                '    print(f"DRY-RUN (no write); evidence={out.relative_to(ROOT)} would be {len(payload)} bytes")\n')
    assert head_old in orig and tail_old in orig, "checker patch anchors not found"
    return orig.replace(head_old, head_new).replace(tail_old, tail_new)


def unified(path_a: str, text_a: str, path_b: str, text_b: str) -> str:
    return "".join(difflib.unified_diff(
        text_a.splitlines(keepends=True), text_b.splitlines(keepends=True),
        fromfile="a/" + path_a, tofile="b/" + path_b, n=3))


# ------------------------------------------------------------------------ experiments
def gate(root: Path, rel: str):
    r = run(["python3", str(root / HELD["GATE"]), "--json", str(root / rel)], root)
    verdict = None
    try:
        verdict = json.loads(r["stdout"]).get("verdict")
    except Exception:
        pass
    return {"exit": r["exit"], "verdict": verdict, "stdout": r["stdout"][:400]}


def verdict_census(prefixes):
    hits = {}
    for p in sorted(ROOT.glob("reviews/*.json")):
        try:
            raw = p.read_text()
        except Exception:
            continue
        matched = sorted({pr for pr in prefixes if pr in raw})
        if not matched:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            d = {}
        hits[p.name] = {"verdict": d.get("verdict"), "reviewer": d.get("reviewer") or d.get("actor"),
                        "matched": matched}
    return hits


def main() -> int:
    started = datetime.datetime.now().astimezone()
    DIFFS.mkdir(parents=True, exist_ok=True)
    before = {k: sha(ROOT / v) for k, v in HELD.items()}

    man28 = json.loads((ROOT / HELD["FROZEN"]).read_text())
    frozen_files = json.loads(json.dumps(man28["files"]))   # deep copy: comparison baseline

    # P01 canonical pins
    check("P01-frozen-rev28", before["FROZEN"] == REV28_FROZEN_SHA, REV28_FROZEN_SHA,
          before["FROZEN"], "any byte change to FROZEN.json before the packet is cited")
    for name in ("F1", "F2a", "F2b", "F2b_mirror", "EVIDENCE", "CHECKER"):
        rel = HELD[name]
        check(f"P01-pin-{name}", before[name] == frozen_files[rel]["sha256"],
              frozen_files[rel]["sha256"], before[name],
              f"disk hash of {rel} differs from the FROZEN rev28 pin")

    # Pristine mirror
    build_mirror(PRISTINE)
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    shutil.copytree(PRISTINE, SANDBOX)
    n_files = sum(1 for p in SANDBOX.rglob("*") if p.is_file())
    check("B01-mirror-built", (SANDBOX / HELD["FROZEN"]).exists() and n_files >= 45,
          "44 pinned files + FROZEN.json",
          f"{n_files} files", "a pinned file missing from the mirror")

    base = copy_work("baseline")
    v = run(["python3", str(base / HELD["VERIFIER"])], base)
    check("B02-baseline-verify-frozen", v["exit"] == 0, "exit 0", f"exit {v['exit']}", "verify_frozen fails on the frozen revision")
    g = {n: gate(base, HELD[n]) for n in ("F1", "F2a", "F2b")}
    check("B03-baseline-gates", all(x["exit"] == 0 and x["verdict"] == "pass" for x in g.values()),
          "all three exit 0 pass", json.dumps({k: (x["exit"], x["verdict"]) for k, x in g.items()}),
          "canonical gate rejects a frozen schema")
    ev = base / HELD["EVIDENCE"]
    c0 = run(["python3", str(base / HELD["CHECKER"])], base)
    check("B04-checker-reproduces-summary", sha(ev) == frozen_files[HELD["EVIDENCE"]]["sha256"],
          frozen_files[HELD["EVIDENCE"]]["sha256"] + " (summary regenerated)",
          f"{sha(ev)} exit={c0['exit']}",
          "an unpatched checker run does not overwrite the canonical evidence path")

    # ---- repair work tree
    w = copy_work("repair")
    f2b = w / HELD["F2b"]
    f2b_m = w / HELD["F2b_mirror"]
    orig_txt = f2b.read_text()
    assert orig_txt == f2b_m.read_text()
    check("A00-LF01-defect-present", orig_txt.count(LF01_OLD) == 1, "1 occurrence of the inverted premise",
          f"{orig_txt.count(LF01_OLD)} occurrence(s)", "the inverted premise is absent from the frozen bytes")
    dir_before = directional_findings(__import__("yaml").safe_load(orig_txt))
    check("A01-LF01-flagged-before", len(dir_before) == 1 and dir_before[0]["rule"] == "DIR-1",
          "DIR-1 finding on forbidden_transfers[0]", json.dumps(dir_before),
          "the frozen inverted premise is not detectable by the directional grammar")

    new_txt = orig_txt.replace(LF01_OLD, LF01_NEW)
    f2b.write_text(new_txt)
    f2b_m.write_text(new_txt)
    dl = list(difflib.unified_diff(orig_txt.splitlines(), new_txt.splitlines(), lineterm=""))
    changed = sum(1 for line in dl if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    check("A02-LF01-one-line", changed == 2 and len(new_txt) == len(orig_txt) + 1,
          "exactly one changed line (2 +/- rows), byte delta +1",
          f"rows={changed} bytes {len(orig_txt)}->{len(new_txt)}",
          "the repair edits more than the single inverted word")
    dir_after = directional_findings(__import__("yaml").safe_load(new_txt))
    check("A03-LF01-clean-after", dir_after == [], "no directional findings", json.dumps(dir_after),
          "the repaired premise still contradicts the file's own chain")
    eq_ok, eq_obs = mirror_equality(w)
    check("A04-mirror-pair-equal", eq_ok, "canonical == authoring mirror", json.dumps(eq_obs),
          "only one of the two mirrored copies was edited")
    g2 = {n: gate(w, HELD[n]) for n in ("F1", "F2a", "F2b")}
    check("A05-gates-after-LF01", all(x["exit"] == 0 and x["verdict"] == "pass" for x in g2.values()),
          "all three exit 0 pass", json.dumps({k: (x["exit"], x["verdict"]) for k, x in g2.items()}),
          "the L-FORM-01 edit breaks a structural gate rule")

    # ---- L-FORM-02 (O3)
    assert sha(ENRICHED_SRC) == ENRICHED_SHA, "enriched source copy hash drift"
    ev_w = w / HELD["EVIDENCE"]
    shutil.copy2(ENRICHED_SRC, ev_w)
    check("B05-enriched-restored", sha(ev_w) == ENRICHED_SHA, ENRICHED_SHA, sha(ev_w),
          "the enriched byte copy is not the declared 675a99d0 generation")
    enriched = json.loads(ev_w.read_text())
    check("B06-enriched-fields", enriched.get("map_taxonomy_sha256") == before["F0_canonical"]
          and enriched.get("lead_contract_sha256") == before["F0_supplement"] and enriched.get("consistent") is True,
          "tree hashes present, consistent=true",
          json.dumps({k: enriched.get(k) for k in ("map_taxonomy_sha256", "lead_contract_sha256", "consistent")}),
          "the enriched evidence does not bind the frozen taxonomy trees")

    checker = w / HELD["CHECKER"]
    orig_checker = checker.read_text()
    patched = patched_checker_text(orig_checker)
    checker.write_text(patched)
    dchk = unified(HELD["CHECKER"], orig_checker, HELD["CHECKER"], patched)
    (DIFFS / "check_taxonomy_consistency--O3-guard.patch.diff").write_text(dchk)
    # verify the diff applies cleanly with GNU patch -p1 on the pristine copy
    apply_dir = copy_work("patchcheck")
    (apply_dir / "tmp.diff").write_text(dchk)
    ap = run(["patch", "-p1", "--dry-run", "-i", "tmp.diff"], apply_dir)
    check("B07-diff-applies-clean", ap["exit"] == 0, "patch --dry-run exit 0", f"exit {ap['exit']}: {ap['stderr'][:160]}",
          "the emitted unified diff does not apply to the pinned checker bytes")

    r_dry1 = run(["python3", str(checker)], w)
    h_dry1 = sha(ev_w)
    r_dry2 = run(["python3", str(checker)], w)
    h_dry2 = sha(ev_w)
    check("B08-dryrun-writes-nothing", h_dry1 == ENRICHED_SHA and h_dry2 == ENRICHED_SHA,
          "evidence unchanged across two default runs", f"{h_dry1[:12]} / {h_dry2[:12]}",
          "the patched checker writes the evidence path without --write")
    check("B09-dryrun-verdict", r_dry1["exit"] == 0 and r_dry2["exit"] == 0 and "DRY-RUN" in r_dry1["stdout"],
          "exit 0 + DRY-RUN banner", f"exit={r_dry1['exit']} stdout={r_dry1['stdout'][:80]!r}",
          "the patched checker no longer reports the consistency verdict")
    r_wr = run(["python3", str(checker), "--write"], w)
    written = json.loads(ev_w.read_text())
    check("B10-write-emits-tree-hashes", r_wr["exit"] == 0 and "map_taxonomy_sha256" in written
          and "measured_at" in written and written["map_taxonomy_sha256"] == before["F0_canonical"],
          "exit 0, enriched format on --write", f"exit={r_wr['exit']} keys={sorted(written)[:6]}",
          "--write still emits the summary format without tree hashes")
    shutil.copy2(ENRICHED_SRC, ev_w)  # restore declared bytes before re-freeze

    # ---- candidate re-freeze rev29 (regenerate recomputes every entry from the mirror)
    regen = run(["python3", str(w / HELD["FREEZER"]), "--revision", "29",
                 "--delta", "W083-REV13-REPAIR-PACKET candidate: L-FORM-01 inverted premise repaired in F2b (both copies); L-FORM-02 closed by checker --write guard + restored enriched evidence 675a99d0",
                 "--at", started.isoformat(timespec="seconds")], w)
    check("B11-refreeze-exit", regen["exit"] == 0, "regenerate_frozen exit 0",
          f"exit {regen['exit']}: {regen['stdout'][:200]}", "the pinned re-freeze tool fails in the mirror")
    man29 = json.loads((w / HELD["FROZEN"]).read_text())
    v29 = run(["python3", str(w / HELD["VERIFIER"])], w)
    check("B12-verify-rev29", v29["exit"] == 0, "verify_frozen exit 0 at rev29",
          f"exit {v29['exit']}: {v29['stdout'][:200]}", "the candidate rev29 manifest does not match the repaired tree")

    moved, unchanged = [], []
    for rel in sorted(man29["files"]):
        h28 = frozen_files.get(rel, {}).get("sha256")
        h29 = man29["files"][rel]["sha256"]
        (moved if h28 != h29 else unchanged).append(rel)
    expected_moved = sorted([HELD["F2b"], HELD["F2b_mirror"], HELD["EVIDENCE"], HELD["CHECKER"]])
    check("B13-delta-scope", sorted(moved) == expected_moved, expected_moved, sorted(moved),
          "the candidate revision moves a pinned file outside the four intended entries")
    check("B14-rev29-declared-hash", man29["files"][HELD["EVIDENCE"]]["sha256"] == ENRICHED_SHA
          and man29["revision"] == 29, f"rev29 pins evidence at {ENRICHED_SHA[:12]}",
          f"rev={man29['revision']} ev={man29['files'][HELD['EVIDENCE']]['sha256'][:12]}",
          "the re-freeze does not pin the restored enriched evidence")
    decl = {}
    for name in ("F1", "F2a", "F2b"):
        doc = __import__("yaml").safe_load((w / HELD[name]).read_text())
        decl[name] = str((doc.get("f0_binding") or {}).get("consistency_evidence_sha256", ""))
    check("B15-declarations-match", all(v == ENRICHED_SHA for v in decl.values()),
          "all three declarations == " + ENRICHED_SHA[:12], json.dumps({k: v[:12] for k, v in decl.items()}),
          "a schema declaration still points at a hash other than the re-pinned evidence")

    # ---- mutants / controls
    m1 = copy_work("m1_chain_flipped")
    t = (m1 / HELD["F2b"]).read_text()
    (m1 / HELD["F2b"]).write_text(t.replace("contains E_C2", "contains E_C0", 1))
    f1 = directional_findings(__import__("yaml").safe_load((m1 / HELD["F2b"]).read_text()))
    check("C01-mutant-chain-flip-flagged", len(f1) >= 1, ">=1 finding on a flipped chain",
          json.dumps(f1)[:200], "a flipped containment chain is not flagged")

    m1b = copy_work("m1b_strength_flipped")
    t1b = (m1b / HELD["F2b"]).read_text().replace("C2-inextendibility is strictly weaker",
                                                  "C2-inextendibility is strictly stronger")
    (m1b / HELD["F2b"]).write_text(t1b)
    f1b = directional_findings(__import__("yaml").safe_load(t1b))
    check("C01b-mutant-strength-flagged", any(x["rule"] == "DIR-2" for x in f1b),
          "DIR-2 finding on a flipped strength word", json.dumps(f1b)[:200],
          "a flipped weaker/stronger word is not flagged")

    m2 = copy_work("m2_single_copy")
    (m2 / HELD["F2b"]).write_text(new_txt)
    eq2, obs2 = mirror_equality(m2)
    check("C02-mutant-single-copy-caught", not eq2, "mirror equality False", json.dumps(obs2),
          "a half-applied repair passes the mirror-pair check")

    m3 = copy_work("m3_evidence_summary")
    decl3 = str((__import__("yaml").safe_load((m3 / HELD["F2b"]).read_text()).get("f0_binding") or {}).get("consistency_evidence_sha256"))
    check("C03-mutant-summary-evidence-caught", sha(m3 / HELD["EVIDENCE"]) != decl3,
          "declaration != measured summary hash", f"decl {decl3[:12]} vs measured {sha(m3 / HELD['EVIDENCE'])[:12]}",
          "the declaration check passes while the canonical evidence is the summary format")

    m4 = copy_work("m4_taxonomy_mutated")
    tax = m4 / "research_map/formulation_taxonomy.yaml"
    taxdoc = __import__("yaml").safe_load(tax.read_text())
    taxdoc["classes"]["AF-WCC-VAC-GEN"]["exclusions"] = []
    tax.write_text(__import__("yaml").safe_dump(taxdoc, sort_keys=False))
    ev4 = m4 / HELD["EVIDENCE"]
    h4_before = sha(ev4)
    (m4 / HELD["CHECKER"]).write_text(patched)   # exercise the repaired (dry-run) checker
    r4 = run(["python3", str(m4 / HELD["CHECKER"])], m4)
    check("C04-mutant-taxonomy-detected", r4["exit"] != 0 and sha(ev4) == h4_before,
          "checker exits non-zero and dry-run writes nothing",
          f"exit={r4['exit']} evidence {h4_before[:12]}->{sha(ev4)[:12]}",
          "a mutated taxonomy still returns consistent or the dry-run writes")

    m5 = copy_work("m5_drift_free_refreeze")
    r5 = run(["python3", str(m5 / HELD["FREEZER"]), "--revision", "29", "--delta", "drift-free control",
              "--at", started.isoformat(timespec="seconds")], m5)
    m5man = json.loads((m5 / HELD["FROZEN"]).read_text())
    keydiff = sorted(set(frozen_files) ^ set(m5man["files"]))
    drift = [r for r in sorted(set(frozen_files) & set(m5man["files"]))
             if frozen_files[r]["sha256"] != m5man["files"][r]["sha256"]]
    check("C05-refreeze-no-masking", r5["exit"] == 0 and drift == [] and keydiff == [],
          "0 file entries drift; pin key set unchanged",
          f"exit={r5['exit']} drifted={drift[:4]} keydiff={keydiff[:4]}",
          "the re-freeze tool rewrites or masks a drifted pin")

    # ---- verdict census
    census = verdict_census(["55d0a1ea", "cce9c601", "5476a3f2", "675a99d0", "9e335e9b"])
    f2b_void = sorted(k for k, val in census.items() if "55d0a1ea" in val["matched"])
    f1_keep = sorted(k for k, val in census.items() if "cce9c601" in val["matched"])
    f2a_keep = sorted(k for k, val in census.items() if "5476a3f2" in val["matched"])
    check("V01-census-nonempty", len(f2b_void) > 0 and (len(f1_keep) > 0 or len(f2a_keep) > 0),
          "F2b verdicts voided, F1/F2a verdicts retain their hashes",
          f"F2b={len(f2b_void)} F1={len(f1_keep)} F2a={len(f2a_keep)}",
          "no review file cites the affected hashes (census is vacuous)")

    # ---- confinement
    after = {k: sha(ROOT / v) for k, v in HELD.items()}
    check("X01-canonical-untouched", before == after, "all canonical hashes unchanged",
          json.dumps({k: (before[k] == after[k]) for k in before}),
          "the packet wrote to a canonical path")

    # ---- artifacts
    lf01_c = unified(HELD["F2b"], orig_txt, HELD["F2b"], new_txt)
    (DIFFS / "af_scc_c0_vacuum--LFORM01.patch.diff").write_text(lf01_c)
    lf01_m = unified(HELD["F2b_mirror"], orig_txt, HELD["F2b_mirror"], new_txt)
    (DIFFS / "af_scc_c0_vacuum.mirror--LFORM01.patch.diff").write_text(lf01_m)

    steps = [
        {"step": 1, "cmd": "python3 artifacts/formulation/tools/verify_frozen.py", "cwd": "repo root",
         "expect": "exit 0 (rev28 intact), 44/44", "note": "freeze check before touching anything"},
        {"step": 2, "cmd": "patch -p1 -i artifacts/worker-083/rev13_repair_packet/diffs/af_scc_c0_vacuum--LFORM01.patch.diff && patch -p1 -i artifacts/worker-083/rev13_repair_packet/diffs/af_scc_c0_vacuum.mirror--LFORM01.patch.diff",
         "cwd": "repo root", "expect": "both copies now measure the same new hash",
         "note": "L-FORM-01; moves F2b hash -> F2b verdicts at 55d0a1ea are void"},
        {"step": 3, "cmd": "cp artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json artifacts/formulation/evidence/taxonomy_consistency.json",
         "cwd": "repo root", "expect": "sha256 675a99d0d25b...", "note": "L-FORM-02 restore existing enriched bytes"},
        {"step": 4, "cmd": "patch -p1 -i artifacts/worker-083/rev13_repair_packet/diffs/check_taxonomy_consistency--O3-guard.patch.diff",
         "cwd": "repo root", "expect": "sha256 changes; default run is dry-run",
         "note": "L-FORM-02 guard; prevents the next checker run from destroying the enriched evidence"},
        {"step": 5, "cmd": "python3 artifacts/formulation/tools/regenerate_frozen.py --revision 29 --delta \"L-FORM-01 wording repair (F2b) + L-FORM-02 O3 evidence restore/guard\" --at <ISO8601>",
         "cwd": "repo root", "expect": "44 files pinned; 4 entries moved",
         "note": "one manifest revision; F1/F2a/F0 hashes unchanged"},
        {"step": 6, "cmd": "python3 artifacts/formulation/tools/verify_frozen.py && python3 artifacts/formulation/tools/check_class_schema.py --json schemas/af_scc_c0_vacuum.yaml",
         "cwd": "repo root", "expect": "exit 0 / pass", "note": "post-repair freeze + gate"},
        {"step": 7, "cmd": "python3 artifacts/formulation/tools/check_taxonomy_consistency.py",
         "cwd": "repo root", "expect": "DRY-RUN + CONSISTENT; evidence unchanged",
         "note": "no write without --write"},
    ]
    packet = {
        "packet_id": "W083-REV13-REPAIR-PACKET-01",
        "created_at": started.isoformat(timespec="seconds"),
        "actor": "worker-083",
        "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "nodes": ["F1", "F2a", "F2b"],
        "authority": "worker evidence only; no canonical path written; no gate verdict or node transition claimed",
        "base_frozen": {"path": HELD["FROZEN"], "revision": 28, "sha256": before["FROZEN"]},
        "repairs": [
            {"id": "L-FORM-01", "source": "worker-058 HF-1; worker-060 CS-01; astra-lead-formulation lead-form-20260912T004452-02",
             "edit": f"{LF01_OLD!r} -> {LF01_NEW!r}",
             "files": [HELD["F2b"], HELD["F2b_mirror"]],
             "hash_move_expected": True, "verdicts_void": "F2b verdicts bound to 55d0a1ea"},
            {"id": "L-FORM-02", "source": "worker-096 O3 recommendation; worker-086 root cause",
             "edit": "checker --write guard + tree hashes + measured_at; restore enriched 675a99d0 at the canonical evidence path",
             "files": [HELD["CHECKER"], HELD["EVIDENCE"]],
             "hash_move_expected": True, "verdicts_void": "none (F1/F2a schema bytes unchanged)"},
        ],
        "steps": steps,
        "diffs": {
            "lform01_canonical": "diffs/af_scc_c0_vacuum--LFORM01.patch.diff",
            "lform01_mirror": "diffs/af_scc_c0_vacuum.mirror--LFORM01.patch.diff",
            "lform02_checker": "diffs/check_taxonomy_consistency--O3-guard.patch.diff",
        },
        "measured": {
            "f2b_old_sha256": before["F2b"], "f2b_new_sha256": sha(w / HELD["F2b"]),
            "evidence_restored_sha256": ENRICHED_SHA,
            "checker_old_sha256": before["CHECKER"], "checker_new_sha256": sha(checker),
            "candidate_rev29_moved_entries": sorted(moved),
            "verdict_census": {"f2b_void": f2b_void, "f1_retained": f1_keep, "f2a_retained": f2a_keep},
        },
        "falsifiers": [
            "the F2b file at the candidate new hash still contains 'strictly larger' or the directional check flags it",
            "a patched-checker default run changes the evidence bytes",
            "candidate rev29 verify_frozen exits non-zero",
            "more or fewer than the four intended pinned entries move",
            "any F1/F2a/F0 schema byte changes (would void verdicts the packet claims to preserve)",
            "an extension-set reading under which E_C2 strictly contains E_C0",
        ],
    }
    (PKT / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
    fails = [c for c in CHECKS if not c["ok"]]
    evidence = {
        "run_id": "W083-REV13-REPAIR-PACKET-01",
        "actor": "worker-083",
        "created_at": started.isoformat(timespec="seconds"),
        "canonical_writes": False,
        "checks_total": len(CHECKS),
        "checks_failed": [c["check_id"] for c in fails],
        "checks": CHECKS,
        "verdict": "PACKET_VALIDATED" if not fails else "PACKET_INVALID",
        "notes": [
            "directional grammar is a packet-internal DIR-1/DIR-2 check over reason strings; it is not a "
            "re-derivation of the worker-058/worker-060 containment checkers",
            "candidate rev29 is built only inside this artifact's mirror; applying the packet to canonical "
            "bytes requires controller authorization (freeze-hold)",
            "L-FORM-02 uses worker-096 O3, which preserves the F1/F2a schema hashes; the lead's "
            "L-FORM-02 note proposed refreshing the three declarations (O2), which would void all three",
        ],
    }
    (PKT / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"verdict": evidence["verdict"], "checks": len(CHECKS),
                      "failed": [c["check_id"] for c in fails],
                      "f2b_new": sha(w / HELD["F2b"])[:12],
                      "moved": sorted(moved)}, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
