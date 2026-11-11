import unittest
from pathlib import Path
from unittest.mock import patch

import app


ROOT = Path(__file__).resolve().parents[1]


class SpaceAppTests(unittest.TestCase):
    def test_gradio_app_exposes_only_the_browser_interface(self):
        config = app.demo.get_config_file()
        component_types = [component["type"] for component in config["components"]]

        self.assertEqual(component_types.count("html"), 1)
        self.assertTrue(set(component_types) <= {"html", "api"})
        self.assertEqual(len(config["dependencies"]), 1)
        self.assertEqual(config["dependencies"][0]["api_name"], "lookup_official_draws")
        self.assertIsNone(app.zero_gpu_compatibility_marker())
        html = config["components"][0]["props"]["value"]
        self.assertIn('id="ticket-form"', html)
        self.assertIn('id="csv-file"', html)

    def test_client_assets_are_included_in_the_gradio_launch(self):
        javascript = app.build_javascript()
        styles = app.build_styles()

        self.assertIn("DrawlogGames", javascript)
        self.assertIn("DrawlogCsv", javascript)
        self.assertIn("DrawlogResults", javascript)
        self.assertIn("DrawlogTicketCheck", javascript)
        self.assertIn("lookup_official_draws", str(app.demo.get_config_file()["dependencies"]))
        self.assertIn('document.getElementById("ticket-form")', javascript)
        self.assertIn(".gradio-container", styles)
        self.assertIn("#drawlog-app select", styles)
        self.assertIn("#drawlog-app a", styles)

    def test_hugging_face_deployments_include_python_modules(self):
        workflows = (
            ROOT / ".github" / "workflows" / "hf-space.yml",
            ROOT / ".github" / "workflows" / "update-vietlott-results.yml",
        )

        for workflow in workflows:
            with self.subTest(workflow=workflow.name):
                self.assertIn('cp -R scripts "$temp_dir/scripts"', workflow.read_text())

    def test_automated_results_commits_use_the_github_app(self):
        workflow = (ROOT / ".github" / "workflows" / "update-vietlott-results.yml").read_text()

        self.assertIn("actions/create-github-app-token@v1", workflow)
        self.assertIn("vars.PASCAL_AUTOMATION_APP_ID", workflow)
        self.assertIn("secrets.PASCAL_AUTOMATION_PRIVATE_KEY", workflow)
        self.assertIn("348848148+pascal-automation-agent[bot]@users.noreply.github.com", workflow)
        self.assertIn('git push "https://github.com/${GITHUB_REPOSITORY}.git" HEAD:main', workflow)
        self.assertNotIn("github-actions[bot]", workflow)

    def test_history_api_returns_draws_in_an_explicit_response(self):
        draw = {"draw_id": "123", "draw_date": "2026-11-10"}
        with patch("app.lookup_official_draws", return_value=[draw]):
            self.assertEqual(
                app.lookup_official_draws_api("power_6_55", "2026-11-10"),
                {"draws": [draw], "error": None},
            )

    def test_history_api_reports_backend_errors_explicitly(self):
        with (
            patch("app.lookup_official_draws", side_effect=RuntimeError("upstream unavailable")),
            self.assertLogs("app", level="ERROR") as logs,
        ):
            response = app.lookup_official_draws_api("power_6_55", "2026-11-10")
        self.assertEqual(response, {"draws": [], "error": "RuntimeError: upstream unavailable"})
        self.assertIn("Draw history lookup failed", logs.output[0])


if __name__ == "__main__":
    unittest.main()
