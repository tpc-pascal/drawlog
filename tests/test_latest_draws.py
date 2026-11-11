import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.update_latest_draws import (
    _fetch_url,
    _is_plausible_fallback,
    _parse_xoso_third_party,
    _result_content,
    parse_homepage,
    render_results_script,
)


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

    def test_parses_valid_third_party_keno_results(self):
        balls = "".join(
            f'<span id="ball_{index}">{index}</span>'
            for index in range(1, 21)
        )
        page = (
            '<div id="kq-ky-pre">#302520</div>'
            '<div id="titleKeno">Thứ 4 ngày 11/11/2026</div>'
            f"{balls}"
        )

        result = _parse_xoso_third_party(page)["keno"]

        self.assertEqual(result["draw_id"], "302520")
        self.assertEqual(result["draw_date"], "2026-11-11")
        self.assertEqual(len(result["numbers"]), 20)
        self.assertEqual(result["source_label"], "xoso.net.vn")

    def test_rejects_malformed_third_party_results_instead_of_silently_skipping(self):
        page = "XS Max 3D Thứ Xổ số Max 3D Pro"

        with self.assertRaisesRegex(ValueError, "missing its draw ID or date"):
            _parse_xoso_third_party(page)

    def test_rejects_fallback_results_older_than_or_conflicting_with_snapshot(self):
        previous = {
            "draw_id": "01156",
            "draw_date": "2026-11-09",
            "numbers": ["131", "822"],
        }
        matching = {
            "draw_id": "1156",
            "draw_date": "2026-11-09",
            "numbers": ["131", "822"],
            "source_label": "xoso.net.vn",
        }
        older = {
            "draw_id": "01156",
            "draw_date": "2026-11-06",
            "numbers": ["962", "391"],
            "source_label": "xoso.net.vn",
        }
        conflicting = {
            "draw_id": "01156",
            "draw_date": "2026-11-09",
            "numbers": ["962", "391"],
            "source_label": "xoso.net.vn",
        }
        newer = {
            "draw_id": "01157",
            "draw_date": "2026-11-10",
            "numbers": ["962", "391"],
            "source_label": "xoso.net.vn",
        }

        self.assertTrue(_is_plausible_fallback(matching, previous))
        self.assertFalse(_is_plausible_fallback(older, previous))
        self.assertFalse(_is_plausible_fallback(conflicting, previous))
        self.assertTrue(_is_plausible_fallback(newer, previous))

    @patch("scripts.update_latest_draws.time.sleep")
    @patch("scripts.update_latest_draws.urllib.request.urlopen")
    def test_does_not_retry_forbidden_source_requests(self, urlopen, sleep):
        urlopen.side_effect = HTTPError("https://vietlott.vn/", 403, "Forbidden", {}, None)

        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            _fetch_url("https://vietlott.vn/")

        urlopen.assert_called_once()
        sleep.assert_not_called()

    def test_snapshot_comparison_includes_stale_status(self):
        current = {"draw_id": "1", "draw_date": "2026-11-10", "stale": True}
        verified = {"draw_id": "1", "draw_date": "2026-11-10", "stale": False}

        self.assertNotEqual(_result_content(current), _result_content(verified))


if __name__ == "__main__":
    unittest.main()
