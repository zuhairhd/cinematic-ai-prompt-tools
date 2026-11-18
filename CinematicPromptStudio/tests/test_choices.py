import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import choices
import core


class ChoiceTests(unittest.TestCase):
    def test_every_field_has_tip_and_options(self):
        self.assertEqual(set(choices.OPTIONS), set(core.FIELDS))
        self.assertEqual(set(choices.TIPS), set(core.FIELDS))
        for key, options in choices.OPTIONS.items():
            labels = [label for label, _, _ in options]
            self.assertGreaterEqual(len(options), 4, key)
            self.assertEqual(len(labels), len(set(labels)), key)

    def test_every_option_passes_validation(self):
        plan = core.validate_analysis(choices.build_guided_plan())
        for key, options in choices.OPTIONS.items():
            for label, instruction, _ in options:
                candidate = copy.deepcopy(plan)
                candidate["fields"][key] = choices.option_record(key, label)
                validated = core.validate_analysis(candidate)
                self.assertEqual(validated["fields"][key]["choice"], instruction)
                self.assertEqual(validated["fields"][key]["basis"], "user")

    def test_presets_and_related_reference_real_options(self):
        for name, picks in choices.PRESETS.items():
            for key, label in picks.items():
                self.assertIsNotNone(choices.find_option(key, label), (name, key, label))
        for key, related in choices.RELATED.items():
            self.assertTrue({key, *related} <= set(core.FIELDS))

    def test_guided_plan_compiles_full_prompt(self):
        text = core.build_prompt(choices.build_guided_plan(), "4:5", "Midjourney")
        self.assertIn("85 mm", text)
        self.assertTrue(text.endswith("--ar 4:5 --raw"))


if __name__ == "__main__":
    unittest.main()
