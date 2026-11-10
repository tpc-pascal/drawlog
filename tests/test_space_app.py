import unittest

import app


class SpaceAppTests(unittest.TestCase):
    def test_gradio_app_exposes_only_the_browser_interface(self):
        config = app.demo.get_config_file()

        self.assertEqual(
            [component["type"] for component in config["components"]],
            ["html"],
        )
        self.assertEqual(config["dependencies"], [])
        self.assertIsNone(app.zero_gpu_compatibility_marker())
        html = config["components"][0]["props"]["value"]
        self.assertIn('id="ticket-form"', html)
        self.assertIn('id="csv-file"', html)

    def test_client_assets_are_included_in_the_gradio_launch(self):
        javascript = app.build_javascript()
        styles = app.build_styles()

        self.assertIn("DrawlogGames", javascript)
        self.assertIn("DrawlogCsv", javascript)
        self.assertIn('document.getElementById("ticket-form")', javascript)
        self.assertIn(".gradio-container", styles)
        self.assertIn("#drawlog-app select", styles)
        self.assertIn("#drawlog-app a", styles)


if __name__ == "__main__":
    unittest.main()
