import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "agent_forest.py"
CONFIG_PATH = ROOT / "assets" / "agent-forest.config.example.json"


spec = importlib.util.spec_from_file_location("agent_forest", MODULE_PATH)
agent_forest = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(agent_forest)


class AgentForestTests(unittest.TestCase):
    def setUp(self):
        self.config = agent_forest.load_config(CONFIG_PATH)

    def test_resolve_preset_agents(self):
        payload = {"task": "Assess this proposal."}
        resolved = agent_forest.resolve_agents(self.config, payload, "research-squad-4")
        self.assertEqual(len(resolved), 4)
        self.assertEqual(resolved[0]["name"], "Evidence Hunter")
        self.assertEqual(resolved[1]["id"], "systems-thinker")

    def test_inline_persona_refs_can_override_goal(self):
        payload = {
            "task": "Stress test the proposal.",
            "agents": [
                {"persona_ref": "evidence-hunter"},
                {"persona_ref": "systems-thinker"},
                {
                    "persona_ref": "risk-auditor",
                    "goal": "Prioritize reliability and rollout risks first.",
                },
                {"persona_ref": "contrarian"},
            ],
        }
        resolved = agent_forest.resolve_agents(self.config, payload, None)
        self.assertEqual(len(resolved), 4)
        self.assertEqual(
            resolved[2]["goal"], "Prioritize reliability and rollout risks first."
        )

    def test_agent_count_validation_rejects_too_small_forest(self):
        payload = {
            "task": "Too small.",
            "agents": [
                {"name": "A", "role": "alpha"},
                {"name": "B", "role": "beta"},
                {"name": "C", "role": "gamma"},
            ],
        }
        with self.assertRaises(agent_forest.ConfigError):
            agent_forest.prepare_run(self.config, payload, None)

    def test_build_messages_includes_task_and_sections(self):
        payload = {
            "task": "Evaluate the rollout plan.",
            "context": "The main chat model will synthesize later.",
            "constraints": ["Surface hidden risk.", "Use concise markdown."],
            "report_sections": ["Judgment", "Evidence", "Risks"],
            "agents": [
                {"persona_ref": "evidence-hunter"},
                {"persona_ref": "systems-thinker"},
                {"persona_ref": "risk-auditor"},
                {"persona_ref": "contrarian"},
            ],
        }
        plan = agent_forest.prepare_run(self.config, payload, None)
        first_messages = plan["agents"][0]["request_body"]["messages"]
        self.assertEqual(first_messages[0]["role"], "system")
        self.assertIn("Evaluate the rollout plan.", first_messages[1]["content"])
        self.assertIn("Judgment", first_messages[1]["content"])
        self.assertIn("Surface hidden risk.", first_messages[1]["content"])

    def test_parse_sse_response_collects_content_chunks(self):
        raw = "\n".join(
            [
                'data: {"choices":[{"delta":{"content":"Hel"}}]}',
                'data: {"choices":[{"delta":{"content":"lo"}}]}',
                'data: {"choices":[{"delta":{"content":" world"},"finish_reason":"stop"}],"usage":{"total_tokens":12}}',
                "data: [DONE]",
            ]
        )
        parsed = agent_forest.parse_sse_response(raw)
        self.assertEqual(parsed["content"], "Hello world")
        self.assertEqual(parsed["finish_reason"], "stop")
        self.assertEqual(parsed["usage"]["total_tokens"], 12)


if __name__ == "__main__":
    unittest.main()
