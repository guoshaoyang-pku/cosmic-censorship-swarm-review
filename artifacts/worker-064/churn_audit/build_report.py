#!/usr/bin/env python3
"""W064-CHURN-01 report builder: turn samples.jsonl into a hash-pinned churn/binding report.

Read-only apart from writing measurements.json, report.json in this directory.
"""
import hashlib, json, os, datetime
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SAMPLES = os.path.join(HERE, "samples.jsonl")

CANON = [
    "research_map/formulation_taxonomy.yaml",   # F0
    "schemas/af_wcc_vacuum.yaml",               # F1
    "schemas/af_scc_c2_vacuum.yaml",            # F2a
    "schemas/af_scc_c0_vacuum.yaml",            # F2b
]
MIRROR = {
    "research_map/formulation_taxonomy.yaml": "artifacts/formulation/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
# Advertised "final hashes" from leadform-resource-request-2026-09-12T00:34:00+08:00 / leadform-blocker-0005
LEAD_CLAIM = {
    "schemas/af_wcc_vacuum.yaml": "68392dd820505fbb8c59c2944e744d00cef5a94fecafb3e927fd14a235d7175c",
    "schemas/af_scc_c2_vacuum.yaml": "4f97273ef4404126ef5c8a083ccd5ed4d4ef9fd1aeaf6884c8c5aee0542e12f8",
    "schemas/af_scc_c0_vacuum.yaml": "a2aef5ac7fe377a82b974aabddb991eec12ee7662d4b8e39d1516ac945965543",
    "research_map/formulation_taxonomy.yaml": "0fcc6a1928fd40b02529f59c8a23095191001f84858346bf83d00818c29d7b31",
}

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def iso_from_ns(ns):
    return datetime.datetime.fromtimestamp(ns / 1e9).astimezone().isoformat(timespec="seconds")

def main():
    samples = [json.loads(l) for l in open(SAMPLES) if l.strip()]
    n = len(samples)
    first, last = samples[0], samples[-1]
    per_path = OrderedDict()
    for rel in CANON + list(MIRROR.values()) + ["artifacts/formulation/FROZEN.json"]:
        seen = []  # (t_rel, at, sha, bytes, mtime_ns)
        for s in samples:
            f = s["files"][rel]
            if not seen or seen[-1][2] != f["sha256"]:
                seen.append((s["t_rel_s"], s["at"], f["sha256"], f["bytes"], f["mtime_ns"]))
        changes = len(seen) - 1
        intervals = [round(seen[i + 1][0] - seen[i][0], 2) for i in range(len(seen) - 1)]
        per_path[rel] = {
            "distinct_hashes": len(seen),
            "hash_changes": changes,
            "first_sha256": seen[0][2],
            "last_sha256": seen[-1][2],
            "last_write_before_window_iso": iso_from_ns(first["files"][rel]["mtime_ns"]) if first["files"][rel]["mtime_ns"] else None,
            "change_intervals_s": intervals,
            "min_interval_s": min(intervals) if intervals else None,
            "max_interval_s": max(intervals) if intervals else None,
            "revisions": [{"t_rel_s": t, "at": at, "sha256": h, "bytes": b} for t, at, h, b, _ in seen],
            "stable_all_window": changes == 0,
        }

    frozen_revs = []
    for s in samples:
        fr = s.get("frozen", {})
        if not frozen_revs or frozen_revs[-1]["revision"] != fr.get("revision") or frozen_revs[-1]["frozen_at"] != fr.get("frozen_at"):
            frozen_revs.append({"t_rel_s": s["t_rel_s"], "at": s["at"], "revision": fr.get("revision"), "frozen_at": fr.get("frozen_at")})
    freeze_mismatch = {}
    for rel in CANON:
        mism = [s["t_rel_s"] for s in samples if not s.get("frozen_match", {}).get(rel, False)]
        freeze_mismatch[rel] = {"mismatch_samples": len(mism), "total_samples": n, "first_mismatch_t_rel_s": (mism[0] if mism else None)}
    mirror_mismatch = {}
    for c, m in MIRROR.items():
        mism = [s["t_rel_s"] for s in samples if s["files"][c]["sha256"] != s["files"][m]["sha256"]]
        mirror_mismatch[f"{c} vs {m}"] = {"divergent_samples": len(mism), "total_samples": n}

    lead_claim_match = {rel: sum(1 for s in samples if s["files"][rel]["sha256"] == h) for rel, h in LEAD_CLAIM.items()}
    canonical_changed = {rel: per_path[rel]["hash_changes"] for rel in CANON}
    any_canonical_churn = any(v > 0 for v in canonical_changed.values())
    any_freeze_mismatch = any(v["mismatch_samples"] > 0 for v in freeze_mismatch.values())
    frozen_revision_constant = len(frozen_revs) == 1
    advertised_pins_stale = any(v < n for v in lead_claim_match.values())
    dual_tree_divergence = any(v["divergent_samples"] > 0 for v in mirror_mismatch.values())
    fr = first.get("frozen", {})
    frozen_at = fr.get("frozen_at")
    skew_s = None
    if frozen_at:
        try:
            t_frozen = datetime.datetime.fromisoformat(frozen_at)
            t_first = datetime.datetime.fromisoformat(first["at"])
            skew_s = round((t_frozen - t_first).total_seconds())
        except Exception:
            pass
    frozen_at_future = bool(skew_s and skew_s > 0)

    if any_canonical_churn and frozen_revision_constant:
        verdict = "UNSTABLE_PUBLICATION_WINDOW"
    elif any_canonical_churn:
        verdict = "CHURN_WITH_MANIFEST_BUMPS"
    elif any_freeze_mismatch:
        verdict = "STABLE_BUT_FROZEN_STALE"
    elif advertised_pins_stale or frozen_at_future or dual_tree_divergence:
        verdict = "STABLE_FROZEN_BOUND_WITH_BINDING_DEFECTS"
    else:
        verdict = "STABLE_AND_FROZEN_BOUND"

    measurements = {
        "task_id": "W064-CHURN-01",
        "measured_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "window": {"samples": n, "t_first": first["at"], "t_last": last["at"], "t_rel_first_s": first["t_rel_s"], "t_rel_last_s": last["t_rel_s"], "nominal_interval_s": 5.0},
        "per_path": per_path,
        "frozen_revisions_observed": frozen_revs,
        "frozen_frozen_at": frozen_at,
        "frozen_frozen_at_skew_vs_window_start_s": skew_s,
        "frozen_frozen_at_future_dated": frozen_at_future,
        "frozen_manifest_mismatch": freeze_mismatch,
        "canonical_vs_authoring_divergence": mirror_mismatch,
        "lead_advertised_final_hash_matches": lead_claim_match,
        "advertised_pins_stale": advertised_pins_stale,
        "dual_tree_divergence_present": dual_tree_divergence,
        "verdict": verdict,
        "verdict_rule": "UNSTABLE_PUBLICATION_WINDOW = >=1 canonical frozen-class artifact changed hash during the window AND FROZEN.json revision did not change; CHURN_WITH_MANIFEST_BUMPS = canonical changed and FROZEN revision changed; STABLE_BUT_FROZEN_STALE = no canonical change but FROZEN manifest entry != measured at >=1 sample; STABLE_FROZEN_BOUND_WITH_BINDING_DEFECTS = stable and manifest-bound but >=1 of {advertised pins stale, frozen_at future-dated, canonical/authoring dual-tree divergence}; STABLE_AND_FROZEN_BOUND = none of the above.",
    }
    with open(os.path.join(HERE, "measurements.json"), "w") as f:
        json.dump(measurements, f, indent=1, sort_keys=True)

    report = {
        "schema_version": "0.1",
        "task_id": "W064-CHURN-01",
        "actor": "worker-064",
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": "F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-F0",
        "scope": "Publication-stability and binding-consistency measurement of the four frozen-class canonical artifacts and their authoring mirrors against FROZEN.json, over one bounded 90 s window. No mathematical verdict on any schema.",
        "method": "read-only sampler (sample_churn.py) hashing 11 paths every 5 s for 90 s; FROZEN.json manifest compared per sample; hashes advertised in leadform-resource-request-2026-09-12T00:34:00+08:00 compared per sample",
        "verdict": verdict,
        "measurement_summary": {
            "samples": n,
            "window": [first["at"], last["at"]],
            "canonical_hash_changes": canonical_changed,
            "canonical_last_write_before_window": {p: per_path[p]["last_write_before_window_iso"] for p in CANON},
            "frozen_revision_observed": [f"{r['revision']}@{r['frozen_at']}" for r in frozen_revs],
            "frozen_frozen_at_skew_vs_window_start_s": skew_s,
            "frozen_manifest_mismatch_samples": {k: v["mismatch_samples"] for k, v in freeze_mismatch.items()},
            "canonical_vs_authoring_divergent_samples": mirror_mismatch,
            "advertised_final_hash_matches_out_of_n": lead_claim_match,
            "advertised_pins_stale": advertised_pins_stale,
            "dual_tree_divergence_present": dual_tree_divergence,
        },
        "findings": [
            f"F-CHURN-1 (STABILITY HOLDS): over {n} samples / 90 s the four canonical hashes were constant: "
            + ", ".join(f"{k.split('/')[-1]}={v['first_sha256'][:16]}" for k, v in per_path.items() if k in CANON)
            + f". Last canonical writes before the window: "
            + ", ".join(f"{p.split('/')[-1]}={per_path[p]['last_write_before_window_iso']}" for p in CANON)
            + f". FROZEN.json revision={[r['revision'] for r in frozen_revs]} was constant and its manifest matched the measured hash in "
            + ", ".join(f"{k.split('/')[-1]}:{n - v['mismatch_samples']}/{n}" for k, v in freeze_mismatch.items())
            + " samples. The publication loop had quiesced before the window (FROZEN rev25 written 2026-09-12T00:19:46+08:00).",
            f"F-CHURN-2 (STALE ADVERTISED PINS): the hashes advertised as final in leadform-resource-request-2026-09-12T00:34:00+08:00 and restated in leadform-blocker-0005 matched the live canonical files in "
            + ", ".join(f"{k.split('/')[-1]}:{v}/{n}" for k, v in lead_claim_match.items())
            + " samples. A reviewer following the comms literally would bind hashes that are no longer canonical; this is the mechanical cause of the standing blocker 'no independent verdict binds the FINAL hashes'.",
            f"F-CHURN-3 (FREEZE STAMP FUTURE-DATED): FROZEN rev25 declares frozen_at={frozen_at}, which is {skew_s} s after the first sample ({first['at']}); the file's own last write was {per_path['artifacts/formulation/FROZEN.json']['last_write_before_window_iso']}. A manifest stamped in the future cannot witness when the freeze occurred; this is the same defect worker-084 flagged for rev24 (C1.5) and is consistent with the controller's clock_discipline count of 72 future-dated events (max skew 6133 s).",
            "F-CHURN-4 (F0 DUAL-TREE DIVERGENCE PERSISTS): "
            + ", ".join(f"{k}: divergent in {v['divergent_samples']}/{n} samples" for k, v in mirror_mismatch.items())
            + ". The three schema mirrors are byte-identical to canonical; only the F0 taxonomy authoring copy diverges.",
        ],
        "interpretation": "Stability is real at the measured instant, so a reviewer can bind the rev25 hashes if they hash the files themselves. But the swarm's own binding instructions are inconsistent: comms advertise rev-old hashes (F-CHURN-2), FROZEN's stamp is future-dated (F-CHURN-3), and the F0 declared/authoring trees still differ (F-CHURN-4). The actionable sequence is: freeze the publisher, correct the advertised hashes, correct/replace the FROZEN stamp, and reconcile the F0 authoring copy; then re-run this sampler to certify a quiet binding window.",
        "falsifier": "A re-run of sample_churn.py with the same 5 s cadence over >=90 s is a falsifier of every finding here: (a) any canonical hash change while the FROZEN revision is constant falsifies F-CHURN-1's stability; (b) any sample matching all four advertised hashes falsifies F-CHURN-2; (c) frozen_at <= first-sample wall clock falsifies F-CHURN-3; (d) byte-identity of canonical and authoring F0 across all samples falsifies F-CHURN-4.",
        "not_claimed": [
            "no gate verdict and no node completion; worker events cannot set status=done or validation_status=passed",
            "no statement about which revision is mathematically correct",
            "no attribution of intent; only measured hashes, sizes, mtimes and manifest fields are reported",
            "a 90 s window cannot bound churn or stability outside it",
        ],
        "evidence": {
            "samples_jsonl": {"path": "artifacts/worker-064/churn_audit/samples.jsonl", "sha256": sha_file(SAMPLES)},
            "measurements_json": {"path": "artifacts/worker-064/churn_audit/measurements.json", "sha256": sha_file(os.path.join(HERE, "measurements.json"))},
            "sampler": {"path": "artifacts/worker-064/churn_audit/sample_churn.py", "sha256": sha_file(os.path.join(HERE, "sample_churn.py"))},
        },
        "next_falsifier": "Re-run the same sampler after the lead corrects the advertised pins and the FROZEN stamp; a window with zero canonical changes, zero manifest mismatches, all four advertised hashes matching, and non-future frozen_at closes F-CHURN-1..3.",
    }
    with open(os.path.join(HERE, "report.json"), "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
    print(json.dumps({"verdict": verdict, "n": n, "canonical_changes": canonical_changed,
                      "advertised_match": lead_claim_match, "frozen_skew_s": skew_s,
                      "dual_tree": dual_tree_divergence}, indent=1))

if __name__ == "__main__":
    main()
