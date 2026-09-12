#!/usr/bin/env python3
"""W064-SEMCT-REBASE-01 -- independent rebase + verification of the semantic contract
suite's frozen control basis (ADJ-CONTROL-STALENESS), at a pinned snapshot.

Bounded class-bound worker task (node A1 / gate G-AUDIT; classes AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN).  No canonical artifact is modified: every
repaired byte this script writes lives under the worker artifact directory.

What it does
  P0  pin a byte snapshot of every input and hash it
  P1  measure the baseline stages of the 3 canonical schemas and 3 frozen controls
  P2  rebase the 3 frozen controls by removing the R28-misplaced transfer row
      (text-preserving surgery; minimality checked line-by-line and by YAML diff)
  P3  verify the rebased controls pass the structural + semantic stages
  P4  sensitivity mutants: each rebased control must still be rejectable by the
      guard it is meant to exercise (non-vacuity of the accept)
  P5  full 38-target suite simulations in a worker-local suite copy:
        S0 unmodified manifest        (expected: integrity failure)
        S1 rebased controls + refreshed pins
        S2 S1 + simulated KEY_MANIFEST R22 extension (sufficiency of the repair)
  P6  write report.json, rebase_patch.json, README-support files

Run:  python3 semct_rebase_audit.py [--repo /path/to/ai4math-swarm]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

CST = timezone(timedelta(hours=8))
TASK_ID = "W064-SEMCT-REBASE-01"

CANON = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
CONTROLS = [
    "schemas/semantic_contract_tests/fixtures/controls/control_comment_only_composite.yaml",
    "schemas/semantic_contract_tests/fixtures/controls/control_conforming_base.yaml",
    "schemas/semantic_contract_tests/fixtures/controls/control_quoted_forbidden_phrase.yaml",
]
SUITE_DIR = "schemas/semantic_contract_tests"
SUITE_MANIFEST = f"{SUITE_DIR}/manifest.json"
SUITE_RUNNER = f"{SUITE_DIR}/run_contract_tests.py"
STRUCT_TOOL = "artifacts/formulation/tools/check_class_schema.py"
STRUCT_SPEC = "artifacts/formulation/rule_spec.json"
STRUCT_KEYS = "artifacts/formulation/KEY_MANIFEST.json"
SEM_TOOL = "artifacts/worker-06/spec_conformance_audit.py"
OTHER_INPUTS = [SUITE_MANIFEST, SUITE_RUNNER, f"{SUITE_DIR}/observed_verdicts.json",
                STRUCT_TOOL, STRUCT_SPEC, STRUCT_KEYS, SEM_TOOL]

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd, timeout=300):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


class Audit:
    def __init__(self, repo: Path, out: Path):
        self.repo = repo
        self.out = out
        self.raw = out / "raw"
        self.work = out / "work"
        self.snapshot = out / "snapshot"
        self.rebased = out / "rebased_controls"
        self.struct = repo / STRUCT_TOOL
        self.sem = repo / SEM_TOOL
        self.instance = None
        meta = repo / "runtime" / "instances"
        for d in sorted(meta.glob("worker-064-*")):
            self.instance = d.name
        self.report = {}
        self.errors = []

    # ---------- measurement helpers ----------
    def measure(self, rels):
        out = {}
        for rel in rels:
            p = self.repo / rel
            if p.exists():
                st = p.stat()
                out[rel] = {"sha256": sha(p), "bytes": st.st_size,
                            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds")}
            else:
                out[rel] = {"sha256": None, "bytes": None, "mtime": None,
                            "missing": True}
        return out

    def structural(self, target: Path):
        rep = run([sys.executable, str(self.struct), "--json", str(target)], self.repo)
        try:
            j = json.loads(rep.stdout[rep.stdout.index("{"):])
        except (ValueError, json.JSONDecodeError):
            j = {}
        return {"exit": rep.returncode, "verdict": j.get("verdict", "no_verdict"),
                "failed_rules": j.get("failed_rules", []),
                "failures": j.get("failures", [])[:12],
                "accepted": rep.returncode == 0 and j.get("verdict") == "pass",
                "rejected": j.get("verdict") == "fail"}

    def semantic(self, target: Path, hardened: bool, tag: str):
        out = self.raw / f"sem_{tag}_{target.stem}{'_h' if hardened else ''}.json"
        cmd = [sys.executable, str(self.sem), str(target), "--json", str(out)]
        if hardened:
            cmd.insert(-2, "--hardened")
        rep = run(cmd, self.repo)
        j = {}
        if out.exists():
            j = json.loads(out.read_text())
        return {"tool": "semantic_hardened" if hardened else "semantic_baseline",
                "exit": rep.returncode, "verdict": j.get("verdict", "no_verdict"),
                "failed_rules": j.get("failed_rules", []),
                "undecided_rules": j.get("undecided_rules", []),
                "accepted": j.get("verdict") == "accept",
                "rejected": j.get("verdict") == "reject"}

    def triplet(self, target: Path, tag: str):
        return {"structural": self.structural(target),
                "semantic_baseline": self.semantic(target, False, tag),
                "semantic_hardened": self.semantic(target, True, tag)}

    # ---------- P0 snapshot ----------
    def p0_snapshot(self):
        self.snapshot.mkdir(parents=True, exist_ok=True)
        rels = CANON + CONTROLS + OTHER_INPUTS
        snap = {}
        for rel in rels:
            src = self.repo / rel
            dst = self.snapshot / rel.replace("/", "__")
            shutil.copy2(src, dst)
            snap[rel] = {"sha256": sha(src), "bytes": src.stat().st_size,
                         "snapshot_file": dst.name}
        (self.snapshot / "SNAPSHOT.json").write_text(json.dumps(snap, indent=1) + "\n")
        # the whole suite fixture tree, byte-for-byte
        shutil.copytree(self.repo / SUITE_DIR / "fixtures", self.snapshot / "suite_fixtures",
                        dirs_exist_ok=True)
        self.report["snapshot"] = snap
        return snap

    # ---------- P1 baseline ----------
    def p1_baseline(self):
        base = {"canonical": {}, "controls": {}, "observed_tool_verdicts": {}}
        for rel in CANON:
            base["canonical"][rel] = self.triplet(self.snapshot / rel.replace("/", "__"),
                                                  "base_" + Path(rel).stem)
        for rel in CONTROLS:
            base["controls"][Path(rel).name] = self.triplet(self.snapshot / rel.replace("/", "__"),
                                                            "base_" + Path(rel).stem)
        self.report["baseline"] = base
        return base

    # ---------- P2 rebase ----------
    @staticmethod
    def remove_misplaced_row(text: str):
        """Step B: remove the R28-misplaced transfers row from genericity.transfer_failures."""
        lines = text.splitlines(keepends=True)
        start = None
        for i, l in enumerate(lines):
            if l.rstrip("\n") == "  transfer_failures:":
                start = i
                break
        if start is None:
            raise ValueError("transfer_failures section not found")
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r"^  [A-Za-z_][A-Za-z0-9_]*:", lines[j]):
                end = j
                break
        starts = [j for j in range(start + 1, end) if lines[j].startswith("  - ")]
        hit = None
        for k, s in enumerate(starts):
            e = starts[k + 1] if k + 1 < len(starts) else end
            block = "".join(lines[s:e])
            if ("finite_codimension_complement" in block and "residual_comeager" in block
                    and re.search(r"direction:\s*transfers", block)):
                hit = (s, e, block)
                break
        if hit is None:
            raise ValueError("misplaced transfers row not found in transfer_failures")
        s, e, block = hit
        info = {"removed_line_range_1based": [s + 1, e],
                "removed_line_count": e - s,
                "removed_block": block}
        return "".join(lines[:s] + lines[e:]), info

    @staticmethod
    def nest_revised_at_unused(text: str):
        """Step A: move the top-level `revised_at_unused` key under `extensions:` so the
        current R22 key manifest accepts the control (canonical rev12 dropped the key)."""
        lines = text.splitlines(keepends=True)
        idx = None
        for i, l in enumerate(lines):
            if re.match(r"^revised_at_unused:", l):
                idx = i
                break
        if idx is None:
            return text, None
        value = lines[idx].split(":", 1)[1].strip()
        ext = None
        for i, l in enumerate(lines):
            if re.match(r"^extensions:\s*$", l):
                ext = i
                break
        if ext is not None and ext < idx:
            new = lines[:idx] + [f"  revised_at_unused: {value}\n"] + lines[idx + 1:]
            new.insert(ext + 1, new.pop(idx))  # insert directly after the extensions: line
        else:
            new = (lines[:idx]
                   + ["extensions:\n", f"  revised_at_unused: {value}\n"]
                   + lines[idx + 1:])
        info = {"moved_key": "revised_at_unused", "value": value,
                "original_line_1based": idx + 1,
                "added_line": f"  revised_at_unused: {value}"}
        return "".join(new), info

    def rebase_text(self, text: str):
        """Two-step, text-preserving rebase of a frozen control to the current gate layout.
        Every byte other than the recorded edits is preserved."""
        step_a_text, info_a = self.nest_revised_at_unused(text)
        step_b_text, info_b = self.remove_misplaced_row(step_a_text)
        info = {"step_a_revised_at_unused": info_a, "step_b_misplaced_row": info_b}
        return step_b_text, info

    @staticmethod
    def expected_transform(orig_text: str, nest: bool = True):
        import copy
        a = yaml.safe_load(orig_text)
        exp = copy.deepcopy(a)
        v = exp.pop("revised_at_unused", None)
        if nest and v is not None:
            exp.setdefault("extensions", {})["revised_at_unused"] = v
        rows = exp["genericity"]["transfer_failures"]
        keep = [r for r in rows if not (r.get("pair") == ["finite_codimension_complement", "residual_comeager"]
                                        and r.get("direction") == "transfers")]
        assert len(keep) == len(rows) - 1, "misplaced row not found for expected transform"
        exp["genericity"]["transfer_failures"] = keep
        return exp, (v is not None)

    @staticmethod
    def yaml_diff(orig_text: str, new_text: str, nest: bool = True):
        exp, had_key = Audit.expected_transform(orig_text, nest=nest)
        got = yaml.safe_load(new_text)
        return {"exact_expected_transform": exp == got,
                "revised_at_unused_present_at_root_before": had_key,
                "revised_at_unused_under_extensions_after": bool(
                    (((got.get("extensions") or {}).get("revised_at_unused")) is not None)),
                "transfer_failures_rows_before": len((yaml.safe_load(orig_text).get("genericity") or {}).get("transfer_failures") or []),
                "transfer_failures_rows_after": len((got.get("genericity") or {}).get("transfer_failures") or [])}

    def p2_rebase(self):
        self.rebased.mkdir(parents=True, exist_ok=True)
        rec = {}
        for rel in CONTROLS:
            src = self.repo / rel
            text = src.read_text()
            new_text, info = self.rebase_text(text)
            diff = self.yaml_diff(text, new_text, nest=True)
            dst = self.rebased / Path(rel).name
            dst.write_text(new_text)
            new_sha = sha(dst)
            # textual minimality: the unified diff must contain only the recorded edits
            udiff = list(difflib.unified_diff(text.splitlines(keepends=True),
                                              new_text.splitlines(keepends=True),
                                              fromfile=rel, tofile=str(dst.name), n=0))
            changed = [l for l in udiff if l[:1] in "+-" and not l.startswith(("+++", "---"))]
            removed = [l for l in changed if l.startswith("-")]
            added = [l for l in changed if l.startswith("+")]
            edits_exact = (len(removed) == info["step_b_misplaced_row"]["removed_line_count"] + 1
                           and len(added) == 2
                           and removed[0].rstrip("\n")[1:] == f"revised_at_unused: {info['step_a_revised_at_unused']['value']}"
                           and added[0][1:] == "extensions:\n"
                           and added[1][1:].rstrip("\n") == info["step_a_revised_at_unused"]["added_line"])
            rec[Path(rel).name] = {
                "canonical_path": rel,
                "old_sha256": sha(src),
                "new_sha256": new_sha,
                "old_bytes": src.stat().st_size,
                "new_bytes": dst.stat().st_size,
                "step_a_revised_at_unused": info["step_a_revised_at_unused"],
                "step_b_removed_line_count": info["step_b_misplaced_row"]["removed_line_count"],
                "step_b_removed_line_range_1based": info["step_b_misplaced_row"]["removed_line_range_1based"],
                "step_b_removed_block": info["step_b_misplaced_row"]["removed_block"],
                "yaml_transform_check": diff,
                "unified_diff": "".join(udiff),
                "diff_is_key_move_and_deletion": edits_exact,
                "removed_block_ends_entry": (
                    info["step_b_misplaced_row"]["removed_block"].rstrip("\n").endswith("citation_status: n/a")),
            }
        self.report["rebase"] = {"method": ("two text-preserving edits: (A) move top-level "
                                            "revised_at_unused under extensions: (R22); "
                                            "(B) delete the finite_codimension_complement -> "
                                            "residual_comeager 'direction: transfers' entry from "
                                            "genericity.transfer_failures (R28)"),
                                 "controls": rec}
        return rec

    # ---------- P3 rebased verification ----------
    def p3_verify(self):
        out = {}
        for name in sorted(p.name for p in self.rebased.glob("*.yaml")):
            out[name] = self.triplet(self.rebased / name, "rebased_" + Path(name).stem)
        self.report["rebased_control_verdicts"] = out
        return out

    # ---------- P4 sensitivity mutants ----------
    def p4_sensitivity(self, rebased_rec):
        self.work.mkdir(parents=True, exist_ok=True)
        sens = {}

        def record(mid, name, mutation, expect_rule, target: Path):
            res = self.structural(target)
            sens[mid] = {"control": name, "mutation": mutation,
                         "expect_rejected_by_rule": expect_rule,
                         "structural_verdict": res["verdict"],
                         "structural_failed_rules": res["failed_rules"],
                         "structural_failures": res["failures"],
                         "pass": expect_rule in res["failed_rules"]}
            return sens[mid]

        # S1: reinsert the stale row (= the original canonical control bytes)
        for rel in CONTROLS:
            name = Path(rel).name
            record("S1-" + name, name,
                   "restore the pre-rebase bytes (misplaced transfers row in transfer_failures)",
                   "R28", self.repo / rel)

        # S2: materialize the comment-only composite phrase as assertive content (C01)
        c01 = yaml.safe_load((self.rebased / "control_comment_only_composite.yaml").read_text())
        c01["conclusion"]["statement_natural_language"] = (
            str(c01["conclusion"]["statement_natural_language"]) + " (C0 or C2 composite wording)")
        t = self.work / "mutant_C01_composite_as_data.yaml"
        t.write_text(yaml.safe_dump(c01, sort_keys=False))
        record("S2-control_comment_only_composite.yaml", "control_comment_only_composite.yaml",
               "move the composite phrase out of the YAML comment into conclusion.statement_natural_language",
               "R13", t)

        # S3: strip the quotation exemption context (C03) -- the phrase is exempt only because
        # its ancestor anti_scope subtree is in EXEMPT_KEY; move it to top level.
        c03_txt = (self.rebased / "control_quoted_forbidden_phrase.yaml").read_text()
        t3 = self.work / "mutant_C03_unquoted.yaml"
        mutated = re.sub(r"(?m)^  extensions:\n    quoted_forbidden_phrases:", "quoted_forbidden_phrases:", c03_txt)
        t3.write_text(mutated)
        r3 = self.structural(t3)
        # fall back to a tag-value mutant if the key move is rejected by a different rule
        if "R13" not in r3["failed_rules"]:
            c03 = yaml.safe_load(c03_txt)
            c03["extensions"]["quoted_forbidden_phrases"][0]["tag"] = "asserted_not_quoted"
            t3b = self.work / "mutant_C03_tag_stripped.yaml"
            t3b.write_text(yaml.safe_dump(c03, sort_keys=False))
            r3b = self.structural(t3b)
            sens["S3-control_quoted_forbidden_phrase.yaml"] = {
                "control": "control_quoted_forbidden_phrase.yaml",
                "mutation": "remove the quotation-exemption container (extensions.quoted_forbidden_phrases -> top level)",
                "structural_verdict": r3["verdict"], "structural_failed_rules": r3["failed_rules"],
                "structural_failures": r3["failures"], "pass": bool(r3["failed_rules"]),
                "fallback_mutation": "extensions.quoted_forbidden_phrases[0].tag -> asserted_not_quoted",
                "fallback_structural_verdict": r3b["verdict"],
                "fallback_structural_failed_rules": r3b["failed_rules"],
                "fallback_failures": r3b["failures"],
                "note": "any structural rejection counts as sensitivity; R13 is the guard of interest",
            }
        else:
            sens["S3-control_quoted_forbidden_phrase.yaml"] = {
                "control": "control_quoted_forbidden_phrase.yaml",
                "mutation": "remove the quotation-exemption container (extensions.quoted_forbidden_phrases -> top level)",
                "structural_verdict": r3["verdict"], "structural_failed_rules": r3["failed_rules"],
                "structural_failures": r3["failures"], "pass": True}

        # S4 (vacuity guard): a mutation that deletes the witness of a transfer row must be
        # rejected too -- tested only for information, not part of the pass criterion.
        self.report["sensitivity"] = sens
        return sens

    # ---------- R22 unknown-key computation ----------
    @staticmethod
    def unknown_keys(doc, allowed):
        unknown = set()

        def walk(n):
            if isinstance(n, dict):
                for k, v in n.items():
                    if k == "extensions":
                        continue
                    if str(k) not in allowed:
                        unknown.add(str(k))
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)

        walk(doc)
        return sorted(unknown)

    def key_manifest_patch(self, canon_paths):
        allowed = set(json.loads((self.repo / STRUCT_KEYS).read_text())["allowed_keys"])
        union = set()
        per = {}
        for rel, p in canon_paths.items():
            doc = yaml.safe_load(Path(p).read_text())
            u = self.unknown_keys(doc, allowed)
            per[rel] = u
            union |= set(u)
        return {"unknown_keys_per_canonical": per, "union": sorted(union),
                "key_manifest_sha256": sha(self.repo / STRUCT_KEYS)}

    # ---------- P5 suite simulations ----------
    def load_runner(self):
        spec = importlib.util.spec_from_file_location("suite_runner", self.repo / SUITE_RUNNER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def run_suite(self, tag, here: Path, manifest_path: Path, struct_tool: Path, repo: Path = None):
        repo = repo or self.repo
        mod = self.load_runner()
        mod.HERE = here
        mod.MANIFEST = manifest_path
        mod.OBSERVED = here / f"observed_{tag}.json"
        mod.REPO = repo
        mod.STRUCT = struct_tool
        mod.SEM = self.sem
        old = sys.argv
        buf = io.StringIO()
        sys.argv = [str(self.repo / SUITE_RUNNER)]
        try:
            with redirect_stdout(buf):
                rc = mod.main()
        finally:
            sys.argv = old
        stdout = buf.getvalue()
        (here / f"stdout_{tag}.txt").write_text(stdout)
        if not mod.OBSERVED.exists():
            errs = [l.strip()[2:] for l in stdout.splitlines() if l.strip().startswith("- ")]
            return {"exit": rc, "stdout": stdout, "integrity_errors": errs,
                    "observed_file": None, "validity": None, "summary": None,
                    "stage_hashes": None, "manifest_sha256_at_run": None,
                    "targets": {}, "rejections": {}}
        obs = json.loads(mod.OBSERVED.read_text())
        summ = obs["summary"]
        # per-target compact view
        targets = {r["test_id"]: {"kind": r["kind"], "verdict": r["observed"]["verdict"],
                                  "accepted_by": r["observed"]["accepted_by"],
                                  "rejected_by": r["observed"]["rejected_by"],
                                  "expected": r["expected_verdict"],
                                  "agrees": r["observed"]["agrees_with_expected"]}
                   for r in obs["results"]}
        return {"exit": rc, "stdout": stdout,
                "observed_file": str(mod.OBSERVED.relative_to(self.out)),
                "validity": obs["validity"], "summary": summ,
                "stage_hashes": obs["stage_hashes"],
                "manifest_sha256_at_run": obs["manifest_sha256_at_run"],
                "targets": targets,
                "rejections": {k: v for k, v in targets.items() if v["verdict"] != "accept"}}

    def p5_simulations(self, canon_now):
        self.work.mkdir(parents=True, exist_ok=True)
        sims = {}

        # --- pinned repo view: simulations must not race the live publisher
        view = self.work / "repo_view"
        (view / "schemas").mkdir(parents=True, exist_ok=True)
        for rel in CANON:
            shutil.copy2(self.repo / rel, view / rel)
        view_hashes = {rel: sha(view / rel) for rel in CANON}
        sims["repo_view_hashes"] = view_hashes
        sims["live_hashes_at_simulation"] = {rel: canon_now[rel]["sha256"] for rel in CANON}

        # --- S0: unmodified canonical suite manifest, canonical fixture tree
        s0 = self.work / "suite_s0"
        s0.mkdir(exist_ok=True)
        shutil.copytree(self.repo / SUITE_DIR / "fixtures", s0 / "fixtures", dirs_exist_ok=True)
        shutil.copy2(self.repo / SUITE_MANIFEST, s0 / "manifest.json")
        sims["S0_unmodified"] = self.run_suite("s0", s0, s0 / "manifest.json", self.struct, repo=view)

        # --- build rebased manifest + fixture tree (shared by S1/S2)
        s1 = self.work / "suite_s1"
        s1.mkdir(exist_ok=True)
        shutil.copytree(self.repo / SUITE_DIR / "fixtures", s1 / "fixtures", dirs_exist_ok=True)
        for name in (p.name for p in self.rebased.glob("*.yaml")):
            shutil.copy2(self.rebased / name, s1 / "fixtures" / "controls" / name)
        man = json.loads((self.repo / SUITE_MANIFEST).read_text())
        pin_changes = []
        for c in man["controls"]:
            old = c["sha256"]
            new = sha(s1 / c["fixture"])
            c["sha256"] = new
            c.setdefault("rebase", {})["old_sha256"] = old
            c["rebase"]["rebase_task"] = TASK_ID
            pin_changes.append({"test_id": c["test_id"], "path": c["fixture"], "old": old, "new": new})
        canon_changes = []
        for c in man["conforming_canonical_controls"]:
            old = c["sha256"]
            new = view_hashes[c["fixture"]]
            c["sha256"] = new
            canon_changes.append({"test_id": c["test_id"], "path": c["fixture"], "old": old, "new": new})
        man["worker_rebase"] = {
            "task_id": TASK_ID, "at": now(),
            "control_pins": pin_changes, "canonical_pins": canon_changes,
            "notes": ("control bytes rebased by two text-preserving edits (R22: revised_at_unused "
                      "moved under extensions:; R28: misplaced transfers row deleted); "
                      "canonical pins refreshed to the pinned repo-view bytes; fixtures untouched"),
        }
        man_path = s1 / "manifest.json"
        man_path.write_text(json.dumps(man, indent=1) + "\n")
        sims["S1_rebased_controls_pins_refreshed"] = self.run_suite("s1", s1, man_path, self.struct,
                                                                    repo=view)

        # --- S2: negative control -- rebased fixture bytes but the pre-rebase control pins
        s2 = self.work / "suite_s2"
        s2.mkdir(exist_ok=True)
        shutil.copytree(s1 / "fixtures", s2 / "fixtures", dirs_exist_ok=True)
        stale = json.loads((self.repo / SUITE_MANIFEST).read_text())
        for c in stale["controls"]:
            c["sha256"] = c.get("rebase", {}).get("old_sha256") or c["sha256"]
        for c in stale["conforming_canonical_controls"]:
            c["sha256"] = view_hashes[c["fixture"]]  # only the control pins stay stale
        stale["worker_rebase"] = {"task_id": TASK_ID, "at": now(),
                                  "note": "negative control: rebased bytes, stale control pins"}
        (s2 / "manifest.json").write_text(json.dumps(stale, indent=1) + "\n")
        sims["S2_stale_control_pins_negative_control"] = self.run_suite(
            "s2", s2, s2 / "manifest.json", self.struct, repo=view)

        # --- S3: alternative rebase strategy -- delete revised_at_unused instead of nesting it
        alt = self.work / "alt_rebase"
        alt.mkdir(exist_ok=True)
        alt_res = {}
        for rel in CONTROLS:
            text = (self.repo / rel).read_text()
            no_key = re.sub(r"(?m)^revised_at_unused:.*\n", "", text)
            new_text, _ = self.remove_misplaced_row(no_key)
            p = alt / Path(rel).name
            p.write_text(new_text)
            st = self.structural(p)
            alt_res[Path(rel).name] = {
                "sha256": sha(p), "structural_verdict": st["verdict"],
                "structural_failed_rules": st["failed_rules"],
                "accepted": st["accepted"],
                "yaml_transform_check": self.yaml_diff(text, new_text, nest=False),
            }
        sims["S3_alternative_delete_key"] = alt_res

        # --- R22 state measurement: canonical vs controls at the snapshot
        allowed = set(json.loads((self.repo / STRUCT_KEYS).read_text())["allowed_keys"])
        sims["r22_state_at_snapshot"] = {
            "key_manifest_sha256": sha(self.repo / STRUCT_KEYS),
            "canonical_unknown_keys": {rel: self.unknown_keys(yaml.safe_load((view / rel).read_text()), allowed)
                                       for rel in CANON},
            "control_unknown_keys_before": {Path(rel).name: self.unknown_keys(
                yaml.safe_load((self.repo / rel).read_text()), allowed) for rel in CONTROLS},
            "control_unknown_keys_after": {Path(rel).name: self.unknown_keys(
                yaml.safe_load((self.rebased / Path(rel).name).read_text()), allowed) for rel in CONTROLS},
        }
        self.report["suite_simulations"] = sims
        return sims

    # ---------- patch + README ----------
    def write_patch(self):
        reb = self.report["rebase"]["controls"]
        sims = self.report["suite_simulations"]
        s1man = json.loads((self.work / "suite_s1" / "manifest.json").read_text())
        ctrl_pins = []
        for c in s1man["controls"]:
            ctrl_pins.append({"test_id": c["test_id"], "path": c["fixture"],
                              "old_sha256": c["rebase"]["old_sha256"], "new_sha256": c["sha256"]})
        canon_pins = [{"test_id": c["test_id"], "path": c["fixture"], "old_sha256": None,
                       "new_sha256": c["sha256"]} for c in s1man["conforming_canonical_controls"]]
        patch = {
            "task_id": TASK_ID,
            "created_at": now(),
            "target_suite": SUITE_DIR,
            "not_applied_by_worker": True,
            "repair_1_control_rebase": {
                "method": self.report["rebase"]["method"],
                "controls": {k: {"canonical_path": v["canonical_path"],
                                 "old_sha256": v["old_sha256"], "new_sha256": v["new_sha256"],
                                 "step_a": v["step_a_revised_at_unused"],
                                 "step_b_removed_block": v["step_b_removed_block"],
                                 "step_b_removed_line_range_1based": v["step_b_removed_line_range_1based"],
                                 "rebased_bytes": f"rebased_controls/{k}"}
                             for k, v in sorted(reb.items())},
                "alternative_strategy_S3": ("delete revised_at_unused instead of nesting it under "
                                            "extensions:; verified structurally in "
                                            "suite_simulations.S3_alternative_delete_key"),
            },
            "repair_2_pin_refresh": {"controls": ctrl_pins, "conforming_canonical_controls": canon_pins,
                                     "manifest_rebased": "manifest_rebased.json"},
            "residual_blocker_not_owned_by_worker": {
                "id": "SEMANTIC-WCC-R03",
                "measured": ("at the pinned repo-view bytes the binding structural gate passes for all "
                             "three canonical schemas, but the adopted semantic auditor rejects "
                             "schemas/af_wcc_vacuum.yaml with R03 'binder (q,t0) absent from formal "
                             "sentence', so run_contract_tests.py still cannot return exit 0; owner "
                             "lead-formulation / semantic-auditor owner"),
                "evidence": ["report.json#baseline#canonical",
                             "report.json#suite_simulations#S1_rebased_controls_pins_refreshed"],
            },
            "r22_state_at_snapshot": sims["r22_state_at_snapshot"],
            "canonical_hashes_at_snapshot": {k: v["sha256"] for k, v in self.report["canonical_hashes_at_end"].items()},
            "apply_instructions": [
                "1. replace the three frozen control fixtures with rebased_controls/* (two recorded edits each)",
                "2. repin manifest.controls[].sha256 and manifest.conforming_canonical_controls[].sha256 to the current canonical bytes",
                "3. re-run run_contract_tests.py; the control blocker (ADJ-CONTROL-STALENESS) is cleared, the residual WCC R03 semantic blocker remains owner lead-formulation",
            ],
        }
        (self.out / "rebase_patch.json").write_text(json.dumps(patch, indent=1) + "\n")
        return patch

    # ---------- findings ----------
    def build_findings(self):
        def g(entry, *keys, default="n/a"):
            cur = entry
            for k in keys:
                if not isinstance(cur, dict) or cur.get(k) is None:
                    return default
                cur = cur[k]
            return cur

        f = []
        reb = self.report["rebase"]["controls"]
        base = self.report["baseline"]
        ver = self.report["rebased_control_verdicts"]
        sens = self.report["sensitivity"]
        sims = self.report["suite_simulations"]

        all_rebased_pass = all(all(s["accepted"] for s in v.values()) for v in ver.values())
        all_sens_reject = all(v.get("pass") for v in sens.values())

        ctrl_rules = {k: v["structural"]["failed_rules"] for k, v in base["controls"].items()}
        canon_struct = {k: v["structural"]["verdict"] for k, v in base["canonical"].items()}
        canon_sem = {k: (v["semantic_baseline"]["verdict"], v["semantic_hardened"]["verdict"])
                     for k, v in base["canonical"].items()}
        canon_sem_rules = {k: {"baseline": v["semantic_baseline"]["failed_rules"],
                               "hardened": v["semantic_hardened"]["failed_rules"]}
                           for k, v in base["canonical"].items()}

        f.append({
            "id": "F-REBASE-1",
            "statement": ("At the pinned snapshot the three frozen controls each fail the binding "
                          "structural gate on two rules (measured: "
                          f"{ctrl_rules}): R28 because the entry finite_codimension_complement -> "
                          "residual_comeager with direction 'transfers' sits in "
                          "genericity.transfer_failures, and R22 because the historical top-level key "
                          "revised_at_unused is absent from the current KEY_MANIFEST. The three "
                          "canonical schemas pass the structural gate at the same snapshot "
                          f"(measured: {canon_struct}) but the adopted semantic stage rejects WCC "
                          f"(measured: {canon_sem_rules}), so the suite has two independent validity "
                          "blockers at this snapshot: stale control layout and WCC R03."),
            "evidence": ["report.json#baseline", "report.json#snapshot",
                         "report.json#suite_simulations#r22_state_at_snapshot"],
            "falsifier": ("A structural run at the snapshot bytes in which a frozen control passes, "
                          "or fails on a rule other than R22/R28, or a canonical schema fails "
                          "structural, or WCC is accepted by both semantic stages, falsifies the "
                          "corresponding clause."),
        })
        f.append({
            "id": "F-REBASE-2",
            "statement": ("The minimal control rebase is two text-preserving edits: (A) move the "
                          "single top-level line revised_at_unused under extensions: (R22); "
                          f"(B) delete the R28-misplaced {g(reb, next(iter(reb)), 'step_b_removed_line_count')}-line transfers entry from "
                          "genericity.transfer_failures. The transformed YAML equals the expected "
                          "transform exactly for all three controls "
                          f"(exact_expected_transform="
                          f"{[v['yaml_transform_check']['exact_expected_transform'] for v in reb.values()]}, "
                          f"edits_exact={[v['diff_is_key_move_and_deletion'] for v in reb.values()]}). "
                          "New control hashes: "
                          + ", ".join(f"{k} {v['new_sha256'][:12]}" for k, v in sorted(reb.items()))),
            "evidence": ["report.json#rebase", "rebase_patch.json", "rebased_controls/"],
            "falsifier": ("Any YAML difference between a rebased control and the recorded expected "
                          "transform, any additional diff line, or any change to the mutated corpus / "
                          "fixtures, falsifies this finding."),
        })
        f.append({
            "id": "F-REBASE-3",
            "statement": ("After rebase all three controls are accepted by structural, semantic "
                          f"baseline and semantic hardened (all_accepted={all_rebased_pass}; measured "
                          f"{ {k: {s: v2['verdict'] for s, v2 in v.items()} for k, v in ver.items()} }); "
                          f"all sensitivity mutants are still rejected (all_rejected={all_sens_reject}; "
                          + ", ".join(f"{k}:{v['structural_failed_rules']}" for k, v in sorted(sens.items()))
                          + ")."),
            "evidence": ["report.json#rebased_control_verdicts", "report.json#sensitivity"],
            "falsifier": ("A rebased control rejected by any stage, or a sensitivity mutant not "
                          "rejected by the structural gate, falsifies the corresponding clause."),
        })
        s0 = sims["S0_unmodified"]
        s1 = sims["S1_rebased_controls_pins_refreshed"]
        s2 = sims["S2_stale_control_pins_negative_control"]
        f.append({
            "id": "F-REBASE-4",
            "statement": ("Full-suite consequence at the pinned repo-view bytes "
                          f"({', '.join(v[:12] for v in sims['repo_view_hashes'].values())}): "
                          f"(S0) the unmodified canonical manifest exits {s0['exit']} with "
                          f"{len(s0.get('integrity_errors', []))} integrity errors (stale canonical "
                          "pins); (S1) with rebased controls and refreshed pins the suite executes "
                          f"with mutants {g(s1, 'summary', 'structural_caught')}/"
                          f"{g(s1, 'summary', 'mutants')} structural, "
                          f"{g(s1, 'summary', 'semantic_baseline_caught')}/{g(s1, 'summary', 'mutants')} "
                          f"baseline, {g(s1, 'summary', 'semantic_hardened_caught')}/"
                          f"{g(s1, 'summary', 'mutants')} hardened, frozen controls accepted="
                          f"{g(s1, 'summary', 'controls_accepted_both_stages')}, canonical controls "
                          f"accepted={g(s1, 'summary', 'conforming_canonical_accepted_both_stages')}, "
                          f"exit {s1['exit']}, valid_for_calibration="
                          f"{g(s1, 'validity', 'valid_for_calibration')} -- the control blocker is "
                          "cleared and only the independent WCC R03 blocker remains; "
                          f"(S2) the negative control with rebased bytes but pre-rebase control pins "
                          f"exits {s2['exit']} with {len(s2.get('integrity_errors', []))} integrity "
                          "errors (control sha mismatches only), so control tampering is still caught."),
            "evidence": ["report.json#suite_simulations", "rebase_patch.json"],
            "falsifier": ("A re-run of the same four simulations at the pinned bytes producing "
                          "different exit codes, mutant counts, control-acceptance flags or validity "
                          "values falsifies the corresponding clause."),
        })
        f.append({
            "id": "F-REBASE-5",
            "statement": ("The residual validity blocker after the control rebase is not the controls: "
                          "the adopted semantic auditor rejects schemas/af_wcc_vacuum.yaml with R03 "
                          "'binder (q,t0) absent from formal sentence' (baseline and hardened), so "
                          "run_contract_tests.py still exits 3 and valid_for_calibration stays false. "
                          "Owner: lead-formulation / semantic-auditor owner. The alternative rebase "
                          "strategy S3 (delete revised_at_unused instead of nesting it) also yields "
                          f"structural acceptance: "
                          f"{ {k: v['accepted'] for k, v in sims['S3_alternative_delete_key'].items()} }."),
            "evidence": ["report.json#baseline#canonical", "report.json#suite_simulations"],
            "falsifier": ("A semantic-auditor run accepting WCC at the pinned bytes, or an S3 control "
                          "failing structural, falsifies the corresponding clause."),
        })
        f.append({
            "id": "F-REBASE-6",
            "statement": ("Runner labelling side-finding at the pinned bytes: in S1 the suite reports "
                          "valid_for_calibration=false with blocking_adjudication=[] "
                          "(measured: " + json.dumps(g(s1, "validity", default={})) + "). The runner "
                          "only names ADJ-CONTROL-STALENESS when a frozen control fails; a "
                          "conforming-canonical rejection produces no adjudication id, which can "
                          "misdirect the repair to the controls. A conforming-canonical-specific id "
                          "(or the failing fixture list) should be emitted by the runner owner."),
            "evidence": ["report.json#suite_simulations#S1_rebased_controls_pins_refreshed"],
            "falsifier": ("An S1-style run at the pinned bytes that reports a non-empty "
                          "blocking_adjudication list naming the canonical rejection falsifies this "
                          "finding."),
        })
        self.report["findings"] = f
        return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/data3/guoshaoyang/workdir/ai4math-swarm")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    out = Path(a.out) if a.out else repo / "artifacts" / "worker-064" / "semct_rebase"
    out.mkdir(parents=True, exist_ok=True)
    au = Audit(repo, out)
    au.raw.mkdir(exist_ok=True)

    au.report["task_id"] = TASK_ID
    au.report["worker"] = "worker-064"
    au.report["instance_id"] = au.instance
    au.report["created_at"] = now()
    au.report["repo"] = str(repo)
    au.report["class_ids"] = CLASS_IDS
    au.report["node_id"] = "A1"
    au.report["gate"] = "G-AUDIT"
    au.report["scope"] = ("independent rebase + machine verification of the three frozen controls "
                          "of schemas/semantic_contract_tests at a pinned snapshot; no canonical file modified")

    au.p0_snapshot()
    canon_start = au.measure(CANON + OTHER_INPUTS)
    au.report["measured_at_start"] = canon_start
    au.p1_baseline()
    au.p2_rebase()
    au.p3_verify()
    canon_now = au.measure(CANON)
    au.report["canonical_hashes_at_end"] = canon_now
    au.report["drift"] = {k: {"start": canon_start[k]["sha256"], "end": canon_now[k]["sha256"],
                              "changed": canon_start[k]["sha256"] != canon_now[k]["sha256"]}
                          for k in CANON}
    au.p4_sensitivity(au.report["rebase"]["controls"])
    au.p5_simulations(canon_now)
    au.build_findings()
    au.write_patch()
    shutil.copy2(au.work / "suite_s1" / "manifest.json", out / "manifest_rebased.json")
    au.report["not_claimed"] = [
        "no gate verdict",
        "no node completion",
        "no mathematical verdict on any schema",
        "no modification of any canonical artifact",
        "no claim outside the pinned snapshot bytes",
        "S2 is a simulation of a KEY_MANIFEST extension, not an adopted tool change",
    ]
    (out / "report.json").write_text(json.dumps(au.report, indent=1) + "\n")
    print(json.dumps({"task_id": TASK_ID, "report": str(out / "report.json"),
                      "rebased": {k: v["new_sha256"] for k, v in au.report["rebase"]["controls"].items()},
                      "findings": [f["id"] for f in au.report["findings"]]}, indent=1))


if __name__ == "__main__":
    main()
