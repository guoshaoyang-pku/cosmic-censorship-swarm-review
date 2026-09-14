# Swarm effectiveness protocol

The harness evaluates epistemic quality, not token count or successful HTTP responses.

For each output, a reviewer must: (1) assign a formulation class ID; (2) extract atomic claims; (3) mark each as theorem, reported result, model proposal, or speculation; (4) verify citations against primary sources; (5) identify hidden assumptions and forbidden generalizations; (6) test whether the proposed experiment has a falsifier and reproducible artifact; and (7) score the eight rubric dimensions.

A result is accepted only if two independent reviewers agree within one point on the total and neither finds a hard failure. Disagreement sends the item to adjudication. The harness records cost, latency, duplicate claims, rejected claims, and information gain per call.

Efficiency metrics:

- accepted-claim rate = accepted atomic claims / total atomic claims;
- citation verification rate = verified citations / cited citations;
- hard-failure rate;
- unique class coverage per 1,000 output tokens;
- reviewer agreement (Krippendorff-style categorical agreement or simple exact/within-one rate);
- cost per accepted claim and cost per unresolved ambiguity removed.

No model output may update the canonical theorem ledger without passing this protocol.
