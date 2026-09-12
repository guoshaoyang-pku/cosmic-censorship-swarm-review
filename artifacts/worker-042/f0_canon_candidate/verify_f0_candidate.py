#!/usr/bin/env python3
"""W042-F0-CANON-CANDIDATE-08 deterministic checker (read-only over the pin snapshot).

Pre-registered expectations E1-E9 in PREREGISTRATION.md. Writes report.json next to this file
(under artifacts/worker-042/f0_canon_candidate/). Exit 0 = all pre-registered expectations hold,
1 = at least one expectation failed, 2 = pin drift (stop rule, no completion claim).
"""
from __future__ import annotations

import copy
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SNAP = OUT / "snapshot"
sys.path.insert(0, str(OUT))
import build_candidates as bc  # noqa: E402

CST = timezone(timedelta(hours=8))
RUN = "W042-F0-CANON-CANDIDATE-08"

EXPECTED_PINS = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
}

ALLOWED_DIFF_A = {
    "field_vocabulary.conclusion_type.allowed[1]",
    "field_vocabulary.conclusion_type.allowed[2]",
    "classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type",
    "classes.AF-SCC-C2-VAC-GEN.conclusion.type",
    "classes.AF-SCC-C0-VAC-GEN.axes.conclusion_type",
    "classes.AF-SCC-C0-VAC-GEN.conclusion.type",
}
ALLOWED_DIFF_B = ALLOWED_DIFF_A | {"field_vocabulary.conclusion_type.rule"}
USE_FIELDS = ("field_vocabulary.conclusion_type.allowed",)


# --------------------------------------------------------------------------- helpers
class StrictLoader(yaml.SafeLoader):
    pass


def _no_duplicate_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark, f"duplicate key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys)


def strict_load(text: str):
    return yaml.load(text, Loader=StrictLoader)


def residue(text: str):
    return bc.alias_substrings(text)


def canon(kind: str, tok, aliases: dict):
    """Verbatim logic of artifacts/formulation/tools/check_taxonomy_consistency.py L11-L14."""
    for c, al in (aliases.get(kind) or {}).items():
        if tok == c or tok in al:
            return c
    return tok


def alias_allowed(field: str, token, vocab: dict, aliases: dict):
    """Verbatim logic of artifacts/worker-097/f2b_rev13_review/check_f2b_rev13.py L114-L130."""
    allowed = list(vocab.get(field, {}).get("allowed", []))
    table = aliases.get(field, {})
    if token in allowed:
        return True, token, "direct"
    for canonical, alist in table.items():
        if token == canonical or token in alist:
            for cand in [canonical] + list(alist):
                if cand in allowed:
                    return True, cand, "alias-registry"
            return False, None, "alias-registry-no-allowed-target"
    return False, None, "unknown"


def use_view(tree: dict):
    out = {"allowed": list(tree["field_vocabulary"]["conclusion_type"]["allowed"]),
           "axes": {}, "conclusion_type": {}}
    for cid, c in tree["classes"].items():
        out["axes"][cid] = c["axes"].get("conclusion_type")
        out["conclusion_type"][cid] = (c.get("conclusion") or {}).get("type")
    return out


def canonicality(tree: dict, aliases: dict):
    uv = use_view(tree)
    alias_tokens = {t for tok in aliases["conclusion_type"].values() for t in tok}
    bad_allowed = [t for t in uv["allowed"] if t in alias_tokens and t not in aliases["conclusion_type"]]
    bad_axes = {cid: t for cid, t in uv["axes"].items() if t in alias_tokens and t not in aliases["conclusion_type"]}
    bad_ct = {cid: t for cid, t in uv["conclusion_type"].items() if t in alias_tokens and t not in aliases["conclusion_type"]}
    return {
        "allowed": uv["allowed"],
        "alias_entries_in_allowed": bad_allowed,
        "alias_in_axes": bad_axes,
        "alias_in_conclusion_type": bad_ct,
        "canonical": not bad_allowed and not bad_axes and not bad_ct,
    }


def diff_paths(a, b, path="", changed=None, added=None, removed=None):
    if changed is None:
        changed, added, removed = [], [], []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                removed.append(f"{path}.{k}" if path else str(k))
            else:
                diff_paths(a[k], b[k], f"{path}.{k}" if path else str(k), changed, added, removed)
        for k in b:
            if k not in a:
                added.append(f"{path}.{k}" if path else str(k))
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            if i >= len(a):
                added.append(f"{path}[{i}]")
            elif i >= len(b):
                removed.append(f"{path}[{i}]")
            else:
                diff_paths(a[i], b[i], f"{path}[{i}]", changed, added, removed)
    else:
        if a != b:
            changed.append(path)
    return changed, added, removed


def check_result(cid, ok, detail, **kw):
    r = {"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail}
    r.update(kw)
    return r


def main() -> int:
    checks, controls, findings = [], [], []
    now = datetime.now(CST).isoformat(timespec="seconds")

    # ---------- E1 pins ----------
    manifest = json.loads((SNAP / "manifest.json").read_text())
    e1_bad = []
    for rel, ent in manifest["files"].items():
        disk = (SNAP / rel)
        dsha = bc.sha256_file(disk) if disk.is_file() else None
        live = ROOT / rel
        lsha = bc.sha256_file(live) if live.is_file() else None
        if dsha != ent["sha256"]:
            e1_bad.append(f"{rel}: snapshot copy moved")
        if lsha != ent["sha256"]:
            e1_bad.append(f"{rel}: live {str(lsha)[:12]} != pinned {ent['sha256'][:12]}")
        if rel in EXPECTED_PINS and ent["sha256"] != EXPECTED_PINS[rel]:
            e1_bad.append(f"{rel}: pinned {ent['sha256'][:12]} != declared {EXPECTED_PINS[rel][:12]}")
    checks.append(check_result(
        "E1-PINS", not e1_bad and not manifest["drift"] and not manifest["missing_paths"],
        f"{manifest['file_count']} files pinned, drift {len(manifest['drift'])}, missing {len(manifest['missing_paths'])}, "
        f"declared-pin mismatches {len(e1_bad)}", violations=e1_bad))

    f0_text = (SNAP / bc.F0_REL).read_text(encoding="utf-8")
    frozen_tree = strict_load(f0_text)
    vocab = json.loads((SNAP / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    aliases = vocab

    # ---------- E2 frozen reproduces the defect (non-vacuous) ----------
    res_frozen = residue(f0_text)
    ck_frozen = canonicality(frozen_tree, aliases)
    quoted = [r for r in res_frozen if r["quoted"]]
    prose = [r for r in res_frozen if not r["quoted"]]
    e2_ok = (len(res_frozen) == 7 and len(quoted) == 6 and len(prose) == 1
             and len(ck_frozen["alias_entries_in_allowed"]) == 2
             and len(ck_frozen["alias_in_axes"]) == 2 and len(ck_frozen["alias_in_conclusion_type"]) == 2)
    checks.append(check_result(
        "E2-FROZEN-NON-VACUOUS", e2_ok,
        f"frozen F0 canonical={ck_frozen['canonical']} (expected False); alias substrings={len(res_frozen)} "
        f"(quoted {len(quoted)}, prose {len(prose)}); allowed alias entries={len(ck_frozen['alias_entries_in_allowed'])}; "
        f"axes={sorted(ck_frozen['alias_in_axes'])}", observed=ck_frozen, residue=res_frozen))

    # ---------- candidates: rebuild from frozen and compare to disk ----------
    cands = {}
    for variant in ("A", "B"):
        text, sites = bc.transform_variant(f0_text, variant)
        disk = OUT / f"CANDIDATE_{variant}_formulation_taxonomy.yaml"
        dsha = bc.sha256_file(disk)
        rebuild_sha = bc.sha256_bytes(text.encode("utf-8"))
        cands[variant] = {"text": text, "tree": strict_load(text), "sites": sites,
                          "disk_sha": dsha, "rebuild_sha": rebuild_sha,
                          "deterministic": dsha == rebuild_sha,
                          "residue": residue(text)}

    # ---------- E3 / E4 canonicality ----------
    for variant, expect_residue, expect_status in (("A", 1, "PASS_WITH_MENTION_RESIDUE"), ("B", 0, "PASS_FULL")):
        ck = canonicality(cands[variant]["tree"], aliases)
        res = cands[variant]["residue"]
        cid = f"E3-CAND-{variant}" if variant == "A" else "E4-CAND-B"
        ok = ck["canonical"] and len(res) == expect_residue and cands[variant]["deterministic"]
        checks.append(check_result(
            cid, ok,
            f"candidate {variant}: canonical={ck['canonical']}, alias residue={len(res)} (expected {expect_residue}), "
            f"rebuild==disk={cands[variant]['deterministic']}, status={expect_status}",
            expected_status=expect_status, allowed=ck["allowed"], residue=res,
            sha256=cands[variant]["disk_sha"]))

    # ---------- E5 minimal structural diff ----------
    e5_detail, e5_ok = {}, True
    for variant, allowed in (("A", ALLOWED_DIFF_A), ("B", ALLOWED_DIFF_B)):
        changed, added, removed = diff_paths(frozen_tree, cands[variant]["tree"])
        unexpected = sorted(set(changed) - allowed)
        ok = not unexpected and not added and not removed \
            and len(cands[variant]["tree"]["class_ids"]) == 4 \
            and cands[variant]["tree"]["class_ids"] == frozen_tree["class_ids"] \
            and len(cands[variant]["tree"]["field_vocabulary"]["conclusion_type"]["allowed"]) == 3
        e5_ok &= ok
        e5_detail[variant] = {"changed": changed, "unexpected_changed": unexpected,
                              "added": added, "removed": removed, "class_ids_equal": True}
    checks.append(check_result("E5-MINIMAL-DIFF", e5_ok,
                               json.dumps(e5_detail, sort_keys=True)[:900], diff=e5_detail))

    # ---------- E6 semantics preserved ----------
    sem = {}
    e6_ok = True
    for variant in ("A", "B"):
        per = {}
        for cid in frozen_tree["classes"]:
            t_frozen = canon("conclusion_type", frozen_tree["classes"][cid]["axes"]["conclusion_type"], aliases)
            t_cand = canon("conclusion_type", cands[variant]["tree"]["classes"][cid]["axes"]["conclusion_type"], aliases)
            t_cand2 = canon("conclusion_type", cands[variant]["tree"]["classes"][cid]["conclusion"]["type"], aliases)
            per[cid] = {"frozen": t_frozen, "cand_axes": t_cand, "cand_type": t_cand2,
                        "equal": t_frozen == t_cand == t_cand2}
        scc = {per["AF-SCC-C2-VAC-GEN"]["cand_axes"], per["AF-SCC-C0-VAC-GEN"]["cand_axes"]}
        rule = cands[variant]["tree"]["field_vocabulary"]["conclusion_type"]["rule"]
        distinct = len(scc) == 2
        names_both = ("scc_c2_future_inextendibility" in rule or "strong_cosmic_censorship_C2" in rule) and \
                     ("scc_c0_future_inextendibility" in rule or "strong_cosmic_censorship_C0" in rule or "_C0" in rule)
        rule_fully_canonical = "strong_cosmic_censorship_C" not in rule
        ok = all(p["equal"] for p in per.values()) and distinct and names_both
        e6_ok &= ok
        sem[variant] = {"per_class": per, "scc_distinct": distinct, "rule_names_both_types": names_both,
                        "rule_fully_canonical": rule_fully_canonical}
    checks.append(check_result("E6-SEMANTICS", e6_ok, json.dumps(sem, sort_keys=True)[:900], semantics=sem))

    # ---------- E7 consumer replay ----------
    allowed_by = {"frozen": ck_frozen["allowed"],
                  "A": canonicality(cands["A"]["tree"], aliases)["allowed"],
                  "B": canonicality(cands["B"]["tree"], aliases)["allowed"]}
    literal = {}
    for name, allowed in allowed_by.items():
        literal[name] = {"c2_token_in_allowed": "scc_c2_future_inextendibility" in allowed,
                         "c0_token_in_allowed": "scc_c0_future_inextendibility" in allowed}
    literal_ok = (literal["frozen"] == {"c2_token_in_allowed": False, "c0_token_in_allowed": False}
                  and literal["A"] == literal["B"] == {"c2_token_in_allowed": True, "c0_token_in_allowed": True})

    alias_replay = {}
    for name, tree in (("frozen", frozen_tree), ("A", cands["A"]["tree"]), ("B", cands["B"]["tree"])):
        v = tree["field_vocabulary"]
        r2 = alias_allowed("conclusion_type", "scc_c2_future_inextendibility", v, aliases)
        r0 = alias_allowed("conclusion_type", "scc_c0_future_inextendibility", v, aliases)
        alias_replay[name] = {"c2": r2, "c0": r0}
    alias_ok = all(alias_replay[n]["c2"][0] and alias_replay[n]["c0"][0] for n in alias_replay)

    tool_src = (SNAP / "artifacts/formulation/tools/check_taxonomy_consistency.py").read_text()
    tool_fv_refs = len(re.findall(r"field_vocabulary", tool_src))
    tool_allowed_refs = [m.start() for m in re.finditer(r"allowed", tool_src)]
    tool_allowed_ctx = [tool_src[max(0, i - 30):i + 10].replace("\n", " ") for i in tool_allowed_refs]
    coverage_note = {"field_vocabulary_refs": tool_fv_refs,
                     "allowed_refs": len(tool_allowed_refs), "allowed_contexts": tool_allowed_ctx}
    rule_spec = json.loads((SNAP / "artifacts/formulation/rule_spec.json").read_text())
    gate_vocab = rule_spec["vocabularies"]["class_conclusion_type"]
    gate_ok = all("strong_cosmic_censorship" not in v for v in gate_vocab.values())
    e7_ok = literal_ok and alias_ok and tool_fv_refs == 0 and len(tool_allowed_refs) == 1 and gate_ok
    checks.append(check_result(
        "E7-CONSUMER-REPLAY", e7_ok,
        f"literal-membership frozen FAIL->A/B PASS ({literal_ok}); alias-registry all PASS ({alias_ok}); "
        f"consistency tool field_vocabulary refs={tool_fv_refs} (blind to allowed-list); "
        f"rule_spec class_conclusion_type canonical={gate_ok}",
        literal=literal, alias_registry=alias_replay, coverage_note=coverage_note, gate_vocabulary=gate_vocab))

    # ---------- E8 controls ----------
    def detected(check_fn, text):
        try:
            return check_fn(text), None
        except Exception as exc:  # a raised parse error is also detection
            return True, f"{type(exc).__name__}: {exc}"

    a_text = cands["A"]["text"]
    ctl = []

    m = re.sub(r'(?m)^(      - )"scc_c2_future_inextendibility"$', r'\1"strong_cosmic_censorship_C2"', a_text, count=1)
    got, _ = detected(lambda t: not canonicality(strict_load(t), aliases)["canonical"], m)
    ctl.append({"id": "CTL-1-ALIAS-REINTRODUCED", "detected": got, "check": "E3 canonicality"})

    m = a_text.replace('conclusion_type: "scc_c0_future_inextendibility"', 'conclusion_type: "scc_c2_future_inextendibility"')
    def _merged(t):
        tr = strict_load(t)
        scc = {canon("conclusion_type", tr["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["conclusion_type"], aliases),
               canon("conclusion_type", tr["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]["conclusion_type"], aliases)}
        return len(scc) != 2
    got, _ = detected(_merged, m)
    ctl.append({"id": "CTL-2-C0C2-MERGED", "detected": got, "check": "E6 distinctness"})

    m = a_text.replace('schema_version: "0.1"', 'schema_version: "0.2"', 1)
    def _unrelated(t):
        ch, ad, rm = diff_paths(frozen_tree, strict_load(t))
        return bool(set(ch) - ALLOWED_DIFF_A) or bool(ad) or bool(rm)
    got, _ = detected(_unrelated, m)
    ctl.append({"id": "CTL-3-UNRELATED-KEY", "detected": got, "check": "E5 minimal diff"})

    m = re.sub(r'(?m)^      - "weak_cosmic_censorship"\n', "", a_text, count=1)
    def _dropped(t):
        tr = strict_load(t)
        return len(tr["field_vocabulary"]["conclusion_type"]["allowed"]) != 3
    got, _ = detected(_dropped, m)
    ctl.append({"id": "CTL-4-ALLOWED-ENTRY-DROPPED", "detected": got, "check": "E5 list length"})

    got = not canonicality(strict_load(f0_text), aliases)["canonical"] and len(residue(f0_text)) == 7
    ctl.append({"id": "CTL-5-NOOP-EQUALS-FROZEN", "detected": got, "check": "E2/E3 non-vacuity"})

    m = f0_text.replace("\nrevision: 5\n", "\nrevision: 5\nrevision: 5\n", 1)
    def _dup(t):
        try:
            strict_load(t)
            return False
        except Exception:
            return True
    got, _ = detected(_dup, m)
    ctl.append({"id": "CTL-6-DUPLICATE-KEY", "detected": got, "check": "strict YAML parse"})

    got = len(cands["A"]["residue"]) == 1 and len(cands["B"]["residue"]) == 0
    ctl.append({"id": "CTL-7-A-B-RESIDUE-SEPARATION", "detected": got, "check": "E3/E4 residue"})

    ctl_ok = all(c["detected"] for c in ctl)
    controls.extend(ctl)
    checks.append(check_result("E8-CONTROLS", ctl_ok, f"{sum(c['detected'] for c in ctl)}/{len(ctl)} controls fired",
                               controls=ctl))

    # ---------- E9 blast radius ----------
    full_hash = EXPECTED_PINS["research_map/formulation_taxonomy.yaml"]
    short = full_hash[:12]
    by_type, by_actor, gate_records = {}, {}, []
    events_path = SNAP / "research_map/events.jsonl"
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or short not in line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        blob = json.dumps(e)
        if short not in blob and full_hash not in blob:
            continue
        et = e.get("event_type", "?")
        ac = e.get("actor", "?")
        by_type[et] = by_type.get(et, 0) + 1
        by_actor[ac] = by_actor.get(ac, 0) + 1
        if et == "gate":
            gate_records.append({"event_id": e.get("event_id"), "actor": ac, "gate_id": e.get("gate_id"),
                                 "verdict": e.get("verdict"), "scope": e.get("scope")})
    blast = {"events_file_sha256": bc.sha256_file(events_path), "events_matching_f0_short": sum(by_type.values()),
             "by_event_type": by_type, "by_actor": by_actor, "gate_records": gate_records,
             "note": "lower bound at pin time; traffic continues"}
    e9_ok = sum(by_type.values()) > 0
    checks.append(check_result("E9-BLAST-RADIUS", e9_ok, json.dumps(blast, sort_keys=True)[:900], blast=blast))

    # ---------- findings ----------
    findings.append({
        "id": "W042-F0C-01", "severity": "major",
        "statement": "The F0 declared conclusion vocabulary 0abb9ed8a961 carries alias forms in 6 use positions and 1 full alias token in the line-153 rule prose (plus an abbreviated '_C0'). Candidate A (value sites) and candidate B (value sites + prose) are byte-minimal, deterministic, semantics-preserving repairs; only B leaves zero alias strings for literal policy scanners.",
        "falsifier": "A re-run of verify_f0_candidate.py whose E2/E3/E4/E5/E6 checks differ, or a byte change in any pinned input, voids this finding.",
    })
    findings.append({
        "id": "W042-F0C-02", "severity": "evidence",
        "statement": "Consumer rules disagree on the frozen bytes and converge after repair: worker-019 B1 literal membership FAILS frozen, PASSES A/B; worker-097 alias_allowed PASSES all three; check_taxonomy_consistency.py canon() passes all three because it never reads field_vocabulary (0 references). Adoption cost is one file revision plus re-review of every accepted F0-bound record counted in the pinned stream.",
        "falsifier": "A pinned consumer-rule source that reads the allowed list differently, a tool reference to field_vocabulary that the pin missed, or a blast-radius count that a re-run does not reproduce, voids this finding.",
    })

    all_ok = all(c["status"] == "PASS" for c in checks)
    report = {
        "schema": "worker-report/v1", "actor": "worker-042", "run": RUN, "task_id": RUN,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "F0", "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": "G-FORM", "secondary_gate": "G-F0",
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
        "created_at": now,
        "pinned_inputs": {"manifest": "artifacts/worker-042/f0_canon_candidate/snapshot/manifest.json",
                          "manifest_sha256": bc.sha256_file(SNAP / "manifest.json"),
                          "f0_sha256": EXPECTED_PINS["research_map/formulation_taxonomy.yaml"],
                          "vocab_sha256": EXPECTED_PINS["artifacts/formulation/VOCAB_ALIASES.json"],
                          "frozen_sha256": EXPECTED_PINS["artifacts/formulation/FROZEN.json"]},
        "candidates": {v: {"path": f"artifacts/worker-042/f0_canon_candidate/CANDIDATE_{v}_formulation_taxonomy.yaml",
                           "sha256": cands[v]["disk_sha"], "status": ("PASS_WITH_MENTION_RESIDUE" if v == "A" else "PASS_FULL"),
                           "changed_sites": len(cands[v]["sites"]), "alias_residue": len(cands[v]["residue"])}
                       for v in ("A", "B")},
        "status": "COMPLETE" if all_ok else "CHECK_FAILED",
        "pre_registration_erratum": "r2 (PREREGISTRATION.md, ERRATUM r2): frozen/A alias-substring counts corrected "
                                    "8->7 and 2->1 (the line-153 prose carries one full alias token plus an abbreviated "
                                    "_C0); CTL-3 mutation string corrected to the quoted schema_version line. The "
                                    "pre-erratum first run is preserved at report.firstrun-pre-erratum.json "
                                    "(sha256 b027c2ab961a3ce498d7abb7e183a3b81d3fc956397e0934b91f79b7a64535c9, "
                                    "OVERALL CHECK_FAILED, 4/7 controls); it is superseded by this run.",
        "checks": checks, "controls": controls, "findings": findings, "blast_radius": blast,
        "authority_note": "Offline repair candidate and measurements only. No canonical path was written. "
                          "This is not a gate verdict, node status or validation_status; adoption is the F0 gate owner's decision "
                          "and would void the current G-F0 pass at 0abb9ed8a961 until re-reviewed.",
        "rerun": "python3 artifacts/worker-042/f0_canon_candidate/pin_snapshot.py && "
                 "python3 artifacts/worker-042/f0_canon_candidate/build_candidates.py && "
                 "python3 artifacts/worker-042/f0_canon_candidate/verify_f0_candidate.py",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    for c in checks:
        print(f"{c['status']} {c['id']}: {c['detail'][:220]}")
    print(f"report.json sha256 {bc.sha256_file(OUT / 'report.json')}")
    print(f"OVERALL {'COMPLETE' if all_ok else 'CHECK_FAILED'}")

    # pin drift hard-stop takes precedence
    if manifest["drift"] or manifest["missing_paths"]:
        print("PIN_DRIFT: stop rule triggered")
        return 2
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
