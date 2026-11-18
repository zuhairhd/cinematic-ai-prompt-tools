import copy
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import core


class GuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.studio = app.Studio()
        except app.tk.TclError as exc:
            if "display" in str(exc).lower():
                self.skipTest("A working desktop display is required.")
            raise
        self.addCleanup(self.studio.destroy)
        self.studio.update()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_demo_edit_clipboard_export_and_project_roundtrip(self):
        self.studio.demo()
        self.studio.update()
        self.assertEqual(len(self.studio.analysis["fields"]), 33)
        self.studio.notebook.select(1)
        self.studio.tree.selection_set("lens")
        self.studio.update()
        self.studio.put(self.studio.edit, "Use a 50 mm full-frame lens with gentle optical falloff.", readonly=False)
        self.studio.apply_choice()
        self.studio.copy_prompt()
        self.assertIn("50 mm", self.studio.clipboard_get())
        path = Path(self.temp.name) / "export.txt"
        with patch.object(app.filedialog, "asksaveasfilename", return_value=str(path)):
            self.studio.export()
        self.assertIn("50 mm", path.read_text())
        project = Path(self.temp.name) / "project.json"
        with patch.object(app.filedialog, "asksaveasfilename", return_value=str(project)):
            self.assertTrue(self.studio.save())
        self.studio.load_path(project)
        self.assertEqual(self.studio.analysis["fields"]["lens"]["basis"], "user")

    def test_guided_plan_option_and_kit(self):
        self.studio.guided()
        self.studio.update()
        self.assertEqual(len(self.studio.analysis["fields"]), 33)
        self.studio.tree.selection_set("lens")
        self.studio.update()
        self.assertIn("85mm portrait", self.studio.option_box.cget("values"))
        self.studio.option_choice.set("35mm environmental")
        self.studio.option_selected()
        self.studio.apply_choice()
        row = self.studio.analysis["fields"]["lens"]
        self.assertTrue(row["choice"].startswith("35 mm"))
        self.assertIn("guided options", row["reason"])
        self.assertIn("Camera-to-subject distance", self.studio.status.get())
        self.studio.kit_choice.set("After hours: split light")
        self.studio.apply_kit()
        self.assertIn("Split lighting", self.studio.output.get("1.0", "end"))

    def prepare_test_image(self):
        path = Path(self.temp.name) / "test.png"
        Image.new("RGB", (320, 400), (60, 80, 90)).save(path)
        self.studio.prepared = core.prepare_image(path)
        self.studio.image_meta = self.studio.prepared.metadata
        self.studio.render_image()
        self.studio.api_key = "test-only"

    def run_until_done(self):
        deadline = time.monotonic() + 3
        while self.studio.busy and time.monotonic() < deadline:
            self.studio.update()
            time.sleep(0.01)
        self.assertFalse(self.studio.busy)

    def test_background_success_updates_real_widgets(self):
        self.prepare_test_image()
        analysis = core.load_project(app.ROOT / "example_project.json")["analysis"]
        with patch.object(app, "analyze_image", return_value=(analysis, {})):
            self.studio.start_analysis()
            self.run_until_done()
        self.assertIn("33/33", self.studio.status.get())
        self.assertIn("LIGHTING", self.studio.output.get("1.0", "end"))

    def test_background_error_preserves_existing_plan(self):
        self.prepare_test_image()
        self.studio.analysis = core.load_project(app.ROOT / "example_project.json")["analysis"]
        original = copy.deepcopy(self.studio.analysis)
        with patch.object(app, "analyze_image", side_effect=core.StudioError("mock connection failure")), patch.object(app.messagebox, "showerror") as error:
            self.studio.start_analysis()
            self.run_until_done()
        self.assertEqual(self.studio.analysis, original)
        error.assert_called_once()

    def test_canceled_late_result_is_discarded(self):
        self.studio.job_id = 10
        self.studio.set_busy(True)
        self.studio.cancel()
        self.studio.events.put((10, "success", (None, None, None, None)))
        self.studio.poll()
        self.assertIsNone(self.studio.analysis)
        self.assertFalse(self.studio.busy)


if __name__ == "__main__":
    unittest.main()
