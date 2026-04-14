# Agent Forest Payload Schema

The executor expects a JSON payload passed with `--payload-file` or `--payload-json`.

## Required Field

- `task`: the user task given to every agent

## Optional Fields

- `preset`: preset name if you want the payload itself to choose one
- `context`: shared background for all agents
- `constraints`: array of rules or evaluation criteria
- `report_sections`: array of section names expected in each report
- `output_format`: usually `markdown`
- `model`: run-wide model override
- `agents`: inline dynamic agents for this run

## Dynamic Agents Example

```json
{
  "task": "Evaluate whether we should launch the new agent-forest workflow this week.",
  "context": "We already have a planning model in the main chat window. Only the sub-agent reports should use the external API.",
  "constraints": [
    "Call out hidden operational risk.",
    "Assume engineering time is limited.",
    "Prefer concrete recommendations over generic advice."
  ],
  "report_sections": [
    "Main Judgment",
    "Evidence",
    "Risks",
    "Recommended Next Step"
  ],
  "agents": [
    {
      "name": "Launch Optimist",
      "role": "argue for shipping soon",
      "persona": "pragmatic and forward-leaning",
      "goal": "Make the strongest case for launching this week with clear safeguards."
    },
    {
      "name": "Failure Hunter",
      "role": "focus on launch failure modes",
      "persona": "skeptical and operationally sharp",
      "goal": "Identify what could break in the first 72 hours."
    },
    {
      "name": "User Trust Lens",
      "role": "represent user confidence and clarity",
      "persona": "empathetic and trust-sensitive",
      "goal": "Estimate whether the experience will feel coherent to users."
    },
    {
      "name": "Execution Planner",
      "role": "translate the decision into a staged rollout",
      "persona": "sequence-minded and concrete",
      "goal": "Give the leanest rollout plan that still reduces risk."
    }
  ]
}
```

## Persona Ref Example

```json
{
  "task": "Assess the proposal from multiple stable viewpoints.",
  "constraints": [
    "Use concise markdown.",
    "Surface contradictions explicitly."
  ],
  "agents": [
    {
      "persona_ref": "evidence-hunter"
    },
    {
      "persona_ref": "risk-auditor",
      "goal": "Prioritize security and reliability risk first."
    },
    {
      "persona_ref": "operator",
      "goal": "Write the leanest viable rollout plan."
    },
    {
      "persona_ref": "contrarian"
    }
  ]
}
```

## Preset Example

```json
{
  "task": "Review the decision from our default research squad.",
  "context": "The chat model will synthesize the final answer after the reports come back."
}
```

Run it with:

```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.example.json \
  --payload-file /tmp/forest-payload.json \
  --preset research-squad-4 \
  --progress \
  --pretty
```
