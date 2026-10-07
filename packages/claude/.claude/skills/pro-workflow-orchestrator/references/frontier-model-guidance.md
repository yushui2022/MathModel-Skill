# Frontier model execution guidance

Read this reference after P0 when `pro_config.json` contains a matched model profile or
when an unrecognized model needs a current capability review. The profile catalog is a
maintained execution hint, not proof that a particular account or harness exposes every
capability.

The catalog was updated on 2026-10-07 for GPT-6.1 Sol, Claude Opus 5.5, and
Claude Fable 5.1. Each profile keeps its own verification date; updating one model
does not renew the others. Unknown versions and unlisted dated snapshots remain
unverified instead of inheriting an older model's capabilities.

P0 does not call a vendor API, identify a gateway's underlying model, or change a
host setting. `model_verification` records these limits. `ultra` is not a portable
API effort: old profiles retain a local alias with a warning; new profiles require
the documented value or a verified host-specific mapping.

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

## GPT-6.1 Sol

- Canonical ID: `gpt-6.1-sol`. P0 also accepts human labels such as `gptsol6.1`;
  these labels are not alternative API IDs.
- A custom tool-using harness must use Responses, not Chat Completions. Supported
  API efforts are `low`, `medium`, `high`, `xhigh`, and `max`; default is `medium`.
  Do not send `none`, `minimal`, or `ultra` as an API effort.
- Pro recommends `max` for modeling and independent review, and `high` for prose.
  These are project starting points, not measured quality guarantees. Record the
  actual host setting, preserve isolated roles, and compare effort levels in evals.
- Use the same artifact-first, multi-turn authoring as Astra. A larger context or
  output window is not a reason to skip numerical checks or compress the paper.

Source: [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

## Claude Opus 5.5 and Fable 5.1 integration

- Use `claude-opus-5-5` or `claude-fable-5-1`. Adaptive thinking is always enabled;
  disabling it or forcing a particular tool is not a compatible integration.
- Their thinking blocks are model/conversation-bound. Preserve history according
  to the host protocol; after switching models, resume from artifacts and a factual
  handoff, not copied private thinking. Do not edit earlier turns to inject a new role.
- Opus 5.5 defaults to `medium`, Fable 5.1 to `high` on the API. Both expose five
  effort levels through `max`. Pro phase recommendations remain explicit; an omitted
  setting must not be reported as `max`. Test effort changes on actual contest cases.
- Reserve enough output for both thinking and text. Write the paper in persistent
  sections across turns when necessary, then unify and review the same source.
- Custom clients must handle tool results and progress events correctly; absence
  of visible progress text does not mean no work happened. Opus 5.5 no longer accepts
  `computer_20251124` on the Claude API/Google Cloud. Let the host manage current tool
  versions; do not edit the user's client configuration automatically.

Sources: [Opus 5.5 overview](https://platform.claude.com/docs/en/models/opus-5-5/overview),
[Fable 5.1 changes](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1),
[effort controls](https://platform.claude.com/docs/en/build-with-claude/effort).

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
