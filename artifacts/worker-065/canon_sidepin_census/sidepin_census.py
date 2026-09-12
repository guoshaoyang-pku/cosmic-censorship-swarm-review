#!/usr/bin/env python3
"""W065-CANON-SIDEPIN-CENSUS-04 driver.

One bounded class-bound task (AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM):

  Measure every declared hash side-pin on the canonical paths at FROZEN rev29
  / live bytes, classify each as live / stale / missing, quantify the F2b
  accept-path blast radius (how many reviewers' *accept* mass sits on the hash
  the stale sidecar advertises), build artifact-local repair shadows for the
  two mechanical registries, and gate the whole instrument with 7 controls.

Read-only on every canonical path. Writes only under this artifact directory.
Exits 0 when the instrument is valid (even if the finding is "defects exist");
exits 1 on instrument failure or an unstable measurement window.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import check_sidepins as cs  # noqa: E402

REGISTRY_PATHS = (
    "entry_hashes.json",
    "artifacts/formulation/FROZEN.json",
    "schemas/af_scc_regularities.yaml",
    "schemas/af_scc_c0_vacuum.yaml.sha256",
)
SHADOW = HERE / "repair_shadow"
CONTROLS = HERE / "controls"

# Interpretation layer (clearly separated from measurement): hashes that
# reviews on disk record as superseded revisions for the same target.
SUPERSEDED_EVIDENCE = {
    "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508": {
        "target": "schemas/af_scc_c0_vacuum.yaml",
        "recorded_as": "rev11/rev12 hash, superseded by rev13 b2ab6acb",
        "evidence": ["reviews/F2b-review-rev27-a.json#observation",
                     "reviews/F2b-review-rev27-b.json#stale-side-pins",
                     "artifacts/worker-087/gform_independence_r2/addendum_f2b_sidecar.json"],
    },
    "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503": {
        "target": "schemas/af_wcc_vacuum.yaml",
        "recorded_as": "F1 rev12 hash, superseded by rev13 d9cebb94",
        "evidence": ["runtime/state/controller_verification/astra-lifecycle-06-decisions.json#REC-23"],
    },
    "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2": {
        "target": "schemas/af_scc_c2_vacuum.yaml",
        "recorded_as": "F2a rev11/rev12 hash, superseded by rev13 e9a27996",
        "evidence": ["runtime/state/controller_verification/astra-lifecycle-06-decisions.json#REC-23"],
    },
    "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc": {
        "target": "research_map/formulation_taxonomy.yaml",
        "recorded_as": "F0 taxonomy pre-rev5 hash, superseded by 0abb9ed8",
        "evidence": ["research_map/research_map.json#gates.G-F0", "HANDOFF.md#section-4"],
    },
    "af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b": {
        "target": "artifacts/formulation/FROZEN.json",
        "recorded_as": "FROZEN pre-rev29 manifest hash, superseded by 815e0807",
        "evidence": ["runtime/state/controller_verification/astra-lifecycle-06-decisions.json#REC-24"],
    },
}

FROZEN_PATH = "artifacts/formulation/FROZEN.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(paths) -> dict:
    out = {}
    for rel in sorted(set(paths)):
        if rel in cs.MOVING_TARGETS:
            continue  # moving by policy; excluded from the stability predicate
        p = REPO / rel
        if p.is_file():
            out[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        else:
            out[rel] = {"sha256": None, "bytes": None}
    return out


def registrar_meta() -> dict:
    meta = {}
    for rel in REGISTRY_PATHS:
        p = REPO / rel
        if not p.is_file():
            meta[rel] = None
            continue
        row = {"sha256": sha256_file(p), "bytes": p.stat().st_size,
               "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(p.stat().st_mtime))}
        if rel.endswith("af_scc_regularities.yaml"):
            try:
                import yaml
                doc = yaml.safe_load(p.read_text())
                row["revision"] = doc.get("revision")
                row["supersedes_sha256"] = doc.get("supersedes_sha256")
                row["component_pins"] = {c.get("role"): c.get("sha256")
                                         for c in (doc.get("components") or [])}
            except Exception:  # noqa: BLE001
                pass
        meta[rel] = row
    return meta


def _windows_rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def build_shadow(live: dict) -> dict:
    """Artifact-local repair shadow: mechanical registries refreshed to live bytes."""
    if SHADOW.exists():
        shutil.rmtree(SHADOW)
    (SHADOW / "schemas").mkdir(parents=True)
    manifest = {"base_root": str(REPO), "files": []}

    # 1. entry_hashes.json -> every resolvable non-moving pin at live bytes
    entry = json.loads((REPO / "entry_hashes.json").read_text())
    refreshed = {}
    for target, advertised in entry.items():
        live_hash = None
        if target not in cs.MOVING_TARGETS:
            p = REPO / target
            if p.is_file():
                live_hash = sha256_file(p)
        refreshed[target] = live_hash or advertised
    out = SHADOW / "entry_hashes.json"
    out.write_text(json.dumps(refreshed, indent=1, sort_keys=True) + "\n")

    # 2. sidecar -> live hash, basename form preserved
    sidecar = REPO / "schemas/af_scc_c0_vacuum.yaml.sha256"
    live_c0 = sha256_file(REPO / "schemas/af_scc_c0_vacuum.yaml")
    out2 = SHADOW / "schemas/af_scc_c0_vacuum.yaml.sha256"
    out2.write_text(f"{live_c0}  af_scc_c0_vacuum.yaml\n")

    # 3. aggregator -> exact textual substitution of whatever each component
    #    currently advertises, refreshed to the live hash (no-op if already live)
    agg_text = (REPO / "schemas/af_scc_regularities.yaml").read_text()
    comps = {}
    try:
        import yaml
        doc = yaml.safe_load(agg_text)
        for c in (doc.get("components") or []):
            if isinstance(c, dict) and c.get("path") and c.get("sha256"):
                comps[c["path"]] = c["sha256"]
    except Exception:  # noqa: BLE001
        pass
    if not comps:
        comps = {p["target"]: p["advertised"] for p in cs.parse_registries(REPO)
                 if p["source_kind"] == "aggregator_component"}
    subs = []
    for target, advertised in sorted(comps.items()):
        live_hash = sha256_file(REPO / target)
        if advertised == live_hash:
            subs.append({"target": target, "old": advertised, "new": live_hash,
                         "substitution": "none-already-live"})
            continue
        count = agg_text.count(advertised)
        if count != 1:
            raise RuntimeError(
                f"aggregator substitution for {target} matched {count} times, expected 1")
        agg_text = agg_text.replace(advertised, live_hash)
        subs.append({"target": target, "old": advertised, "new": live_hash,
                     "substitution": "applied"})
    out3 = SHADOW / "schemas/af_scc_regularities.yaml"
    out3.write_text(agg_text)

    for rel, base in (("entry_hashes.json", "entry_hashes.json"),
                      ("schemas/af_scc_c0_vacuum.yaml.sha256", "schemas/af_scc_c0_vacuum.yaml.sha256"),
                      ("schemas/af_scc_regularities.yaml", "schemas/af_scc_regularities.yaml")):
        manifest["files"].append({
            "shadow": rel,
            "base": base,
            "base_sha256": sha256_file(REPO / base),
            "shadow_sha256": sha256_file(SHADOW / rel),
            "substitutions": subs if rel.endswith("af_scc_regularities.yaml") else None,
        })
    (SHADOW / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def run_checker(root: Path, targets: Path):
    proc = subprocess.run(
        [sys.executable, str(HERE / "check_sidepins.py"), "--root", str(root),
         "--targets", str(targets), "--json-out", str(HERE / "_last_check.json")],
        capture_output=True, text=True)
    doc = None
    if (HERE / "_last_check.json").is_file():
        doc = json.loads((HERE / "_last_check.json").read_text())
        (HERE / "_last_check.json").unlink()
    return proc.returncode, doc, proc.stderr.strip()


def _copy_shadow(name: str) -> Path:
    dest = CONTROLS / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SHADOW, dest)
    return dest


def run_controls(live_rc: int) -> list:
    if CONTROLS.exists():
        shutil.rmtree(CONTROLS)
    CONTROLS.mkdir(parents=True)
    results = []

    def record(cid, desc, rc, doc, expect_rc, expect_cat=None, expect_target=None):
        cats = {r["category"] for r in (doc or {}).get("gate_relevant_defects", [])}
        hit = True
        if expect_cat:
            rows = [r for r in (doc or {}).get("gate_relevant_defects", [])
                    if r["category"] == expect_cat
                    and (expect_target is None or r["target"] == expect_target)]
            hit = bool(rows)
        results.append({"id": cid, "description": desc, "rc": rc, "expected_rc": expect_rc,
                        "detected_categories": sorted(cats), "expected_category": expect_cat,
                        "expected_target": expect_target, "pass": rc == expect_rc and hit})

    # K0 live tree must fail closed
    record("K0", "live tree: stale gate-relevant side-pins present -> checker exits 2",
           live_rc, None, 2)

    # K1 clean shadow must pass
    rc, doc, err = run_checker(SHADOW, REPO)
    record("K1", "repaired shadow: all pins refreshed -> checker exits 0", rc, doc, 0)

    # K2 revert the F2b sidecar to the recorded superseded hash
    d = _copy_shadow("K2_sidecar_superseded")
    (d / "schemas/af_scc_c0_vacuum.yaml.sha256").write_text(
        "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508  af_scc_c0_vacuum.yaml\n")
    rc, doc, err = run_checker(d, REPO)
    record("K2", "shadow with F2b sidecar reverted to superseded 1bb78ce9 -> detected",
           rc, doc, 2, "STALE", "af_scc_c0_vacuum.yaml")

    # K3 garbage hash on F1
    d = _copy_shadow("K3_entry_garbage")
    eh = json.loads((d / "entry_hashes.json").read_text())
    eh["schemas/af_wcc_vacuum.yaml"] = "de" * 32
    (d / "entry_hashes.json").write_text(json.dumps(eh, indent=1, sort_keys=True) + "\n")
    rc, doc, err = run_checker(d, REPO)
    record("K3", "shadow with F1 entry replaced by non-hash garbage -> detected",
           rc, doc, 2, "STALE", "schemas/af_wcc_vacuum.yaml")

    # K4 repointed pin: F1 entry carries the live F2a hash
    d = _copy_shadow("K4_entry_repointed")
    eh = json.loads((d / "entry_hashes.json").read_text())
    eh["schemas/af_wcc_vacuum.yaml"] = sha256_file(REPO / "schemas/af_scc_c2_vacuum.yaml")
    (d / "entry_hashes.json").write_text(json.dumps(eh, indent=1, sort_keys=True) + "\n")
    rc, doc, err = run_checker(d, REPO)
    record("K4", "shadow with F1 entry repointed to the live F2a hash -> detected",
           rc, doc, 2, "STALE", "schemas/af_wcc_vacuum.yaml")

    # K5 aggregator c0 pin reverted
    d = _copy_shadow("K5_aggregator_superseded")
    text = (d / "schemas/af_scc_regularities.yaml").read_text()
    live_c0 = sha256_file(REPO / "schemas/af_scc_c0_vacuum.yaml")
    text = text.replace(live_c0, "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508")
    (d / "schemas/af_scc_regularities.yaml").write_text(text)
    rc, doc, err = run_checker(d, REPO)
    record("K5", "shadow with aggregator c0 pin reverted to superseded hash -> detected",
           rc, doc, 2, "STALE", "schemas/af_scc_c0_vacuum.yaml")

    # K6 missing target on a canonical root
    d = _copy_shadow("K6_missing_target")
    eh = json.loads((d / "entry_hashes.json").read_text())
    eh["schemas/__nonexistent__.yaml"] = "ab" * 32
    (d / "entry_hashes.json").write_text(json.dumps(eh, indent=1, sort_keys=True) + "\n")
    rc, doc, err = run_checker(d, REPO)
    record("K6", "shadow with a pin to a nonexistent canonical target -> detected",
           rc, doc, 2, "TARGET_MISSING", "schemas/__nonexistent__.yaml")

    return results


def _declared_hashes(d: dict) -> set:
    """Hashes a review record *declares* as the reviewed artifact (not mentions)."""
    out = set()
    for key in ("reviewed_sha256", "artifact_sha256", "declared_sha256", "pin_sha256"):
        v = d.get(key)
        if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
            out.add(v)
    t = d.get("target")
    if isinstance(t, dict):
        for key in ("sha256", "artifact_sha256", "pin_sha256", "reviewed_sha256"):
            v = t.get(key)
            if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
                out.add(v)
    return out


def _names_f2b(d: dict) -> bool:
    for key in ("node_id", "target_id"):
        if str(d.get(key) or "") == "F2b":
            return True
    t = d.get("target")
    if isinstance(t, dict) and str(t.get("node_id") or "") == "F2b":
        return True
    for key in ("artifact", "path", "canonical_path"):
        if "af_scc_c0_vacuum" in str(d.get(key) or ""):
            return True
    if isinstance(t, dict) and "af_scc_c0_vacuum" in str(t.get("path") or ""):
        return True
    return False


def f2b_blast_radius(live: dict) -> dict:
    """Independent re-derivation of accept mass per F2b hash, by *declared* binding.

    Universe: reviews/*.json only. The accepted event stream is excluded because
    its review records do not carry a declared artifact hash (measured: the F2b
    accept events have reviewed_sha256/artifact_sha256 null), so it cannot bind.
    """
    revoked = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
    live_hash = sha256_file(REPO / "schemas/af_scc_c0_vacuum.yaml")
    live_accepts, revoked_accepts = {}, {}
    n_f2b_accepts = 0
    for f in sorted((REPO / "reviews").glob("*.json")):
        try:
            d = json.loads(f.read_text(errors="replace"))
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("verdict") != "accept" or not _names_f2b(d):
            continue
        n_f2b_accepts += 1
        declared = _declared_hashes(d)
        row = {"review_file": str(f.relative_to(REPO)),
               "reviewer": d.get("reviewer") or f.stem,
               "created_at": d.get("created_at"),
               "score": d.get("score"),
               "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict")}
        if live_hash in declared:
            live_accepts.setdefault(str(d.get("reviewer") or f.stem), []).append(row)
        elif revoked in declared:
            revoked_accepts.setdefault(str(d.get("reviewer") or f.stem), []).append(row)
    return {
        "measured_live_f2b_sha256": live_hash,
        "sidecar_advertised_sha256": revoked,
        "scan_universe": "reviews/*.json (declared-hash binding; event stream has null hashes)",
        "n_f2b_accept_records": n_f2b_accepts,
        "f2b_accept_reviewers_declaring_live_hash": {
            k: v for k, v in sorted(live_accepts.items())},
        "f2b_accept_reviewers_declaring_superseded_hash": {
            k: v for k, v in sorted(revoked_accepts.items())},
        "note": ("Reviewer independence/clustering is the r3 adjudication's job (see "
                 "worker-087 W087-GFORM-INDEP-05, which measured 1 live F2b cluster at "
                 "01:04; worker-090/071/072 full-schema accepts landed 01:08-01:10 and are "
                 "listed here as measured, not adjudicated)."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generated-at", default=None)
    args = ap.parse_args(argv)
    generated_at = args.generated_at or "UNSPECIFIED"

    # ---- measure inside a stable window (bounded retry: this repo moves) ----
    attempts = []
    shadow_manifest = None
    controls = None
    live = None
    registries = None
    window, drift = "UNSTABLE", []
    for attempt in range(1, 6):
        live = cs.measure(REPO, REPO)
        registries = registrar_meta()
        paths = set(REGISTRY_PATHS)
        for r in live["pins"]:
            if r.get("resolved_path"):
                paths.add(r["resolved_path"])
            paths.add(r["target"])
        for m in live["mirror_alignment"]:
            paths.add(m["canonical"])
            paths.add(m["mirror"])
        pre = snapshot(paths)
        shadow_manifest = build_shadow(live)
        live_rc, _, _ = run_checker(REPO, REPO)
        controls = run_controls(live_rc)
        post = snapshot(paths)
        drift = sorted(k for k in pre if pre[k] != post[k])
        attempts.append({
            "attempt": attempt,
            "drift": {k: {"pre": pre[k], "post": post[k]} for k in drift},
            "window": "STABLE" if not drift else "UNSTABLE",
        })
        window = "STABLE" if not drift else "UNSTABLE"
        if not drift:
            break
        time.sleep(2.0)
    mid_run_observations = []
    for a in attempts[:-1]:
        for path, delta in a["drift"].items():
            mid_run_observations.append({"path": path, "observed_pre": delta["pre"],
                                         "observed_post": delta["post"]})

    defect_rows = live["gate_relevant_defects"]
    superseded_rows = [r for r in defect_rows
                       if r["advertised"] in SUPERSEDED_EVIDENCE
                       and SUPERSEDED_EVIDENCE[r["advertised"]]["target"] == r.get("resolved_path")]
    by_source = {}
    for r in defect_rows:
        by_source.setdefault(r["source"], []).append(r["target"])

    verdict = ("SIDEPIN_TRAP_CONFIRMED" if defect_rows and window == "STABLE"
               else "SIDEPINS_CLEAN" if not defect_rows else "WINDOW_UNSTABLE")
    instrument_valid = window == "STABLE" and all(c["pass"] for c in controls)

    census = {
        "task_id": "W065-CANON-SIDEPIN-CENSUS-04",
        "actor": "worker-065",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "generated_at": generated_at,
        "instrument": "check_sidepins.py",
        "window_status": window,
        "window_drift": drift,
        "window_attempts": attempts,
        "mid_run_observations": mid_run_observations,
        "registries_measured": registries,
        "n_pins_measured": live["n_pins"],
        "category_counts": live["counts"],
        "mirror_alignment": [{k: m[k] for k in ("canonical", "aligned", "canonical_sha256")}
                             for m in live["mirror_alignment"]],
        "gate_relevant_defects": [
            {k: r.get(k) for k in ("source", "source_kind", "target", "resolved_path",
                                   "advertised", "live_sha256", "frozen_pin_for_target",
                                   "advertised_is_live_hash_of", "gate_relevant")}
            for r in defect_rows
        ],
        "advisory_defects": [
            {k: r.get(k) for k in ("source", "target", "resolved_path", "advertised",
                                   "live_sha256", "gate_relevant")}
            for r in live["advisory_defects"]
        ],
        "defects_by_source": {k: sorted(v) for k, v in sorted(by_source.items())},
        "superseded_pin_interpretation": {
            "rows": [{"advertised": r["advertised"], "live_sha256": r["live_sha256"],
                      "target": r["resolved_path"], **SUPERSEDED_EVIDENCE[r["advertised"]]}
                     for r in superseded_rows],
            "disclaimer": ("Interpretation layer: the defect is the measured inequality; the "
                           "'superseded' label is cited from reviews/decisions on disk, not "
                           "decided by the checker."),
        },
        "f2b_blast_radius": f2b_blast_radius(live),
        "repair_shadow": shadow_manifest,
        "controls": controls,
        "instrument_valid": instrument_valid,
        "verdict": verdict,
        "falsifier": (
            "Any pin this census classifies STALE is shown to resolve its target correctly "
            "under a declared resolution rule (FROZEN path_policy redirect, or a documented "
            "alias); or any gate-relevant target's bytes change between the window pre and "
            "post readings (window UNSTABLE voids the measurement at the newer revision); or "
            "a refreshed shadow this census calls clean is shown to still advertise a "
            "non-live hash for a canonical target."),
    }
    (HERE / "sidepin_census.json").write_text(json.dumps(census, indent=1, sort_keys=True) + "\n")
    (HERE / "control_results.json").write_text(
        json.dumps({"controls": controls, "live_checker_rc": live_rc,
                    "all_pass": all(c["pass"] for c in controls)}, indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "verdict": verdict,
        "window": window,
        "n_pins": live["n_pins"],
        "counts": live["counts"],
        "gate_relevant_defects": len(defect_rows),
        "defects_by_source": {k: len(v) for k, v in sorted(by_source.items())},
        "superseded_rows": len(superseded_rows),
        "f2b_live_accept_reviewers": sorted(
            census["f2b_blast_radius"]["f2b_accept_reviewers_declaring_live_hash"]),
        "f2b_superseded_accept_reviewers": sorted(
            census["f2b_blast_radius"]["f2b_accept_reviewers_declaring_superseded_hash"]),
        "controls_pass": f"{sum(c['pass'] for c in controls)}/{len(controls)}",
        "instrument_valid": instrument_valid,
    }, indent=1, sort_keys=True))
    return 0 if instrument_valid else 1


if __name__ == "__main__":
    sys.exit(main())
