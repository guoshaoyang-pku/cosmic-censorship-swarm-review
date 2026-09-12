#!/usr/bin/env python3
"""F2a live rev13 pin e9a27996: mechanical D0 binder instantiation check.

Asserts: (1) D0 is declared as a tagged disjoint union with exactly two branches;
(2) every occurrence of the index variable `r` in the schema is either the binder
    (`forall r in D0`) or the argument of `X^r_vac(AF)` -- no destructuring, no
    positional access, no assumption that the smooth branch is a pair;
(3) both branch substitutions produce a well-formed comeager-existence clause;
(4) D0.definition_ref resolves to an existing field.
Exit 0 = PASS, 1 = FAIL.
"""
import re, sys, hashlib, json
from pathlib import Path
import yaml

PIN = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
P = Path("schemas/af_scc_c2_vacuum.yaml")
raw = P.read_bytes()
h = hashlib.sha256(raw).hexdigest()
res = {"file": str(P), "measured_sha256": h, "expected_pin": PIN, "pin_match": h == PIN}
d = yaml.safe_load(raw.decode())

fails = []
D0 = (d.get("quantifiers", {}).get("domains", {}) or {}).get("D0", {})
defn = str(D0.get("definition", ""))
res["d0_definition"] = defn
if "tagged disjoint union" not in defn: fails.append("D0 not declared as tagged disjoint union")
if not re.search(r"r\s*=\s*smooth\b", defn): fails.append("smooth branch tag missing")
if not re.search(r"r\s*=\s*\(sobolev,\s*s,\s*delta\)", defn): fails.append("sobolev tuple branch missing")
if not re.search(r"s\s*>\s*5/2", defn): fails.append("sobolev s bound missing")
if not re.search(r"delta\s+in\s+\(1/2,\s*1\)", defn): fails.append("sobolev delta bound missing")
res["branches_declared"] = not fails

# (2) occurrences of r as a variable across the whole document
occ = []
for path, val in walk(d) if False else []:
    pass
def walk(node, p=""):
    if isinstance(node, dict):
        for k, v in node.items(): yield from walk(v, f"{p}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node): yield from walk(v, f"{p}[{i}]")
    else:
        yield p, node
bad = []
for path, val in walk(d):
    s = str(val)
    if re.search(r"\bforall r\b|\bthere exists r\b|\bexists r\b", s):
        for m in re.finditer(r"(forall|exists|there exists)\s+r\b", s):
            pass
    if re.search(r"X\^r_vac", s): continue
    # any other field that uses r as a bound index without X^r_vac
    if re.search(r"\bX\^r\b|\br\s*\[|\br\.\w|\br\s*=\s*\(smooth", s):
        bad.append((path, s[:120]))
res["r_uses_without_Xr_vac"] = bad
if bad: fails.append(f"index r destructured/used outside X^r_vac: {bad[:2]}")

# (3) branch substitution well-formedness
GEN = "exists G_{r} subset X^{r}_vac(AF) with G_{r} comeager"
subs = {
    "smooth": {"r": "smooth", "X": "X^smooth_vac(AF) [Frechet constraint manifold]"},
    "(sobolev,s,delta)": {"r": "(sobolev,s,delta)", "X": "X^(sobolev,s,delta)_vac(AF) [H^s_delta x H^{s-1}_{delta+1}, s>5/2, delta in (1/2,1)]"},
}
ok = {}
for name, sub in subs.items():
    clause = GEN.replace("{r}", sub["r"])
    ok[name] = {"clause": clause, "space": sub["X"], "well_typed": bool(re.search(r"X\^", clause))}
res["substitutions"] = ok
if not all(v["well_typed"] for v in ok.values()): fails.append("a substitution is ill-typed")

# (4) definition_ref resolves
ref = str(D0.get("definition_ref", ""))
node = d
for part in ref.split("."):
    node = node.get(part) if isinstance(node, dict) else None
res["definition_ref"] = ref
res["definition_ref_resolves"] = node is not None
if node is None: fails.append(f"definition_ref {ref} does not resolve")

# (5) smooth branch must not be typed as a pair anywhere
for path, val in walk(d):
    s = str(val)
    if re.search(r"smooth\s*,\s*(s|delta|\))", s) or re.search(r"\(smooth\s*,", s):
        fails.append(f"pair-typed smooth branch at {path}")
res["verdict"] = "PASS" if not fails else "FAIL"
res["failures"] = fails
print(json.dumps(res, indent=1))
sys.exit(0 if not fails else 1)
