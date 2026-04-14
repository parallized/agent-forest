---
name: agent-forest
description: Orchestrate a 4-32 agent parallel investigation workflow where the current conversation model plans the forest and synthesizes the final answer, while an external OpenAI-compatible API generates the individual agent reports. Use this skill for multi-perspective research, adversarial review, architecture tradeoff analysis, due diligence, or any task that benefits from distinct parallel viewpoints with optional persisted personas and presets.
---

# Agent Forest

## Overview

Use this skill when the user wants a true multi-agent workflow instead of a single-pass answer.

Keep the responsibility split strict:

- The current conversation model owns planning, agent design, and final synthesis.
- The external API owns the 4-32 parallel agent reports.
- Do not offload the final integrated answer to the external agents.

## When To Use

Use `agent-forest` when the task benefits from multiple independent viewpoints:

- research and investigation
- market scans or competitive analysis
- architecture debates and tradeoff reviews
- risk discovery and adversarial critique
- product strategy or launch readiness review

Skip this skill for small edits, simple factual questions, or tasks where a single deterministic pass is enough.

## Workflow

1. Decide whether the task needs a forest.
2. In the chat model, design a forest with `4-32` distinct agents.
3. Choose one of two planning modes:
   - Dynamic mode: define the agents inline for the current task.
   - Persistent mode: use `persona_ref` entries or a preset from `assets/agent-forest.config.example.json`.
4. Prepare a JSON payload containing:
   - `task`
   - optional `context`
   - optional `constraints`
   - optional `report_sections`
   - either `agents` or a `preset`
5. Run the executor script.
6. Read the returned agent reports.
7. Synthesize the final answer locally in the current conversation.

## Default Execution Posture

- Default to optimistic execution: draft the payload and try `run` first.
- Do not gate the first attempt on `validate-config`, deep config inspection, or extra confirmation unless the user explicitly asks for that.
- If the run fails, use the concrete error to decide the next step.
- Only ask the user for input when the executor proves something is actually missing, such as an API key, base URL, or task detail.
- For chat-driven runs, do not create payload temp files unless the user explicitly asks for saved artifacts. Prefer `--payload-stdin` first, then `--payload-json`.
- For result files, prefer stdout by default, but allow the runtime to spill oversized JSON into a temp file when needed to avoid transport truncation.

## Execution Rules

- Always keep the forest size between `4` and `32`.
- Agent roles should be meaningfully distinct.
- Prefer persisted personas when the user wants stable personalities across runs.
- Prefer inline agents when the task is unusual or needs bespoke viewpoints.
- Treat every external agent response as a report, not the final answer.
- After the reports return, explicitly compare, reconcile, and synthesize them in the chat model.
- For live runs, prefer `python scripts/agent_forest.py run --progress ...` so the user can see real execution status while the forest is running.
- If your terminal tool supports streaming sessions, keep the run attached and relay short status updates using the actual counts for completed, running, pending, and failed agents.
- Tell the user the planned forest size before launch, and explicitly report which personas or agent viewpoints were selected for this run. Include the persona names, and include roles or goals when that adds clarity.
- Keep progress updates anchored to real agent events instead of estimated percentages.
- Never describe the forest as "starting", "running", or "waiting" after the terminal has already emitted `completed forest` or the shell command has exited successfully. At that point, switch to finished-state wording and continue with synthesis or follow-up research.
- If the runtime switches to summary stdout and saves the full result to a temp file, tell the user that happened and include a clickable file link to the saved JSON.
- Prefer the mutable config path `assets/agent-forest.config.json` for chat-driven runs. If it does not exist yet, the runtime will fall back to the sibling example config automatically.

## Commands

Run first with the mutable config path:

```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-stdin \
  --stdout-mode auto \
  --progress \
  --pretty
<<'JSON'
{"task":"...","agents":[{"persona_ref":"evidence-hunter"},{"persona_ref":"systems-thinker"},{"persona_ref":"risk-auditor"},{"persona_ref":"contrarian"}]}
JSON
```

Persist API settings from the conversation:

```bash
python scripts/agent_forest.py configure \
  --config assets/agent-forest.config.json \
  --api-base https://ai.huan666.de/v1/chat/completions \
  --model grok-4.20-expert \
  --api-key sk-...
```

List available presets:

```bash
python scripts/agent_forest.py list-presets \
  --config assets/agent-forest.config.json
```

Run with a preset:

```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-stdin \
  --preset research-squad-4 \
  --stdout-mode auto \
  --progress \
  --pretty
<<'JSON'
{"task":"..."}
JSON
```

Run with fully dynamic agents:

```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-json '{"task":"...","agents":[{"persona_ref":"evidence-hunter"},{"persona_ref":"systems-thinker"},{"persona_ref":"risk-auditor"},{"persona_ref":"contrarian"}]}' \
  --stdout-mode auto \
  --progress \
  --pretty
```

Inspect the compiled requests without calling the API:

```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-json '{"task":"...","agents":[{"persona_ref":"evidence-hunter"},{"persona_ref":"systems-thinker"},{"persona_ref":"risk-auditor"},{"persona_ref":"contrarian"}]}' \
  --stdout-mode full \
  --dry-run \
  --pretty
```

Validate the config only when you need to troubleshoot configuration issues:

```bash
python scripts/agent_forest.py validate-config \
  --config assets/agent-forest.config.json
```

`--progress` writes live status logs to `stderr`. `--stdout-mode auto` keeps full JSON on `stdout` when it is small enough, and automatically saves oversized results to a temp file while leaving a compact summary plus file path on `stdout`.

## Payload Guidance

Read these only when needed:

- Config details: `references/configuration.md`
- Payload schema and examples: `references/payload-schema.md`

Good payloads are explicit about the task, evidence standard, and report shape. Keep synthesis instructions out of the external agents unless the user explicitly wants one agent to act as a recommendation voice. Final synthesis still happens locally.

## Conversation Configuration

When the user provides `api_key`, `model`, or `api_base` in chat, persist them into the writable config instead of asking the user to edit JSON manually.

- Prefer `assets/agent-forest.config.json` as the mutable file.
- Keep `assets/agent-forest.config.example.json` as the checked-in template.
- Use `configure` to update provider settings directly from the conversation.
