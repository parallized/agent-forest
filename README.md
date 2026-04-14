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
- **Live Progress Logs**: Optional `--progress` output shows completed, running, pending, and failed agents in real time while preserving JSON output on `stdout`.

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

### Install as a Global Skill

1. Clone the repository:
   ```bash
   git clone https://github.com/parallized/agent-forest.git
   cd agent-forest
   ```

2. Install for Codex, Claude Code, or both:
   ```bash
   ./install.sh
   ```

   Target a single platform if you want:
   ```bash
   ./install.sh --target codex
   ./install.sh --target claude
   ```

   On Windows PowerShell:
   ```powershell
   .\install.ps1
   .\install.ps1 --target codex
   .\install.ps1 --target claude
   ```

3. Set up your environment:
   ```bash
   export AGENT_FOREST_API_KEY="your-api-key-here"
   ```

4. Update the installed config:
   - Codex: `~/.codex/skills/agent-forest/assets/agent-forest.config.json`
   - Claude Code: `~/.claude/skills/agent-forest/assets/agent-forest.config.json`

   If you reinstall over an existing copy, use `--force`.

5. Invoke the skill:
   - Codex: let it auto-discover the installed skill, or reference `$agent-forest`
   - Claude Code: invoke `/agent-forest` or let Claude load it when relevant

6. Configure the provider from conversation or CLI:
   ```bash
   python ~/.codex/skills/agent-forest/scripts/agent_forest.py configure \
     --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
     --api-base https://ai.huan666.de/v1/chat/completions \
     --model grok-4.20-expert \
     --api-key your-api-key
   ```

## 📖 Usage

### Default Flow: Run First
Start with a real run. The executor will read `agent-forest.config.json` when present and fall back to the sibling example config when it is not, so you can try the workflow before doing extra setup work:
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py run \
  --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
  --payload-stdin \
  --preset research-squad-4 \
  --progress \
  --pretty
<<'JSON'
{"task":"Review the decision from our default research squad."}
JSON
```

If something is actually missing, use the concrete error to decide the next step. For chat-driven runs, prefer `--payload-stdin` or `--payload-json` so you do not create throwaway payload files. `validate-config` is mainly for troubleshooting:
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py validate-config \
  --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json
```

### Run a Research Pass (Preset)
Use the `research-squad-4` preset for a balanced investigation:
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py run \
  --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
  --payload-stdin \
  --preset research-squad-4 \
  --progress \
  --pretty
<<'JSON'
{"task":"Review the decision from our default research squad."}
JSON
```

### Inspect Requests (Dry Run)
Verify the agent prompts without calling the API:
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py run \
  --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
  --payload-json '{"task":"Review the decision from our default research squad."}' \
  --dry-run \
  --pretty
```

`--progress` writes live status logs to `stderr`, so you can watch the forest run without breaking the final JSON on `stdout`.

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
