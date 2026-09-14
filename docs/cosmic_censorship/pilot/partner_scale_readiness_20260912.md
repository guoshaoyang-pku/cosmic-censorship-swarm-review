# Swarm partner-scale readiness — 2026-09-12

## Decision

**Do not hand this over as an unattended large-scale service yet.** It is ready for a supervised, capped pilot with a partner who supplies multiple API accounts, provided that the partner accepts the evidence-first workflow and keeps numerical production gated.

The right handover unit is the harness plus recovery hardening, not a promise that the swarm is a reliable mathematical research oracle.

## What last night's run proves

- The five-role DeepSeek Flash cycle completed **5/5** after correcting the endpoint and disabling reasoning for that run.
- The four independent review roles completed **4/4** after one network retry.
- The first formulation was rejected by the gates: it merged WCC/SCC and C0/C2 variants, left genericity and visibility under-specified, and supplied no verifiable citations.
- The overnight remote run recorded **592 finished group instances** (formulation 145, literature 148, numerics 150, audit 149) and tens of thousands of artifacts. These counts demonstrate throughput and artifact production; they do not establish that every artifact is useful, independent, or accepted.
- The stop was caused by **DeepSeek quota exhaustion**. The supervisor opened a quota circuit and correctly reported zero live sessions. Panel fixes separated stale instance directories from live workers and narrowed counts to the project namespace.

## Stability assessment

### Already good enough for a supervised pilot

1. Class-bound roles, explicit gates, falsifiers, hashes, and checkpoint-oriented prompts are present.
2. Numerics are explicitly blocked until formulation and audit gates pass.
3. Worker output is stored with stdout/stderr, trajectory, metadata, and exit status in the hardened remote design.
4. A quota circuit and recovery probe were added; the probe is intended to launch only after the circuit expires and to verify exit code, trajectory completion, and quota stderr.
5. Independent review caught a substantive false formulation in the first cycle, so the system is not treating API success as scientific success.

### Still below partner-scale unattended standard

1. **Provider failover is not implemented as a common abstraction.** The pilot client reads one key from a fixed local path and one endpoint/model from environment variables. Runtime launchers call a fixed wrapper. A partner API pool cannot be used safely by merely adding credentials.
2. **Failure classification is too narrow.** The quota circuit looks for one exact quota string; 429, 402, 5xx, timeout, connection reset, malformed response, and stream disconnect paths are not shown to share the same retry/failover policy.
3. **The circuit is a pause, not durable recovery.** It uses a time window and a single controller probe. There is no demonstrated account rotation, per-provider health score, budget reservation, or proof that queued tasks resume exactly once after recovery.
4. **The launchers use tmux session names as the lifecycle key.** The prior run needed namespace and stale-metadata repairs. That is acceptable for one supervised host, but weak as the primary identity/idempotency layer for hundreds or thousands of workers.
5. **The simple pilot client has no durable queue or retry ledger.** It writes one JSON file per role, but does not persist attempt IDs, lease ownership, retry class, or exactly-once artifact commit semantics.
6. **The artifact count is not an acceptance metric.** The run has many artifacts, while G-FORM/G-LIT/G-NUM/G-AUDIT were still pending and N1 was locked at the observation point. Throughput must be reported beside accepted/rejected/duplicate/failed counts.
7. **The current local scripts contain deployment-specific absolute paths** (/data3/... and $HOME/workdir/...) and the pilot client contains a fixed key-file path. They are not a portable partner package.

## Recommended handover envelope

Start with 20–50 workers, one controller, four leads, and a hard per-provider budget. Keep the following rules:

- provider calls go through one adapter that returns normalized ok, retryable, quota, auth, timeout, rate_limit, and invalid_output outcomes;
- each task gets a durable task_id, attempt_id, lease timeout, provider ID, and idempotency key;
- retry only retryable failures, rotate providers on quota/auth/rate-limit classes, and never duplicate a committed artifact;
- stop launching new work when the health probe fails; finish or checkpoint current work;
- report live workers, completed tasks, accepted artifacts, rejected artifacts, retries by class, duplicate rate, and provider spend;
- keep self-gravitating numerical production disabled until the formulation and audit gates are explicitly green.

## Go/no-go gate for larger rollout

Move beyond the capped pilot only after one controlled failover drill passes:

1. exhaust or revoke provider A during active work;
2. observe classification, circuit opening, provider B selection, and queue recovery;
3. verify no task is silently lost and no committed artifact is duplicated;
4. verify every new instance has trajectory, stdout/stderr, exit code, checkpoint, and killability;
5. rerun the acceptance dashboard and show accepted/rejected/duplicate/retry counts;
6. repeat the drill at least once with a transient 5xx/timeout fault.

Until that drill is recorded, the honest status is **scientifically well-governed pilot harness; operationally not yet a partner-scale unattended swarm**.
