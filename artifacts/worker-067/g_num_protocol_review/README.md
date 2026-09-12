# worker-067 - independent G-NUM protocol review (C8)

Target: `numerics/CONVERGENCE_PROTOCOL.md` rev 3 at sha256
`1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` (stable across the whole review window).

Verdict: **revise** (score 4.0, no hard failures), on finding F1 only.
C1/C2/C3 are closed and independently reproduced; C4 is controller-side.
F1: section 3.4 says `dt proportional to h` runs are never quoted as spatial, but the
proposal's certified *spatial* order claim is built exactly on constant-CFL runs
(dt = 0.1/0.05/0.025/0.0125 at cfl=0.5). Temporal subdominance is nevertheless
measured (two-CFL probe relative change 4.6e-07; dt=dr^0.5 control collapses the
order to 1.06), so no measured number changes - the normative text needs scoping in
rev 4 (see review.json F1.required_action_rev4).

Reproduce: `python3 artifacts/worker-067/g_num_protocol_review/verify_r3.py`
(stdlib; writes verification_log.json plus the two rerun JSONs in this directory).
