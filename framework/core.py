"""
Core of the search swarm: task protocol, verified-only archive, retractable ledger,
dead-end channel, instrumentation.

Design is not free-form -- every structural choice below is forced by something measured
in this project on 2026-09-09/10:

  * The archive accepts ONLY machine-verified artifacts. FunSearch gets this right and it is
    why it has no error-propagation problem at all: the LLM's reasoning never enters the store,
    only code that ran. Everything an agent merely *claims* stays out.
  * Proposer heterogeneity was the one lever that moved anything offline (37% of useful
    coverage) while every orchestration mechanism sat in the noise -- but with a real LLM
    proposer, mixing in a weaker family LOST on every axis. So the pool is heterogeneous by
    default AND the ledger accounts per family, because whether heterogeneity pays is
    task-dependent and has to be measured, not assumed.
  * Dead ends are broadcast; winners are not. Two generations of systems (FunSearch 2023,
    AlphaEvolve lineage 2025-26) broadcast only the best program and nothing about failure.
    Broadcasting winners is what drives premature convergence; broadcasting refuted regions
    prunes without steering. My own A/B found this cuts island redundancy ~17% without
    improving the score, so it is instrumented rather than assumed to help.
  * Everything is instrumented. Without coverage/redundancy/late-growth you cannot tell
    "the swarm is exploring" from "the swarm collapsed 40 minutes ago", and no open
    implementation measures any of it.
"""
from __future__ import annotations
import json, os, time, math, threading, hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Iterable


# ---------------------------------------------------------------- task protocol

@dataclass
class Candidate:
    """What a proposer produces. `payload` is whatever the task's verifier consumes."""
    payload: Any
    source: str                      # agent id
    family: str                      # model family, for per-family accounting
    parents: list[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class Verdict:
    """What the verifier returns. This is the only thing allowed to enter the archive."""
    ok: bool                          # did it verify at all (well-formed, ran, legal object)
    solved: bool                      # is it a full answer to the problem
    score: float                      # higher is better; comparable within a task
    descriptor: tuple                 # behaviour coordinates for the archive grid
    evidence: dict = field(default_factory=dict)
    reason: str = ""                  # why it failed, when it did


class Task:
    """A problem the swarm can attack. Subclass and implement all four."""
    name: str = "task"
    descriptor_axes: tuple = ()

    def prompt(self, parents: list[Candidate], deadends: list[str]) -> str:
        raise NotImplementedError

    def parse(self, raw: str) -> Any | None:
        raise NotImplementedError

    def verify(self, payload: Any) -> Verdict:
        """MUST be deterministic, machine-checkable, and cheap in HUMAN hours.
        This is the whole gate. If it needs a person to read it, the task does not belong
        in this framework."""
        raise NotImplementedError

    def deadend_key(self, payload: Any, v: Verdict) -> str | None:
        """A short, reusable statement of a refuted region, or None. This is what gets
        broadcast -- never a promising direction."""
        return None


# ---------------------------------------------------------------- archive

class Archive:
    """Islands of MAP-Elites cells. A cell keyed by behaviour descriptor keeps its own best,
    so a mediocre entry in an unexplored cell survives -- it competes only inside its cell,
    never against the global leader. That property is the reason a low-scoring but structurally
    novel candidate does not get eliminated early."""

    def __init__(self, n_islands=5, rng=None):
        self.n_islands = n_islands
        self.islands: list[dict[tuple, Candidate]] = [{} for _ in range(n_islands)]
        self.scores: list[dict[tuple, float]] = [{} for _ in range(n_islands)]
        self.lock = threading.Lock()
        self.history: list[tuple[float, int, tuple]] = []     # (t, island, descriptor)

    def admit(self, island: int, c: Candidate, v: Verdict) -> bool:
        """Returns True if this became (or replaced) a cell elite."""
        if not v.ok:
            return False
        with self.lock:
            cur = self.scores[island].get(v.descriptor)
            if cur is None or v.score > cur:
                self.islands[island][v.descriptor] = c
                self.scores[island][v.descriptor] = v.score
                self.history.append((time.time(), island, v.descriptor))
                return True
            return False

    def sample_parents(self, island: int, k: int, rng) -> list[Candidate]:
        with self.lock:
            cells = list(self.islands[island].items())
        if not cells:
            return []
        # softmax over cell scores, low temperature: exploit within an island,
        # diversity comes from the cell structure and from island isolation, not from noise
        sc = [self.scores[island][d] for d, _ in cells]
        mx = max(sc)
        w = [math.exp((s - mx) / 0.15) for s in sc]
        tot = sum(w)
        out = []
        for _ in range(min(k, len(cells))):
            r = rng.random() * tot
            acc = 0.0
            for (d, cand), wi in zip(cells, w):
                acc += wi
                if acc >= r:
                    out.append(cand)
                    break
        return out

    def coverage(self) -> int:
        with self.lock:
            return len(set().union(*[set(i.keys()) for i in self.islands]) if self.islands else set())

    def redundancy(self) -> float:
        """Fraction of occupied cells that more than one island also occupies. High = islands
        are doing each other's work."""
        with self.lock:
            allc = [set(i.keys()) for i in self.islands]
        union = set().union(*allc) if allc else set()
        if not union:
            return 0.0
        dup = sum(1 for d in union if sum(1 for s in allc if d in s) > 1)
        return dup / len(union)

    def late_growth(self, frac=1 / 3) -> int:
        """New descriptors discovered in the last `frac` of the run minus those in the first
        `frac`. Negative means the search is saturating; this is the collapse detector."""
        with self.lock:
            h = list(self.history)
        if len(h) < 6:
            return 0
        n = len(h)
        a, b = h[: int(n * frac)], h[int(n * (1 - frac)):]
        return len({d for _, _, d in b}) - len({d for _, _, d in a})

    def best(self) -> tuple[float, Candidate | None]:
        with self.lock:
            bs, bc = -1e18, None
            for isl in range(self.n_islands):
                for d, s in self.scores[isl].items():
                    if s > bs:
                        bs, bc = s, self.islands[isl][d]
            return bs, bc


# ---------------------------------------------------------------- ledger

class Ledger:
    """Append-only provenance with retraction. Every admitted artifact records what it was
    derived from, so when something is retracted the invalidated subtree is computable.
    Without this, retraction is impossible and an error is permanent -- which is exactly the
    failure mode a shared blackboard has and FunSearch avoids only by admitting nothing
    unverified in the first place."""

    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.lock = threading.Lock()
        self.parents: dict[str, list[str]] = {}
        self.retracted: set[str] = set()

    @staticmethod
    def aid(payload) -> str:
        return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]

    def record(self, c: Candidate, v: Verdict) -> str:
        i = self.aid(c.payload)
        with self.lock:
            self.parents[i] = list(c.parents)
            with open(self.path, 'a') as f:
                f.write(json.dumps(dict(id=i, t=time.time(), source=c.source, family=c.family,
                                        parents=c.parents, ok=v.ok, solved=v.solved,
                                        score=v.score, descriptor=list(v.descriptor),
                                        reason=v.reason)) + '\n')
        return i

    def retract(self, i: str) -> list[str]:
        """Retract an artifact and everything derived from it. Returns the invalidated set."""
        with self.lock:
            dead, frontier = set(), [i]
            while frontier:
                cur = frontier.pop()
                if cur in dead:
                    continue
                dead.add(cur)
                frontier += [k for k, ps in self.parents.items() if cur in ps]
            self.retracted |= dead
            with open(self.path, 'a') as f:
                f.write(json.dumps(dict(retract=sorted(dead), t=time.time())) + '\n')
        return sorted(dead)


# ---------------------------------------------------------------- dead ends

class DeadEnds:
    """Refuted regions, broadcast to everyone. Deliberately asymmetric with the archive:
    winners stay island-local, failures go global. Prunes without steering."""

    def __init__(self, path, cap=40):
        self.path, self.cap = path, cap
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.items: list[str] = []
        self.seen: set[str] = set()
        self.lock = threading.Lock()
        self.hits = 0

    def add(self, key: str | None):
        if not key:
            return
        with self.lock:
            if key in self.seen:
                self.hits += 1
                return
            self.seen.add(key)
            self.items.append(key)
            with open(self.path, 'a') as f:
                f.write(json.dumps(dict(key=key, t=time.time())) + '\n')

    def recent(self, k=None) -> list[str]:
        with self.lock:
            return self.items[-(k or self.cap):]


# ---------------------------------------------------------------- metrics

class Metrics:
    def __init__(self):
        self.t0 = time.time()
        self.calls = 0
        self.parsed = 0
        self.verified = 0
        self.admitted = 0
        self.solved = 0
        self.by_family: dict[str, dict[str, int]] = {}
        self.lock = threading.Lock()

    def note(self, family, parsed=False, verified=False, admitted=False, solved=False):
        with self.lock:
            self.calls += 1
            f = self.by_family.setdefault(family, dict(calls=0, parsed=0, verified=0,
                                                       admitted=0, solved=0))
            f['calls'] += 1
            for k, hit in (('parsed', parsed), ('verified', verified),
                           ('admitted', admitted), ('solved', solved)):
                if hit:
                    setattr(self, k, getattr(self, k) + 1)
                    f[k] += 1

    def snapshot(self, archive: Archive, deadends: DeadEnds) -> dict:
        with self.lock:
            base = dict(elapsed=round(time.time() - self.t0), calls=self.calls,
                        parsed=self.parsed, verified=self.verified,
                        admitted=self.admitted, solved=self.solved,
                        by_family={k: dict(v) for k, v in self.by_family.items()})
        base.update(coverage=archive.coverage(), redundancy=round(archive.redundancy(), 3),
                    late_growth=archive.late_growth(), deadends=len(deadends.items),
                    deadend_hits=deadends.hits)
        return base
