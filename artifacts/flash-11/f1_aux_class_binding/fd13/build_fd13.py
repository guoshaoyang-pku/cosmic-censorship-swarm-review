#!/usr/bin/env python3
"""FD-13 build: byte-minimal leak/control repros + clause-local R12 patch proposal.

Bounded task: FORM-DIFF-02 / node F1 / gate G-CLASSBIND.
Binds to the FROZEN rev19 tool + rule_spec (both still byte-match on disk):
  artifacts/formulation/tools/check_class_schema.py  sha256 000e09e4...  (R12 lives here)
  artifacts/formulation/rule_spec.json               sha256 40f9bb9e...
The repro is a single-sentence textual mutation of the WCC schema: no YAML round-trip,
so every byte outside the mutated sentence is preserved.

Outputs (all under fd13/):
  minimal_repro_rev19.yaml   leak, base = frozen rev19 corpus copy  (f962c117)
  control_rev19.yaml         legit geodesic control, same base
  minimal_repro_current.yaml leak, base = current authoring schema (b65fcc0f, rebase check)
  control_current.yaml       legit geodesic control, same base
  tools/patched_check_class_schema.py  proposed R12 clause-scope fix
  rule_spec.json / KEY_MANIFEST.json   byte-copies the patched tool resolves to
  r12_proposal.diff          exact unified diff of the proposal
  build_manifest.json        all input/output hashes
"""
from __future__ import annotations

import difflib
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIND = HERE.parent                      # f1_aux_class_binding
REPO = BIND.parents[2]                  # ai4math-swarm

CANON_TOOL = REPO / "artifacts/formulation/tools/check_class_schema.py"
CANON_SPEC = REPO / "artifacts/formulation/rule_spec.json"
CANON_KEYM = REPO / "artifacts/formulation/KEY_MANIFEST.json"

BASE_TOOL_SHA = "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"
BASE_SPEC_SHA = "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"

SOURCES = {
    "rev19": BIND / "corpus/canonical/af_wcc_vacuum.yaml",           # f962c117 (frozen rev19)
    "current": REPO / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",  # b65fcc0f (rebased)
}

# The mutation anchor is the final words of the WCC non_vacuity.condition value.
ANCHOR = "worker-16 F1-16-03 accepted).\""
LEAK = "worker-16 F1-16-03 accepted). The maximal development is C^2-inextendible.\""
CONTROL = ("worker-16 F1-16-03 accepted). Any singular point is witnessed by a "
           "future-inextendible causal geodesic of finite affine length.\"")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def mutate(src: Path, old: str, new: str) -> bytes:
    text = src.read_text()
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"anchor not unique in {src}: {n} occurrences")
    return text.replace(old, new).encode()


def emit(rel: str, data: bytes) -> dict:
    p = HERE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return {"path": f"fd13/{rel}", "sha256": sha256_bytes(data), "bytes": len(data)}


# ---------------------------------------------------------------- repros
manifest: dict = {"built_at": None, "sources": {}, "fixtures": [], "patch": {}}

for tag, src in SOURCES.items():
    if not src.exists():
        raise SystemExit(f"missing source {src}")
    manifest["sources"][tag] = {"path": str(src.relative_to(REPO)), "sha256": sha256_file(src)}
    for kind, new in (("leak", LEAK), ("control", CONTROL)):
        data = mutate(src, ANCHOR, new)
        rec = emit(f"{kind}_{tag}.yaml", data)
        rec.update({"kind": kind, "base": tag, "expect": "reject/R12" if kind == "leak" else "accept"})
        manifest["fixtures"].append(rec)

# ---------------------------------------------------------------- patched tool
base_bytes = CANON_TOOL.read_bytes()
base_sha = sha256_bytes(base_bytes)
if base_sha != BASE_TOOL_SHA:
    raise SystemExit(f"canonical tool moved: {base_sha} != {BASE_TOOL_SHA}; re-derive the patch")

OLD = '''                for pat in FOREIGN[fam]:
                    if pat == "INEXTENDIB_NON_GEODESIC":
                        if INEXTENDIB.search(s) and not GEODESIC.search(s):
                            self.fail("R12", f"SCC-style inextendibility in {'.'.join(p)}")
                        continue
'''
NEW = '''                for pat in FOREIGN[fam]:
                    if pat == "INEXTENDIB_NON_GEODESIC":
                        # FD-13 (flash-11, 2026-09-12): the geodesic exemption must be
                        # clause-local, not field-global. A single field may legitimately
                        # speak of future-inextendible causal GEODESICS in one sentence and
                        # carry a non-geodesic inextendibility claim (SCC content) in the
                        # next; the field-global guard exempted the whole field.
                        for _clause in re.split(r"(?<=[.;])\\s+", s):
                            if INEXTENDIB.search(_clause) and not GEODESIC.search(_clause):
                                self.fail("R12", f"SCC-style inextendibility in {'.'.join(p)}")
                        continue
'''
base_text = base_bytes.decode()
if base_text.count(OLD) != 1:
    raise SystemExit(f"patch anchor not unique: {base_text.count(OLD)}")
patched_text = base_text.replace(OLD, NEW)
patched_bytes = patched_text.encode()

emit("tools/patched_check_class_schema.py", patched_bytes)
# the patched tool resolves SPEC/KEY_MANIFEST at parents[1]; provide byte-copies next to tools/
spec_bytes = CANON_SPEC.read_bytes()
if sha256_bytes(spec_bytes) != BASE_SPEC_SHA:
    raise SystemExit("rule_spec moved; re-derive the patch binding")
emit("rule_spec.json", spec_bytes)
emit("KEY_MANIFEST.json", CANON_KEYM.read_bytes())

diff = "".join(difflib.unified_diff(
    base_text.splitlines(keepends=True),
    patched_text.splitlines(keepends=True),
    fromfile="artifacts/formulation/tools/check_class_schema.py",
    tofile="fd13/tools/patched_check_class_schema.py",
    n=3,
))
emit("r12_proposal.diff", diff.encode())

manifest["patch"] = {
    "base_tool": {"path": "artifacts/formulation/tools/check_class_schema.py",
                  "sha256": base_sha, "binding": "FROZEN rev19"},
    "patched_tool": {"path": "fd13/tools/patched_check_class_schema.py",
                     "sha256": sha256_bytes(patched_bytes)},
    "base_rule_spec_sha256": BASE_SPEC_SHA,
    "proposal": "scope INEXTENDIB_NON_GEODESIC geodesic-exemption per sentence/clause",
    "diff_sha256": sha256_bytes(diff.encode()),
}

import datetime
manifest["built_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
(HERE / "build_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
print(json.dumps(manifest, indent=1, sort_keys=True))
