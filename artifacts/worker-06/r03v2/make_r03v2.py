#!/usr/bin/env python3
"""Generate the R03-v2 proposal copy and the pre-registered calibration corpus.

Deterministic. Asserts every pinned input hash before use. Writes:

  audit_r03v2.py        proposal copy of the frozen stage-B auditor; exactly two textual
                        deltas from artifacts/worker-06/spec_conformance_audit.py
                        (D1 path rebase, D2 the R03 binder block). Semantic delta: 1.
  fixtures/             byte copies (positive controls) and derived mutants
  fixture_manifest.json hashed corpus definition
  preregistration.json  written BEFORE any auditor is run

The frozen source is never written to.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
W06 = HERE.parent
ROOT = W06.parent.parent

SRC = W06 / "spec_conformance_audit.py"
SRC_SHA = "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec"
WCC = ROOT / "schemas" / "af_wcc_vacuum.yaml"
C2 = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
C0 = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
PINS = {
    str(WCC.relative_to(ROOT)): "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    str(C2.relative_to(ROOT)): "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    str(C0.relative_to(ROOT)): "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}
PROBE10 = W06 / "probe10" / "fixtures"
POS_COPIES = [
    ("p01", "AF-WCC-VAC-GEN", WCC),
    ("p02", "AF-SCC-C2-VAC-GEN", C2),
    ("p03", "AF-SCC-C0-VAC-GEN", C0),
    ("p04", "AF-SCC-C0-VAC-GEN", PROBE10 / "c01_conforming_c0.yaml"),
    ("p05", "AF-SCC-C2-VAC-GEN", PROBE10 / "c02_conforming_c2.yaml"),
    ("p06", "AF-WCC-VAC-GEN", PROBE10 / "c03_conforming_wcc.yaml"),
    ("p07", "AF-SCC-C0-VAC-GEN", PROBE10 / "c04_negated_completeness_c0.yaml"),
    ("p08", "AF-SCC-C0-VAC-GEN", PROBE10 / "c05_negated_observability_c0.yaml"),
]

# ---------------------------------------------------------------- patch (D1, D2)
D1_OLD = "ROOT = HERE.parent.parent\n"
D1_NEW = ("ROOT = HERE.parent.parent.parent  "
          "# [R03-V2 D1] path rebase only: this proposal copy lives one directory deeper\n")

D2_OLD = """                for b in binders:
                    if b not in formal:
                        bad.append(f"binder {b!r} absent from formal sentence")
"""
D2_NEW = '''                # [R03-V2 D2] literal-substring binder test -> binder-head co-binding
                # test.  Frozen R03 falsely rejects canonical AF-WCC-VAC-GEN, whose binder
                # "(q,t0)" is rendered in formal as "q in I+ and t0 in [0,T)".  Proposal
                # only: see artifacts/worker-06/r03v2/ (preregistration, calibration,
                # falsifier).  The frozen tool is not modified.
                _SPAN = 80
                _IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
                _QUANT = re.compile(r"(?:not\\s+exists|forall|exists)\\b")
                _SEP = re.compile(r"[()]|:|;|,|\\bwith\\b|\\bsuch that\\b|\\bwhere\\b|\\bof\\b|\\bletting\\b")

                def _binder_head(_c):
                    _depth = 0
                    for _m in _SEP.finditer(_c):
                        _tok = _m.group(0)
                        if _tok == "(":
                            _depth += 1
                        elif _tok == ")":
                            _depth = max(0, _depth - 1)
                        elif _depth == 0:
                            return _c[:_m.start()]
                    return _c

                _starts = [m.start() for m in _QUANT.finditer(formal)]
                _heads = [_binder_head(formal[a:b])
                          for a, b in zip(_starts, _starts[1:] + [len(formal)])]
                for b in binders:
                    _ids = _IDENT.findall(str(b))
                    if not _ids:
                        bad.append(f"binder {b!r} carries no identifier")
                        continue
                    _hit = False
                    for _h in _heads:
                        _pos, _ok = 0, True
                        for _i in _ids:
                            _m = re.search(rf"\\b{re.escape(_i)}\\b", _h[_pos:])
                            if not _m or (_pos and _m.start() > _SPAN):
                                _ok = False
                                break
                            _pos += _m.start() + len(_i)
                        if _ok:
                            _hit = True
                            break
                    if not _hit:
                        bad.append(f"binder {b!r} not co-bound in one binder head")
'''

WCC_TAIL_A = "not exists q in I+ and t0 in [0,T)"
WCC_TAIL_B = "not exists a in I+ and b in [0,T)"
GAMMA_A = "gamma([t0,T))"
GAMMA_B = "gamma([t1,T))"
JQ_A = "J^-(q)"
JQ_B = "J^-(z)"
WCC_REMARK = "; remark: the coordinate pair (q,t0) is retained from the earlier draft."


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_pins() -> None:
    if sha(SRC) != SRC_SHA:
        sys.exit(f"frozen stage-B source hash drift: {sha(SRC)} != {SRC_SHA}")
    for rel, want in PINS.items():
        got = sha(ROOT / rel)
        if got != want:
            sys.exit(f"pin drift {rel}: {got} != {want}")


def build_patch() -> None:
    text = SRC.read_text()
    for old, new, tag in ((D1_OLD, D1_NEW, "D1"), (D2_OLD, D2_NEW, "D2")):
        if text.count(old) != 1:
            sys.exit(f"{tag} anchor not found exactly once ({text.count(old)})")
        text = text.replace(old, new)
    header = ('"""R03-V2 PROPOSAL COPY of spec_conformance_audit.py (generated, do not hand-edit).\n\n'
              f"source : artifacts/worker-06/spec_conformance_audit.py @ {SRC_SHA}\n"
              "delta  : D1 path rebase (this copy is one directory deeper)\n"
              "         D2 R03 binder check literal-substring -> binder-head co-binding "
              "(the only semantic delta)\n"
              "status : proposal only; falsifier and calibration in "
              "artifacts/worker-06/r03v2/report.json\n"
              '"""')
    idx = text.index('"""', text.index('"""') + 3) + 3
    (HERE / "audit_r03v2.py").write_text(header + text[idx:])


def mutate(src: Path, out: Path, fn) -> str:
    doc = yaml.safe_load(src.read_text())
    note = fn(doc)
    dumped = yaml.safe_dump(doc, sort_keys=False, width=110)
    if yaml.safe_load(dumped) != doc:
        sys.exit(f"round-trip drift while writing {out}")
    out.write_text(dumped)
    return note


def binder_of(doc, target):
    for e in doc["quantifiers"]["ordered"]:
        if str(e.get("binder")) == target:
            return e
    sys.exit(f"binder {target!r} not found")


def make_abs(doc, target, new_binder):
    binder_of(doc, target)["binder"] = new_binder
    return f"ordered binder {target!r} -> {new_binder!r} (identifier absent from formal)"


def make_nonbind_wcc(doc):
    f = doc["quantifiers"]["formal"]
    for a, b in ((WCC_TAIL_A, WCC_TAIL_B), (GAMMA_A, GAMMA_B), (JQ_A, JQ_B)):
        assert f.count(a) == 1, a
        f = f.replace(a, b)
    doc["quantifiers"]["formal"] = f + WCC_REMARK
    return ("formal re-binds the last quantifier over (a,b); (q,t0) survive only in a trailing "
            "remark (literal present -> frozen accepts, declared binder unbound)")


def make_nonbind_c2(doc):
    old = ("not exists a proper future C2 vacuum extension (M',g',iota) of (M,g).")
    new = ("not exists a proper future C2 vacuum extension (N,k,j) of (M,g); remark: the "
           "symbols (M',g',iota) are reserved for a later statement.")
    f = doc["quantifiers"]["formal"]
    assert f.count(old) == 1, old
    doc["quantifiers"]["formal"] = f.replace(old, new)
    return ("formal binds (N,k,j); declared binder (M',g',iota) appears only in a trailing "
            "remark (literal present -> frozen accepts, declared binder unbound)")


def make_nonbind_c0(doc):
    old = ("not exists a proper future C0 metric extension (M',g',iota) of (M,g).")
    new = ("not exists a proper future C0 metric extension (N,k,j) of (M,g); remark: the "
           "symbols (M',g',iota) are reserved for a later statement.")
    f = doc["quantifiers"]["formal"]
    assert f.count(old) == 1, old
    doc["quantifiers"]["formal"] = f.replace(old, new)
    return ("formal binds (N,k,j); declared binder (M',g',iota) appears only in a trailing "
            "remark (literal present -> frozen accepts, declared binder unbound)")


def make_span_probe(doc, filler: int):
    old = "(M',g',iota)"
    new = "(M'," + "x" * filler + ",g',iota)"
    f = doc["quantifiers"]["formal"]
    assert f.count(old) == 1
    doc["quantifiers"]["formal"] = f.replace(old, new)
    return (f"canonical tuple padded with {filler} filler chars inside the tuple "
            "(format variant, not a violation; FP-risk probe)")


def main() -> int:
    check_pins()
    build_patch()
    fx = HERE / "fixtures"
    if fx.exists():
        shutil.rmtree(fx)
    fx.mkdir(parents=True)
    rows = []

    for fid, cid, srcp in POS_COPIES:
        out = fx / f"{fid}_{srcp.stem}.yaml"
        shutil.copyfile(srcp, out)
        rows.append({"id": fid, "kind": "pos", "class_id": cid, "scored": True,
                     "source": str(srcp.relative_to(ROOT)), "source_sha256": sha(srcp),
                     "file": str(out.relative_to(ROOT)), "sha256": sha(out),
                     "mutation": "byte copy", "expect_frozen_r03": "accept",
                     "expect_v2_r03": "accept"})

    abs_specs = [("a01", "AF-WCC-VAC-GEN", WCC, "(q,t0)", "(q,t9)"),
                 ("a02", "AF-SCC-C2-VAC-GEN", C2, "(M',g',iota)", "(M',g',jota)"),
                 ("a03", "AF-SCC-C0-VAC-GEN", C0, "(M',g',iota)", "(M',g',jota)")]
    for fid, cid, srcp, target, newb in abs_specs:
        out = fx / f"{fid}_{srcp.stem}.yaml"
        note = mutate(srcp, out, lambda d, t=target, n=newb: make_abs(d, t, n))
        rows.append({"id": fid, "kind": "neg_abs", "class_id": cid, "scored": True,
                     "source": str(srcp.relative_to(ROOT)), "source_sha256": sha(srcp),
                     "file": str(out.relative_to(ROOT)), "sha256": sha(out),
                     "mutation": note, "expect_frozen_r03": "reject",
                     "expect_v2_r03": "reject"})

    nb_specs = [("b01", "AF-WCC-VAC-GEN", WCC, make_nonbind_wcc),
                ("b02", "AF-SCC-C2-VAC-GEN", C2, make_nonbind_c2),
                ("b03", "AF-SCC-C0-VAC-GEN", C0, make_nonbind_c0)]
    for fid, cid, srcp, fn in nb_specs:
        out = fx / f"{fid}_{srcp.stem}.yaml"
        note = mutate(srcp, out, fn)
        rows.append({"id": fid, "kind": "neg_nonbind", "class_id": cid, "scored": True,
                     "source": str(srcp.relative_to(ROOT)), "source_sha256": sha(srcp),
                     "file": str(out.relative_to(ROOT)), "sha256": sha(out),
                     "mutation": note, "expect_frozen_r03": "accept",
                     "expect_v2_r03": "reject"})

    for i, filler in enumerate((30, 100, 300)):
        out = fx / f"s{i + 1:02d}_c2_span_filler{filler}.yaml"
        note = mutate(C2, out, lambda d, k=filler: make_span_probe(d, k))
        rows.append({"id": f"s{i + 1:02d}", "kind": "span_probe", "class_id": "AF-SCC-C2-VAC-GEN",
                     "scored": False, "source": str(C2.relative_to(ROOT)), "source_sha256": sha(C2),
                     "file": str(out.relative_to(ROOT)), "sha256": sha(out), "mutation": note,
                     "expect_frozen_r03": "accept", "expect_v2_r03": "unscored"})

    manifest = {"artifact": "R03-V2-CALIBRATION-CORPUS", "generated_by": "make_r03v2.py",
                "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
                "frozen_source": str(SRC.relative_to(ROOT)), "frozen_source_sha256": SRC_SHA,
                "proposal_copy": "artifacts/worker-06/r03v2/audit_r03v2.py",
                "proposal_copy_sha256": sha(HERE / "audit_r03v2.py"),
                "scored_ids": [r["id"] for r in rows if r["scored"]],
                "rows": rows}
    (HERE / "fixture_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    prereg = {
        "artifact": "R03-V2-PREREGISTRATION",
        "owner": "worker-006",
        "node_id": "A1", "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "assigned_by": "astra-lead-formulation blocker lead-form-20260912T005843-94 "
                       "(node A1; falsifier names a stage-B rule change under which the "
                       "'(q,t0)' binder no longer fails)",
        "question": "Can the stage-B R03 binder-absence check stop falsely rejecting the "
                    "canonical WCC schema without losing its catch on genuinely unbound binders?",
        "rule": {
            "name": "R03-v2 binder-head co-binding",
            "replaces": "R03 lines 210-212 of artifacts/worker-06/spec_conformance_audit.py",
            "text": "every ordered binder's identifiers must appear, in order, in one quantifier "
                    "clause prefix (the 'binder head': text before the first top-level "
                    ": ; , with / such that / where / of / letting, parens never split), each "
                    "identifier within `span` chars of the previous one",
            "span_default": 80,
            "span_ablation": [13, 20, 40, 60, 80, 120, 1000000000],
        },
        "pins": {**PINS, str(SRC.relative_to(ROOT)): SRC_SHA,
                 "artifacts/worker-06/r03v2/fixture_manifest.json": sha(HERE / "fixture_manifest.json")},
        "corpus": {"positive_controls": 8, "neg_abs": 3, "neg_nonbind": 3,
                   "span_probes_unscored": 3,
                   "gate_negative_regression": "artifacts/formulation/fixtures/negative/*.yaml (30)"},
        "expectations": {
            "pos": "all 8 accepted by R03-v2 (frozen is expected to reject the WCC-class ones)",
            "neg_abs": "rejected by both frozen and R03-v2",
            "neg_nonbind": "frozen accepts (literal present), R03-v2 rejects",
        },
        "decision_rule": "R03-v2 is adoptable at a span iff FP(pos)=0 at that span AND catch(neg_abs)"
                         "=3 AND catch(neg_nonbind)=3; otherwise the span/corpus entry where it fails "
                         "is the reportable blind spot.",
        "falsifier": "Any positive control rejected by R03-v2 (false positive); any neg_abs accepted "
                     "by R03-v2 (lost catch); any gate negative whose frozen R03 rejection is not "
                     "reproduced by R03-v2 for a reason other than the declared literal-tuple "
                     "false-positive family; or any pinned input drift during the run.",
        "authority": "Proposal and measurement evidence only. NOT a gate verdict, NOT a node "
                     "completion, NOT a theorem. The schema owner (lead-formulation) adopts or "
                     "rejects the rule; the controller/lead owns any edit to the frozen tool.",
        "not_claimed": ["gate verdict", "node completion", "theorem", "physics result"],
    }
    (HERE / "preregistration.json").write_text(json.dumps(prereg, indent=1) + "\n")
    print("manifest", sha(HERE / "fixture_manifest.json"))
    print("prereg  ", sha(HERE / "preregistration.json"))
    print("copy    ", sha(HERE / "audit_r03v2.py"))
    print("fixtures", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
