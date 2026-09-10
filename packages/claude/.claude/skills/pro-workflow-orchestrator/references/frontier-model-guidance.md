# Frontier model execution guidance

Read this reference after P0 when `pro_config.json` contains a matched model profile or
when an unrecognized model needs a current capability review. The profile catalog is a
maintained execution hint, not proof that a particular account or harness exposes every
capability.

## Shared Pro policy

- Pause for the user only at checkpoints 1, 2, and 3. Between checkpoints, complete all
  reversible work already authorized by the task.
- Additional stops are limited to missing user-owned data or authorization, an
  irreversible external action outside the approved task, or the same normalized
  failure occurring three consecutive times.
- Launch independent readers, model candidates, replications, and reviewers in parallel
  when the harness supports it. If parallel agents are unavailable, preserve role
  isolation and run them sequentially in fresh sessions. Merely renaming the active
  role in one conversation is not isolation. If the host cannot provide separate
  contexts, report that capability gap instead of producing simulated approvals.
- Keep the lead agent productive while delegated work runs. Wait only when the next
  action depends on a delegated result.
- Treat platform and system instructions as highest priority. Preserve explicit user
  scope and checkpoint decisions. Supporting Skills may refine a phase but cannot add
  checkpoints, change the output root, or weaken a gate.

## GPT-6 Astra

- Use `gpt-6-astra` as the canonical API identifier. A custom API harness must use the
  Responses API for tool calling.
- Use explicit role counts for P1, P2, independent replication, and P8. Do not rely on
  the model to decide whether delegation is worthwhile.
- Audit all loaded project instructions and Pro Skills before P1. Resolve conflicting
  guidance in `instruction_audit.json` instead of silently choosing one rule.
- Prefer `max` for reasoning-heavy modeling and review. Use `high` for the long-form
  paper turn unless an evaluation demonstrates a benefit from a higher setting.

## Claude Fable 5.1

- Use `claude-fable-5-1` as the canonical API identifier. Keep conversation history
  append-only when the harness replays thinking blocks.
- Batch independent tool calls. Let the lead continue other work while subagents run.
- Prefer `max` for hard modeling and independent review, but start long paper authoring
  at `high` so reasoning does not consume the space needed for the deliverable.
- For a long deliverable, reason about evidence and structure, then write the manuscript
  once. Do not draft the full paper in hidden reasoning and repeat it in the response.

## Claude Opus 5 and Sonnet 5

- Use adaptive thinking and the phase effort recorded in `pro_config.json` when the
  harness can change effort by phase.
- The five-role review board remains required, but do not add repeated generic
  self-review loops outside that board. Every additional check needs a distinct failure
  hypothesis or gate.
- Give each subagent an explicit role, allowed inputs, expected artifact, and completion
  condition.

## Unknown or newer models

An unknown model is warned, not blocked. If public network access is available, verify
its canonical ID, current status, reasoning controls, context/output limits, tool use,
and multi-agent behavior using official vendor documentation. Record the URLs and the
date in `pro_config.json` or a companion capability note. Do not relax Pro gates when a
capability is unavailable; use genuinely isolated sequential sessions when supported,
or report the missing capability. Model names do not establish runtime permissions.
