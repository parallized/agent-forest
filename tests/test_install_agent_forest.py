import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "install_agent_forest.py"


spec = importlib.util.spec_from_file_location("install_agent_forest", MODULE_PATH)
install_agent_forest = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(install_agent_forest)


class InstallAgentForestTests(unittest.TestCase):
    def test_install_codex_creates_bundle_and_config_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / ".codex"
            result = install_agent_forest.install_codex(
                source_root=ROOT,
                codex_home=codex_home,
                force=False,
                dry_run=False,
            )
            bundle_root = result["bundle_root"]
            self.assertTrue((bundle_root / "SKILL.md").exists())
            self.assertTrue((bundle_root / "assets" / "agent-forest.config.json").exists())

    def test_install_claude_creates_agent_wrapper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            claude_home = Path(temp_dir) / ".claude"
            result = install_agent_forest.install_claude(
                source_root=ROOT,
                claude_home=claude_home,
                force=False,
                dry_run=False,
            )
            self.assertTrue(result["bundle_root"].exists())
            self.assertTrue((result["bundle_root"] / "SKILL.md").exists())
            self.assertTrue((result["bundle_root"] / "assets" / "agent-forest.config.json").exists())


if __name__ == "__main__":
    unittest.main()
