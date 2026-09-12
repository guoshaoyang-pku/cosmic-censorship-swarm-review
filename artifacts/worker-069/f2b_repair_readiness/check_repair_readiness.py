#!/usr/bin/env python3
"""W069-F2B-REPAIR-READINESS-01 — independent repair-readiness triage for F2b.

Question (measurement, not adjudication): the F2b repair candidate announced by
worker-066 as "ready, not landed" (rebased sha256 84b5d3fa...) clears the two
containment defects.  Which of the *recorded* F2b hard-failure predicates at the
live rev13 / FROZEN rev29 pins does it clear, and which remain live?

The checker is written from the governing artifacts, not from any author's tool:
  * defect predicates are re-implemented here from the finding texts in the
    accepted stream (worker-066 H1/H2, worker-075 VOCAB/LARGER, worker-090
    W090-VOCAB-01/-04, worker-069 HF-069RC-1/B4 and -2/B2, worker-095 HF-05-01,
    worker-015 F-015-05);
  * the candidate is reconstructed from the live bytes plus the byte-exact
    -/+ pairs of the pinned patch, then hash-checked against 84b5d3fa;
  * every predicate is measured on live bytes, on candidate bytes, and on
    pre-registered mutation controls;
  * the containment-denial predicate is measured twice, naive and
    assertion-aware, because the candidate repair retains the old denial as a
    quoted mention inside a bracketed repair note (the project's CF-16
    mention-vs-assertion pattern).

Read-only w.r.t. all canonical paths.  Writes only under this artifact directory.
No gate verdict, no node status, no validation_status promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

# --------------------------------------------------------------------------
# Pins recorded before the run (falsifier: any move voids the binding).
# --------------------------------------------------------------------------
PINS = {
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/evidence/semantic_escape_rebased.json":
        "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
    "artifacts/formulation/tools/run_acceptance.py":
        "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff":
        "d777a8cb84aa7689cd72b0eee767f08486ad07a4d90e28c8f9d6de3be3b77dc7",
}

CANDIDATE_SHA = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"
STALE_CORPUS_BASE = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONTAINMENT_DENIAL = re.compile(r"no\s+containment\s+with", re.IGNORECASE)
SIZE_INVERTED = re.compile(r"strictly\s+larger\s+extension\s+class", re.IGNORECASE)
BRACKET_SPAN = re.compile(r"\[[^\]]*\]")
QUOTED_SPAN = re.compile(r"'[^']*'")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(t: str) -> str:
    return sha256_bytes(t.encode("utf-8"))


def assertion_text(s: str) -> str:
    """Remove bracketed repair notes and quoted spans (mentions, not assertions)."""
    return QUOTED_SPAN.sub("", BRACKET_SPAN.sub("", s))


def conflate_entries(doc) -> list[str]:
    return [s for s in (doc.get("regularity", {}).get("must_not_conflate") or [])
            if isinstance(s, str)]


def p1_naive_hits(doc) -> list[str]:
    return [f"regularity.must_not_conflate[{i}]"
            for i, s in enumerate(conflate_entries(doc))
            if CONTAINMENT_DENIAL.search(s)]


def p1_assertion_hits(doc) -> list[str]:
    return [f"regularity.must_not_conflate[{i}]"
            for i, s in enumerate(conflate_entries(doc))
            if CONTAINMENT_DENIAL.search(assertion_text(s))]


def p2_hits(doc) -> list[str]:
    rows = (doc.get("implication_ledger", {}) or {}).get("forbidden_transfers") or []
    return [f"implication_ledger.forbidden_transfers[{i}].reason"
            for i, row in enumerate(rows)
            if isinstance(row, dict) and isinstance(row.get("reason"), str)
            and SIZE_INVERTED.search(row["reason"])]


class Checker:
    def __init__(self, root: Path, events_snapshot: Path | None = None):
        self.root = root
        self.events_snapshot = events_snapshot
        self.raw: dict = {}
        self.results: list[dict] = []
        self.controls: list[dict] = []
        self.pin_report: list[dict] = []
        self.notes: list[str] = []

    # ---------------- IO helpers ----------------
    def path(self, rel: str) -> Path:
        return self.root / rel

    def read_text(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8")

    def read_json(self, rel: str):
        return json.loads(self.read_text(rel))

    def read_yaml(self, rel: str):
        return yaml.safe_load(self.read_text(rel))

    def record(self, name: str, obj) -> None:
        self.raw[name] = obj

    # ---------------- pin verification ----------------
    def check_pins(self) -> dict:
        out = {}
        for rel, expected in PINS.items():
            p = self.path(rel)
            if not p.exists():
                out[rel] = {"expected": expected, "measured": None, "match": False,
                            "note": "absent"}
                continue
            measured = sha256_bytes(p.read_bytes())
            out[rel] = {"expected": expected, "measured": measured,
                        "match": measured == expected}
        self.record("pins", out)
        self.pin_report = [{"path": k, **v} for k, v in out.items()]
        return out

    # ---------------- candidate reconstruction ----------------
    @staticmethod
    def parse_patch_pairs(diff_text: str) -> list[tuple[str, str]]:
        """Extract byte-exact (-,+) replacement pairs from a unified diff."""
        pairs: list[tuple[str, str]] = []
        old: str | None = None
        for line in diff_text.splitlines():
            if line.startswith("---") or line.startswith("+++"):
                continue
            if line.startswith("-"):
                old = line[1:]
            elif line.startswith("+") and old is not None:
                pairs.append((old, line[1:]))
                old = None
            elif not line.startswith("+"):
                old = None
        return pairs

    def reconstruct_candidate(self) -> dict:
        live = self.read_text("schemas/af_scc_c0_vacuum.yaml")
        diff = self.read_text("artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff")
        pairs = self.parse_patch_pairs(diff)
        cand = live
        applied = []
        for old, new in pairs:
            count = cand.count(old)
            if count != 1:
                raise SystemExit(
                    f"RECONSTRUCTION FAIL: patch pair occurs {count} times (need 1): {old[:80]!r}")
            cand = cand.replace(old, new)
            applied.append({"old_sha256": sha256_text(old), "new_sha256": sha256_text(new),
                            "old_preview": old[:90], "new_preview": new[:90]})
        measured = sha256_text(cand)
        out = {
            "patch_pairs": len(pairs),
            "applied": applied,
            "candidate_sha256": measured,
            "expected_candidate_sha256": CANDIDATE_SHA,
            "match": measured == CANDIDATE_SHA,
            "live_sha256": sha256_text(live),
        }
        self.record("candidate_reconstruction", out)
        if not out["match"]:
            raise SystemExit(
                f"RECONSTRUCTION FAIL: candidate {measured} != announced {CANDIDATE_SHA}")
        raw_dir = self.root / "artifacts/worker-069/f2b_repair_readiness/raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "af_scc_c0_vacuum.repair-candidate.yaml").write_text(cand, encoding="utf-8")
        return out

    # ---------------- predicate bookkeeping ----------------
    def add(self, pid: str, recorded_by: list[str], predicate: str, live: bool,
            candidate: bool, cleared_label: str, survives_label: str,
            baseline_label: str = "BASELINE_OK", detail: str = "") -> None:
        if live and not candidate:
            disposition = cleared_label
        elif live and candidate:
            disposition = survives_label
        else:
            disposition = baseline_label
        self.results.append({
            "predicate_id": pid,
            "recorded_by": recorded_by,
            "predicate": predicate,
            "live_fires": bool(live),
            "candidate_fires": bool(candidate),
            "cleared_by_candidate": bool(live and not candidate),
            "disposition": disposition,
            "detail": detail,
        })

    # ---------------- predicates ----------------
    def run_predicates(self) -> None:
        f2b_live_txt = self.read_text("schemas/af_scc_c0_vacuum.yaml")
        f2b_cand_txt = (self.root / "artifacts/worker-069/f2b_repair_readiness/raw/"
                        "af_scc_c0_vacuum.repair-candidate.yaml").read_text(encoding="utf-8")
        f2b_live = yaml.safe_load(f2b_live_txt)
        f2b_cand = yaml.safe_load(f2b_cand_txt)
        f0 = self.read_yaml("research_map/formulation_taxonomy.yaml")
        registry = self.read_json("artifacts/formulation/VOCAB_ALIASES.json")
        frozen = self.read_json("artifacts/formulation/FROZEN.json")
        evidence = self.read_json("artifacts/formulation/evidence/taxonomy_consistency.json")
        rebased = self.read_json("artifacts/formulation/evidence/semantic_escape_rebased.json")

        live_c0_sha = sha256_text(f2b_live_txt)
        cand_c0_sha = sha256_text(f2b_cand_txt)

        def p1_naive(doc):
            return p1_naive_hits(doc)

        def p1_assertion(doc):
            return p1_assertion_hits(doc)

        # P1a naive text detector
        l1a, c1a = p1_naive(f2b_live), p1_naive(f2b_cand)
        self.add(
            "P1a_containment_denial_naive",
            ["worker-066 W066-R13-F2B-H1", "worker-035 HF-035-R3-01",
             "worker-018 W018-R13-F2B-B1", "worker-044 H1_false_containment_denial",
             "worker-058 F2b stale containment denial", "worker-008 HF-CD-02"],
            "any regularity.must_not_conflate[*] matches /no containment with/i "
            "(no mention/assertion distinction)",
            bool(l1a), bool(c1a), "CLEARED_BY_CANDIDATE", "MENTION_RESIDUE",
            detail=f"live hits={l1a}; candidate hits={c1a} (candidate hit is inside the "
                   f"bracketed repair note, i.e. a quoted mention, not an assertion)")

        # P1b assertion-aware detector
        l1b, c1b = p1_assertion(f2b_live), p1_assertion(f2b_cand)
        self.add(
            "P1b_containment_denial_assertion_aware",
            ["same recorded findings as P1a"],
            "regularity.must_not_conflate[*] matches the denial after removing bracketed "
            "repair notes and quoted spans",
            bool(l1b), bool(c1b), "CLEARED_BY_CANDIDATE", "SURVIVES_CANDIDATE",
            detail=f"live hits={l1b}; candidate hits={c1b}")

        l2, c2 = p2_hits(f2b_live), p2_hits(f2b_cand)
        self.add(
            "P2_inverted_size_premise",
            ["worker-066 W066-R13-F2B-H2", "worker-075 HF-075-F2b-LARGER",
             "worker-047 W047-LFORM01-1", "worker-058 L-FORM-01",
             "worker-097 W097-F2B-HF3", "worker-044 H2_inverted_size_premise",
             "worker-018 W018-R13-F2B-B2", "worker-008 HF-CD-01"],
            "implication_ledger.forbidden_transfers[*].reason matches "
            "/strictly larger extension class/i",
            bool(l2), bool(c2), "CLEARED_BY_CANDIDATE", "SURVIVES_CANDIDATE",
            detail=f"live hits={l2}; candidate hits={c2}")

        allowed = (f0.get("field_vocabulary", {}) or {}).get(
            "conclusion_type", {}).get("allowed", [])
        token_live = f2b_live["conclusion"]["conclusion_type"]
        token_cand = f2b_cand["conclusion"]["conclusion_type"]
        aliases = registry.get("conclusion_type", {})
        canonical_ok = token_live in aliases and bool(set(aliases[token_live]) & set(allowed))
        self.add(
            "P3_conclusion_token_exact_membership",
            ["worker-075 HF-075-F2b-VOCAB", "worker-090 W090-VOCAB-01"],
            "conclusion.conclusion_type not in F0 field_vocabulary.conclusion_type.allowed",
            token_live not in allowed, token_cand not in allowed,
            "CLEARED_BY_CANDIDATE", "SURVIVES_CANDIDATE",
            detail=f"token={token_live!r}; F0 allowed={allowed}; alias-aware membership="
                   f"{'PASS' if canonical_ok else 'FAIL'} under VOCAB_ALIASES.json "
                   f"(registry canonical -> F0-allowed alias); policy={registry.get('policy')!r}")

        live_ref = "vocabulary_aliases_ref" in json.dumps(f2b_live)
        cand_ref = "vocabulary_aliases_ref" in json.dumps(f2b_cand)
        self.add(
            "P4_registry_pointer_absent",
            ["worker-090 W090-VOCAB-04"],
            "schema declares no vocabulary_aliases_ref pointer to the FROZEN-pinned "
            "VOCAB_ALIASES.json while F1 declares one",
            not live_ref, not cand_ref, "CLEARED_BY_CANDIDATE", "SURVIVES_CANDIDATE",
            detail=f"F1 declares vocabulary_aliases_ref=artifacts/formulation/"
                   f"VOCAB_ALIASES.json; F2b live/candidate declared={live_ref}/{cand_ref}")

        gallowed = (f0.get("field_vocabulary", {}) or {}).get(
            "genericity_kind", {}).get("allowed", [])
        gkind = (f2b_live.get("genericity", {}) or {}).get("kind")
        gal = registry.get("genericity_kind", {})
        g_alias_ok = gkind in gal and bool(set(gal[gkind]) & set(gallowed))
        self.add(
            "P5_genericity_kind_exact_membership",
            ["worker-090 W090-VOCAB-01"],
            "genericity.kind not in F0 field_vocabulary.genericity_kind.allowed",
            gkind not in gallowed, gkind not in gallowed,
            "CLEARED_BY_CANDIDATE", "SURVIVES_CANDIDATE",
            detail=f"kind={gkind!r}; F0 allowed={gallowed}; alias-aware membership="
                   f"{'PASS' if g_alias_ok else 'FAIL'}")

        base = rebased.get("base_sha256")
        self.add(
            "P6_acceptance_preflight_stale_base",
            ["worker-069 HF-069RC-1/B4", "worker-081 stale-corpus materiality",
             "worker-075 SF-075-F2b-CORPUS"],
            "semantic_escape_rebased.json base_sha256 != live C0 sha256 "
            "(run_acceptance.py:62 preflight)",
            base != live_c0_sha, base != cand_c0_sha, "CLEARED_BY_CANDIDATE",
            "NON_SCHEMA_BLOCKER",
            detail=f"corpus base={base}; live C0={live_c0_sha[:12]}; candidate C0="
                   f"{cand_c0_sha[:12]}; a schema edit cannot move the corpus pin")

        digests = [k for k, v in evidence.items()
                   if isinstance(v, str) and HEX64.match(v)]
        digest_keys = [k for k in evidence if "sha256" in k.lower() or "digest" in k.lower()]
        declared_ev = (f2b_live.get("f0_binding") or {}).get("consistency_evidence_sha256")
        measured_ev = sha256_bytes(
            self.path("artifacts/formulation/evidence/taxonomy_consistency.json").read_bytes())
        self.add(
            "P7_evidence_not_self_verifying",
            ["worker-069 HF-069RC-2/B2", "worker-044 A2_evidence_not_self_verifying",
             "worker-038 W038-R2LT-F1"],
            "taxonomy_consistency.json embeds no digest of the two trees it compared",
            not (digests or digest_keys), not (digests or digest_keys),
            "CLEARED_BY_CANDIDATE", "NON_SCHEMA_BLOCKER",
            detail=f"declared f0_binding.consistency_evidence_sha256="
                   f"{(declared_ev or '')[:12]} measured={measured_ev[:12]} "
                   f"match={declared_ev == measured_ev} (R4 repaired at rev13); embedded "
                   f"digest keys={digest_keys} 64-hex values={digests}")

        sidecar_rel = "schemas/af_scc_c0_vacuum.yaml.sha256"
        sidecar_p = self.path(sidecar_rel)
        sidecar_val = (sidecar_p.read_text(encoding="utf-8").split()[0]
                       if sidecar_p.exists() else None)
        self.add(
            "P8_stale_c0_sidecar",
            ["worker-015 F-015-05", "worker-054 unpinned auxiliary inputs"],
            "schemas/af_scc_c0_vacuum.yaml.sha256 != live C0 sha256",
            sidecar_val != live_c0_sha, sidecar_val != cand_c0_sha,
            "CLEARED_BY_CANDIDATE", "NON_SCHEMA_BLOCKER",
            detail=f"sidecar={str(sidecar_val)[:12]}; live={live_c0_sha[:12]}")

        # P9 FROZEN pin announcements, strict rule: an artifact event whose declared
        # sha256 field equals the pin (worker-095 HF-05-01/02).
        files = frozen.get("files", {})
        if isinstance(files, list):
            files = {f.get("path"): f.get("sha256") for f in files if isinstance(f, dict)}
        pins = {}
        for rel in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                    "schemas/af_scc_c0_vacuum.yaml",
                    "research_map/formulation_taxonomy.yaml"):
            pin = files.get(rel)
            pin = pin.get("sha256") if isinstance(pin, dict) else pin
            pins[rel] = pin
        declared_artifacts: dict[str, list[str]] = {}
        any_mention: dict[str, int] = {rel: 0 for rel in pins}
        # Snapshot the accepted stream so P9 is reproducible: the live file grows
        # with traffic and would otherwise make the run digest time-dependent.
        # --events-snapshot replays a previously recorded snapshot instead.
        if self.events_snapshot is not None:
            events_text = self.events_snapshot.read_text(encoding="utf-8")
            snapshot_source = str(self.events_snapshot)
        else:
            events_text = self.read_text("research_map/events.jsonl")
            snapshot_source = "research_map/events.jsonl"
        snapshot_rel = ("artifacts/worker-069/f2b_repair_readiness/raw/"
                        "events.snapshot.jsonl")
        snapshot_path = self.root / snapshot_rel
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(events_text, encoding="utf-8")
        self.raw["events_snapshot"] = {
            "source": snapshot_source,
            "snapshot": snapshot_rel,
            "sha256": sha256_text(events_text),
            "bytes": len(events_text.encode("utf-8")),
            "lines": len(events_text.splitlines()),
        }
        for line in events_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict):
                continue
            for rel, pin in pins.items():
                if not pin:
                    continue
                if pin in line:
                    any_mention[rel] += 1
                if e.get("event_type") == "artifact" and e.get("sha256") == pin:
                    declared_artifacts.setdefault(rel, []).append(e.get("event_id"))
        ann = {rel: {"pin": pins[rel],
                     "declared_by_artifact_event": declared_artifacts.get(rel, []),
                     "announced": bool(declared_artifacts.get(rel)),
                     "raw_text_mentions": any_mention[rel]} for rel in pins}
        unannounced = [rel for rel, v in ann.items() if not v["announced"]]
        self.add(
            "P9_frozen_pins_unannounced",
            ["worker-095 HF-05-01", "worker-095 HF-05-02"],
            "FROZEN rev29 manifest pins with no artifact event declaring that sha256 "
            "(raw text mentions do not count)",
            bool(unannounced), bool(unannounced), "CLEARED_BY_CANDIDATE",
            "NON_SCHEMA_BLOCKER",
            detail=f"unannounced={unannounced}; census="
                   f"{ {k: {'announced': v['announced'], 'mentions': v['raw_text_mentions']} for k, v in ann.items()} }")

        def strict_load(txt):
            dups: list = []

            class StrictLoader(yaml.SafeLoader):
                pass

            def construct_mapping(loader_, node, deep=False):
                mapping = {}
                for key_node, value_node in node.value:
                    key = loader_.construct_object(key_node, deep=deep)
                    if key in mapping:
                        dups.append(key)
                    mapping[key] = loader_.construct_object(value_node, deep=deep)
                return mapping

            StrictLoader.add_constructor(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
            return yaml.load(txt, Loader=StrictLoader), dups

        _, live_dups = strict_load(f2b_live_txt)
        _, cand_dups = strict_load(f2b_cand_txt)
        self.add(
            "P10_structural_parse_and_dup_keys", ["positive control"],
            "target parses and carries no duplicate mapping keys",
            bool(live_dups), bool(cand_dups), "CLEARED_BY_CANDIDATE",
            "SURVIVES_CANDIDATE", baseline_label="STRUCTURAL_BASELINE_OK",
            detail=f"live dups={live_dups}; candidate dups={cand_dups}")

        self.record("predicates", self.results)

    # ---------------- controls ----------------
    def run_controls(self) -> None:
        f2b_cand_txt = (self.root / "artifacts/worker-069/f2b_repair_readiness/raw/"
                        "af_scc_c0_vacuum.repair-candidate.yaml").read_text(encoding="utf-8")
        live_txt = self.read_text("schemas/af_scc_c0_vacuum.yaml")
        f1 = self.read_yaml("schemas/af_wcc_vacuum.yaml")
        f2a = self.read_yaml("schemas/af_scc_c2_vacuum.yaml")
        f0 = self.read_yaml("research_map/formulation_taxonomy.yaml")
        allowed = (f0.get("field_vocabulary", {}) or {}).get(
            "conclusion_type", {}).get("allowed", [])

        def ctl(cid, expectation, observed, ok, detail=""):
            self.controls.append({"control_id": cid, "expectation": expectation,
                                  "observed": observed, "pass": bool(ok),
                                  "detail": detail})

        live = yaml.safe_load(live_txt)
        cand = yaml.safe_load(f2b_cand_txt)

        # C1: live bytes fire the assertion-aware P1b and P2 (positive control)
        ctl("C1-live-fires-P1bP2", "live fires P1b and P2",
            {"P1b": p1_assertion_hits(live), "P2": p2_hits(live)},
            bool(p1_assertion_hits(live)) and bool(p2_hits(live)))

        # C2: candidate clears P1b and P2, but still trips the naive P1a (mention)
        ctl("C2-candidate-mention-discrimination",
            "candidate fires P1a on the quoted mention, clears P1b and P2",
            {"P1a": p1_naive_hits(cand), "P1b": p1_assertion_hits(cand),
             "P2": p2_hits(cand)},
            bool(p1_naive_hits(cand)) and not p1_assertion_hits(cand)
            and not p2_hits(cand))

        # C3: re-inserting the denial as an assertion (outside the bracket) re-fires P1b
        mut1 = f2b_cand_txt.replace(
            "was wrong]", "was wrong]. No containment with C2 or C0 is asserted here.")
        ctl("C3-mutation-refires-P1b", "asserted denial re-fires P1b",
            {"P1b": p1_assertion_hits(yaml.safe_load(mut1))},
            bool(p1_assertion_hits(yaml.safe_load(mut1)))
            and not p1_assertion_hits(cand))

        # C4: re-inserting the inverted premise re-fires P2
        mut2 = f2b_cand_txt.replace(
            "C2 is a strictly smaller extension class",
            "C2 is a strictly larger extension class")
        ctl("C4-mutation-refires-P2", "inverted premise re-fires P2",
            {"P2": p2_hits(yaml.safe_load(mut2))},
            bool(p2_hits(yaml.safe_load(mut2))) and not p2_hits(cand))

        # C5: the exact-membership test discriminates -- F1's token is allowed
        ctl("C5-exact-membership-discriminates",
            "F1 conclusion token passes exact membership while F2a/F2b fail",
            {"F1": f1["conclusion"]["conclusion_type"] in allowed,
             "F2a": f2a["conclusion"]["conclusion_type"] in allowed,
             "F2b": yaml.safe_load(f2b_cand_txt)["conclusion"]["conclusion_type"] in allowed},
            f1["conclusion"]["conclusion_type"] in allowed
            and f2a["conclusion"]["conclusion_type"] not in allowed)

        # C6: patch-pair uniqueness (reconstruction soundness)
        diff = self.read_text("artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff")
        pairs = self.parse_patch_pairs(diff)
        uniq = all(live_txt.count(o) == 1 for o, _ in pairs)
        ctl("C6-patch-pairs-unique", "each patch pair occurs exactly once in live bytes",
            {"pairs": len(pairs), "unique": uniq}, uniq and len(pairs) == 2)

        # C7: assertion-aware stripping is non-vacuous on the live bytes
        ctl("C7-stripping-non-vacuous",
            "assertion-aware stripping removes quoted/bracketed spans but leaves the "
            "live denial detectable",
            {"live_naive": p1_naive_hits(live),
             "live_assertion_aware": p1_assertion_hits(live),
             "candidate_assertion_aware": p1_assertion_hits(cand)},
            bool(p1_assertion_hits(live)) and not p1_assertion_hits(cand))

        self.record("controls", self.controls)

    # ---------------- finalize ----------------
    def finalize(self) -> dict:
        pins_after = {}
        for rel, expected in PINS.items():
            p = self.path(rel)
            pins_after[rel] = sha256_bytes(p.read_bytes()) if p.exists() else None
        stable = all(pins_after[rel] == PINS[rel] for rel in PINS)
        self.controls.append({
            "control_id": "C8-pins-stable-entry-exit",
            "expectation": "all pinned inputs byte-identical at exit",
            "observed": stable, "pass": bool(stable),
            "detail": {k: (v[:12] if v else None) for k, v in pins_after.items()}})
        cleared = [r["predicate_id"] for r in self.results if r["cleared_by_candidate"]]
        survives = [r["predicate_id"] for r in self.results
                    if r["live_fires"] and not r["cleared_by_candidate"]]
        non_schema = [r["predicate_id"] for r in self.results
                      if r["disposition"] == "NON_SCHEMA_BLOCKER"]
        controls_ok = all(c["pass"] for c in self.controls)
        payload = {
            "task_id": "W069-F2B-REPAIR-READINESS-01",
            "node_id": "F2b",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
            "gate": "G-FORM",
            "verdict": "REPAIR_PARTIAL_RESIDUALS_LIVE",
            "candidate": {
                "path": "artifacts/worker-069/f2b_repair_readiness/raw/"
                        "af_scc_c0_vacuum.repair-candidate.yaml",
                "sha256": CANDIDATE_SHA,
                "source_patch": "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff",
            },
            "pins": {k: {"sha256": v, "match": self.raw["pins"][k]["match"]}
                     for k, v in PINS.items()},
            "reconstruction": self.raw["candidate_reconstruction"],
            "input_snapshots": {"research_map/events.jsonl": self.raw["events_snapshot"]},
            "predicates": self.results,
            "summary": {
                "cleared_by_candidate": cleared,
                "survives_candidate": survives,
                "non_schema_blockers": non_schema,
                "controls_pass": controls_ok,
                "controls_total": len(self.controls),
            },
            "controls": self.controls,
            "falsifier": (
                "Re-run check_repair_readiness.py at the same pins. This triage is falsified if: "
                f"(a) the reconstructed candidate does not hash to {CANDIDATE_SHA}; "
                "(b) P1b or P2 fires on the candidate bytes, or a mutation control stops "
                "discriminating; (c) any predicate recorded cleared_by_candidate=true fires on the "
                "candidate at re-run; (d) the vocabulary status is shown to be exact-membership-"
                "binding by a governing text (moving P3/P5 from alias-inversion to sustained schema "
                "defect) or VOCAB_ALIASES.json is shown non-authoritative; (e) run_acceptance.py "
                "reports ACCEPTANCE: PASS with record.base_sha256 == the live C0 sha256 (P6 "
                "cleared), taxonomy_consistency.json is regenerated carrying the digests of both "
                "compared trees (P7 cleared), schemas/af_scc_c0_vacuum.yaml.sha256 is refreshed to "
                "the live C0 sha256 (P8 cleared), or an artifact event declaring each FROZEN rev29 "
                "schema pin appears in the accepted stream (P9 cleared); or (f) any pinned input "
                "hash moves."
            ),
            "authority": "Worker-level measurement only. No gate verdict, no node status, no "
                         "validation_status promotion, no canonical write.",
        }
        # Digest covers measurement content only (not provenance fields such as
        # whether the event stream was read live or replayed).
        digest_payload = {
            "pins": payload["pins"],
            "candidate": payload["candidate"],
            "reconstruction": payload["reconstruction"],
            "input_snapshots": {
                k: {"snapshot": v["snapshot"], "sha256": v["sha256"]}
                for k, v in payload["input_snapshots"].items()},
            "predicates": payload["predicates"],
            "summary": payload["summary"],
            "controls": payload["controls"],
        }
        payload["run_digest"] = sha256_text(
            json.dumps(digest_payload, sort_keys=True, separators=(",", ":")))
        self.record("payload", payload)
        return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--events-snapshot", default=None,
                    help="replay a recorded events.jsonl snapshot instead of the live stream")
    args = ap.parse_args()

    here = Path(__file__).resolve()
    root = Path(args.root).resolve() if args.root else here.parents[3]
    out_dir = Path(args.out).resolve() if args.out else here.parent
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    events_snapshot = Path(args.events_snapshot).resolve() if args.events_snapshot else None

    c = Checker(root, events_snapshot=events_snapshot)
    c.check_pins()
    c.reconstruct_candidate()
    c.run_predicates()
    c.run_controls()
    payload = c.finalize()

    (raw_dir / "predicates.json").write_text(
        json.dumps(c.results, indent=1, sort_keys=True), encoding="utf-8")
    (raw_dir / "controls.json").write_text(
        json.dumps(c.controls, indent=1, sort_keys=True), encoding="utf-8")
    (raw_dir / "pins_before.json").write_text(
        json.dumps(c.raw["pins"], indent=1, sort_keys=True), encoding="utf-8")
    (out_dir / "report.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")

    print(f"verdict: {payload['verdict']}  run_digest={payload['run_digest'][:16]}")
    print(f"cleared: {payload['summary']['cleared_by_candidate']}")
    print(f"survives: {payload['summary']['survives_candidate']}")
    print(f"controls: {payload['summary']['controls_pass']} "
          f"({payload['summary']['controls_total']})")
    return 0 if payload["summary"]["controls_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
