import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from unittest import mock
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

    def test_configure_can_create_mutable_config_from_example(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "agent-forest.config.json"
            example_path = Path(temp_dir) / "agent-forest.config.example.json"
            example_path.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

            exit_code = agent_forest.main(
                [
                    "configure",
                    "--config",
                    str(config_path),
                    "--api-base",
                    "https://example.com/v1/chat/completions",
                    "--model",
                    "demo-model",
                    "--api-key",
                    "sk-demo-12345678",
                ]
            )

            self.assertEqual(exit_code, 0)
            saved = agent_forest.load_json(config_path)
            self.assertEqual(saved["api"]["base_url"], "https://example.com/v1/chat/completions")
            self.assertEqual(saved["api"]["model"], "demo-model")
            self.assertEqual(saved["api"]["api_key"], "sk-demo-12345678")

    def test_run_command_can_emit_live_progress_without_breaking_json_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "agent-forest.config.json"
            config = agent_forest.load_json(CONFIG_PATH)
            config["api"]["base_url"] = "https://example.com/v1/chat/completions"
            config["api"]["api_key"] = "sk-demo-12345678"
            agent_forest.write_json(config_path, config)

            payload = {
                "task": "Assess this proposal.",
                "agents": [
                    {"persona_ref": "evidence-hunter"},
                    {"persona_ref": "systems-thinker"},
                    {"persona_ref": "risk-auditor"},
                    {"persona_ref": "contrarian"},
                ],
            }

            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with (
                mock.patch.object(
                    agent_forest,
                    "chat_completion_request",
                    return_value={
                        "content": "report body",
                        "finish_reason": "stop",
                        "usage": {"total_tokens": 12},
                    },
                ),
                contextlib.redirect_stdout(stdout_buffer),
                contextlib.redirect_stderr(stderr_buffer),
            ):
                exit_code = agent_forest.main(
                    [
                        "run",
                        "--config",
                        str(config_path),
                        "--payload-json",
                        json.dumps(payload),
                        "--progress",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("starting forest with 4 agents", stderr_buffer.getvalue())
            self.assertIn("completed forest", stderr_buffer.getvalue())

            rendered = json.loads(stdout_buffer.getvalue())
            self.assertEqual(rendered["summary"]["succeeded_agents"], 4)
            self.assertEqual(rendered["summary"]["failed_agents"], 0)


if __name__ == "__main__":
    unittest.main()
