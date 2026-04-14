# Agent Forest 🌲

[English](README.md) | [中文](README_ZH.md)

**Agent Forest** is an orchestration framework for parallel agent investigation. It leverages the power of many specialized LLM agents to provide multi-perspective research, architecture reviews, risk discovery, and product strategy analysis.

Instead of a single-pass answer, Agent Forest coordinates a "forest" of 4 to 32 agents to explore a problem space from diverse angles, with a central "synthesizer" model (your current conversation) integrating the results.

## 🚀 Key Features

- **Parallel Investigation**: Run up to 32 agents concurrently to slice through complex research tasks.
- **Diverse Perspectives**: Use a library of personas (Evidence Hunter, Risk Auditor, Systems Thinker, Contrarian, etc.) to ensure no stone is left unturned.
- **Flexible Orchestration**: Choose between dynamic inline agent definitions or persistent, reusable presets.
- **Strict Synthesis**: Maintains a clear boundary between agent reports (external) and final synthesis (local), preventing "hallucinated consensus."
- **OpenAI-Compatible**: Works with any API provider following the OpenAI chat completion standard.

## 🛠 Project Structure

- `agents/`: Logic for agent behavior and persona management.
- `scripts/`: CLI tools for running and validating the forest.
- `assets/`: Configuration examples and agent presets.
- `references/`: Detailed documentation on configuration and payload schemas.
- `tests/`: Suite for validating framework logic.

## 🚦 Getting Started

### Prerequisites

- Python 3.8+
- An API key for an OpenAI-compatible provider (e.g., OpenAI, Anthropic via proxy, Grok, etc.)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/parallized/agent-forest.git
   cd agent-forest
   ```

2. Set up your environment:
   ```bash
   export AGENT_FOREST_API_KEY="your-api-key-here"
   ```

3. Prepare your config:
   ```bash
   cp assets/agent-forest.config.example.json assets/agent-forest.config.json
   ```

## 📖 Usage

### Validate Configuration
Ensure your setup is correct before running a forest:
```bash
python scripts/agent_forest.py validate-config --config assets/agent-forest.config.json
```

### Run a Research Pass (Preset)
Use the `research-squad-4` preset for a balanced investigation:
```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-file path/to/your-task.json \
  --preset research-squad-4 \
  --pretty
```

### Inspect Requests (Dry Run)
Verify the agent prompts without calling the API:
```bash
python scripts/agent_forest.py run \
  --config assets/agent-forest.config.json \
  --payload-file path/to/your-task.json \
  --dry-run \
  --pretty
```

## 🧠 Payload Example

A typical payload defines the task and the desired report structure:

```json
{
  "task": "Should we migrate our core database from PostgreSQL to a distributed NoSQL solution?",
  "context": "We are currently handling 10k RPS with a 2TB dataset growing at 10% monthly.",
  "report_sections": ["Executive Summary", "Technical Feasibility", "Operational Risks", "Cost Analysis"]
}
```

## 📚 Documentation

For more advanced topics, check out:
- [Configuration Guide](references/configuration.md)
- [Payload Schema & Examples](references/payload-schema.md)
- [Skill Reference](SKILL.md)

---

Built with 🌲 by the Agent Forest team.
