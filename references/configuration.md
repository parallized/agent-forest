# Agent Forest Configuration

`assets/agent-forest.config.json` is the preferred writable control plane for this skill.

If the mutable config file does not exist yet, runtime commands such as `run` and `list-presets` can fall back to the sibling `assets/agent-forest.config.example.json` file for read-only defaults. This supports a "try first, fix only what is missing" workflow.

## Top-Level Keys

- `api`: external OpenAI-compatible endpoint settings
- `forest`: hard limits and concurrency controls
- `reporting`: default format and sections for agent reports
- `prompts`: shared prompt fragments used for every agent call
- `persona_library`: stable reusable personalities
- `presets`: named groups of agents for repeatable runs

## API

Recommended pattern:

- set `api_key_env` to an environment variable such as `AGENT_FOREST_API_KEY`
- leave `api_key` as `null` in versioned files
- use `agent_forest.py configure` to persist user-provided `api_key`, `model`, or `api_base` into a writable config copy

Supported fields:

- `base_url`: chat completions endpoint
- `api_key`: optional literal fallback, not recommended for committed files
- `api_key_env`: environment variable name for the bearer token
- `model`: default model for all agents unless overridden
- `timeout_seconds`: per-request timeout
- `request_defaults`: optional extra request fields merged into every API call

The bundled example sets `"stream": false` because the provided endpoint defaults to SSE streaming. The executor can parse both regular JSON and `text/event-stream`, but disabling streaming gives simpler responses when the provider honors it.

## Conversation-Friendly Updates

The runtime includes a config mutation command:

```bash
python scripts/agent_forest.py configure \
  --config assets/agent-forest.config.json \
  --api-base https://ai.huan666.de/v1/chat/completions \
  --model grok-4.20-expert \
  --api-key sk-...
```

You can also keep the key in an environment variable:

```bash
python scripts/agent_forest.py configure \
  --config assets/agent-forest.config.json \
  --api-key-env AGENT_FOREST_API_KEY \
  --clear-api-key
```

For live runs from chat, pair the executor with `--progress` so the terminal can surface real-time agent state without corrupting the final JSON payload. Prefer `--payload-stdin` or `--payload-json` over writing temporary payload files, and leave `--stdout-mode` on `auto` so oversized results can spill into a temp file instead of getting truncated:

```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-stdin \
  --stdout-mode auto \
  --preset research-squad-4 \
  --progress \
  --pretty
<<'JSON'
{"task":"Review the decision from our default research squad."}
JSON
```

If a large run spills to a temp file, stdout will contain a compact JSON summary with the saved file path under `stdout.full_output_file`.

Use `validate-config` when you specifically want to troubleshoot configuration, not as a mandatory preflight for every run:

```bash
python scripts/agent_forest.py validate-config \
  --config assets/agent-forest.config.json
```

## Forest

- `min_agents` and `max_agents` should stay within `4-32`
- `default_agent_count` is for planning guidance only
- `max_parallel_requests` caps request fan-out to protect the endpoint

## Persona Library

Each persona entry can contain:

- `name`
- `role`
- `persona`
- `goal`
- `system_prompt`
- `model`
- `temperature`

These entries are reusable building blocks. A payload can reference them with `persona_ref`.

## Presets

A preset is a named list of agents. Each item can be:

- a string: `"risk-auditor"`
- or an object:

```json
{
  "persona_ref": "risk-auditor",
  "goal": "Focus on launch-week failure modes first."
}
```

This lets you keep personalities fixed while still overriding the mission for a specific run.
