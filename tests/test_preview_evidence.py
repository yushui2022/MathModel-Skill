"""Preview images cannot promote themselves to formal computational evidence."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parents[1] / "packages/claude/.claude/skills/data-cleaning-and-visualization/scripts"
sys.path.insert(0, str(DIRECTORY))
import generate_paper_figures_from_plan as generator
from paper_figure_templates import infer_template


class PreviewTests(unittest.TestCase):
    def test_preview_has_nonformal_role(self):
        item = generator.index_item({"figure_id": "f1", "output_path": "figures/test.png"}, True)
        self.assertEqual(item["evidence_role"], "exploratory")
        self.assertNotEqual(item["status"], "computed")

    def test_sensitivity_hint_title_and_type_cannot_bypass(self):
        for spec in ({"title": "参数敏感性"}, {"chart_type": "sensitivity_curve"},
                     {"template_hint": "plot_sensitivity_curve"}):
            with self.subTest(spec=spec), patch.object(generator, "plot_figure_spec") as plot:
                result = generator.generate_one(spec)
                self.assertFalse(result["exists"])
                self.assertEqual(result["evidence_role"], "exploratory")
                plot.assert_not_called()

    def test_chinese_heatmap_is_recognized(self):
        self.assertEqual(infer_template({"title": "特征热图"}), "heatmap")

    def test_generated_preview_title_is_explicit(self):
        import pandas as pd
        with tempfile.TemporaryDirectory(prefix="mathmodel-preview-") as temp:
            source = Path(temp) / "data.csv"
            source.write_text("x,y\n1,2\n2,4\n", encoding="utf-8")
            target = Path(temp) / "figure.png"
            with patch.object(generator, "plot_figure_spec", return_value={
                "ok": True, "path": str(target), "template": "line", "placeholder": False
            }) as plot:
                result = generator.generate_one({"data_source": str(source), "output_path": str(target),
                                                 "title": "Trend", "chart_type": "line"})
            self.assertTrue(plot.call_args.args[1]["title"].startswith("探索草图"))
            self.assertEqual(result["evidence_role"], "exploratory")


if __name__ == "__main__":
    unittest.main()
