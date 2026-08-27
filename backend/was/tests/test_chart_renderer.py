"""Tests for WAS Matplotlib and Seaborn chart rendering."""

# Standard Python Libraries
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Third-Party Libraries
from matplotlib import pyplot as plt
from PIL import Image

# First-Party Libraries
from was_reports import chart_renderer, report_metrics

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "was_report_metrics.xml"
CURRENT_TIME = datetime(2026, 8, 27, 13, 0)


class ChartRendererTests(unittest.TestCase):
    """Validate chart filenames, formats, and resource cleanup."""

    def test_render_report_charts_creates_active_template_images(self) -> None:
        """Render all five generated PNG files used by the legacy template."""
        metrics = report_metrics.calculate_finding_metrics(
            FIXTURE_PATH.read_bytes(),
            CURRENT_TIME,
        )
        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory)
            artifacts = chart_renderer.render_report_charts(
                finding_metrics=metrics,
                ages=[26, 57, 87],
                severities=["4", "3", "5"],
                asset_directory=output_directory,
            )
            artifact_paths = [
                artifacts.owasp_graph,
                artifacts.group_graph,
                artifacts.donut,
                artifacts.histogram,
                artifacts.monthly,
            ]
            for artifact_path in artifact_paths:
                self.assertTrue(artifact_path.is_file())
                with Image.open(artifact_path) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertGreater(image.width, 0)
                    self.assertGreater(image.height, 0)

        self.assertEqual(plt.get_fignums(), [])

    def test_percentage_values_handles_empty_groups(self) -> None:
        """Return zero percentages when no group findings exist."""
        self.assertEqual(
            chart_renderer.percentage_values([0, 0, 0]),
            [0.0, 0.0, 0.0],
        )

    def test_format_month_year_matches_legacy_labels(self) -> None:
        """Format month labels without platform-specific strftime flags."""
        self.assertEqual(chart_renderer.format_month_year("August 2026"), "8/26")

    def test_render_empty_group_graph_still_creates_png(self) -> None:
        """Preserve the legacy empty pie-chart artifact behavior."""
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "figure3.png"
            result = chart_renderer.render_group_graph({}, output_path)

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.is_file())

        self.assertEqual(plt.get_fignums(), [])


if __name__ == "__main__":
    unittest.main()
