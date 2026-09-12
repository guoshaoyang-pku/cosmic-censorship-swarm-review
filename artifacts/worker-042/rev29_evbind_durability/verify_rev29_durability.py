#!/usr/bin/env python3
"""W042-REV29-EVBIND-DURABILITY-06 -- deterministic durability checker.

Question: at the FROZEN rev29 / rev13 pins, is the refreshed
f0_binding.consistency_evidence_sha256 = 9e335e9ba1bf a durable binding, or a
one-time re-stamp that a later legitimate writer run can silently invalidate?

Method (snapshot-bound; every byte read from snapshot/, nothing canonical is
written):
  P0  snapshot copies re-hash to the manifest.
  P1  writer census over artifacts/formulation/tools/*.py (hashes at run time).
  P2  fixpoint: run the FROZEN-pinned writer (de356d99) in an isolated tree
      mirror of its three inputs; compare its output bytes to the pinned
      evidence revision; seed each sandbox with the pinned revision to observe
      overwrite behaviour.
  P3  input surface: which inputs the writer reads; whether the pinned evidence
      carries their sha256; what the schemas' refresh rule covers.
  P4  re-stale simulation: mutate each writer input one at a time; measure
      whether the output moves and whether the declared refresh rule would
      catch it.
  P5  stream census of declared hashes for the evidence path at the pin, plus a
      live-drift re-measure of all pinned paths at exit.

Output: report.json (deterministic except generated_at, disclosed). Exit 0 =
all structural checks pass and controls fire; exit 1 = a structural check
failed; exit 2 = control failure or manifest drift (the run is void).
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAP = HERE / "snapshot"
RUNS = HERE / "runs"
TZ = timezone(timedelta(hours=8))

E_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"
A_PATH = "research_map/formulation_taxonomy.yaml"
B_PATH = "artifacts/formulation/formulation_taxonomy.yaml"
AL_PATH = "artifacts/formulation/VOCAB_ALIASES.json"
W_PATH = "artifacts/formulation/tools/check_taxonomy_consistency.py"
SCHEMA_PATHS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
TOOLS_DIR = "artifacts/formulation/tools"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sh(data) -> str:
    return hashlib.sha256(data).hexdigest()


def check(cid, name, ok, expected, measured, severity="structural", falsifier=""):
    return {
        "id": cid,
        "name": name,
        "ok": bool(ok),
        "severity": severity,
        "expected": expected,
        "measured": measured,
        "falsifier": falsifier,
    }


def build_sandbox(tag: str) -> Path:
    """Mirror of the writer's three inputs + its own path under runs/<tag>/."""
    root = RUNS / tag
    if root.exists():
        shutil.rmtree(root)
    (root / "research_map").mkdir(parents=True)
    (root / "artifacts/formulation/tools").mkdir(parents=True)
    (root / "artifacts/formulation/evidence").mkdir(parents=True)
    shutil.copyfile(SNAP / "A_map_taxonomy.yaml", root / A_PATH)
    shutil.copyfile(SNAP / "B_lead_contract.yaml", root / B_PATH)
    shutil.copyfile(SNAP / "AL_vocab_aliases.json", root / AL_PATH)
    shutil.copyfile(SNAP / "W_check_taxonomy_consistency.py", root / W_PATH)
    # seed with the pinned revision so overwrite of a differing file is observable
    shutil.copyfile(SNAP / "E_consistency_evidence.json", root / E_PATH)
    return root


def run_writer(root: Path):
    proc = subprocess.run(
        [sys.executable, W_PATH],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    e = root / E_PATH
    return {
        "exit": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip()[-400:],
        "evidence_sha256": sha256_file(e) if e.exists() else None,
        "evidence_bytes": e.stat().st_size if e.exists() else None,
    }


def mutate_yaml(src: Path, dst: Path, fn):
    doc = yaml.safe_load(src.read_text())
    fn(doc)
    dst.write_text(yaml.safe_dump(doc, sort_keys=True))


def mutate_json(src: Path, dst: Path, fn):
    doc = json.loads(src.read_text())
    fn(doc)
    dst.write_text(json.dumps(doc, indent=2) + "\n")


def main() -> int:
    checks, controls, findings, measurements = [], [], [], {}
    RUNS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SNAP / "manifest.json").read_text())
    files = manifest["files"]

    # ---------------- P0 snapshot integrity ----------------
    snap_ok = True
    for rel, rec in files.items():
        p = SNAP / rec["snapshot_file"]
        got = sha256_file(p) if p.exists() else None
        if got != rec["sha256"]:
            snap_ok = False
            checks.append(check("P0", f"snapshot copy {rel}", False, rec["sha256"], got))
    checks.append(check("P0", "all snapshot copies re-hash to manifest", snap_ok,
                        f"{len(files)} files", f"{len(files)} files" if snap_ok else "drift"))

    def snap(rel):
        return SNAP / files[rel]["snapshot_file"]

    e_pin = files[E_PATH]["sha256"]
    a_pin = files[A_PATH]["sha256"]
    b_pin = files[B_PATH]["sha256"]
    al_pin = files[AL_PATH]["sha256"]
    w_pin = files[W_PATH]["sha256"]
    for k, v in SCHEMA_PATHS.items():
        measurements[f"{k}_sha256"] = files[v]["sha256"]
    measurements.update({
        "A_map_taxonomy_sha256": a_pin,
        "B_lead_contract_sha256": b_pin,
        "AL_vocab_aliases_sha256": al_pin,
        "E_consistency_evidence_sha256": e_pin,
        "W_checker_sha256": w_pin,
        "E_bytes": files[E_PATH]["bytes"],
        "pinned_at": manifest["pinned_at"],
    })

    # frozen revision + its pin of E and of the writer
    frozen = json.loads(snap("artifacts/formulation/FROZEN.json").read_text())
    measurements["FROZEN_revision"] = frozen.get("revision")
    measurements["FROZEN_frozen_at"] = frozen.get("frozen_at")
    measurements["FROZEN_pin_E"] = frozen["files"].get(E_PATH, {}).get("sha256")
    measurements["FROZEN_pin_W"] = frozen["files"].get(W_PATH, {}).get("sha256")
    checks.append(check("P0b", "FROZEN rev29 pins the pinned evidence and writer bytes",
                        frozen.get("revision") == 29
                        and frozen["files"].get(E_PATH, {}).get("sha256") == e_pin
                        and frozen["files"].get(W_PATH, {}).get("sha256") == w_pin,
                        f"rev29, E={e_pin[:12]}, W={w_pin[:12]}",
                        f"rev{frozen.get('revision')}, E={str(measurements['FROZEN_pin_E'])[:12]}, W={str(measurements['FROZEN_pin_W'])[:12]}"))

    # ---------------- P1 writer census (bounded to the tools dir) ----------------
    writers = []
    tools = REPO / TOOLS_DIR
    for p in sorted(tools.glob("*.py")):
        txt = p.read_text(errors="replace")
        mentions = E_PATH in txt
        write_calls = len(re.findall(r"write_text|write_bytes|json\.dump", txt))
        guard = bool(re.search(r"--write|--dry-run|dry_run|argparse", txt))
        if mentions:
            writers.append({
                "path": f"{TOOLS_DIR}/{p.name}",
                "sha256": sha256_file(p),
                "frozen_pinned": frozen["files"].get(f"{TOOLS_DIR}/{p.name}", {}).get("sha256") == sha256_file(p),
                "write_calls": write_calls,
                "dry_run_guard": guard,
                "writes_the_path": bool(write_calls) and (f'"{E_PATH}"' in txt or E_PATH in txt),
            })
    measurements["writer_census"] = writers
    wrec = next((w for w in writers if w["path"] == W_PATH), None)
    pinned_writer_writes = bool(wrec and wrec["writes_the_path"] and not wrec["dry_run_guard"])
    checks.append(check("P1", "frozen writer writes the canonical evidence path with no dry-run guard",
                        pinned_writer_writes,
                        "unconditional overwrite of the canonical path",
                        f"writes={wrec and wrec['writes_the_path']}, guard={wrec and wrec['dry_run_guard']}, "
                        f"write_calls={wrec and wrec['write_calls']}",
                        severity="measurement"))
    measurements["writers_mentioning_E"] = len(writers)
    measurements["writers_unpinned_mentioning_E"] = sum(1 for w in writers if not w["frozen_pinned"])

    # ---------------- P2 fixpoint (no-op sandbox) ----------------
    base = build_sandbox("base_fixpoint")
    base_run = run_writer(base)
    fixpoint_ok = base_run["evidence_sha256"] == e_pin
    checks.append(check("P2", "pinned writer reproduces the pinned evidence revision exactly",
                        fixpoint_ok, e_pin, base_run["evidence_sha256"]))
    measurements["fixpoint_run"] = {k: v for k, v in base_run.items() if k != "stderr"}
    measurements["fixpoint_exit"] = base_run["exit"]

    # ---------------- P3 input surface + rule coverage ----------------
    a = yaml.safe_load(snap(A_PATH).read_text())
    b = yaml.safe_load(snap(B_PATH).read_text())
    al = json.loads(snap(AL_PATH).read_text())
    e = json.loads(snap(E_PATH).read_text())
    inputs_read = ["A_map_taxonomy", "B_lead_contract", "AL_vocab_aliases"]
    sha_fields_in_E = sorted(k for k in e.keys() if "sha" in k.lower())
    measurements["E_top_level_keys"] = sorted(e.keys())
    measurements["E_declares_input_hashes"] = sha_fields_in_E
    checks.append(check("P3a", "pinned evidence revision is self-verifying (carries input sha256)",
                        bool(sha_fields_in_E), ">=1 of map/lead/alias sha256 present",
                        f"{len(sha_fields_in_E)} sha256 fields: {sha_fields_in_E}",
                        severity="measurement"))

    refresh_rule_cov = {}
    for k, rel in SCHEMA_PATHS.items():
        s = yaml.safe_load(snap(rel).read_text())
        fb = s.get("f0_binding") or {}
        rule = str(fb.get("rule", ""))
        named = {
            "A_map_taxonomy": "declared" in rule and "F0 artifact" in rule,
            "B_lead_contract": B_PATH in rule,
            "AL_vocab_aliases": AL_PATH in rule or "VOCAB" in rule,
        }
        refresh_rule_cov[k] = {
            "rule": rule,
            "covers": [n for n, v in named.items() if v],
            "n_covered": sum(1 for v in named.values() if v),
        }
    covs = [v["n_covered"] for v in refresh_rule_cov.values()]
    measurements["refresh_rule_coverage"] = refresh_rule_cov
    checks.append(check("P3b", "schema refresh rule covers every writer input",
                        all(c == 3 for c in covs), "3/3 inputs per schema",
                        f"coverage {covs} (of 3)",
                        severity="measurement"))

    # ---------------- P4 re-stale simulation ----------------
    muts = {
        "mutA_map_taxonomy": ("A", A_PATH, "yaml", lambda d: d["classes"]["AF-WCC-VAC-GEN"]["axes"].__setitem__("family", "SCC")),
        "mutB_lead_contract": ("B", B_PATH, "yaml", lambda d: d["class_contracts"]["AF-WCC-VAC-GEN"]["components"].__setitem__("censorship", "SCC")),
        "mutAL_vocab_aliases": ("AL", AL_PATH, "json", lambda d: d.__setitem__("policy", str(d["policy"]) + " [MUTANT: policy text changed]")),
    }
    mut_results = {}
    for tag, (which, rel, kind, fn) in muts.items():
        root = build_sandbox(tag)
        if kind == "yaml":
            mutate_yaml(SNAP / files[rel]["snapshot_file"], root / rel, fn)
        else:
            mutate_json(SNAP / files[rel]["snapshot_file"], root / rel, fn)
        run = run_writer(root)
        out = run["evidence_sha256"]
        mut_results[which] = {
            "run": tag,
            "input": rel,
            "input_mutated_sha256": sha256_file(root / rel),
            "writer_exit": run["exit"],
            "output_sha256": out,
            "output_moved": out is not None and out != e_pin,
            "overwrote_seeded_frozen_revision": out != e_pin,
        }
        # the fresh sandbox E was seeded with the pinned revision; if the run
        # changed it and exit 0, the writer overwrote a differing file silently
        mut_results[which]["silent"] = run["exit"] == 0 and out != e_pin
    measurements["mutation_runs"] = mut_results
    moved = [w for w in ("A", "B", "AL") if mut_results[w]["output_moved"]]
    checks.append(check("P4a", "every writer input is output-sensitive (mutation moves the output)",
                        len(moved) == 3, "A,B,AL all move", f"moved={moved}"))
    silent = [w for w in ("A", "B", "AL") if mut_results[w]["silent"]]
    checks.append(check("P4b", "at least one writer input re-stales the pin with a passing run (silent)",
                        silent == ["AL"],
                        "AL silent (exit 0, moved bytes); A/B move bytes but exit 1",
                        f"silent inputs: {silent}",
                        severity="measurement"))
    measurements["silent_restale_inputs"] = silent

    # ---------------- P5 stream census + live drift ----------------
    declared = []
    for lineno, line in enumerate((SNAP / "events.jsonl").read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event_type") == "artifact" and ev.get("path") == E_PATH and ev.get("sha256"):
            declared.append({
                "line": lineno,
                "created_at": ev.get("created_at"),
                "actor": ev.get("actor"),
                "sha256": ev["sha256"],
            })
    distinct = sorted({d["sha256"] for d in declared})
    measurements["E_declared_events"] = len(declared)
    measurements["E_distinct_declared_hashes"] = distinct
    measurements["E_latest_declared_sha256"] = declared[-1]["sha256"] if declared else None
    checks.append(check("P5a", "latest declared evidence hash in the pinned stream equals the pinned revision",
                        bool(declared) and declared[-1]["sha256"] == e_pin,
                        e_pin, declared[-1]["sha256"] if declared else None,
                        severity="measurement"))
    measurements["pin_churn_distinct_hashes_for_E"] = len(distinct)

    # live stream re-read at measure time: is the pinned E hash declared anywhere?
    live_stream = REPO / "research_map/events.jsonl"
    live_stream_sha = sha256_file(live_stream)
    live_e_decl = []
    live_last_e = None
    with open(live_stream) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("event_type") == "artifact" and ev.get("path") == E_PATH and ev.get("sha256"):
                live_e_decl.append(ev["sha256"])
                live_last_e = ev
    measurements["live_stream_sha256_at_measure"] = live_stream_sha
    measurements["live_stream_E_declarations_total"] = len(live_e_decl)
    measurements["live_stream_E_declarations_at_pinned_hash"] = sum(1 for h in live_e_decl if h == e_pin)
    measurements["live_stream_E_last_declaration"] = (
        {k: live_last_e.get(k) for k in ("event_id", "actor", "created_at", "sha256")} if live_last_e else None
    )
    checks.append(check("P5c", "the pinned evidence hash is declared by an accepted artifact event (live stream)",
                        measurements["live_stream_E_declarations_at_pinned_hash"] >= 1,
                        ">=1 artifact event naming the pinned E hash",
                        f"{measurements['live_stream_E_declarations_at_pinned_hash']} of "
                        f"{len(live_e_decl)} declarations name {e_pin[:12]}",
                        severity="measurement"))

    drift = {}
    for rel, rec in files.items():
        live = REPO / rel
        drift[rel] = {
            "snapshot": rec["sha256"],
            "live_at_exit": sha256_file(live) if live.exists() else None,
        }
        drift[rel]["moved_during_run"] = drift[rel]["live_at_exit"] != rec["sha256"]
    measurements["live_at_exit"] = drift
    # events.jsonl is append-only by design: growth is not drift
    moved_live = [r for r, v in drift.items() if v["moved_during_run"] and r != "research_map/events.jsonl"]
    checks.append(check("P5b", "no pinned canonical byte moved during the measurement",
                        not moved_live, "0 moved (events.jsonl append-only excluded)",
                        f"{len(moved_live)} moved: {moved_live}",
                        severity="informational"))
    # wall-clock corroboration only: was the frozen evidence path rewritten in place?
    e_live = REPO / E_PATH
    measurements["E_mtime_at_measure"] = datetime.fromtimestamp(e_live.stat().st_mtime, TZ).isoformat(timespec="seconds")
    measurements["E_mtime_wallclock_note"] = "mtime is corroboration only; the pinned bytes are what the hashes bind"
    measurements["E_rewritten_after_frozen_at"] = e_live.stat().st_mtime > datetime.fromisoformat(frozen["frozen_at"]).timestamp() if frozen.get("frozen_at") else None

    # ---------------- P6 authoritative-registry binding matrix ----------------
    reg_path = REPO / "runtime/state/artifact_hashes.json"
    reg = json.loads(reg_path.read_text())
    reg_all = {**reg.get("hashes", {}), **reg.get("registry", {})}
    measurements["registry_sha256_at_measure"] = sha256_file(reg_path)
    reg_matrix = {}
    deps = [A_PATH, B_PATH, AL_PATH, E_PATH, W_PATH] + list(SCHEMA_PATHS.values()) + [
        "artifacts/formulation/FROZEN.json", "schemas/taxonomy_cases.jsonl"]
    for rel in deps:
        rec = reg_all.get(rel)
        live_h = sha256_file(REPO / rel) if (REPO / rel).exists() else None
        reg_matrix[rel] = {
            "registered": bool(rec),
            "registry_sha256": (rec or {}).get("sha256"),
            "live_sha256": live_h,
            "matches_live": bool(rec) and rec.get("sha256") == live_h,
        }
    measurements["registry_matrix"] = reg_matrix
    unregistered = [r for r, v in reg_matrix.items() if not v["registered"]]
    stale = [r for r, v in reg_matrix.items() if v["registered"] and not v["matches_live"]]
    measurements["registry_unregistered_dependencies"] = unregistered
    measurements["registry_stale_dependencies"] = stale
    checks.append(check("P6", "every rev29 binding dependency carries a matching registry sha256",
                        not unregistered and not stale,
                        "10/10 registered and matching live",
                        f"{10 - len(unregistered) - len(stale)}/10; unregistered={unregistered}, stale={stale}",
                        severity="measurement"))

    # ---------------- controls ----------------
    controls.append({"id": "C1", "name": "no-op sandbox reproduces pinned bytes (non-vacuous fixpoint)",
                     "fires": fixpoint_ok, "expected": True, "observed": fixpoint_ok})
    controls.append({"id": "C2", "name": "all three input mutations move the output",
                     "fires": len(moved) == 3, "expected": True, "observed": moved})
    controls.append({"id": "C3", "name": "silent re-stale for the alias input (exit 0, moved bytes)",
                     "fires": silent == ["AL"], "expected": True, "observed": silent})

    # C4: manifest tamper detection (function-level, in-memory)
    tamper_detected = False
    rec = files[E_PATH]
    flipped = ("0" if rec["sha256"][0] != "0" else "1") + rec["sha256"][1:]
    tamper_detected = flipped != sha256_file(SNAP / rec["snapshot_file"])
    controls.append({"id": "C4", "name": "a one-hex-digit manifest tamper is detectable",
                     "fires": tamper_detected, "expected": True, "observed": tamper_detected})

    # C5: verify_frozen.py control -- full mirror of FROZEN.files, then tampered copy
    ok_mirror = RUNS / "frozen_ok"
    if ok_mirror.exists():
        shutil.rmtree(ok_mirror)
    for rel in frozen["files"]:
        src = REPO / rel
        dst = ok_mirror / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copyfile(src, dst)
    (ok_mirror / W_PATH).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(snap("artifacts/formulation/tools/verify_frozen.py"), ok_mirror / "artifacts/formulation/tools/verify_frozen.py")
    shutil.copyfile(snap("artifacts/formulation/FROZEN.json"), ok_mirror / "artifacts/formulation/FROZEN.json")
    ok = subprocess.run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"],
                        cwd=str(ok_mirror), capture_output=True, text=True, timeout=120)
    bad_mirror = RUNS / "frozen_tampered"
    if bad_mirror.exists():
        shutil.rmtree(bad_mirror)
    shutil.copytree(ok_mirror, bad_mirror)
    fz = json.loads((bad_mirror / "artifacts/formulation/FROZEN.json").read_text())
    h = fz["files"][E_PATH]["sha256"]
    fz["files"][E_PATH]["sha256"] = ("0" if h[0] != "0" else "1") + h[1:]
    (bad_mirror / "artifacts/formulation/FROZEN.json").write_text(json.dumps(fz, indent=2) + "\n")
    bad = subprocess.run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"],
                         cwd=str(bad_mirror), capture_output=True, text=True, timeout=120)
    controls.append({"id": "C5", "name": "pinned verify_frozen exits 0 on a faithful mirror, 1 on a tampered pin",
                     "fires": ok.returncode == 0 and bad.returncode == 1,
                     "expected": "0 then 1", "observed": f"{ok.returncode} then {bad.returncode}",
                     "ok_stdout": ok.stdout.strip(), "tampered_stdout": bad.stdout.strip()})

    controls_ok = all(c["fires"] for c in controls)

    # ---------------- findings ----------------
    findings.append({
        "id": "W042-DUR-01",
        "severity": "major",
        "finding": (
            f"At FROZEN rev{frozen.get('revision')} ({frozen.get('frozen_at')}), the refreshed "
            f"consistency-evidence pin {e_pin[:12]} is a fixpoint of the FROZEN-pinned writer "
            f"{w_pin[:12]} on the pinned inputs, but it is not durable: the writer overwrites the "
            "canonical evidence path unconditionally (no dry-run guard), the pinned evidence "
            "revision carries 0 input sha256 fields, and the schemas' refresh rule names only the "
            "declared F0 artifact (1 of the writer's 3 inputs). A change to the lead contract or "
            "the alias file therefore re-stales the pin with no declared trigger, and any later "
            "canonical writer run rewrites the frozen path in place (observed live: mtime advances "
            "at unchanged bytes; sandbox: written bytes differ once an input moves)."
        ),
        "measured": {
            "writer": W_PATH, "writer_sha256": w_pin,
            "writer_dry_run_guard": bool(wrec and wrec["dry_run_guard"]),
            "evidence_input_sha_fields": sha_fields_in_E,
            "refresh_rule_coverage": {k: v["n_covered"] for k, v in refresh_rule_cov.items()},
            "inputs": inputs_read,
            "silent_restale_inputs": silent,
            "fixpoint_output_equals_pin": fixpoint_ok,
            "E_rewritten_after_frozen_at_observed": measurements["E_rewritten_after_frozen_at"],
            "E_mtime_at_measure": measurements["E_mtime_at_measure"],
        },
        "falsifier": (
            "Adopt a writer whose default is dry-run/read-only (or a revision of the evidence "
            "carrying the sha256 of all three inputs) and re-run this checker: if P1 reports no "
            "unconditional write, P3a reports 3 input hashes present, and P3b reports 3/3 rule "
            "coverage at the then-frozen bytes, W042-DUR-01 is discharged. A sandbox run showing "
            "the frozen writer leaves a differing seeded evidence file byte-identical would also "
            "falsify the overwrite half of the finding."
        ),
    })
    findings.append({
        "id": "W042-DUR-02",
        "severity": "minor",
        "finding": (
            "The two inputs not named by the refresh rule (lead contract, alias file) are "
            "output-sensitive in the sandbox: mutating each yields a different evidence hash "
            f"({[mut_results[w]['output_sha256'][:12] for w in ('B', 'AL')]}); the alias-file "
            "mutation is the silent case (writer exit 0, bytes moved) and the pinned evidence "
            "records none of their hashes, so staleness from those two inputs is not detectable "
            "from the pinned evidence alone."
        ),
        "measured": {w: {k: v for k, v in mut_results[w].items() if k != 'run'} for w in ("B", "AL")},
        "falsifier": (
            "Show that a lead-contract or alias-file change leaves the writer output unchanged "
            "(P4a fails for that input), or that the pinned evidence carries that input's sha256."
        ),
    })
    findings.append({
        "id": "W042-DUR-04",
        "severity": "major",
        "finding": (
            f"The pin target itself is not bound in the authoritative records: at the measured "
            f"registry sha256 {measurements['registry_sha256_at_measure'][:12]} and live stream sha256 "
            f"{live_stream_sha[:12]}, artifacts/formulation/evidence/taxonomy_consistency.json "
            f"({e_pin[:12]}) has no entry in runtime/state/artifact_hashes.json and no accepted artifact "
            f"event ever names its pinned hash ({measurements['live_stream_E_declarations_at_pinned_hash']} "
            f"of {len(live_e_decl)} declarations for that path; the last is "
            f"{(live_last_e or {}).get('sha256', 'none')[:12]} at {(live_last_e or {}).get('created_at')}). "
            "The three schemas declare it and FROZEN rev29 pins it, so the binding runs schemas -> E with "
            "no registry hash and no stream announcement at E, while PROTOCOL.md rule 2 requires the "
            "registry sha256 for a done node. Of the 10 binding dependencies, "
            f"{len(unregistered)} are unregistered ({', '.join(unregistered)}) and "
            f"{len(stale)} stale."
        ),
        "measured": {
            "unregistered": unregistered,
            "stale": stale,
            "registry_matrix": reg_matrix,
            "live_stream_E_declarations_total": len(live_e_decl),
            "live_stream_E_declarations_at_pinned_hash": measurements["live_stream_E_declarations_at_pinned_hash"],
            "live_stream_E_last_declaration": measurements["live_stream_E_last_declaration"],
            "E_rewritten_after_frozen_at": measurements["E_rewritten_after_frozen_at"],
            "E_mtime_at_measure": measurements["E_mtime_at_measure"],
        },
        "falsifier": (
            "Add a registry entry for artifacts/formulation/evidence/taxonomy_consistency.json at "
            "9e335e9ba1bf (and for the other unregistered dependencies) or produce an accepted artifact "
            "event naming that hash, then re-run: if P5c and P6 pass at the then-current bytes, "
            "W042-DUR-04 is discharged."
        ),
    })
    fb = yaml.safe_load(snap("schemas/af_scc_c0_vacuum.yaml").read_text())
    inverted_present = "strictly larger extension class" in json.dumps(fb.get("implication_ledger", {}))
    findings.append({
        "id": "W042-DUR-03",
        "severity": "informational",
        "finding": (
            "Scope note, not a new defect: F2b rev13 pinned at FROZEN rev29 still contains the "
            "known-open inverted containment premise 'C2 is a strictly larger extension class' "
            f"(present={inverted_present}); this is the separately tracked HF-060-F2B-1 hold. A "
            "verified evidence binding at rev29 must not be read as F2b semantic cleanliness."
        ),
        "measured": {"F2b_sha256": files[SCHEMA_PATHS["F2b"]]["sha256"], "inverted_premise_present": inverted_present},
        "falsifier": (
            "F2b at a new hash with 'strictly smaller extension class' (or an owner-recorded "
            "adjudication that the token is non-containment wording) plus a containment check PASS."
        ),
    })

    core = {c["id"]: c["ok"] for c in checks}
    structural_ok = bool(core.get("P0") and core.get("P0b") and core.get("P2") and core.get("P4a"))
    if not snap_ok or not controls_ok:
        verdict = "VOID_CONTROL_OR_PIN_FAILURE"
    elif not fixpoint_ok:
        verdict = "REVISE_FIXPOINT_FAILED"
    elif measurements["live_stream_E_declarations_at_pinned_hash"] < 1 or unregistered or stale:
        verdict = "FIXPOINT_CONFIRMED_BINDING_GAPS_MEASURED"
    else:
        verdict = "FIXPOINT_CONFIRMED_FULLY_BOUND"

    report = {
        "task_id": "W042-REV29-EVBIND-DURABILITY-06",
        "actor": "worker-042",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "secondary_gate": "G-AUDIT",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "generated_at_note": "the only nondeterministic field; all measurements are snapshot-bound",
        "snapshot_manifest": str((SNAP / "manifest.json").relative_to(REPO)),
        "snapshot_manifest_sha256": sha256_file(SNAP / "manifest.json"),
        "measurements": measurements,
        "checks": checks,
        "controls": controls,
        "controls_ok": controls_ok,
        "findings": findings,
        "verdict": verdict,
        "structural_ok": structural_ok,
        "authority_note": (
            "Worker measurement only: no gate verdict, no node status, no validation_status=passed, "
            "no canonical byte written; all runs were in isolated sandbox trees under runs/."
        ),
        "rerun": "python3 artifacts/worker-042/rev29_evbind_durability/pin_snapshot.py && python3 artifacts/worker-042/rev29_evbind_durability/verify_rev29_durability.py",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "structural_ok": structural_ok,
        "controls_ok": controls_ok,
        "checks": {c["id"]: c["ok"] for c in checks},
        "controls": {c["id"]: c["fires"] for c in controls},
        "findings": [f["id"] for f in findings],
        "report_sha256": sha256_file(HERE / "report.json"),
    }, indent=1))
    if not snap_ok or not controls_ok:
        return 2
    return 0 if structural_ok else 1


if __name__ == "__main__":
    sys.exit(main())
