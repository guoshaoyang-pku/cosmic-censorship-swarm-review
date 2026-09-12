#!/usr/bin/env python3
"""W022-EVBIND-GUARD-01 -- durable writer/publish guard for the taxonomy-consistency
evidence-binding regression (G-FORM; classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN + F0/AF-WCC-SCALAR-SPH).

Context.  The three rev12 class schemas declare
    f0_binding.consistency_evidence_sha256 = 675a99d0...
while the canonical path artifacts/formulation/evidence/taxonomy_consistency.json
holds 9e335e9b..., a 495-byte "lean" document that dropped the two input-tree
binding fields.  worker-086 and worker-092 adjudicated the collision and
recommended R2 + a WRITER GUARD (worker-092 README).  This instrument is that
guard: it classifies the live state, independently recomputes the semantic
payload, proves the destructive-writer mechanism in a sandbox, publishes a
bound candidate only under the worker's own path, and proves its own
fail-closed behaviour with negative controls.

READ-ONLY on every canonical path.  Writes only under this directory.
Exit 0 iff the instrument itself is sound (all controls behaved as expected and
no pinned input drifted during the run).  The evidence-state classification and
publish gate are output data, not exit-code conditions.

Usage:  python3 verify_evbind_guard_022.py [--root REPO] [--out OUTDIR]
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2]  # .../artifacts/worker-022/evbind_guard -> repo root

CANON_SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
TREE_A = "research_map/formulation_taxonomy.yaml"          # map taxonomy  (declared F0)
TREE_B = "artifacts/formulation/formulation_taxonomy.yaml"  # lead contract (supplement)
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"
GFORM_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
ALL_CLASSES = GFORM_CLASSES + ["AF-WCC-SCALAR-SPH"]

ARCHIVE_GLOBS = [
    # pre-existing third-party archives first: resolving the declared hash from the
    # worker's own pin would be circular.
    "artifacts/worker-086/gform_rev12/pinned/*.json",
    "artifacts/worker-086/evidence_collision/restore_candidate/*.json",
    "artifacts/worker-092/evbind/pinned/*.json",
    "artifacts/worker-030/evidence_pin_repair/*.json",
    "artifacts/worker-022/evbind_guard/pinned/*.json",
]


def iso(dt):
    return dt.isoformat(timespec="seconds")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


def load_json(p):
    return json.loads(Path(p).read_text())


def load_yaml(p):
    return yaml.safe_load(Path(p).read_text())


class EvidenceGuard:
    def __init__(self, root: Path, out: Path):
        self.root = root
        self.out = out
        self.checks = []
        self.controls = []
        self.run_at = iso(datetime.now(TZ))
        self.pins = {}
        self.observed = {}

    # ---------------------------------------------------------------- helpers
    def check(self, cid, axis, ok, severity, detail):
        self.checks.append(
            {"id": cid, "axis": axis, "ok": bool(ok), "severity": severity, "detail": detail}
        )
        return bool(ok)

    def control(self, cid, expectation, observed_ok, detail):
        passed = bool(observed_ok) == bool(expectation)
        self.controls.append(
            {
                "id": cid,
                "expected_behaviour_observed": passed,
                "expected": expectation,
                "detail": detail,
            }
        )
        return passed

    def pin(self, rel):
        p = self.root / rel
        if not p.exists():
            self.pins[rel] = None
            return None
        h = sha256_file(p)
        self.pins[rel] = h
        return h

    # -------------------------------------------------- 1. declared vs live
    def declared_hashes(self):
        out = {}
        for rel in CANON_SCHEMAS:
            txt = (self.root / rel).read_text()
            m = re.search(r"consistency_evidence_sha256:\s*\"?([0-9a-f]{64})", txt)
            d = re.search(r"declared_f0_sha256:\s*\"?([0-9a-f]{64})", txt)
            c = re.search(r"checked_at:\s*\"?([0-9T:+\-]+)", txt)
            out[rel] = {
                "declared_evidence": m.group(1) if m else None,
                "declared_f0": d.group(1) if d else None,
                "checked_at": c.group(1) if c else None,
            }
        return out

    def resolve_archive(self, target):
        """Return (path, doc) of the first archived copy whose sha256 == target."""
        for g in ARCHIVE_GLOBS:
            for p in sorted(self.root.glob(g)):
                try:
                    b = p.read_bytes()
                except OSError:
                    continue
                if sha256_bytes(b) == target:
                    try:
                        return str(p.relative_to(self.root)), json.loads(b)
                    except Exception:
                        return str(p.relative_to(self.root)), None
        return None, None

    def classify(self, declared, live, archive_path, archive_doc, tree_a, tree_b):
        if declared == live:
            return "BOUND_OK", "declared == measured at the canonical path"
        if archive_path is None:
            return "PHANTOM", "declared hash resolves to no archived byte copy"
        if archive_doc is None:
            return "UNRESOLVED_DOC", "archived copy found but not JSON-parseable"
        ea, eb = archive_doc.get("map_taxonomy_sha256"), archive_doc.get("lead_contract_sha256")
        if ea == tree_a and eb == tree_b:
            return (
                "REGRESSION_UNBOUND",
                "declared revision is archived, carries both tree bindings and its embedded "
                "tree hashes still equal the live trees; the canonical path holds a lean "
                "revision that dropped them",
            )
        return (
            "STALE_DECLARATION",
            f"declared revision archived but embedded trees differ (map {ea} vs live {tree_a}; "
            f"lead {eb} vs live {tree_b})",
        )

    # ------------------------------------------- 2. independent consistency
    def canon(self, kind, tok, aliases):
        if tok is None:
            return None
        for canonical, al in (aliases.get(kind) or {}).items():
            if tok == canonical or tok in al:
                return canonical
        return tok

    def independent_consistency(self, a, b, aliases):
        errs = []
        aid, bid = set(a.get("class_ids") or []), set(b.get("class_contracts") or {})
        if aid != bid:
            errs.append(f"class id sets differ: {sorted(aid)} vs {sorted(bid)}")
        shared = sorted(aid & bid)
        per_class = {}
        for cid in shared:
            ca, cb = a["classes"][cid], b["class_contracts"][cid]
            ax, comp = ca.get("axes") or {}, cb.get("components") or {}
            row = []
            if ax.get("family") != comp.get("censorship"):
                row.append(f"family {ax.get('family')} vs {comp.get('censorship')}")
            ra = ax.get("regularity_token")
            rb = None if comp.get("regularity_token") == "none" else comp.get("regularity_token")
            if ra != rb:
                row.append(f"regularity {ra} vs {rb}")
            ta = self.canon("conclusion_type", ax.get("conclusion_type"), aliases)
            tb = self.canon("conclusion_type", cb.get("conclusion_type"), aliases)
            if ta != tb:
                row.append(f"conclusion_type {ta} vs {tb}")
            if not ca.get("exclusions") or not cb.get("exclusions"):
                row.append("exclusions empty on one side")
            if not ca.get("test_cases") or not cb.get("positive_test_case"):
                row.append("test cases missing on one side")
            if ax.get("family") == "SCC" and not ca.get("known_obstruction"):
                row.append("SCC without known_obstruction")
            ga = self.canon("genericity_kind", ax.get("genericity_kind"), aliases)
            frozen = ((b.get("axis_registry") or {}).get("genericity_axis") or {}).get("frozen") or {}
            gb = self.canon("genericity_kind", frozen.get(cid), aliases)
            if ga != gb:
                row.append(f"genericity {ga} vs {gb}")
            per_class[cid] = row
            errs.extend(f"{cid}: {e}" for e in row)

        # contract-text divergences D1-D3 (metalinguistic revision notes stripped)
        def text(cid):
            t = str((a["classes"].get(cid, {}).get("conclusion") or {}).get("text", ""))
            return re.sub(r"\[[^\]]*\]", " ", t)

        d1 = []
        wcc = text("AF-WCC-VAC-GEN").replace(" ", "")
        if re.search(r"J\^?-?\(I\+\)", wcc):
            d1.append("AF-WCC-VAC-GEN still uses the set-based J-(I+) visibility form")
        if not re.search(r"J\^?-?\(q", wcc):
            d1.append("AF-WCC-VAC-GEN lacks the single-q tail predicate")
        d2 = [c for c in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN") if "future" not in text(c).lower()]
        d3 = [c for c in ALL_CLASSES if "comeager" not in text(c).lower()]
        for c in d1:
            errs.append("D1: " + c)
        for c in d2:
            errs.append(f"D2: {c} does not state future-inextendibility")
        for c in d3:
            errs.append(f"D3: {c} text drops the explicit comeager quantifier")

        # cross-tree entailment rules
        allowed = (a.get("transfer_rules") or {}).get("allowed") or []
        forbidden = (a.get("transfer_rules") or {}).get("forbidden") or []
        ledger = b.get("implication_ledger") or []
        t1 = any(r.get("from") == "AF-SCC-C0-VAC-GEN" and r.get("to") == "AF-SCC-C2-VAC-GEN" for r in allowed)
        x1 = any(
            r.get("from") == "AF-SCC-C2-VAC-GEN" and r.get("to") == "AF-SCC-C0-VAC-GEN"
            for r in forbidden
        ) or any("C2-VAC-GEN -> AF-SCC-C0" in str(r.get("pattern", "")) for r in forbidden)
        li = any(
            r.get("from") == "AF-SCC-C0-VAC-GEN"
            and r.get("to") == "AF-SCC-C2-VAC-GEN"
            and r.get("direction") == "one_way"
            for r in ledger
        )
        if not (t1 and li):
            errs.append("C0 => C2 one-way entailment not recorded on both sides")
        if not x1:
            errs.append("C2 => C0 converse not forbidden in the map taxonomy")
        return {
            "independent_consistent": not errs,
            "independent_errors": errs,
            "per_class": per_class,
            "shared_classes": shared,
            "d1_metalinguistic_mentions": [
                m.group(0) for m in re.finditer(r"J\^?-?\(I\+\)", str((a["classes"].get("AF-WCC-SCALAR-SPH", {}).get("conclusion") or {}).get("text", "")))
            ] if "AF-WCC-SCALAR-SPH" in a.get("classes", {}) else [],
        }

    # -------------------------------------------------- 3. bound candidate
    @staticmethod
    def build_candidate(live_doc, tree_a, tree_b, measured_at):
        semantic_keys = [
            "map_taxonomy",
            "lead_contract",
            "consistent",
            "errors",
            "contract_divergences",
            "notes",
            "classes_compared",
            "alias_policy",
        ]
        cand = {k: live_doc[k] for k in semantic_keys if k in live_doc}
        cand["map_taxonomy_sha256"] = tree_a
        cand["lead_contract_sha256"] = tree_b
        cand["measured_at"] = measured_at
        return cand

    @staticmethod
    def validate_candidate(cand, live_doc, tree_a, tree_b, run_dt):
        problems = []
        if cand.get("map_taxonomy_sha256") != tree_a:
            problems.append("map_taxonomy_sha256 missing or not equal to live tree A")
        if cand.get("lead_contract_sha256") != tree_b:
            problems.append("lead_contract_sha256 missing or not equal to live tree B")
        for k in ("consistent", "errors", "contract_divergences", "classes_compared"):
            if k not in cand:
                problems.append(f"semantic field {k} missing")
            elif live_doc.get(k) != cand.get(k):
                problems.append(f"semantic field {k} differs from the live payload")
        for k, v in cand.items():
            if isinstance(v, str):
                m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00)$", v)
                if m:
                    try:
                        if datetime.fromisoformat(v) > run_dt:
                            problems.append(f"future-dated stamp in {k}: {v}")
                    except ValueError:
                        problems.append(f"unparseable stamp in {k}: {v}")
        return problems

    # -------------------------------------------------- 4. sandbox replay
    def sandbox_replay(self, live_hash, drift):
        sb = self.out / "sandbox"
        checker = sb / "artifacts/formulation/tools/check_taxonomy_consistency.py"
        tree_a = sb / "research_map/formulation_taxonomy.yaml"
        out = sb / "artifacts/formulation/evidence/taxonomy_consistency.json"

        def run():
            return subprocess.run(
                [sys.executable, str(checker)], cwd=str(sb), capture_output=True, text=True
            )

        r = run()
        live_sb = sha256_file(out)
        c1 = live_sb == live_hash
        self.control(
            "C1-pinned-checker-replay",
            True,
            c1,
            f"pinned checker in the sandbox wrote {live_sb[:12]} (exit {r.returncode}); "
            f"live canonical snapshot {live_hash[:12]}",
        )

        # negative control: mutate one class family (targeted, via a YAML round-trip)
        orig = tree_a.read_text()
        doc_a = yaml.safe_load(orig)
        before = doc_a["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]["family"]
        doc_a["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]["family"] = "WCC"
        tree_a.write_text(yaml.safe_dump(doc_a, sort_keys=False))
        rm = run()
        try:
            docm = json.loads(out.read_text())
        except Exception:
            docm = {}
        c2 = rm.returncode == 1 and docm.get("consistent") is False
        self.control(
            "C2-mutant-family-negative-control",
            True,
            c2,
            f"AF-SCC-C0-VAC-GEN axes.family {before}->WCC in the sandbox tree -> exit "
            f"{rm.returncode}, consistent={docm.get('consistent')} "
            "(a PASS on the unmutated tree is therefore meaningful)",
        )
        tree_a.write_text(orig)
        rr = run()
        c3 = sha256_file(out) == live_hash
        self.control("C3-sandbox-restore", True, c3, "restored sandbox reproduces the live snapshot again")
        return c1 and c2 and c3

    # ---------------------------------------------------------------- main
    def run(self):
        now_dt = datetime.now(TZ)

        # -- pins
        for rel in CANON_SCHEMAS + [FROZEN, TREE_A, TREE_B, ALIASES, CHECKER, EVIDENCE]:
            self.pin(rel)
        pins_start = dict(self.pins)

        declared = self.declared_hashes()
        live_hash = self.pins[EVIDENCE]
        tree_a, tree_b = self.pins[TREE_A], self.pins[TREE_B]
        live_doc = load_json(self.root / EVIDENCE)

        # H1 declared identical across the three schemas
        dv = {v["declared_evidence"] for v in declared.values()}
        self.check(
            "H1-declared-evidence-single-valued",
            "declaration census",
            len(dv) == 1 and None not in dv,
            "hard" if len(dv) != 1 else "info",
            f"declared consistency_evidence_sha256 per schema: "
            + ", ".join(f"{Path(k).name}={(v['declared_evidence'] or 'MISSING')[:12]}" for k, v in declared.items()),
        )
        declared_ev = next(iter(dv)) if len(dv) == 1 else None

        # H2 live measurement
        self.check(
            "H2-live-evidence-measured",
            "measurement",
            live_hash is not None,
            "info",
            f"{EVIDENCE} = {live_hash[:12] if live_hash else 'MISSING'} ({len((self.root / EVIDENCE).read_bytes())} B)",
        )

        # H3/H4 classification
        arch_path, arch_doc = (None, None)
        if declared_ev:
            arch_path, arch_doc = self.resolve_archive(declared_ev)
        state, why = self.classify(declared_ev, live_hash, arch_path, arch_doc, tree_a, tree_b)
        self.observed["classification"] = state
        self.observed["classification_reason"] = why
        self.observed["declared_revision_resolves_at"] = arch_path
        self.check(
            "H3-binding-state-classified",
            "declared vs measured",
            state == "BOUND_OK",
            "hard",
            f"state={state}: {why}",
        )
        unbound = not ({"map_taxonomy_sha256", "lead_contract_sha256"} <= set(live_doc.keys()))
        self.check(
            "H4-live-document-is-bound-form",
            "evidence content",
            not unbound,
            "hard",
            f"live doc keys missing tree bindings: "
            f"{sorted({'map_taxonomy_sha256', 'lead_contract_sha256'} - set(live_doc.keys())) or 'none'}",
        )

        # H5 archived declared revision binds the LIVE trees
        if arch_doc:
            self.check(
                "H5-declared-revision-binds-live-trees",
                "binding content",
                arch_doc.get("map_taxonomy_sha256") == tree_a
                and arch_doc.get("lead_contract_sha256") == tree_b,
                "hard",
                f"archived declared doc embedded map={str(arch_doc.get('map_taxonomy_sha256'))[:12]} "
                f"lead={str(arch_doc.get('lead_contract_sha256'))[:12]}; live map={tree_a[:12]} lead={tree_b[:12]}",
            )
        else:
            self.check(
                "H5-declared-revision-binds-live-trees",
                "binding content",
                False,
                "hard",
                "declared revision not found in any pinned archive path",
            )

        # H6 FROZEN pin
        frozen = load_json(self.root / FROZEN)
        fp = ((frozen.get("files") or {}).get(EVIDENCE) or {}).get("sha256")
        self.check(
            "H6-freeze-does-not-pin-an-unbound-revision",
            "freeze binding",
            fp != live_hash or not unbound,
            "hard",
            f"FROZEN rev{frozen.get('revision')} frozen_at={frozen.get('frozen_at')} pins evidence "
            f"{(fp or 'ABSENT')[:12]}; live {(live_hash or 'ABSENT')[:12]} -> the freeze pins the "
            f"{'lean/unbound' if fp == live_hash and unbound else 'bound'} revision",
        )

        # H7 checked_at ordering vs declared doc measured_at
        if arch_doc and arch_doc.get("measured_at"):
            rows = []
            for rel, v in declared.items():
                ca = v.get("checked_at")
                if ca:
                    try:
                        rows.append((rel, datetime.fromisoformat(ca), datetime.fromisoformat(arch_doc["measured_at"])))
                    except ValueError:
                        pass
            if rows:
                # checked_at is stored per-schema (single TS); compare the max
                latest = max(r[1] for r in rows)
                early = latest < min(r[2] for r in rows)
                self.check(
                    "H7-binding-checked-before-declared-evidence-existed",
                    "timestamp ordering",
                    not early,
                    "soft" if early else "info",
                    f"schema checked_at(max)={iso(latest)} vs declared evidence measured_at="
                    f"{arch_doc['measured_at']}"
                    + (" -> the binding was stamped before the revision it names existed" if early else " -> ordered"),
                )

        # -- independent consistency recomputation
        a = load_yaml(self.root / TREE_A)
        b = load_yaml(self.root / TREE_B)
        al = load_json(self.root / ALIASES)
        ic = self.independent_consistency(a, b, al)
        self.observed["independent_consistency"] = ic
        agree = bool(live_doc.get("consistent")) == ic["independent_consistent"] and (
            live_doc.get("contract_divergences") or []
        ) == [] and ic["independent_consistent"]
        self.check(
            "H8-independent-consistency-agrees-with-live-payload",
            "semantic payload",
            agree,
            "hard" if not agree else "info",
            f"independent consistent={ic['independent_consistent']} "
            f"(errors={len(ic['independent_errors'])}); live consistent={live_doc.get('consistent')} "
            f"divergences={live_doc.get('contract_divergences')}",
        )
        self.check(
            "H9-class-coverage",
            "semantic payload",
            set(live_doc.get("classes_compared") or []) == set(ALL_CLASSES),
            "hard",
            f"live classes_compared={live_doc.get('classes_compared')}; expected 4 incl. F0 scalar class",
        )

        # -- bound candidate + round-trip + negative controls
        cand = self.build_candidate(live_doc, tree_a, tree_b, str(frozen.get("frozen_at")))
        cpath = self.out / "candidate/taxonomy_consistency.bound.json"
        cpath.write_text(json.dumps(cand, indent=2) + "\n")
        self.observed["candidate_sha256"] = sha256_file(cpath)
        problems = self.validate_candidate(cand, live_doc, tree_a, tree_b, now_dt)
        self.control("C4-bound-candidate-round-trip", True, not problems, f"problems={problems}")

        n1 = dict(cand)
        n1.pop("map_taxonomy_sha256", None)
        self.control(
            "C5-negative-missing-tree-binding",
            True,
            bool(self.validate_candidate(n1, live_doc, tree_a, tree_b, now_dt)),
            "drop map_taxonomy_sha256 -> guard must refuse",
        )
        n2 = dict(cand)
        n2["lead_contract_sha256"] = "0" * 64
        self.control(
            "C6-negative-mutated-tree-binding",
            True,
            bool(self.validate_candidate(n2, live_doc, tree_a, tree_b, now_dt)),
            "mutate lead_contract_sha256 -> guard must refuse",
        )
        n3 = dict(cand)
        n3["measured_at"] = iso(now_dt + timedelta(hours=1))
        self.control(
            "C7-negative-future-stamp",
            True,
            bool(self.validate_candidate(n3, live_doc, tree_a, tree_b, now_dt)),
            "future measured_at -> guard must refuse",
        )
        phantom_state, _ = self.classify("f" * 64, live_hash, None, None, tree_a, tree_b)
        self.control(
            "C8-negative-phantom-declaration",
            True,
            phantom_state == "PHANTOM",
            f"unknown declared hash classified as {phantom_state} (not REGRESSION)",
        )

        # -- sandbox replay
        self.sandbox_replay(live_hash, None)

        # -- drift
        drift = {}
        for rel, h0 in pins_start.items():
            h1 = sha256_file(self.root / rel) if (self.root / rel).exists() else None
            if h0 != h1:
                drift[rel] = {"start": h0, "end": h1}
        moved = bool(drift)

        controls_ok = all(c["expected_behaviour_observed"] for c in self.controls)
        hard_fail = [c for c in self.checks if c["severity"] == "hard" and not c["ok"]]
        report = {
            "schema_version": "0.1",
            "artifact_kind": "evidence_binding_guard_report",
            "task_id": "W022-EVBIND-GUARD-01",
            "actor": "worker-022",
            "created_at": self.run_at,
            "gate": "G-FORM",
            "node_ids": ["F1", "F2a", "F2b"],
            "class_ids": GFORM_CLASSES,
            "authority": "worker measurement only; no canonical write, no gate verdict, no node status",
            "pins": pins_start,
            "declaration_census": declared,
            "observed": self.observed,
            "checks": self.checks,
            "controls": self.controls,
            "classification": state,
            "publish_gate": "ALLOW" if state == "BOUND_OK" else "BLOCK",
            "instrument_ok": controls_ok and not moved,
            "hard_findings": [c["id"] for c in hard_fail],
            "drift": drift,
            "moved_during_check": moved,
            "falsifier": (
                "Repair the ordering: keep/restore a consistency-evidence revision that carries "
                "map_taxonomy_sha256 and lead_contract_sha256 equal to the live trees at the canonical "
                "path (or re-declare all three schemas to a bound revision) and re-run this guard: "
                "classification becomes BOUND_OK and publish_gate ALLOW, falsifying the REGRESSION "
                "finding. Instrument self-falsifiers: any control C1-C8 not behaving as required, or "
                "any pinned input drifting mid-run, makes this report void rather than falsified."
            ),
            "advisory": (
                "worker-092 R2/R3 remain the repair options; this guard supplies the missing durable "
                "piece: it must be run before any publish step that would write the canonical evidence "
                "path, and it refuses (BLOCK) whenever the canonical document lacks the two tree bindings."
            ),
        }
        rp = self.out / "report.json"
        rp.write_text(json.dumps(report, indent=2) + "\n")
        print(f"classification={state} publish_gate={report['publish_gate']} "
              f"instrument_ok={report['instrument_ok']} hard_findings={report['hard_findings']}")
        print(f"report={rp} sha256={sha256_file(rp)[:12]}")
        return 0 if report["instrument_ok"] else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    return EvidenceGuard(Path(args.root).resolve(), Path(args.out).resolve()).run()


if __name__ == "__main__":
    sys.exit(main())
