"""Exercise the optional Gold addon through a separate addon namespace."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
from test_addon import Client


def load_gold(client):
    private = client.lua.table()
    client.lua.globals().WowTogetherGoldDB = client.lua.table()
    source = (ROOT / "WowTogether_Gold" / "Gold.lua").read_text()
    client.lua.execute("assert(loadstring(...))(select(2, ...))", source, "WowTogether_Gold", private)
    return private


class GoldSkeletonTests(unittest.TestCase):
    def test_registration_settings_slash_and_probe(self):
        client = Client(quests=(), default_guide=True)
        private = load_gold(client)
        self.assertTrue(private.enabled)
        self.assertIsNot(private, client.ns)
        self.assertIsNotNone(client.ns.ui.viewChoice.options["module:gold"])
        self.assertIsNotNone(client.ns.settings.pages["module:gold"])
        self.assertTrue(client.ns.Option("gold.recordLoot"))
        client.ns.SetOption("gold.recordLoot", False)
        self.assertFalse(client.ns.Option("gold.recordLoot"))
        self.assertFalse(private.db.settings["gold.recordLoot"])
        client.ns.SetFilter("module:gold")
        client.lua.globals().SlashCmdList.WOWTOGETHER("gold")
        logs = client.lua.globals().logs
        self.assertIn("Gold tab", logs[len(logs)])
        client.ns.Diagnostics()
        report = client.ns.diagnosticsText.GetText(client.ns.diagnosticsText)
        self.assertIn("Gold module: ready", report)
        self.assertIn("Loot recording: off", report)

    def test_old_api_disables_with_chat_line(self):
        client = Client(quests=(), default_guide=True)
        client.lua.globals().WowTogetherModuleAPI.version = 0
        private = load_gold(client)
        self.assertFalse(private.enabled)
        self.assertIsNone(client.ns.ui.viewChoice.options["module:gold"])
        logs = client.lua.globals().logs
        self.assertIn("API v1 is required", logs[len(logs)])

    def test_toc_and_release_zip(self):
        toc = (ROOT / "WowTogether_Gold" / "WowTogether_Gold.toc").read_text()
        for line in ("## Interface: 16001", "## LoadOnDemand: 1",
                     "## Dependencies: WowTogether", "## SavedVariables: WowTogetherGoldDB",
                     "## X-WowTogether-Min: 0.8.107"):
            self.assertIn(line, toc.splitlines())
        with tempfile.TemporaryDirectory() as output:
            subprocess.run([sys.executable, str(ROOT / "tools" / "build_release.py"),
                            "--output", output], cwd=ROOT, check=True, capture_output=True)
            archive = next(Path(output).glob("WowTogether-*.zip"))
            with ZipFile(archive) as package:
                self.assertIn("WowTogether_Gold/WowTogether_Gold.toc", package.namelist())
                self.assertIn("WowTogether_Gold/Gold.lua", package.namelist())
                self.assertIsNone(package.testzip())


if __name__ == "__main__":
    unittest.main()
