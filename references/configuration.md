# Agent Forest Configuration

`assets/agent-forest.config.example.json` is the persisted control plane for this skill.

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

Supported fields:

- `base_url`: chat completions endpoint
- `api_key`: optional literal fallback, not recommended for committed files
- `api_key_env`: environment variable name for the bearer token
- `model`: default model for all agents unless overridden
- `timeout_seconds`: per-request timeout
- `request_defaults`: optional extra request fields merged into every API call

The bundled example sets `"stream": false` because the provided endpoint defaults to SSE streaming. The executor can parse both regular JSON and `text/event-stream`, but disabling streaming gives simpler responses when the provider honors it.

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
