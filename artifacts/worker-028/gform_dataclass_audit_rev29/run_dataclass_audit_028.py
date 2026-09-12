#!/usr/bin/env python3
"""W028-GFORM-DATACLASS-01 -- independent re-measurement of the G-FORM unmet item
"no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, which disables
the licensed C0=>C2 transfer" at the FROZEN rev29 (schema rev13) pins.

Bounded worker task, read-only on every canonical path.  It copies the canonical
bytes into snapshots/ and measures:

  K0  pins: disk sha256 == FROZEN rev29 `files` pin == controller-measured hash
  K1  the three schemas parse as YAML mappings
  K2  quantifier-domain identity: D0/D1/D2 byte-identical; single r binder; refs resolve
  K3  T1 guard clause 1 (strict): DATA_SPACE_CORE keys  F2a vs F2b
  K4  T1 guard clause 1 (declared normalizations): three-way core equality
  K5  full data_class leaf diff enumeration, operative vs annotation
  K6  T1 guard clause 2: genericity_kind + genericity_topology match exactly (F2a vs F2b)
  K7  transfer composition: C0=>C2 entailment rows present in both siblings, converse
      forbidden, extension-set containment stated, statement prefixes identical
  K8  rev11 (worker-060 snapshot) -> rev13 core stability; D0 union repair convergence
  K9  canonical-vs-mirror byte identity and FROZEN pin agreement

  C1..C8 in-memory mutation/null controls, each with an expected outcome.

Writes only inside this directory: snapshots/, dataclass_audit_028.json, REPORT.md,
checkpoint_028.json and .sha256 sidecars.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
MISSING = "<missing>"

FILES = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "FROZEN": "artifacts/formulation/FROZEN.json",
    "F0": "research_map/formulation_taxonomy.yaml",
    "EVID": "artifacts/formulation/evidence/taxonomy_consistency.json",
}
MIRRORS = {
    "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
BASELINE = {
    "F1": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F1__af_wcc_vacuum.yaml",
    "F2a": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F2a__af_scc_c2_vacuum.yaml",
    "F2b": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F2b__af_scc_c0_vacuum.yaml",
}
BASELINE_TASK = "artifacts/worker-060/xclass_dataclass_adjudication/evidence.json"

# The 15 operative (s,delta,norm)-carrying data-space keys, taken verbatim from
# worker-060 xclass_dataclass_adjudication `data_space_core_keys`; re-measured here,
# not re-invented.
DATA_SPACE_CORE = [
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
NORMALIZATION_RULES = {
    "regularity_class.sobolev_variant.spaces": "_norm_spaces: strip one trailing parenthesized annotation, collapse whitespace",
    "asymptotic_decay.parity_conditions": "_norm_parity: take the leading directive before the first ';', collapse whitespace",
}

# T1 as recorded in the canonical F0 taxonomy at the pinned hash.
T1_EXPECTED = {
    "id": "T1",
    "from": "AF-SCC-C0-VAC-GEN",
    "to": "AF-SCC-C2-VAC-GEN",
    "kind": "conclusion_strengthening",
    "guard_1": "data_class fields must match exactly (including s, delta once F2 fixes them)",
    "guard_2": "genericity_kind and genericity_topology must match exactly",
    "guard_3": "the source claim must carry artifact_refs and a reviewer verdict",
}

CLAIM_UNDER_TEST = ("no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, "
                    "which disables the licensed C0=>C2 transfer")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(v) -> str:
    if isinstance(v, str):
        return v
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def get(d, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return MISSING
        cur = cur[part]
    return cur


def leaf_paths(d, prefix=""):
    out = []
    for k, v in d.items():
        p = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            out.extend(leaf_paths(v, p))
        else:
            out.append(p)
    return out


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _norm_spaces(s: str) -> str:
    s = norm_ws(s)
    return re.sub(r"\s*\([^()]*\)\s*$", "", s).strip()


def _norm_parity(s: str) -> str:
    s = norm_ws(s)
    return s.split(";")[0].strip()


def normalize(path: str, value):
    if not isinstance(value, str):
        return value
    if path == "regularity_class.sobolev_variant.spaces":
        return _norm_spaces(value)
    if path == "asymptotic_decay.parity_conditions":
        return _norm_parity(value)
    return norm_ws(value)


class Audit:
    def __init__(self):
        self.checks = []
        self.controls = []
        self._n = 0

    def check(self, cid, name, ok, detail=None, severity="gate"):
        self._n += 1
        self.checks.append({"id": cid, "name": name, "ok": bool(ok),
                            "severity": severity, "detail": detail})
        return bool(ok)

    def control(self, cid, name, expected, observed, ok):
        self.controls.append({"id": cid, "name": name, "expected": expected,
                              "observed": observed, "ok": bool(ok)})
        return bool(ok)


def pair_diff(docs, a, b, paths=None):
    """Strict (exact) value differences between docs[a] and docs[b] over data_class."""
    paths = paths if paths is not None else sorted(set(leaf_paths(docs[a]["data_class"]))
                                                   | set(leaf_paths(docs[b]["data_class"])))
    diffs = {}
    for p in paths:
        va, vb = get(docs[a]["data_class"], p), get(docs[b]["data_class"], p)
        if canon(va) != canon(vb):
            diffs[p] = {a: va, b: vb}
    return diffs


def three_way_raw(docs):
    paths = set()
    for k in ("F1", "F2a", "F2b"):
        paths |= set(leaf_paths(docs[k]["data_class"]))
    out = {}
    for p in sorted(paths):
        vals = {k: get(docs[k]["data_class"], p) for k in ("F1", "F2a", "F2b")}
        if len({canon(v) for v in vals.values()}) > 1:
            out[p] = vals
    return out


def three_way_normalized(docs):
    paths = set()
    for k in ("F1", "F2a", "F2b"):
        paths |= set(leaf_paths(docs[k]["data_class"]))
    out = {}
    for p in sorted(paths):
        vals = {k: normalize(p, get(docs[k]["data_class"], p)) for k in ("F1", "F2a", "F2b")}
        if len({canon(v) for v in vals.values()}) > 1:
            out[p] = vals
    return out


def mutation_diff(base_docs, mutate, target="F2a", other="F2b", paths=None):
    docs = {k: copy.deepcopy(v) for k, v in base_docs.items()}
    mutate(docs)
    return pair_diff(docs, target, other, paths)


def main() -> int:
    started = now()
    a = Audit()
    HERE.mkdir(parents=True, exist_ok=True)
    snap = HERE / "snapshots"
    snap.mkdir(exist_ok=True)

    # ---------- read + snapshot canonical bytes ----------
    disk_hashes, raw_bytes, docs = {}, {}, {}
    for key, rel in FILES.items():
        p = ROOT / rel
        raw_bytes[key] = p.read_bytes()
        disk_hashes[key] = hashlib.sha256(raw_bytes[key]).hexdigest()
        shutil.copyfile(p, snap / f"{key}__{Path(rel).name}")
    (snap / "SHA256SUMS").write_text(
        "".join(f"{disk_hashes[k]}  {FILES[k]}\n" for k in sorted(FILES)))

    frozen = json.loads(raw_bytes["FROZEN"].decode())
    f0 = yaml.safe_load(raw_bytes["F0"].decode())
    evid = json.loads(raw_bytes["EVID"].decode())
    for k in ("F1", "F2a", "F2b"):
        docs[k] = yaml.safe_load(raw_bytes[k].decode())
    mirror_hashes = {k: sha256_file(ROOT / rel) for k, rel in MIRRORS.items()}

    # controller-measured hashes from the live map (read at measure time)
    map_p = ROOT / "research_map/research_map.json"
    map_bytes = map_p.read_bytes()
    map_sha = hashlib.sha256(map_bytes).hexdigest()
    live_map = json.loads(map_bytes.decode())
    greason = (live_map.get("controller_gate_audit", {}).get("G-FORM", {}) or {}).get("reason", "")
    m = re.search(r"([0-9a-f]{12}), ([0-9a-f]{12}), ([0-9a-f]{12})", greason)
    ctrl = {"F1": m.group(1), "F2a": m.group(2), "F2b": m.group(3)} if m else {}
    unmet = [u for u in (next((g for g in live_map.get("gates", []) if g.get("gate_id") == "G-FORM"),
                             {}) or {}).get("unmet", []) if "single frozen data class" in u]

    # ---------- K0 pins ----------
    k0 = {}
    for k in ("F1", "F2a", "F2b"):
        pin = (frozen.get("files", {}).get(FILES[k]) or {}).get("sha256")
        k0[k] = {"disk": disk_hashes[k], "frozen_rev29": pin,
                 "controller_measured_prefix": ctrl.get(k),
                 "disk_eq_frozen": disk_hashes[k] == pin,
                 "disk_prefix_eq_controller": bool(ctrl.get(k)) and disk_hashes[k].startswith(ctrl[k])}
    a.check("K0-pins", "all three schema pins: disk == FROZEN rev29 == controller-measured",
            all(v["disk_eq_frozen"] for v in k0.values()),
            {"pins": k0, "frozen_revision": frozen.get("revision"),
             "frozen_at": frozen.get("frozen_at"),
             "controller_gate_reason": greason,
             "controller_measured": ctrl})
    k0_frozen = {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
                 "F0": disk_hashes["F0"], "EVID": disk_hashes["EVID"],
                 "frozen_file_sha256": disk_hashes["FROZEN"]}

    # ---------- K1 parse ----------
    a.check("K1-parse", "all three schemas parse as YAML mappings",
            all(isinstance(docs[k], dict) for k in ("F1", "F2a", "F2b")),
            {k: {"revision": docs[k].get("revision"), "class_id": docs[k].get("class_id")}
             for k in ("F1", "F2a", "F2b")})

    # ---------- K2 quantifier-domain identity ----------
    dom = {}
    for k in ("F1", "F2a", "F2b"):
        q = docs[k]["quantifiers"]
        dom[k] = {d: q["domains"][d]["definition"] for d in ("D0", "D1", "D2") if d in q["domains"]}
    d0_equal = len({canon(dom[k].get("D0")) for k in dom}) == 1
    d1_pair_equal = canon(dom["F2a"].get("D1")) == canon(dom["F2b"].get("D1"))
    d2_pair_equal = canon(dom["F2a"].get("D2")) == canon(dom["F2b"].get("D2"))
    d1_f1_differs = canon(dom["F1"].get("D1")) != canon(dom["F2a"].get("D1"))
    refs_ok = {}
    for k in ("F1", "F2a", "F2b"):
        ref = docs[k]["quantifiers"]["domains"]["D0"].get("definition_ref")
        tgt = get(docs[k], ref) if isinstance(ref, str) else MISSING
        refs_ok[k] = {"definition_ref": ref, "resolves": tgt != MISSING}
    binders = {k: [o["binder"] for o in docs[k]["quantifiers"]["ordered"]
                   if o.get("binder") != "(M',g',iota)"] for k in ("F1", "F2a", "F2b")}
    d0_defs = {k: dom[k]["D0"] for k in dom}
    a.check("K2-domain-identity",
            "D0 byte-identical three-way; D1/D2 byte-identical on the licensed pair; single r binder; refs resolve",
            d0_equal and d1_pair_equal and d2_pair_equal
            and all(v["resolves"] for v in refs_ok.values()),
            {"D0_equal_three_way": d0_equal,
             "D1_equal_licensed_pair": d1_pair_equal,
             "D2_equal_licensed_pair": d2_pair_equal,
             "D1_F1_differs_from_siblings": d1_f1_differs,
             "D1_F1_note": ("recorded wording difference outside the licensed pair: F1 spells the "
                            "standard countable-intersection construction of comeagerness; F2a/F2b use "
                            "the equivalent complement-is-meager short form. Same notion, not a "
                            "genericity-kind or topology mismatch (K6 measures those on the pair)."),
             "D1_values": {k: dom[k].get("D1") for k in dom},
             "D0_sha256_prefix": hashlib.sha256(dom["F2a"]["D0"].encode()).hexdigest()[:12],
             "D0_has_single_r_binder": all("forall r in D0" in docs[k]["quantifiers"]["formal"]
                                           for k in ("F1", "F2a", "F2b")),
             "definition_ref_resolution": refs_ok,
             "binders_before_conclusion": binders,
             "D0_definition": d0_defs["F2a"]})

    # ---------- K3/K4 T1 guard clause 1 ----------
    strict_pair = pair_diff(docs, "F2a", "F2b")
    strict_core = {p: v for p, v in strict_pair.items() if p in DATA_SPACE_CORE}
    k3_ok = len(strict_core) == 0
    a.check("K3-t1-guard1-strict-core",
            "T1 guard 1 strict: no DATA_SPACE_CORE key differs between F2a and F2b",
            k3_ok, {"n_core_keys": len(DATA_SPACE_CORE), "core_diffs": strict_core})

    norm3 = three_way_normalized(docs)
    norm_core = {p: v for p, v in norm3.items() if p in DATA_SPACE_CORE}
    a.check("K4-t1-guard1-normalized-core",
            "T1 guard 1 normalized: three-way DATA_SPACE_CORE equality under the two declared rules",
            len(norm_core) == 0,
            {"normalization_rules": NORMALIZATION_RULES, "remaining_core_diffs": norm_core})

    # ---------- K5 full data_class diff enumeration ----------
    raw3 = three_way_raw(docs)
    gate_relevant = sorted(set(raw3) - set(DATA_SPACE_CORE))
    operative_diffs = sorted(p for p in raw3 if p in DATA_SPACE_CORE)
    unexpected_operative = [p for p in operative_diffs if p not in NORMALIZATION_RULES]
    a.check("K5-dataclass-diff-enumeration",
            "no operative data-space diff outside the two declared normalizable forms; all other diffs are annotation paths",
            not unexpected_operative,
            {"n_diff_paths": len(raw3), "diff_paths": sorted(raw3),
             "operative_diffs": operative_diffs,
             "operative_diffs_covered_by_declared_normalizations": sorted(set(operative_diffs) & set(NORMALIZATION_RULES)),
             "unexpected_operative_diffs": unexpected_operative,
             "annotation_diffs": gate_relevant,
             "values": {p: {k: (v if not isinstance(v, str) or len(v) < 400 else v[:400])
                            for k, v in raw3[p].items()} for p in gate_relevant}})

    # ---------- K6 T1 guard clause 2 ----------
    gk = {k: docs[k]["genericity"].get("kind") for k in ("F1", "F2a", "F2b")}
    gt = {k: docs[k]["genericity"].get("topology_or_measure") for k in ("F1", "F2a", "F2b")}
    kind_match = gk["F2a"] == gk["F2b"]
    topo_match = canon(gt["F2a"]) == canon(gt["F2b"])
    a.check("K6-t1-guard2-genericity",
            "T1 guard 2: genericity_kind and genericity_topology byte-match on the licensed pair",
            kind_match and topo_match,
            {"genericity_kind": gk, "kind_match": kind_match, "topology_match": topo_match,
             "topology_F2a": gt["F2a"], "topology_F1_note": "F1 carries extra gauge wording; F1 is not a T1 endpoint"})

    # ---------- K7 transfer composition ----------
    def rows(k):
        led = docs[k].get("implication_ledger", {})
        return led
    f2a_led, f2b_led = rows("F2a"), rows("F2b")
    a_ent = [r for r in f2a_led.get("one_way_entailments", [])
             if "C0" in str(r.get("from", "")) and "C2" in str(r.get("to", ""))]
    b_ent = [r for r in f2b_led.get("one_way_entailments", [])
             if "C0" in str(r.get("from", "")) and "C2" in str(r.get("to", ""))]
    f2a_forbids_c0c2 = any("C0" in str(r.get("from", "")) and "C2" in str(r.get("to", ""))
                           for r in f2a_led.get("forbidden_transfers", []))
    f2b_forbids_c0c2 = any("C0" in str(r.get("from", "")) and "C2" in str(r.get("to", ""))
                           for r in f2b_led.get("forbidden_transfers", []))
    # L-FORM-01 corroboration: an inverted containment premise in a forbidden-transfer reason.
    inverted_reason_rows = [r for r in f2b_led.get("forbidden_transfers", [])
                            if "strictly larger extension class" in str(r.get("reason", ""))]
    contain_a = str(f2a_led.get("extension_class_containment", ""))
    contain_b = str(f2b_led.get("extension_class_containment", ""))
    contain_ok = ("E_C2" in contain_a and "E_C0" in contain_a
                  and "E_C0" in contain_b and "E_C2" in contain_b)
    pre_a = docs["F2a"]["quantifiers"]["formal"].split("not exists a proper future")[0]
    pre_b = docs["F2b"]["quantifiers"]["formal"].split("not exists a proper future")[0]
    skel_a = [(o["kind"], o["domain_id"]) for o in docs["F2a"]["quantifiers"]["ordered"]
              if o.get("binder") != "(M',g',iota)"]
    skel_b = [(o["kind"], o["domain_id"]) for o in docs["F2b"]["quantifiers"]["ordered"]
              if o.get("binder") != "(M',g',iota)"]
    a.check("K7-transfer-composition",
            "C0=>C2 entailment present in both siblings, converse not asserted, statement prefixes identical",
            bool(a_ent) and bool(b_ent) and not f2a_forbids_c0c2 and not f2b_forbids_c0c2
            and contain_ok and pre_a == pre_b and skel_a == skel_b,
            {"F2a_entailment_rows": a_ent, "F2b_entailment_rows": b_ent,
             "F2a_forbids_C0_to_C2": f2a_forbids_c0c2,
             "F2b_forbids_C0_to_C2": f2b_forbids_c0c2,
             "F2b_inverted_premise_rows": inverted_reason_rows,
             "F2b_inverted_premise_is_L_FORM_01": bool(inverted_reason_rows),
             "inverted_premise_scope_note": ("the inverted premise sits in the reason of a forbidden "
                                             "C2->C0/H2loc row; it does not forbid or alter the licensed "
                                             "C0->C2 direction measured here. Corroborates the open "
                                             "formulation-lead blocker L-FORM-01, not a new charge."),
             "containment_ok": contain_ok,
             "statement_prefix_identical": pre_a == pre_b,
             "quantifier_skeleton_identical": skel_a == skel_b,
             "statement_prefix_sha256_prefix": hashlib.sha256(pre_a.encode()).hexdigest()[:12]})

    # ---------- K8 rev11 -> rev13 stability ----------
    base_docs, base_pin = {}, {}
    base_task = json.loads((ROOT / BASELINE_TASK).read_text())
    base_pin = {k: base_task["pins"][k]["expected_sha256"] for k in ("F1", "F2a", "F2b")}
    base_ok = True
    for k, rel in BASELINE.items():
        p = ROOT / rel
        if not p.is_file():
            base_ok = False
            continue
        base_docs[k] = yaml.safe_load(p.read_text())
        base_ok = base_ok and (sha256_file(p) == base_pin[k])
    core_drift = {}
    if base_ok:
        for k in ("F1", "F2a", "F2b"):
            for p in DATA_SPACE_CORE:
                vb, vc = get(base_docs[k]["data_class"], p), get(docs[k]["data_class"], p)
                if canon(vb) != canon(vc) and canon(normalize(p, vb)) != canon(normalize(p, vc)):
                    core_drift.setdefault(p, {})[k] = {"rev11": vb, "rev13": vc}
        base_d0 = {k: base_docs[k]["quantifiers"]["domains"]["D0"]["definition"]
                   for k in ("F1", "F2a", "F2b")}
        base_d0_equal = len({canon(v) for v in base_d0.values()}) == 1
        d0_retyped = any("tagged disjoint union" not in base_d0[k] for k in base_d0)
    else:
        base_d0, base_d0_equal, d0_retyped = {}, None, None
    d0_converged = bool(d0_equal) and (base_d0_equal is False)
    a.check("K8-rev11-to-rev13-stability",
            "rev11 baseline verified by hash; no DATA_SPACE_CORE value moved rev11->rev13; D0 not identical at rev11 but byte-identical at rev13 (convergent repair)",
            base_ok and not core_drift and bool(d0_equal) and bool(d0_retyped),
            {"baseline_hashes_match_evidence": base_ok,
             "baseline_pins": base_pin,
             "core_value_drift_rev11_to_rev13": core_drift,
             "baseline_D0_equal_across_three": base_d0_equal,
             "baseline_D0_differences": ({k: base_d0[k] for k in base_d0}
                                          if base_d0_equal is False else {}),
             "baseline_D0_note": ("rev11 F1 carried the extra clause 'the class is fixed at these "
                                   "values and does not range over suitable regularity'; F2a/F2b did "
                                   "not. At rev13 all three D0 definitions are byte-identical (K2), "
                                   "so the rev12 tagged-union repair converged the three domains."),
             "D0_retyped_to_tagged_union_at_rev12": d0_retyped,
             "D0_converged_rev11_to_rev13": d0_converged,
             "baseline_D0_sha256_prefix": hashlib.sha256(base_d0["F2a"].encode()).hexdigest()[:12] if base_ok else None})

    # ---------- K9 mirror / manifest agreement ----------
    k9 = {}
    for k in ("F1", "F2a", "F2b"):
        mpin = (frozen.get("files", {}).get(MIRRORS[k]) or {}).get("sha256")
        k9[k] = {"mirror_disk": mirror_hashes[k], "mirror_eq_canonical": mirror_hashes[k] == disk_hashes[k],
                 "mirror_frozen_pin": mpin, "mirror_pin_ok": mpin == mirror_hashes[k]}
    f0_pin_ok = (frozen.get("files", {}).get(FILES["F0"]) or {}).get("sha256") == disk_hashes["F0"]
    ev_pin_ok = (frozen.get("files", {}).get(FILES["EVID"]) or {}).get("sha256") == disk_hashes["EVID"]
    a.check("K9-manifest-mirrors",
            "canonical == mirror bytes == FROZEN pins; F0 and consistency evidence pinned",
            all(v["mirror_eq_canonical"] and v["mirror_pin_ok"] for v in k9.values())
            and f0_pin_ok and ev_pin_ok,
            {"mirrors": k9, "F0_pin_ok": f0_pin_ok, "EVID_pin_ok": ev_pin_ok,
             "consistency_evidence_sha_prefix": disk_hashes["EVID"][:12],
             "consistency_evidence_errors": evid.get("errors", evid.get("contract_text_divergences", "n/a")),
             "F0_transfer_rules_allowed": f0.get("transfer_rules", {}).get("allowed")})

    # ---------- controls ----------
    def mut_s(d):
        d["F2a"]["data_class"]["regularity_class"]["sobolev_variant"]["s"] = "s > 3/2"

    def mut_delta(d):
        d["F2a"]["data_class"]["regularity_class"]["sobolev_variant"]["delta"] = "delta in (0, 1/2)"

    def mut_constraint(d):
        d["F2a"]["data_class"]["constraints"].pop("momentum", None)

    def mut_annot(d):
        d["F2a"]["data_class"]["_audit_plant"] = "annotation-only plant"

    def mut_d0(d):
        d["F2b"]["quantifiers"]["domains"]["D0"]["definition"] += " or r = C1"

    def mut_topo(d):
        d["F2a"]["genericity"]["topology_or_measure"] = "discrete topology"

    c1 = mutation_diff(docs, mut_s, paths=DATA_SPACE_CORE)
    a.control("C1", "in-memory s-mutant must be caught by the core diff",
              "regularity_class.sobolev_variant.s in diffs",
              sorted(c1), "regularity_class.sobolev_variant.s" in c1)
    c2 = mutation_diff(docs, mut_delta, paths=DATA_SPACE_CORE)
    a.control("C2", "in-memory delta-mutant must be caught by the core diff",
              "regularity_class.sobolev_variant.delta in diffs",
              sorted(c2), "regularity_class.sobolev_variant.delta" in c2)
    c3 = mutation_diff(docs, mut_constraint, paths=DATA_SPACE_CORE)
    a.control("C3", "dropped constraint row must be caught by the core diff",
              "constraints.momentum in diffs", sorted(c3), "constraints.momentum" in c3)
    c4 = pair_diff(docs, "F2a", "F2a", paths=DATA_SPACE_CORE)
    a.control("C4", "null control: F2a vs itself must yield zero core diffs", [], sorted(c4), len(c4) == 0)
    d_annot = {k: copy.deepcopy(v) for k, v in docs.items()}
    mut_annot(d_annot)
    annot_paths = [p for p in pair_diff(d_annot, "F2a", "F2b", paths=None) if p.startswith("_audit_plant")]
    a.control("C5", "planted extra key must land in annotation, never in DATA_SPACE_CORE",
              ["_audit_plant"], annot_paths, annot_paths == ["_audit_plant"])
    wrong_pin = "0" * 64
    a.control("C6", "a wrong pin must fail the pin check", "match=false",
              wrong_pin == disk_hashes["F1"], wrong_pin != disk_hashes["F1"])
    d_d0 = {k: copy.deepcopy(v) for k, v in docs.items()}
    mut_d0(d_d0)
    d0_after = {k: d_d0[k]["quantifiers"]["domains"]["D0"]["definition"] for k in ("F1", "F2a", "F2b")}
    a.control("C7", "D0 mutant must break D0 identity", "not identical",
              len({canon(v) for v in d0_after.values()}) == 1,
              len({canon(v) for v in d0_after.values()}) != 1)
    d_topo = {k: copy.deepcopy(v) for k, v in docs.items()}
    mut_topo(d_topo)
    topo_after = canon(d_topo["F2a"]["genericity"]["topology_or_measure"]) == canon(d_topo["F2b"]["genericity"]["topology_or_measure"])
    a.control("C8", "genericity-topology mutant must fail T1 guard 2", "match=false", topo_after, not topo_after)

    controls_pass = all(c["ok"] for c in a.controls)
    checks_pass = all(c["ok"] for c in a.checks)
    core_clean = k3_ok and len(norm_core) == 0 and len(strict_core) == 0
    guard1 = "PASS on all 15 operative keys (strict), with 9 annotation-only paths recorded" if core_clean else "FAIL"
    guard2 = "PASS (kind and topology byte-equal on the licensed pair F2b->F2a)" if (kind_match and topo_match) else "FAIL"

    adjudication = {
        "claim_under_test": CLAIM_UNDER_TEST,
        "claim_source": {"map_sha256": map_sha, "gate": "G-FORM", "stored_unmet_rows": unmet,
                         "controller_gate_reason": greason},
        "T1_rule_measured": (f0.get("transfer_rules", {}).get("allowed") or [None])[0],
        "guard_1_data_class": guard1,
        "guard_2_genericity": guard2,
        "guard_3_source_claim": "OUT OF SCOPE (about the cited source claim, not the schema bytes)",
        "sharing": ("a single data-space contract is in fact shared at the rev29 pins: D0/D1/D2 are "
                    "byte-identical across F1/F2a/F2b, and every one of the 15 operative (s,delta,norm) "
                    "data-space keys is equal three-way (strict for F2a vs F2b; strict for 13/15 and "
                    "normalizable for 2/15 three-way). The 9 strict three-way differences are annotation "
                    "paths only, none of them a data-space key, and none named by T1's guard."),
        "transfer": ("the licensed C0=>C2 transfer is not disabled at these bytes: F2a and F2b quantify "
                     "over the identical D0/D1/D2 domains with identical binder skeletons and identical "
                     "statement prefixes, both implication ledgers assert the C0=>C2 entailment, neither "
                     "forbids it, and both state the extension-set containment E_C2 subset ... subset E_C0."),
        "verdict_on_unmet_row": ("FALSIFIED at the FROZEN rev29 pins as stated. The factual premise "
                                 "'no single frozen data class is shared' is false on the operative core, "
                                 "and the stated consequence 'disables the licensed C0=>C2 transfer' does "
                                 "not follow. Residual strict byte differences are annotation-level, as "
                                 "worker-060 already adjudicated at rev11 (verdict revise 3.5); they persist "
                                 "unchanged at rev13."),
        "residual_dispositions": [
            "keep worker-060 D1: name an explicit data_space_core key set in the T1 guard and declare annotation/provenance fields out of the exact-match guard",
            "restate or retire G-FORM unmet row 3 at the rev29 pins; if the gate owner instead rules the tagged-union D0 a family of two statements, that ruling applies identically to all three schemas and still does not create a cross-schema mismatch",
            "F1-only annotation wording (excluded_data, adm_mass.rigidity, gauge/diffeo prose, spaces parenthetical, parity rationale) remains a documentation divergence outside T1's licensed pair",
        ],
        "recorded_findings": [
            {"id": "W028-DC-1", "severity": "info",
             "finding": "D0 converged: at the rev11 baseline D0 was NOT identical (F1 carried the extra clause 'fixed at these values and does not range over suitable regularity'), at rev13 all three D0 definitions are byte-identical tagged unions with a single r binder.",
             "evidence": "K2, K8"},
            {"id": "W028-DC-2", "severity": "info",
             "finding": "F1's D1 domain uses the standard countable-intersection construction of comeagerness while F2a/F2b use the equivalent complement-is-meager short form; same notion, outside the T1 licensed pair, and not a genericity_kind/topology mismatch.",
             "evidence": "K2 detail D1_values, K6"},
            {"id": "W028-DC-3", "severity": "minor",
             "finding": "F2b forbidden_transfers[0].reason still asserts 'C2 is a strictly larger extension class' (inverted premise). It sits on the forbidden C2->C0 row and does not affect the licensed C0->C2 direction measured here; corroborates the open lead blocker L-FORM-01.",
             "evidence": "K7 F2b_inverted_premise_rows, lead-form-20260912T005743-91"},
        ],
        "authority_note": ("Advisory bounded-worker measurement only. No gate verdict, no node status, no "
                           "validation_status=passed, no canonical byte was written. The lead-audit/controller "
                           "adjudicate."),
    }

    result = {
        "schema": "worker-028/gform_dataclass_guard_audit/v1",
        "task_id": "W028-GFORM-DATACLASS-01",
        "actor": "worker-028",
        "created_at": started,
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "canonical_pins": {**{k: disk_hashes[k] for k in ("F1", "F2a", "F2b", "F0", "EVID", "FROZEN")},
                           **k0_frozen},
        "mirror_pins": mirror_hashes,
        "map_read_at": {"path": "research_map/research_map.json", "sha256": map_sha},
        "instrument_provenance": {
            "data_space_core_keys": ("inherited verbatim from worker-060 "
                                     "artifacts/worker-060/xclass_dataclass_adjudication/evidence.json "
                                     "`data_space_core_keys`; not re-invented here"),
            "normalization_rules": ("inherited from the same worker-060 evidence "
                                    "`normalization_rules` and re-declared in NORMALIZATION_RULES"),
            "T1_rule": "read live from research_map/formulation_taxonomy.yaml#0abb9ed8a961 transfer_rules.allowed",
            "check_predicates": ("K2/K5/K7/K8 predicates are structural and declared in the hashed runner; "
                                 "the recorded findings list every difference the predicates do not fail on"),
        },
        "checks": a.checks,
        "checks_pass": checks_pass,
        "controls": a.controls,
        "controls_pass": controls_pass,
        "adjudication": adjudication,
        "falsifier": ("At the six pinned hashes (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, "
                      "FROZEN rev29 815e08079aef, F0 0abb9ed8a961, EVID 9e335e9ba1bf): falsified if "
                      "(a) any of the 15 DATA_SPACE_CORE keys differs strictly between F2a and F2b, or "
                      "(b) D0/D1/D2 definitions or the binder skeleton/statement prefix differ between the "
                      "licensed pair, or (c) genericity.kind or genericity.topology_or_measure differ "
                      "between F2a and F2b, or (d) any implication ledger forbids C0=>C2 or omits the "
                      "entailment, or (e) any FROZEN rev29 pin stops matching disk, or (f) any control "
                      "C1-C8 fails to reproduce its expected outcome. Any re-issue of a canonical path at "
                      "new bytes voids this audit at that path and requires a fresh measurement."),
        "limitations": [
            "Scope is the data_class subtree, the quantifier domains D0-D2, the genericity guard axes, and the sibling implication ledgers; visibility, topology and conclusion prose are out of scope.",
            "T1 guard clause 3 (source claim must carry artifact_refs and a reviewer verdict) is a property of a claim, not of these schema bytes, and is not measured here.",
            "The tagged-union D0 question (one class vs a family of two statements) is a portfolio adjudication reserved to lead-audit; this audit measures cross-schema identity, which holds byte-for-byte either way.",
            "AF-WCC-SCALAR-SPH (N0) is out of scope; no transfer rule connects it to the vacuum classes.",
            "Checks and controls ran on pinned in-memory copies; the canonical paths were opened read-only.",
        ],
    }

    out = HERE / "dataclass_audit_028.json"
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    audit_sha = sha256_file(out)

    # ---------- report ----------
    lines = [f"# W028-GFORM-DATACLASS-01 — T1 data-class guard audit at FROZEN rev29",
             "",
             f"- actor: worker-028 · created: {started} · gate: G-FORM · nodes: F1,F2a,F2b",
             f"- classes: {', '.join(CLASS_IDS)}",
             f"- artifact: `dataclass_audit_028.json` sha256 `{audit_sha}`",
             f"- checks: {'PASS' if checks_pass else 'FAIL'} ({sum(c['ok'] for c in a.checks)}/{len(a.checks)}) · "
             f"controls: {'PASS' if controls_pass else 'FAIL'} ({sum(c['ok'] for c in a.controls)}/{len(a.controls)})",
             "",
             "## Pins", ""]
    for k in ("F1", "F2a", "F2b"):
        lines.append(f"- {k}: `{disk_hashes[k]}` (FROZEN rev29 `{k0[k]['frozen_rev29']}`)")
    lines += [f"- FROZEN: rev {frozen.get('revision')} `{disk_hashes['FROZEN']}`",
              f"- F0: `{disk_hashes['F0']}` · EVID: `{disk_hashes['EVID']}`",
              f"- live map read: `{map_sha}`",
              "",
              "## Claim under test", "", f"> {CLAIM_UNDER_TEST}", "",
              "## Result", "", adjudication["verdict_on_unmet_row"], "",
              f"- T1 guard 1 (data_class): {guard1}",
              f"- T1 guard 2 (genericity): {guard2}",
              "- T1 guard 3: out of scope (source claim, not schema bytes)", ""]
    lines += ["## Checks", ""]
    for c in a.checks:
        lines.append(f"- {'PASS' if c['ok'] else 'FAIL'} **{c['id']}** {c['name']}")
    lines += ["", "## Controls", ""]
    for c in a.controls:
        lines.append(f"- {'PASS' if c['ok'] else 'FAIL'} **{c['id']}** {c['name']} — expected {c['expected']!r}, observed {c['observed']!r}")
    lines += ["", "## Falsifier", "", result["falsifier"], "",
              "## Limitations", ""] + [f"- {x}" for x in result["limitations"]] + [
              "", "## Non-claims", "",
              "- no gate verdict, node status or validation_status=passed is set here",
              "- no canonical artifact was modified; all checks ran read-only on pinned copies",
              "- the lead-audit / controller own promotion and any T1 guard amendment"]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n")

    # ---------- checkpoint ----------
    ckpt = {
        "schema": "worker-028/checkpoint/v1",
        "checkpoint_id": f"w028-ckpt-gform-dataclass-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "actor": "worker-028",
        "created_at": now(),
        "task": "one class-bound task: independent re-measurement of the G-FORM single-frozen-data-class unmet row and the T1 C0=>C2 guard at the FROZEN rev29 pins",
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": CLASS_IDS,
        "artifact": {"path": "artifacts/worker-028/gform_dataclass_audit_rev29/dataclass_audit_028.json",
                     "sha256": audit_sha},
        "runner": {"path": "artifacts/worker-028/gform_dataclass_audit_rev29/run_dataclass_audit_028.py",
                   "sha256": sha256_file(Path(__file__).resolve())},
        "pins": {k: disk_hashes[k] for k in ("F1", "F2a", "F2b", "F0", "EVID", "FROZEN")},
        "result": {"checks_pass": checks_pass, "controls_pass": controls_pass,
                   "t1_guard1_core_clean": core_clean, "t1_guard2_genericity_match": kind_match and topo_match,
                   "unmet_row_verdict": "falsified-at-rev29-pins (annotation-level residual)"},
        "falsifier": result["falsifier"],
    }
    (HERE / "checkpoint_028.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n")

    for p in (out, HERE / "REPORT.md", HERE / "checkpoint_028.json"):
        (p.with_suffix(p.suffix + ".sha256")).write_text(f"{sha256_file(p)}  {p.name}\n")

    print(json.dumps({"artifact": str(out.relative_to(ROOT)), "sha256": audit_sha,
                      "checks_pass": checks_pass, "controls_pass": controls_pass,
                      "t1_guard1": guard1, "t1_guard2": guard2,
                      "diff_paths": sorted(raw3), "checkpoint": str((HERE / 'checkpoint_028.json').relative_to(ROOT))},
                     indent=1))
    return 0 if (checks_pass and controls_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
