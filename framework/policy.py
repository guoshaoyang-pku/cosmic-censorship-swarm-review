"""
Selection policies -- the thing that actually varies between architectures.

"Does memory help" is not a question worth spending compute on; the answer is obvious before
you run it, and the 200-call budget curve only confirmed it in a way that took two hours to
become suggestive-but-not-significant. The question that discriminates is WHICH STRUCTURE of
memory works, so the structure is the plugin and everything else -- model, task, verifier,
budget, prompt template -- is held fixed.

Each policy answers exactly one question: given the archive, what goes into the next prompt?

  none            nothing. Tabula rasa, the null.
  flat_elite      the global best k. Pure exploitation. openevolve's default is 70% this.
  islands         FunSearch: pick an island, softmax over cell scores inside it.
  map_elites      pick uniformly among OCCUPIED CELLS, ignoring score. Diversity-first.
  novelty         pick from the LEAST represented cells. Anti-exploitation.
  deadends_only   no parents at all, only the refuted-region list.
  islands_deadend islands, plus the refuted-region list.

The last three are the interesting ones: `deadends_only` isolates whether refutation alone
carries information (nobody broadcasts failure -- neither FunSearch nor the AlphaEvolve
lineage does), and `novelty` tests whether the archive's value is the elites or the map.
"""
from __future__ import annotations
import math, random
from core import Archive, Candidate, DeadEnds


def _cells(arch: Archive, island=None):
    out = []
    with arch.lock:
        rng_islands = range(arch.n_islands) if island is None else [island]
        for i in rng_islands:
            for d, c in arch.islands[i].items():
                out.append((i, d, c, arch.scores[i][d]))
    return out


def none(arch, dead, island, k, rng):
    return [], []


def flat_elite(arch, dead, island, k, rng):
    cs = _cells(arch)
    cs.sort(key=lambda t: -t[3])
    return [c for _, _, c, _ in cs[:k]], []


def islands(arch, dead, island, k, rng):
    return arch.sample_parents(island, k, rng), []


def map_elites(arch, dead, island, k, rng):
    """Uniform over occupied cells. Deliberately ignores score: the claim being tested is that
    the archive's value is the MAP -- coverage of behaviour space -- not the elites in it."""
    cs = _cells(arch)
    if not cs:
        return [], []
    picked = rng.sample(cs, min(k, len(cs)))
    return [c for _, _, c, _ in picked], []


def novelty(arch, dead, island, k, rng):
    """Prefer cells that few islands have reached. Anti-exploitation: if the search collapses
    because everyone chases the leader, this is the policy that should not collapse."""
    cs = _cells(arch)
    if not cs:
        return [], []
    occ = {}
    for _, d, _, _ in cs:
        occ[d] = occ.get(d, 0) + 1
    cs.sort(key=lambda t: (occ[t[1]], -t[3]))
    return [c for _, _, c, _ in cs[:k]], []


def deadends_only(arch, dead, island, k, rng):
    """No parents at all. Isolates the information content of refutation by itself."""
    return [], dead.recent()


def islands_deadend(arch, dead, island, k, rng):
    return arch.sample_parents(island, k, rng), dead.recent()


POLICIES = dict(none=none, flat_elite=flat_elite, islands=islands, map_elites=map_elites,
                novelty=novelty, deadends_only=deadends_only,
                islands_deadend=islands_deadend)
