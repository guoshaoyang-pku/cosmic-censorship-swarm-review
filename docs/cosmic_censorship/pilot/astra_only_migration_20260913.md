# Astra-only migration status — 2026-09-13

## Target topology

- **Local control:** 数学主控, `gpt-6-astra`, `ultra` reasoning.
- **Remote group control:** one Astra controller and four Codex+Astra ultra leads (formulation, literature, numerics, audit).
- **Execution layer:** independently killable Astra ultra Codex processes. Each process receives a bounded class task and must emit a task ID, evidence path, content hash, checkpoint, and falsifier. Process-level delegation is recorded separately from native subagent APIs.
- **Provider policy:** DeepSeek and `dsh` are excluded from the new launcher. DeepSeek artifacts remain immutable historical evidence only.

## Activation gate

The remote launcher performs an authenticated `GET /v1/models` probe before creating any tmux session. As of this snapshot, the configured remote credential returns `401 invalid token` from `https://openai.phybench.cn/v1/models`. Therefore the Astra-only remote swarm is **armed but not live**: no controller, lead, or execution instance is started while the probe fails.

This fail-closed behavior is intentional. It prevents a provider migration from silently falling back to DeepSeek or producing unverified empty trajectories. Once a valid Astra credential is installed, the first run should be a 10–20-slot smoke test with lifecycle, checkpoint, hash, and killability checks before expanding toward 100 slots.

## Local controller

The local 数学主控 loop is running in `ai4math_runtime/math_controller_state/`. Its prompt explicitly records that native `spawn_agent` is unavailable in the current CLI runtime; it must use explicit shell/SSH child processes and label this as process-level delegation. This prevents unsupported native-tool calls from being mistaken for successful subagent execution.

## Readiness decision

The architecture is reviewable and safe to hand to a collaborator for credential setup and capped pilot review. It is not yet evidence that Astra execution is operating remotely, and it is not approval for unattended 100-way production. The existing scientific gates remain unchanged: G-FORM, G-LIT, G-NUM, and G-AUDIT are pending; N1 and self-gravitating production remain locked.
