# Collaborator development line

This branch, [96mcollaborator/full-swarm-development[0m, is the complete cosmic-censorship swarm development line. It is based on [96mswarm-research/ai4math-swarm@shaoyang/cosmic-censorship[0m at the handoff commit recorded in Git history. Use it for development, local validation, controlled execution, and pushing new research artifacts.

The public review branch [[96mintegrated-with-ai4math-swarm[0m](https://github.com/guoshaoyang-pku/cosmic-censorship-swarm-review/tree/integrated-with-ai4math-swarm) remains the compact, frozen collaborator reading package. Keep the two purposes separate:

- **This branch:** complete source tree, runtime state, communication protocol, research map, schemas, harnesses, ledgers, audit artifacts, numerical lane, and historical trajectories.
- **Review branch:** curated summaries, visual dashboard, mathematical explainer, progress paper, formulas, and frozen claim boundary.

## Architecture

~~~text
Human PI
   │ priorities, irreversible scope decisions
   ▼
Astra controller
   │ owns research_map/research_map.json, DAG, gates, checkpoints
   ├── formulation lead ─┐
   ├── literature lead  ─┤
   ├── numerics lead    ─┼── structured events via comms/
   └── audit lead       ─┘
            │
            ▼
      execution agents
            │
            ▼
 artifacts + hashes + reviews + falsifiers
~~~

The global state is [96mresearch_map/research_map.json[0m. Communication is event-based through [96mcomms/[0m; an agent's prose is never enough to complete a node. A node needs the declared artifact, measured hash, validation evidence, and the appropriate reviewer or gate verdict.

## Main subsystems

| Path | Responsibility |
|---|---|
| [96mresearch_map/[0m | class taxonomy, DAG, map validator, lifecycle, assignments, gate state |
| [96mharness/[0m | launch and supervision scripts; inspect before adapting to a new provider |
| [96mruntime/[0m | instance trajectories, checkpoints, state, exit records, hashes |
| [96mcomms/[0m | controller/lead/worker event protocol and handoff messages |
| [96mschemas/[0m | class-bound WCC/SCC formulation schemas and rule specifications |
| [96mframework/[0m | base swarm execution and accounting framework |
| [96mledger/[0m | theorem/citation ledger and evidence records |
| [96mevaluation/[0m | rubrics, ablation designs, gate checks, synthetic dry-runs |
| [96mnumerics/[0m | N0 calibration lane; N1 self-gravitating lane remains locked |
| [96martifacts/[0m, [96mreviews/[0m | worker outputs, audit reports, independent verdicts |
| [96mdocs/cosmic_censorship/[0m | project plan, pilot docs, dashboard and mathematical reports |

## Safe development workflow

1. Read [96mREADME.md[0m, [96mHANDOFF.md[0m, [96mresearch_map/ARCHITECTURE.md[0m, and [96mresearch_map/ASTRA_HANDOFF.md[0m.
2. Validate the map before changing anything:

   ~~~bash
   python3 research_map/validate_map.py
   ~~~

3. Inspect the current gates and [96mnumerics_lock[0m in [96mresearch_map/research_map.json[0m.
4. Work on a class-bound assignment; write an artifact and structured event with evidence refs, hash, blocker, and next falsifier.
5. Run the relevant audit/checker and record its output before marking progress.
6. Push work to this development branch or a child feature branch. Do not push credentials, provider configs, local sockets, or scratch dumps.

The historical harness files may mention the old [96mdsh_fixed.sh[0m / DeepSeek pilot. They are retained for provenance and are not a request to use that provider. Adapt the execution adapter to the collaborator's approved Maso setup only after Maso is actually integrated and credentials are supplied outside Git.

## Provider and credential boundary

This branch intentionally contains **no API keys or provider credentials**. Provider configuration belongs outside the repository, under the operator's own Maso integration. Do not commit [96m.env[0m files, [96m~/.maso[0m contents, credential YAML, tokens, or generated secrets. Before any paid execution, verify the provider adapter with a tiny, reversible probe and record only non-secret metadata.

## Current scientific boundary

The frozen handoff has [96mmap_validator = VALID[0m, [96mevents_total = 9367[0m, [96mregistered artifacts = 656[0m, [96mN1 = blocked/locked[0m, [96mN0 = calibration lane[0m, and no promoted theorem. These are evidence and lifecycle facts. They do not establish WCC or SCC. Preserve the class separation between [96mAF-WCC-VAC-GEN[0m, [96mAF-SCC-C2-VAC-GEN[0m, [96mAF-SCC-C0-VAC-GEN[0m, and scalar/spherical calibration.

Before enabling any large run, require the gates and provider integration to be re-verified against the current checkout. A large worker count is not a substitute for formulation, audit, convergence, citation, and independent-reproduction evidence.
