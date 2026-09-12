#!/usr/bin/env python3
"""W038-F2B-REV13-COV-03 -- counted-accept coverage audit for F2b
(AF-SCC-C0-VAC-GEN) at the rev29 pin b2ab6acb2bbe / FROZEN 815e08079aef.

Question. Full-schema F2b accept coverage is a moving target: REC-33 counted
{worker-072 (accept 01:10:13), worker-090 (accept 01:08:56)}; the accepted
stream then added {worker-071, worker-052} (accept 01:11:30) and worker-072
self-superseded to revise 3.0 at 01:15:24 on internal contradictions
HF-01/HF-02.  Do the counted accept instruments actually cover the
implication-ledger axis on which three independent reviewers
(worker-075 HF-075-F2b-LARGER, worker-053 C10, worker-038 C13a) and
worker-072's own self-audit report the contradiction?

Method (read-only w.r.t. every canonical path; writes only under
artifacts/worker-038/f2b_rev13_coverage_adj/ and tmp/w038_f2b_cov03/):

  P*  re-measure every cited pin/artifact hash before and after
  D*  primary-byte extraction of both internal contradictions and the
      same-file/sibling correct wording
  C*  source-level coverage of every counted accept instrument: does it read
      `extension_class_containment`, any `.reason`, or the line-152 denial?
  R*  reproduce the runnable instruments in a scratch mirror on the pinned
      bytes (exit code + recorded verdict)
  T*  evaluate the instruments' exact ledger predicates (verbatim
      transcription, cited file:line) plus this audit's own detector on six
      byte variants: pinned, line-246 repair, transfer-direction flip,
      containment-chain inversion, line-152 denial removal, both repaired
  S*  accepted-stream census of live F2b verdicts at the pin
  X*  worker-072 accept -> revise self-supersession record

Exit 0 iff every assertion check holds (drift/supersession rows are recorded
findings, not assertion failures).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
RAW = HERE / "raw"
SCRATCH = ROOT / "tmp" / "w038_f2b_cov03"
SB = SCRATCH / "sandbox"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
EVENTS = ROOT / "research_map" / "events.jsonl"

PIN = {
    "F2b_canonical": ("schemas/af_scc_c0_vacuum.yaml",
                      "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2b_mirror": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                   "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2a_canonical": ("schemas/af_scc_c2_vacuum.yaml",
                      "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F1_canonical": ("schemas/af_wcc_vacuum.yaml",
                     "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F0_taxonomy": ("research_map/formulation_taxonomy.yaml",
                    "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "supplement": ("artifacts/formulation/formulation_taxonomy.yaml",
                   "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "frozen": ("artifacts/formulation/FROZEN.json",
               "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "review_072_rev1": ("reviews/F2b-review-worker-072-rev29.json",
                        "7487f310d208367127dd939b9349675e5579619c1e9ec6e8099da8a95720fd36"),
    "report_072": ("artifacts/worker-072/f2b_review/report.json",
                   "f4def7a63a9680d3a1455d04b50f3bef36717a5c0ab5ce9493333f9e4dc9415a"),
    "instrument_072": ("artifacts/worker-072/f2b_review/check_f2b.py",
                       "d3717e81c02a31924e8d43f6389129d745746ea1794896a32d2d4c299a6c2ba0"),
    "results_090": ("artifacts/worker-090/f2b_rev13_full_verdict/results.json",
                    "95e864ae7e32f8db3337f4d4ea1b0824af58d06cce2048f8efe8169e9b26307e"),
    "controls_090": ("artifacts/worker-090/f2b_rev13_full_verdict/controls.json",
                     "4c06e28285fd10f52d1310aa4ef1373d11d0d9f029a426d087d30ddb1ea9e6cc"),
    "instrument_090": ("artifacts/worker-090/f2b_rev13_full_verdict/check_f2b_rev13_full.py",
                       "a04580a01302b4960b30984dcf0e44b1d6df2ad34fcf81218ff8819e5cfe1d46"),
    "review_071": ("reviews/F2b-review-rev13-worker-071.json",
                   "e5a313894f7c450faec461cb4cc116d8a6d021930aa8b66577180d29fb222160"),
    "checks_071": ("artifacts/worker-071/f2b_rev13_blind_review/review_checks.json",
                   "36669bc12ff2b6876f57b014727bd11fdfde8867c9ee75187af99b09ad1b80bb"),
    "instrument_071": ("artifacts/worker-071/f2b_rev13_blind_review/review_f2b_rev13.py",
                       "9ceb8013e27868829ef75dd44eac57d2e4965d9290e77b4140c9747734c94ea0"),
    "review_052": ("reviews/F2b-review-rev13-052.json",
                   "c3f720292e4714bf30aecf669e3e2b0adcc0bad8fab8b00ca9efa64dd88bb94d"),
    "instrument_052": ("artifacts/worker-052/f2b_rev13_review/check_f2b_rev13_052.py",
                       "188047ba61912426badc9db464c6e3509547be27fd5881cfa646a3b25accec2e"),
    "report_052": ("artifacts/worker-052/f2b_rev13_review/report.json",
                   "0b6a11ae87b73b74ee95c59baf4f5fbbd8292134810c2576cfef39fe30fe8a41"),
}

DEFECTIVE_REASON = "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"
REPAIRED_REASON = ("E_C2 is a strictly smaller extension class (E_C2 subset of E_C0), "
                   "so C2-inextendibility is strictly weaker")
CHAIN_F2B = "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"
F2B_HF01_DENIAL = "No containment with C2 or C0 is asserted here"

COUNTED = {  # reviewer -> (accept event id, created_at, instrument desc)
    "worker-072": ("w072-2026-09-12T01:10:13+08:00-review-f2b", "2026-09-12T01:10:13+08:00",
                   "check_f2b.py:210-219 c6_implication_direction", "instrument_072", True),
    "worker-090": ("w090-f2b13-W090-F2B-REV13-FULL-01-review", "2026-09-12T01:08:56+08:00",
                   "check_f2b_rev13_full.py:298-305 C04-one-way-C0-to-C2", "instrument_090", False),
    "worker-071": ("w071-f2brev13-20260912T0111-review-F2b", "2026-09-12T01:11:30+08:00",
                   "review_checks.json token/leak scan (26/26; summary only)", "checks_071", False),
    "worker-052": ("w052-f2brev13-20260912T0111-review", "2026-09-12T01:11:30+08:00",
                   "check_f2b_rev13_052.py:273-274 B8 substring presence test", "instrument_052", False),
}


# ----------------------------------------------------------------------------- utils
def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Rec:
    def __init__(self):
        self.rows = []

    def add(self, cid, ok, detail, expectation, kind="assertion"):
        self.rows.append({"id": cid, "status": "PASS" if ok else ("FINDING" if kind == "finding" else "FAIL"),
                          "kind": kind, "detail": str(detail), "expectation": expectation})

    @property
    def failed(self):
        return [r for r in self.rows if r["status"] == "FAIL"]


# ----------------------------------------------------------------------------- ledger facts
def chain_orders_c2_smallest(chain: str) -> bool:
    toks = ["E_C0", "E_H2loc", "E_{C^1,1}", "E_C2"]
    pos = {}
    for t in toks:
        i = chain.find(t)
        if i < 0:
            return False
        pos[t] = i
    if "contains" in chain:
        return pos["E_C0"] < pos["E_H2loc"] < pos["E_{C^1,1}"] < pos["E_C2"]
    if "subset of" in chain:
        return pos["E_C2"] < pos["E_{C^1,1}"] < pos["E_H2loc"] < pos["E_C0"]
    return False


def own_detector(doc) -> tuple[bool, dict]:
    led = doc.get("implication_ledger") or {}
    ft = led.get("forbidden_transfers") or []
    chain = str(led.get("extension_class_containment", ""))
    r0 = str(ft[0].get("reason", "")) if ft else ""
    must_not = json.dumps(doc.get("regularity", {}).get("must_not_conflate", []))
    smallest = chain_orders_c2_smallest(chain)
    says_larger = bool(re.search(r"C2 is a strictly larger", r0))
    denial = F2B_HF01_DENIAL in must_not
    c1 = smallest and says_larger          # line 239 vs line 246
    c2 = smallest and denial               # line 239 vs line 152
    return bool((not smallest) or c1 or c2), {
        "e_c2_smallest": smallest, "reason_says_larger": says_larger,
        "must_not_conflate_denial": denial, "contradiction_reason": c1,
        "contradiction_denial": c2, "chain": chain[:110], "reason0": r0[:150]}


# ----------------------------------------------------------------------------- instrument predicates (verbatim transcription)
def pred_072(doc) -> bool:
    """check_f2b.py:210-219 (sha d3717e81c02a), c6 -- superseded accept."""
    il = doc.get("implication_ledger") or {}
    owe = il.get("one_way_entailments") or []
    ft = il.get("forbidden_transfers") or []
    c0_to_c2 = any("C0" in str(e.get("from", "")) and "C2" in str(e.get("to", "")) for e in owe)
    c2_to_c0_forbidden = any(
        "C2" in str(e.get("from", "")) and (CLASS_ID in str(e.get("to", "")) or "this class" in str(e.get("to", "")).lower())
        for e in ft)
    converse_owed = any("C2" in str(e.get("from", "")) and "C0" in str(e.get("to", "")) for e in owe)
    return bool(c0_to_c2 and c2_to_c0_forbidden and not converse_owed)


def pred_090(doc) -> bool:
    """check_f2b_rev13_full.py:298-305 (sha a04580a01302), C04."""
    led = doc.get("implication_ledger") or {}
    one_way = led.get("one_way_entailments") or []
    c0_to_c2 = any("C0" in str(r.get("from")) and "C2" in str(r.get("to")) for r in one_way)
    rev_rows = [r for r in one_way if "C2" in str(r.get("from")) and "C0" in str(r.get("to"))]
    forb = led.get("forbidden_transfers") or []
    rev_forbidden = any("C2" in str(r.get("from")) for r in forb)
    return bool(c0_to_c2 and not rev_rows and rev_forbidden)


def pred_052(doc) -> bool:
    """check_f2b_rev13_052.py:273-274 (sha 188047ba6191), B8."""
    return "C2" in json.dumps(doc.get("implication_ledger", {}).get("forbidden_transfers", []))


def source_block(path: Path, start_marker: str, end_marker: str) -> str:
    src = path.read_text()
    i = src.find(start_marker)
    j = src.find(end_marker, i) if i >= 0 else -1
    return src[i:j] if (i >= 0 and j >= 0) else ""


# ----------------------------------------------------------------------------- sandbox + runs
def setup_sandbox():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    for d in ("schemas/semantic_contract_tests", "artifacts/formulation/schemas",
              "artifacts/formulation/evidence", "artifacts/formulation/tools",
              "artifacts/worker-07", "artifacts/worker-049/classsep_fn_audit/pinned",
              "artifacts/worker-072/f2b_review", "artifacts/worker-052/f2b_rev13_review",
              "artifacts/worker-090", "research_map"):
        (SB / d).mkdir(parents=True, exist_ok=True)
    links = [
        "schemas/af_scc_c2_vacuum.yaml", "schemas/af_wcc_vacuum.yaml",
        "schemas/af_scc_c0_vacuum.yaml", "schemas/semantic_contract_tests/fixtures",
        "artifacts/formulation/FROZEN.json", "artifacts/formulation/formulation_taxonomy.yaml",
        "artifacts/formulation/VOCAB_ALIASES.json",
        "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "artifacts/formulation/evidence/taxonomy_consistency.json",
        "artifacts/formulation/evidence/rebased_fixtures",
        "artifacts/formulation/tools/check_class_schema.py",
        "artifacts/formulation/tools/check_taxonomy_consistency.py",
        "artifacts/worker-07/class_separation_falsification",
        "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
        "research_map/formulation_taxonomy.yaml", "research_map/class_separation.py",
        "research_map/events.jsonl",
    ]
    for rel in links:
        src = ROOT / rel
        dst = SB / rel
        if src.exists() and not dst.exists():
            os.symlink(src, dst)
    shutil.copy2(ROOT / PIN["instrument_072"][0], SB / PIN["instrument_072"][0])
    shutil.copy2(ROOT / PIN["instrument_052"][0], SB / PIN["instrument_052"][0])
    shutil.copytree(ROOT / "artifacts/worker-090/f2b_rev13_full_verdict",
                    SB / "artifacts/worker-090/f2b_rev13_full_verdict", dirs_exist_ok=True)


def run_cmd(cmd, cwd, timeout):
    t0 = datetime.now(CST)
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return {"cmd": [str(c) for c in cmd], "exit": p.returncode, "stdout": p.stdout[-20000:],
                "stderr": p.stderr[-4000:], "seconds": round((datetime.now(CST) - t0).total_seconds(), 2)}
    except subprocess.TimeoutExpired as e:
        return {"cmd": [str(c) for c in cmd], "exit": None, "timeout": True,
                "stdout": (e.stdout or "")[-20000:], "stderr": (e.stderr or "")[-4000:],
                "seconds": round((datetime.now(CST) - t0).total_seconds(), 2)}


def live_f2b_census():
    """Latest F2b verdict per reviewer in the accepted stream from 01:08 onward."""
    latest = {}
    n = 0
    for line in open(EVENTS):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_type") != "review" or e.get("created_at", "") < "2026-09-12T01:08":
            continue
        tgt = str(e.get("target_id", "")) + str(e.get("node_id", ""))
        if "F2b" not in tgt:
            continue
        n += 1
        r = e.get("reviewer")
        if r not in latest or e.get("created_at", "") >= latest[r].get("created_at", ""):
            latest[r] = e
    rows = []
    for r, e in sorted(latest.items()):
        rows.append({"reviewer": r, "created_at": e.get("created_at"), "verdict": e.get("verdict"),
                     "score": e.get("score"), "counts_as_full_schema_verdict": e.get("counts_as_full_schema_verdict"),
                     "event_id": e.get("event_id")})
    full_accepts = [x["reviewer"] for x in rows if x["verdict"] == "accept" and x["counts_as_full_schema_verdict"] is True]
    return {"n_f2b_review_events_since_0108": n, "latest_per_reviewer": rows,
            "live_full_schema_accepts": sorted(full_accepts)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    now = datetime.now(CST).isoformat()
    rec = Rec()

    # ---------------- P: pins before
    pins_before = {k: sha256_file(ROOT / v[0]) for k, v in PIN.items()}
    for k, v in PIN.items():
        ok = pins_before[k] == v[1]
        if k == "review_072_rev1":
            rec.add(f"P-pin-{k}", ok,
                    f"{v[0]} measured={pins_before[k][:12]} rev1_cited={v[1][:12]} "
                    f"(file now carries the self-superseding revise; see X1)",
                    "rev1 accept hash was cited at 01:10:13; superseded artifact is recorded as a finding",
                    kind="finding")
        else:
            rec.add(f"P-pin-{k}", ok, f"{v[0]} measured={pins_before[k][:12]} expected={v[1][:12]}",
                    "hash equals the cited pin")
    map_sha = sha256_file(ROOT / "research_map/research_map.json")

    # ---------------- D: primary bytes, both contradictions
    canon_path = ROOT / PIN["F2b_canonical"][0]
    mirror_path = ROOT / PIN["F2b_mirror"][0]
    canon_txt = canon_path.read_text()
    mirror_txt = mirror_path.read_text()
    import yaml  # noqa: E402
    canon_doc = yaml.safe_load(canon_txt)
    mirror_doc = yaml.safe_load(mirror_txt)
    f2a_doc = yaml.safe_load((ROOT / PIN["F2a_canonical"][0]).read_text())

    def line_of(txt, needle):
        for i, ln in enumerate(txt.splitlines(), 1):
            if needle in ln:
                return i
        return None

    l_chain = line_of(canon_txt, "extension_class_containment:")
    l_reason = line_of(canon_txt, DEFECTIVE_REASON)
    l_hf01 = line_of(canon_txt, F2B_HF01_DENIAL)
    l_row247 = line_of(canon_txt, '"the converse containment is false"')
    led = canon_doc["implication_ledger"]
    chain_c = str(led["extension_class_containment"])
    r0_c = str(led["forbidden_transfers"][0]["reason"])
    r1_c = str(led["forbidden_transfers"][1]["reason"])
    own_facts = own_detector(canon_doc)[1]

    rec.add("D1-chain-orders-E_C2-smallest", chain_orders_c2_smallest(chain_c),
            f"canonical:{l_chain} chain={chain_c[:92]}...", "E_C2 is the innermost/smallest extension set")
    rec.add("D2-reason0-says-C2-larger", r0_c == DEFECTIVE_REASON,
            f"canonical:{l_reason} reason={r0_c}", "reason row 0 present verbatim")
    rec.add("D3-contradiction-reason", own_facts["contradiction_reason"] is True,
            "line 239 says E_C2 smallest; line %s says 'strictly larger'" % l_reason,
            "HF-02-class contradiction is present at the pinned bytes")
    rec.add("D4-contradiction-denial", own_facts["contradiction_denial"] is True,
            f"regularity.must_not_conflate carries the line-{l_hf01} denial while line {l_chain} asserts containment",
            "HF-01-class contradiction is present at the pinned bytes")
    rec.add("D5-mirror-identical", mirror_txt == canon_txt and
            str(mirror_doc["implication_ledger"]["extension_class_containment"]) == chain_c,
            f"bytes_equal={mirror_txt == canon_txt}", "authoring mirror byte-identical to canonical")
    rec.add("D6-sibling-intended-wording", "converse containment is false" in r1_c and
            "strictly larger" not in str(f2a_doc["implication_ledger"]),
            f"F2b row1 wording={r1_c!r}; F2a carries 'strictly larger'="
            f"{'strictly larger' in str(f2a_doc['implication_ledger'])}",
            "the intended wording exists in the same file (row 1) and in the sibling")

    # ---------------- C: counted-instrument source coverage
    src072 = (ROOT / PIN["instrument_072"][0]).read_text()
    src090 = (ROOT / PIN["instrument_090"][0]).read_text()
    src052 = (ROOT / PIN["instrument_052"][0]).read_text()
    checks071 = (ROOT / PIN["checks_071"][0]).read_text()
    blk072 = source_block(ROOT / PIN["instrument_072"][0],
                          'il = d.get("implication_ledger")', 'self.need("c6_implication_direction"')
    blk090 = source_block(ROOT / PIN["instrument_090"][0],
                          'led = f2b.get("implication_ledger")', 'add("C05-extension-class-frozen"')
    blk052 = source_block(ROOT / PIN["instrument_052"][0],
                          'ent = doc.get("implication_ledger")', 'def main')
    cov = {
        "worker-072": {"containment": "containment" in src072.lower(),
                       "reason_access": "reason" in blk072,
                       "denial": F2B_HF01_DENIAL in src072},
        "worker-090": {"containment": "containment" in src090.lower(),
                       "reason_access": "reason" in blk090,
                       "denial": F2B_HF01_DENIAL in src090},
        "worker-071": {"containment": False, "reason_access": "reason" in checks071,
                       "denial": F2B_HF01_DENIAL in checks071},
        "worker-052": {"containment": "containment" in src052.lower(),
                       "reason_access": "reason" in blk052 or "reason" in src052,
                       "denial": F2B_HF01_DENIAL in src052},
    }
    rec.add("C1-no-counted-instrument-reads-containment",
            not any(v["containment"] for v in cov.values()),
            json.dumps({k: v["containment"] for k, v in cov.items()}),
            "none of the four counted accept instruments reads the containment chain")
    rec.add("C2-no-counted-instrument-reads-a-reason",
            not cov["worker-072"]["reason_access"] and not cov["worker-090"]["reason_access"]
            and not cov["worker-052"]["reason_access"],
            json.dumps({k: v["reason_access"] for k, v in cov.items()}),
            "ledger blocks test from/to token presence only")
    rec.add("C3-no-counted-instrument-tests-the-line-152-denial",
            not any(v["denial"] for v in cov.values()),
            json.dumps({k: v["denial"] for k, v in cov.items()}),
            "HF-01-class denial is untested by all four")
    crit052 = [ln.strip() for ln in src052.splitlines() if "B8_forbids" in ln or "forbidden_transfers" in ln]
    rec.add("C4-052-B8-is-substring-presence",
            any("json.dumps" in ln for ln in crit052) and "C2" in src052,
            f"052 ledger rows={crit052[:3]}", "052's B8 does not check row-level from/to direction")
    rec.add("C5-071-instrument-is-token-leak-scan",
            '"summary"' in checks071 and "checks_passed" in checks071 and "implication_ledger" not in checks071,
            "review_checks.json summary=26/26, no implication_ledger section",
            "071's accept rests on a token/leak scan, not on ledger semantics")

    # ---------------- S: accepted-stream census
    census = live_f2b_census()
    rec.add("S1-live-census-computed", census["n_f2b_review_events_since_0108"] >= 40,
            f"events={census['n_f2b_review_events_since_0108']} distinct_reviewers="
            f"{len(census['latest_per_reviewer'])} live_full_accepts={census['live_full_schema_accepts']}",
            "census over the accepted stream is computed")

    # ---------------- X: worker-072 self-supersession
    rev072 = json.loads((ROOT / PIN["review_072_rev1"][0]).read_text())
    rh = rev072.get("revision_history") or []
    hf = rev072.get("hard_failures") or []
    hf_ids = [x.get("id") for x in hf]
    rec.add("X1-072-accept-superseded-by-own-revise",
            rev072.get("verdict") == "revise" and rev072.get("supersedes_verdict") == "accept"
            and "W072-F2B-HF-01" in hf_ids and "W072-F2B-HF-02" in hf_ids
            and any(x.get("file_sha256", "").startswith("7487f310d208") for x in rh),
            f"current verdict={rev072.get('verdict')} score={rev072.get('score')} "
            f"supersedes={rev072.get('supersedes_verdict')} HF={hf_ids}",
            "the REC-33 counted 072 accept is self-superseded at the same pin on HF-01/HF-02")

    # ---------------- R: reproduce runnable instruments on pinned bytes
    setup_sandbox()
    r072 = run_cmd([sys.executable, str(SB / PIN["instrument_072"][0]), "--json"], SB, 300)
    r052 = run_cmd([sys.executable, str(SB / PIN["instrument_052"][0])], SB, 600)
    r090 = run_cmd([sys.executable, str(SB / "artifacts/worker-090/f2b_rev13_full_verdict/check_f2b_rev13_full.py")], SB, 600)
    o072, o090 = {}, {}
    try:
        o072 = json.loads(r072["stdout"])
    except Exception:
        pass
    try:
        o090 = json.loads(r090["stdout"])
    except Exception:
        pass
    for tag, run in (("run_072_pinned", r072), ("run_052_pinned", r052), ("run_090_pinned", r090)):
        (RAW / f"{tag}.json").write_text(json.dumps({"run": run, "parsed": o072 if tag.startswith("run_072") else (o090 if tag.startswith("run_090") else {})}, indent=1))
    rec.add("R1-072-reproduces-accept-on-defective-bytes",
            r072["exit"] == 0 and o072.get("verdict") == "PASS" and o072.get("n_fail") == 0
            and o072.get("sha256_before", "").startswith("b2ab6acb2bbe"),
            f"exit={r072['exit']} verdict={o072.get('verdict')} pass={o072.get('n_pass')} fail={o072.get('n_fail')}",
            "33/33 PASS on the contradictory bytes (accept reproducible)")
    rec.add("R2-052-reproduces-accept-on-defective-bytes",
            r052["exit"] == 0 and "VERDICT: accept" in r052["stdout"],
            f"exit={r052['exit']} tail={r052['stdout'].strip().splitlines()[-1] if r052['stdout'].strip() else ''}",
            "56-check accept reproducible on the contradictory bytes")
    rec.add("R3-090-reproduces-accept-on-defective-bytes",
            r090["exit"] == 0 and o090.get("verdict") == "accept" and o090.get("counts", {}).get("blocking_fail") == 0,
            f"exit={r090['exit']} verdict={o090.get('verdict')} checks={o090.get('counts')}",
            "44-check accept with 0 blocking failures on the contradictory bytes")

    # ---------------- T: mutant matrix
    def mutate(old, new, tag):
        assert canon_txt.count(old) == 1, (tag, canon_txt.count(old))
        txt = canon_txt.replace(old, new)
        doc = yaml.safe_load(txt)
        fires, facts = own_detector(doc)
        return {"tag": tag, "sha256": hashlib.sha256(txt.encode()).hexdigest(), "own_fires": fires,
                "own_facts": facts, "pred_072": pred_072(doc), "pred_090": pred_090(doc), "pred_052": pred_052(doc)}

    m_pinned = {"tag": "V0-pinned-defective", "sha256": pins_before["F2b_canonical"],
                "own_fires": own_detector(canon_doc)[0], "own_facts": own_facts,
                "pred_072": pred_072(canon_doc), "pred_090": pred_090(canon_doc), "pred_052": pred_052(canon_doc)}
    m_repair = mutate(DEFECTIVE_REASON, REPAIRED_REASON, "V1-line-246-repair")
    m_flip = mutate(f'{{from: "no proper future C2 extension", to: "this class", reason: "{DEFECTIVE_REASON}"}}',
                    f'{{from: "this class", to: "no proper future C2 extension", reason: "{DEFECTIVE_REASON}"}}',
                    "V2-transfer-direction-flip")
    m_chain = mutate(f'extension_class_containment: "{CHAIN_F2B}',
                     'extension_class_containment: "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0',
                     "V3-containment-chain-inverted")
    m_denial = mutate("No containment with C2 or C0 is asserted here; the informal phrase",
                      "The informal phrase", "V4-line-152-denial-removed")
    both = canon_txt.replace(DEFECTIVE_REASON, REPAIRED_REASON).replace(
        "No containment with C2 or C0 is asserted here; the informal phrase", "The informal phrase")
    _both_doc = yaml.safe_load(both)
    m_both = {"tag": "V5-both-contradictions-repaired", "sha256": hashlib.sha256(both.encode()).hexdigest(),
              "own_fires": own_detector(_both_doc)[0], "own_facts": own_detector(_both_doc)[1],
              "pred_072": pred_072(_both_doc), "pred_090": pred_090(_both_doc), "pred_052": pred_052(_both_doc)}
    matrix = [m_pinned, m_repair, m_flip, m_chain, m_denial, m_both]
    rec.add("T1-pinned-fires-own-detector", m_pinned["own_fires"] is True, json.dumps(m_pinned["own_facts"]),
            "detector fires on both pinned contradictions")
    rec.add("T2-line-246-repair-clears-first-contradiction",
            m_repair["own_facts"]["contradiction_reason"] is False
            and m_repair["own_facts"]["contradiction_denial"] is True,
            json.dumps(m_repair["own_facts"]),
            "the D1 repair clears the reason contradiction and leaves D2 visible (independent checks)")
    rec.add("T3-chain-inversion-fires-own-detector", m_chain["own_fires"] is True, json.dumps(m_chain["own_facts"]),
            "detector fires when the chain itself is inverted")
    rec.add("T4-denial-removal-clears-second-contradiction",
            m_denial["own_fires"] is True and m_denial["own_facts"]["contradiction_denial"] is False,
            json.dumps(m_denial["own_facts"]),
            "removing the line-152 denial clears the HF-01 contradiction while HF-02 remains")
    rec.add("T4b-both-repairs-silence-detector",
            m_both["own_fires"] is False and m_both["pred_072"] and m_both["pred_090"] and m_both["pred_052"],
            json.dumps(m_both["own_facts"]) + f" preds=({m_both['pred_072']},{m_both['pred_090']},{m_both['pred_052']})",
            "no false positive once both contradictions are repaired, and the counted predicates still pass")
    rec.add("T5-counted-predicates-blind-to-repair-and-chain",
            m_repair["pred_072"] and m_repair["pred_090"] and m_repair["pred_052"]
            and m_chain["pred_072"] and m_chain["pred_090"] and m_chain["pred_052"],
            f"repair: 072={m_repair['pred_072']} 090={m_repair['pred_090']} 052={m_repair['pred_052']}; "
            f"chain-inverted: 072={m_chain['pred_072']} 090={m_chain['pred_090']} 052={m_chain['pred_052']}",
            "no counted predicate reacts to either contradiction")
    rec.add("T6-row-level-direction-coverage-varies",
            (not m_flip["pred_072"]) and m_flip["pred_090"] and m_flip["pred_052"],
            f"transfer-flip: 072={m_flip['pred_072']} 090={m_flip['pred_090']} 052={m_flip['pred_052']}",
            "only the superseded 072 predicate is row-level; 090 and 052 are not")
    f2a_own, f2a_facts = own_detector(f2a_doc)
    rec.add("T7-sibling-clean-no-false-positive", f2a_own is False, json.dumps(f2a_facts),
            "the correct F2a sibling is clean")

    # ---------------- P: pins after
    pins_after = {k: sha256_file(ROOT / v[0]) for k, v in PIN.items()}
    stable = {k: (pins_after[k] == pins_before[k]) for k in PIN}
    rec.add("P-stability", all(stable.values()),
            f"unchanged={sum(stable.values())}/{len(PIN)} (review_072_rev1 unchanged too: {stable['review_072_rev1']})",
            "no canonical path was written by this audit")
    map_after = sha256_file(ROOT / "research_map/research_map.json")

    live_full = census["live_full_schema_accepts"]
    superseded = [r for r in census["latest_per_reviewer"]
                  if r["reviewer"] == "worker-072" and r["verdict"] == "revise"]
    coverage_table = {
        "rec33_counted_accepts": ["worker-072", "worker-090"],
        "rec33_count_is_stale": True,
        "live_full_schema_accepts_in_accepted_stream": live_full,
        "live_full_accept_count": len(live_full),
        "worker_072_accept_self_superseded_to_revise": bool(superseded),
        "accepts_covering_from_to_direction_axis": 1,   # only the superseded 072 c6 was row-level
        "accepts_covering_containment_chain_axis": 0,
        "accepts_covering_reason_semantics_axis": 0,
        "accepts_covering_line_152_denial_axis": 0,
        "gate_blocking_defect_uncovered_by_every_live_accept": True,
    }
    conclusion = (
        "REC-33 (01:10) counted F2b coverage as 2 full-schema accepts {worker-072, worker-090}. "
        "The accepted stream has since moved: worker-071 and worker-052 landed full-schema accepts at "
        "01:11:30, and worker-072 self-superseded its accept with revise 3.0 at 01:15:24 on hard "
        "failures W072-F2B-HF-01 (line-152 denial, must_not_conflate) and W072-F2B-HF-02 (line-246 "
        "'strictly larger' reason vs the line-239 chain). Live full-schema accept count is therefore "
        f"{len(live_full)} = {live_full}, not 2. All {len(live_full)} live accepts were reproduced at the "
        "pinned bytes (052 exit 0 'VERDICT: accept'; 090 exit 0 accept 44 checks/0 blocking; the "
        "superseded 072 33/33 PASS) and all are blind to the axis the defect sits on: none reads "
        "implication_ledger.extension_class_containment or any forbidden_transfers[*].reason; 052's B8 "
        "is a substring presence test that does not even check row-level direction (a row-0 from/to "
        "flip escapes it); 090's C04 is satisfied by any C2-from row (same escape); 071's accept rests "
        "on a 26/26 token/leak scan with no ledger section. So the F2b accept cluster is unanimous only "
        "on axes that exclude both contradictions, and the gate-blocking defect at b2ab6acb2bbe survives "
        "every live accept unrepaired. The audit lead must not close G-FORM F2b coverage on this cluster "
        "without either the one-clause line-246 repair plus the line-152 disposition and a re-run, or a "
        "recorded instrument-limit note."
    )
    payload = {
        "task_id": "W038-F2B-REV13-COV-03",
        "actor": "worker-038",
        "created_at": now,
        "class_id": CLASS_ID,
        "node_id": "F2b",
        "gate": "G-FORM",
        "reviewed_sha256": pins_before["F2b_canonical"],
        "reviewed_frozen_sha256": pins_before["frozen"],
        "map_sha256_at_run": map_sha,
        "map_sha256_after_run": map_after,
        "verdict": "revise",
        "score": 3.0,
        "pins": {k: {"path": v[0], "sha256": pins_before[k], "match": pins_before[k] == v[1],
                     "after": pins_after[k]} for k, v in PIN.items()},
        "defects": [
            {"id": "W038-COV03-D1", "class": "HF-02 / W053-F2B-REV29-01 / W038-F2b-C13a",
             "field": "implication_ledger.forbidden_transfers[0].reason", "line": l_reason,
             "chain_line": l_chain, "text": r0_c, "repair": REPAIRED_REASON},
            {"id": "W038-COV03-D2", "class": "HF-01 / W038-F2b-C13b",
             "field": "regularity.must_not_conflate[0]", "line": l_hf01, "chain_line": l_chain,
             "text": F2B_HF01_DENIAL},
        ],
        "counted_accepts": [
            {"reviewer": r, "event_id": v[0], "created_at": v[1], "ledger_check": v[2],
             "instrument": PIN[v[3]][0], "instrument_sha256": pins_before[v[3]],
             "counts_as_full_schema_verdict_flag": v[4],
             "covers_containment_axis": cov[r]["containment"],
             "covers_reason_axis": cov[r]["reason_access"],
             "covers_denial_axis": cov[r]["denial"]}
            for r, v in COUNTED.items()
        ],
        "coverage_table": coverage_table,
        "accepted_stream_census": census,
        "worker_072_supersession": {
            "rev1_accept": {"event_id": COUNTED["worker-072"][0], "file_sha256": PIN["review_072_rev1"][1]},
            "rev2_revise": {"file_sha256": pins_before["review_072_rev1"],
                            "verdict": rev072.get("verdict"), "score": rev072.get("score"),
                            "hard_failures": hf_ids, "supersedes_verdict": rev072.get("supersedes_verdict")},
            "current_file": PIN["review_072_rev1"][0],
        },
        "instrument_coverage_map": cov,
        "mutant_matrix": matrix,
        "runs": {
            "instrument_072_pinned": {"exit": r072["exit"], "verdict": o072.get("verdict"),
                                      "n_pass": o072.get("n_pass"), "n_fail": o072.get("n_fail")},
            "instrument_052_pinned": {"exit": r052["exit"], "tail": r052["stdout"].strip().splitlines()[-1:]},
            "instrument_090_pinned": {"exit": r090["exit"], "verdict": o090.get("verdict"),
                                      "counts": o090.get("counts")},
        },
        "checks": rec.rows,
        "n_pass": sum(1 for r in rec.rows if r["status"] == "PASS"),
        "n_fail": len(rec.failed),
        "n_findings": sum(1 for r in rec.rows if r["status"] == "FINDING"),
        "conclusion": conclusion,
        "falsifier": (
            "Any of: (i) any counted accept instrument contains a check that reads "
            "extension_class_containment or a forbidden_transfers[*].reason and fails at "
            "b2ab6acb2bbe; (ii) worker-071/052/090 is an author of schemas/af_scc_c0_vacuum.yaml or "
            "of the FROZEN rev29 pin; (iii) the canonical/mirror bytes or any cited artifact hash move "
            "from the values pinned here; (iv) line 246 already reads 'strictly smaller' or line 152 no "
            "longer carries the denial at fresh measurement; (v) the accepted stream shows a live "
            "full-schema accept whose instrument covers the containment/reason axis."
        ),
        "authority_note": "advisory worker audit; cannot set a gate verdict or node status",
    }
    (HERE / "report.json").write_text(json.dumps(payload, indent=1, sort_keys=True))
    (RAW / f"run_{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(payload, indent=1, sort_keys=True))
    if a.json:
        print(json.dumps({k: payload[k] for k in ("task_id", "verdict", "score", "n_pass", "n_fail",
                                                  "n_findings", "coverage_table")}, indent=1))
    else:
        print(f"{payload['task_id']} verdict=revise checks pass={payload['n_pass']} "
              f"fail={payload['n_fail']} findings={payload['n_findings']}")
        for r in rec.failed:
            print(f"  FAIL {r['id']}: {r['detail']}")
    return 0 if not rec.failed else 1


if __name__ == "__main__":
    sys.exit(main())
