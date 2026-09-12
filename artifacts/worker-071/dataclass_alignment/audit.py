#!/usr/bin/env python3
"""FORM-DC-ALIGN-071 -- independent data-class alignment measurement across F1/F2a/F2b.

Pre-registered method: artifacts/worker-071/dataclass_alignment/method.json, written before
this script was executed. Tiers, CORE_KEYS and controls are fixed there; this script implements
them literally.

Measurement only. Writes only under artifacts/worker-071/dataclass_alignment/. Never sets a
gate verdict, a node status, or validation_status=passed.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
TASK_ID = "FORM-DC-ALIGN-071"
WORKER = "worker-071"

INPUTS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "F0_canonical": "research_map/formulation_taxonomy.yaml",
    "F0_authoring": "artifacts/formulation/formulation_taxonomy.yaml",
}
SCHEMA_KEYS = ["F1", "F2a", "F2b"]
CLASS_OF = {
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}

# Fixed before the run in method.json.
CORE_KEYS = [
    "matter",
    "cosmological_constant",
    "equations",
    "constraints.hamiltonian",
    "constraints.momentum",
    "regularity_class.default",
    "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "regularity_class.sobolev_variant.spaces",
    "asymptotic_decay.metric",
    "asymptotic_decay.second_fundamental_form",
    "asymptotic_decay.parity_conditions",
    "symmetry",
    "adm_mass.exists",
    "adm_mass.sign",
]

FALSIFIER = (
    "If all three canonical data_class subtrees compare equal at T1, or all CORE_KEYS compare "
    "equal at T2, then the G-FORM unmet item 'no single frozen data class (s,delta,norm) is "
    "shared by F1/F2a/F2b' is refuted at the measured hashes and the authoring data_class_freeze "
    "claim is confirmed; the artifact must report that outcome. If any difference is found, the "
    "(path, file, line, value) witness list is the deliverable and the unmet item stands at "
    "exactly the strength of the difference found. Any change of an input sha256 across the "
    "measurement window voids the measurement at that path."
)

LIMITATIONS = [
    "T3 normalization drops parenthesized and post-semicolon text; every dropped fragment is "
    "listed in dropped_fragments so the normalization is auditable.",
    "Line numbers are value-node start lines from the YAML composer.",
    "Only F1/F2a/F2b are compared; AF-WCC-SCALAR-SPH is out of scope.",
    "The measurement reports strict (T1/T2) and normalized (T3) readings; it does not decide "
    "which reading transfer rule T1 should use.",
    "No gate verdict and no node status are asserted.",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def line_map(path: Path):
    """Map dotted path -> value-node start line (1-based) using the YAML composer."""
    text = path.read_text()
    node = yaml.compose(text)
    out: dict[str, int] = {}

    def walk(n, prefix: str):
        if isinstance(n, yaml.MappingNode):
            for k, v in n.value:
                key = str(k.value)
                p = f"{prefix}.{key}" if prefix else key
                out[p] = v.start_mark.line + 1
                walk(v, p)
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, f"{prefix}[{i}]")

    if node is not None:
        walk(node, "")
    return out


def dig(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def walk_leaves(obj, prefix: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def norm_strict(v) -> str:
    if v is None:
        return "<null>"
    if isinstance(v, bool):
        return "true" if v else "false"
    return re.sub(r"\s+", " ", str(v)).strip()


def norm_core(v):
    """Return (normalized, dropped_fragments). Declared convenience reading (T3)."""
    s = norm_strict(v)
    dropped = [m.group(0) for m in re.finditer(r"\([^)]*\)", s)]
    s = re.sub(r"\([^)]*\)", "", s)
    if ";" in s:
        head, tail = s.split(";", 1)
        dropped.append(";" + tail)
        s = head
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[.,;]+$", "", s).strip()
    return s, dropped


def raw_block(text: str, top_key: str = "data_class"):
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"^{re.escape(top_key)}\s*:", ln):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", lines[j]):
            end = j
            break
    return {"text": "\n".join(lines[start:end]), "line_start": start + 1, "line_end": end}


def pairs(names):
    return [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]


def compare_flat(flats: dict, key_order=None):
    """Compare per-schema flat dicts pairwise; return all_equal + witness lists."""
    out = {"all_equal": True, "pairwise": {}}
    names = list(flats)
    for a, b in pairs(names):
        diffs = []
        keys = key_order if key_order is not None else sorted(set(flats[a]) | set(flats[b]))
        for k in keys:
            va, vb = flats[a].get(k, "<missing>"), flats[b].get(k, "<missing>")
            if va != vb:
                diffs.append({"path": k, a: va, b: vb})
        out["pairwise"][f"{a}_vs_{b}"] = {"n_diffs": len(diffs), "witnesses": diffs}
        if diffs:
            out["all_equal"] = False
    return out


def main() -> dict:
    before = {name: sha256_file(ROOT / rel) for name, rel in INPUTS.items()}
    docs = {name: load_yaml(ROOT / rel) for name, rel in INPUTS.items()}
    lines = {name: line_map(ROOT / INPUTS[name]) for name in SCHEMA_KEYS}
    texts = {name: (ROOT / INPUTS[name]).read_text() for name in SCHEMA_KEYS}

    dc = {name: docs[name]["data_class"] for name in SCHEMA_KEYS}

    # ---- T0 : raw block ----
    blocks = {name: raw_block(texts[name]) for name in SCHEMA_KEYS}
    t0 = {"all_equal": True, "pairwise": {}}
    for a, b in pairs(SCHEMA_KEYS):
        ta, tb = blocks[a]["text"], blocks[b]["text"]
        diff_lines = list(difflib.unified_diff(ta.splitlines(), tb.splitlines(), lineterm=""))
        entry = {
            "equal": ta == tb,
            "n_diff_lines": len([d for d in diff_lines
                                 if d[:1] in ("+", "-") and not d.startswith(("+++", "---"))]),
            "first_diff_line_in_" + a: None,
        }
        if ta != tb:
            t0["all_equal"] = False
            for i, (la, lb) in enumerate(zip(ta.splitlines(), tb.splitlines())):
                if la != lb:
                    entry["first_diff_line_in_" + a] = blocks[a]["line_start"] + i
                    entry["first_diff_pair"] = {a: la, b: lb}
                    break
        t0["pairwise"][f"{a}_vs_{b}"] = entry
    t0["blocks"] = {
        name: {
            "path": INPUTS[name],
            "line_start": blocks[name]["line_start"],
            "line_end": blocks[name]["line_end"],
            "sha256": hashlib.sha256(blocks[name]["text"].encode()).hexdigest(),
        }
        for name in SCHEMA_KEYS
    }

    # ---- T1 : canonical JSON of the full subtree ----
    t1_flat = {name: {p: norm_strict(v) for p, v in walk_leaves(dc[name])} for name in SCHEMA_KEYS}
    t1 = compare_flat(t1_flat)
    for a, b in pairs(SCHEMA_KEYS):
        for w in t1["pairwise"][f"{a}_vs_{b}"]["witnesses"]:
            w["line"] = {a: lines[a].get("data_class." + w["path"]),
                         b: lines[b].get("data_class." + w["path"])}

    # ---- T2 : pre-registered CORE_KEYS, strict ----
    t2_flat, missing, core_table, dropped = {}, {}, {}, {}
    for name in SCHEMA_KEYS:
        flat, miss = {}, []
        for k in CORE_KEYS:
            found, val = dig(dc[name], k)
            if not found:
                miss.append(k)
                flat[k] = "<missing>"
            else:
                flat[k] = norm_strict(val)
        t2_flat[name], missing[name] = flat, miss
    for k in CORE_KEYS:
        row = {name: t2_flat[name][k] for name in SCHEMA_KEYS}
        row["equal_T2"] = len(set(row[n] for n in SCHEMA_KEYS)) == 1
        t3_row = {}
        for name in SCHEMA_KEYS:
            found, val = dig(dc[name], k)
            nv, dr = norm_core(val) if found else ("<missing>", [])
            t3_row[name] = nv
            if dr:
                dropped.setdefault(name, {})[k] = dr
        row["equal_T3"] = len(set(t3_row[n] for n in SCHEMA_KEYS)) == 1
        row["T3_values"] = t3_row
        core_table[k] = row
    t2 = compare_flat(t2_flat, key_order=CORE_KEYS)
    t2["missing_core_keys"] = missing

    # ---- T3 : normalized core ----
    t3_flat = {name: {k: core_table[k]["T3_values"][name] for k in CORE_KEYS} for name in SCHEMA_KEYS}
    t3 = compare_flat(t3_flat, key_order=CORE_KEYS)

    # ---- controls ----
    ext = {}
    for name in SCHEMA_KEYS:
        found, val = dig(docs[name], "regularity.extension_regularity")
        ext[name] = norm_strict(val) if found else "<missing>"
    controls = {
        "sensitivity_positive": {
            "description": "regularity.extension_regularity must differ between F2a (C2) and F2b (C0)",
            "values": ext,
            "pass": ext["F2a"] != ext["F2b"] and ext["F2a"] == "C2" and ext["F2b"] == "C0",
        },
        "self_equality_negative": {
            "description": "F1 vs F1 must be equal at every tier",
            "T1_pass": compare_flat({"F1": t1_flat["F1"], "F1b": t1_flat["F1"]})["all_equal"],
            "T2_pass": compare_flat({"F1": t2_flat["F1"], "F1b": t2_flat["F1"]}, key_order=CORE_KEYS)["all_equal"],
            "T3_pass": compare_flat({"F1": t3_flat["F1"], "F1b": t3_flat["F1"]}, key_order=CORE_KEYS)["all_equal"],
        },
        "projection_non_vacuity": {
            "description": "every CORE_KEY must resolve in every schema",
            "missing": missing,
            "pass": all(not v for v in missing.values()),
        },
    }

    # ---- F0 binding ----
    f0b = {}
    for name in SCHEMA_KEYS:
        found, val = dig(docs[name], "f0_binding")
        declared = (val or {}).get("declared_f0_sha256") if isinstance(val, dict) else None
        f0b[name] = {
            "declared_f0_artifact": (val or {}).get("declared_f0_artifact") if isinstance(val, dict) else None,
            "declared_f0_sha256": declared,
            "matches_F0_canonical": declared == before["F0_canonical"],
            "matches_F0_authoring": declared == before["F0_authoring"],
            "class_contract_pointer": docs[name].get("class_contract_pointer"),
        }

    # ---- claims under test ----
    tax_c = docs["F0_canonical"]
    tax_a = docs["F0_authoring"]
    guard = None
    try:
        guard = tax_c["transfer_rules"]["allowed"][0]["guards"][0]
    except Exception:
        pass

    def find_key(obj, target, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == target:
                    return f"{prefix}.{k}" if prefix else k, v
                got = find_key(v, target, f"{prefix}.{k}" if prefix else k)
                if got:
                    return got
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                got = find_key(v, target, f"{prefix}[{i}]")
                if got:
                    return got
        return None

    freeze = find_key(tax_a, "data_class_freeze")
    claims = {
        "canonical_transfer_T1_guard": {
            "source": "research_map/formulation_taxonomy.yaml#transfer_rules.allowed[0].guards[0]",
            "text": guard,
        },
        "authoring_data_class_freeze": {
            "source": "artifacts/formulation/formulation_taxonomy.yaml#" + (freeze[0] if freeze else "data_class_freeze (not found)"),
            "text": freeze[1] if freeze else None,
        },
        "map_G_FORM_unmet_item": {
            "source": "research_map/research_map.json#gates[gate_id=G-FORM].unmet",
            "text": "no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, which disables the licensed C0=>C2 transfer",
        },
    }

    # ---- hash stability ----
    after = {name: sha256_file(ROOT / rel) for name, rel in INPUTS.items()}
    stability = {
        name: {
            "path": INPUTS[name],
            "sha256_before": before[name],
            "sha256_after": after[name],
            "revision_moved": before[name] != after[name],
        }
        for name in INPUTS
    }

    verdict = {
        "T0_raw_block_shared": t0["all_equal"],
        "T1_canonical_json_shared": t1["all_equal"],
        "T2_core_keys_strict_shared": t2["all_equal"],
        "T3_core_keys_normalized_shared": t3["all_equal"],
        "measurement_valid": (not any(v["revision_moved"] for v in stability.values()))
        and controls["sensitivity_positive"]["pass"]
        and controls["projection_non_vacuity"]["pass"],
    }
    if not verdict["measurement_valid"]:
        verdict["summary"] = "MEASUREMENT INVALID: hash drift or control failure; see controls/hash_stability."
    elif verdict["T1_canonical_json_shared"]:
        verdict["summary"] = (
            "At the measured hashes the three data_class subtrees are canonically equal: the shared "
            "data-class claim is confirmed and the G-FORM unmet item is refuted at these hashes."
        )
    elif verdict["T2_core_keys_strict_shared"]:
        verdict["summary"] = (
            "data_class subtrees differ at T1 (annotation/extra keys) but the pre-registered CORE_KEYS "
            "compare equal at T2: the mathematical data class is shared at T2, the exact-match T1 guard "
            "is not satisfied."
        )
    elif verdict["T3_core_keys_normalized_shared"]:
        verdict["summary"] = (
            "data_class differs at T1 and at strict T2, but the pre-registered CORE_KEYS compare equal "
            "after the declared T3 normalization (parenthetical/post-semicolon text dropped). The "
            "mathematical core is shared only under that normalization; the exact-match T1 guard is "
            "not satisfied at these hashes."
        )
    else:
        verdict["summary"] = (
            "data_class differs at every tier including the declared T3 normalization; the witness "
            "list in T2/T3 is the decisive evidence and the shared-data-class claim fails."
        )

    result = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "generated_at": now(),
        "generator": "artifacts/worker-071/dataclass_alignment/audit.py",
        "method_preregistration": "artifacts/worker-071/dataclass_alignment/method.json",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": [CLASS_OF[n] for n in SCHEMA_KEYS],
        "gate": "G-FORM",
        "inputs": stability,
        "claims_under_test": claims,
        "comparison": {
            "T0_raw_block": t0,
            "T1_canonical_json": t1,
            "T2_core_keys_strict": t2,
            "T3_core_keys_normalized": t3,
        },
        "core_key_table": core_table,
        "dropped_fragments": dropped,
        "controls": controls,
        "f0_binding": f0b,
        "verdict": verdict,
        "falsifier": FALSIFIER,
        "limitations": LIMITATIONS,
        "authority_note": "Measurement only; no gate verdict, no node status, no validation_status=passed.",
    }
    (HERE / "dataclass_alignment.json").write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    # ---- README ----
    def wl(pair, tier):
        return result["comparison"][tier]["pairwise"][pair]["witnesses"]

    md = []
    md.append("# FORM-DC-ALIGN-071 -- data_class alignment across F1/F2a/F2b\n")
    md.append(f"Generated {result['generated_at']} by `audit.py` (hash in `report.json`). "
              "Measurement only: no gate verdict, no node status.\n")
    md.append("## Verdict\n")
    md.append(f"- measurement_valid: **{verdict['measurement_valid']}**")
    md.append(f"- T0 raw block shared: **{verdict['T0_raw_block_shared']}**")
    md.append(f"- T1 canonical-JSON shared: **{verdict['T1_canonical_json_shared']}**")
    md.append(f"- T2 pre-registered core keys, strict: **{verdict['T2_core_keys_strict_shared']}**")
    md.append(f"- T3 core keys, declared normalization: **{verdict['T3_core_keys_normalized_shared']}**")
    md.append(f"\n{verdict['summary']}\n")
    md.append("## T2/T3 witness rows (unequal at T2)\n")
    md.append("| core key | F1 | F2a | F2b | equal T2 | equal T3 |")
    md.append("|---|---|---|---|---|---|")
    for k in CORE_KEYS:
        row = core_table[k]
        if not row["equal_T2"]:
            md.append(f"| `{k}` | {row['F1']} | {row['F2a']} | {row['F2b']} | {row['equal_T2']} | {row['equal_T3']} |")
    md.append("\n## T1 witnesses (first 10)\n")
    for p in ("F1_vs_F2a", "F1_vs_F2b", "F2a_vs_F2b"):
        ws = wl(p, "T1_canonical_json")
        md.append(f"- **{p}**: {len(ws)} differing leaf path(s); first up to 10:")
        for w in ws[:10]:
            md.append(f"  - `{w['path']}`: `{w[ p.split('_vs_')[0] ]}` vs `{w[ p.split('_vs_')[1] ]}`")
    md.append("\n## Measured hashes\n")
    for name in INPUTS:
        md.append(f"- {name} (`{INPUTS[name]}`): `{before[name]}`")
    md.append("\n## Falsifier\n")
    md.append(FALSIFIER + "\n")
    md.append("## Limitations\n")
    for lim in LIMITATIONS:
        md.append(f"- {lim}")
    (HERE / "README.md").write_text("\n".join(md) + "\n")

    # ---- composite report with artifact hashes ----
    files = {
        "method.json": sha256_file(HERE / "method.json"),
        "audit.py": sha256_file(HERE / "audit.py"),
        "dataclass_alignment.json": sha256_file(HERE / "dataclass_alignment.json"),
        "README.md": sha256_file(HERE / "README.md"),
    }
    report = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "created_at": now(),
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": [CLASS_OF[n] for n in SCHEMA_KEYS],
        "gate": "G-FORM",
        "task": "Independent, hash-bound measurement of whether the canonical F1/F2a/F2b data_class "
                "blocks satisfy transfer rule T1's guard 'data_class fields must match exactly'.",
        "artifacts": {k: {"path": f"artifacts/worker-071/dataclass_alignment/{k}", "sha256": v} for k, v in files.items()},
        "result_artifact": "artifacts/worker-071/dataclass_alignment/dataclass_alignment.json#" + files["dataclass_alignment.json"],
        "input_hashes": before,
        "verdict": verdict,
        "key_witnesses": {
            "T1_unequal_paths": sorted({w["path"] for p in t1["pairwise"].values() for w in p["witnesses"]}),
            "T2_unequal_paths": sorted({w["path"] for p in t2["pairwise"].values() for w in p["witnesses"]}),
            "T3_unequal_paths": sorted({w["path"] for p in t3["pairwise"].values() for w in p["witnesses"]}),
        },
        "f0_binding": f0b,
        "falsifier": FALSIFIER,
        "limitations": LIMITATIONS,
        "authority_note": "Measurement only; no gate verdict, no node status, no validation_status=passed.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return report


if __name__ == "__main__":
    out = main()
    print(json.dumps({"task_id": out["task_id"], "verdict": out["verdict"],
                      "artifacts": {k: v["sha256"][:16] for k, v in out["artifacts"].items()}}, indent=2))
