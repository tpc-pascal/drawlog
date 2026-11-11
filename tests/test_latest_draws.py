import json
import unittest
from pathlib import Path

from scripts.update_latest_draws import parse_homepage, render_results_script


FIXTURE = Path(__file__).parent / "fixtures" / "vietlott-homepage.html"


class LatestDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = parse_homepage(FIXTURE.read_text(encoding="utf-8"))
        cls.products = {item["label"]: item for item in cls.results["products"]}

    def test_parses_the_latest_result_for_each_active_product(self):
        self.assertEqual(
            list(self.products),
            ["Lotto 5/35", "Max 3D Pro", "Max 3D", "Power 6/55", "Mega 6/45", "Bingo18", "Keno"],
        )
        self.assertEqual(self.products["Lotto 5/35"]["numbers"], ["06", "15", "22", "27", "31"])
        self.assertEqual(self.products["Lotto 5/35"]["special"], "01")
        self.assertEqual(self.products["Power 6/55"]["special"], "39")
        self.assertEqual(self.products["Mega 6/45"]["numbers"][-1], "36")

    def test_parses_three_digit_prize_modes_and_bingo_keno_draw_ids(self):
        max_3d = self.products["Max 3D"]
        self.assertEqual(
            [(group["mode"], group["prizes"][0]["numbers"]) for group in max_3d["prize_groups"]],
            [("Max 3D", ["251"]), ("Max 3D+", ["131"])],
        )
        self.assertEqual(self.products["Max 3D"]["prize_groups"][0]["prizes"][0]["prize"], "First")
        self.assertEqual(self.products["Max 3D Pro"]["prize_groups"][0]["mode"], "Max 3D Pro+")
        self.assertEqual(self.products["Bingo18"]["draw_id"], "0195424")
        self.assertEqual(self.products["Bingo18"]["total"], 13)
        self.assertEqual(self.products["Bingo18"]["size"], "Big")
        self.assertEqual(self.products["Keno"]["draw_id"], "0302402")
        self.assertEqual(len(self.products["Keno"]["numbers"]), 20)
        self.assertEqual(self.products["Keno"]["parity"], "Even (10)")
        self.assertEqual(self.products["Keno"]["size"], "Small (10)")

    def test_result_script_embeds_only_json_serializable_public_results(self):
        script = render_results_script(self.results)
        self.assertIn("root.DrawlogResults =", script)
        payload_text = script.split(" = ", 1)[1]
        payload, end = json.JSONDecoder().raw_decode(payload_text)
        self.assertEqual(len(payload), 2)
        self.assertTrue(payload_text[end:].startswith(";\n"))

    def test_rejects_a_homepage_missing_any_active_product(self):
        with self.assertRaisesRegex(ValueError, "missing results for"):
            parse_homepage("<html><body></body></html>")


if __name__ == "__main__":
    unittest.main()
