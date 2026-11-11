import unittest
from datetime import date
from urllib.error import HTTPError
from unittest.mock import patch

from scripts.ticket_history import (
    HistoryRowsParser,
    OfficialHistoryBlocked,
    PRODUCT_LOOKUPS,
    _ajaxpro_request,
    _api_payload,
    _lookup_official_draws,
    _lookup_xoso_draws,
    _parse_history_rows,
    _parse_xoso_draw,
    _render_info,
    lookup_official_draws,
)


BINGO_ROW = """
<table><tr>
  <td><a href="/view-detail-bingo18-result?id=0195579">10/11/2026</a>
    <div><a href="/view-detail-bingo18-result?id=0195579">#0195579</a></div></td>
  <td><span class="bong_tron_bingo small">3</span>
    <span class="bong_tron_bingo small">1</span>
    <span class="bong_tron_bingo small">1</span></td>
  <td>5</td><td>Nhỏ</td>
</tr></table>
"""

KENO_ROW = """
<table><tr>
  <td><a href="/view-detail-keno-result?id=0302519">10/11/2026</a>
    <div><a href="/view-detail-keno-result?id=0302519">#0302519</a></div></td>
  <td><span class="bong_tron small">06</span><span class="bong_tron small">10</span>
    <span class="bong_tron small">15</span><span class="bong_tron small">19</span>
    <span class="bong_tron small">36</span><span class="bong_tron small">43</span>
    <span class="bong_tron small">46</span><span class="bong_tron small">49</span>
    <span class="bong_tron small">50</span><span class="bong_tron small">52</span>
    <span class="bong_tron small">53</span><span class="bong_tron small">55</span>
    <span class="bong_tron small">65</span><span class="bong_tron small">68</span>
    <span class="bong_tron small">70</span><span class="bong_tron small">71</span>
    <span class="bong_tron small">72</span><span class="bong_tron small">74</span>
    <span class="bong_tron small">75</span><span class="bong_tron small">76</span></td>
  <td>Chẵn (11)</td><td>Lớn (15)</td>
</tr></table>
"""

MAX3D_PRO_ROW = """
<table><tr><td>
  <div>Kỳ quay: <a href="/max-3DPro?id=00803">00803</a> | Ngày: 10/11/2026</div>
  <h5>Giải Đặc biệt</h5>
  <span class="bong_tron tiny">9</span><span class="bong_tron tiny">0</span><span class="bong_tron tiny">0</span>
  <span class="bong_tron tiny">3</span><span class="bong_tron tiny">9</span><span class="bong_tron tiny">0</span>
  <h5>Giải Nhất</h5>
  <span class="bong_tron tiny">1</span><span class="bong_tron tiny">3</span><span class="bong_tron tiny">2</span>
  <span class="bong_tron tiny">6</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">4</span>
  <span class="bong_tron tiny">8</span><span class="bong_tron tiny">0</span><span class="bong_tron tiny">2</span>
  <span class="bong_tron tiny">3</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">8</span>
  <h5>Giải Nhì</h5>
  <span class="bong_tron tiny">3</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">8</span>
  <span class="bong_tron tiny">4</span><span class="bong_tron tiny">1</span><span class="bong_tron tiny">7</span>
  <span class="bong_tron tiny">1</span><span class="bong_tron tiny">0</span><span class="bong_tron tiny">5</span>
  <span class="bong_tron tiny">4</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">8</span>
  <span class="bong_tron tiny">4</span><span class="bong_tron tiny">8</span><span class="bong_tron tiny">6</span>
  <span class="bong_tron tiny">5</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">9</span>
  <h5>Giải ba</h5>
  <span class="bong_tron tiny">0</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">8</span>
  <span class="bong_tron tiny">9</span><span class="bong_tron tiny">3</span><span class="bong_tron tiny">3</span>
  <span class="bong_tron tiny">5</span><span class="bong_tron tiny">4</span><span class="bong_tron tiny">5</span>
  <span class="bong_tron tiny">8</span><span class="bong_tron tiny">0</span><span class="bong_tron tiny">1</span>
  <span class="bong_tron tiny">7</span><span class="bong_tron tiny">4</span><span class="bong_tron tiny">1</span>
  <span class="bong_tron tiny">6</span><span class="bong_tron tiny">0</span><span class="bong_tron tiny">3</span>
  <span class="bong_tron tiny">4</span><span class="bong_tron tiny">5</span><span class="bong_tron tiny">4</span>
  <span class="bong_tron tiny">1</span><span class="bong_tron tiny">6</span><span class="bong_tron tiny">1</span>
</td></tr></table>
"""


class TicketHistoryTests(unittest.TestCase):
    def test_api_payload_contains_only_public_game_and_date_search_values(self):
        payload = _api_payload(
            "keno",
            {"SiteId": "main.frontend.vi", "SiteLang": "vi"},
            "2026-11-10",
            2,
            119,
        )

        self.assertEqual(payload["GameId"], "6")
        self.assertEqual(payload["DrawDate"], "10/11/2026")
        self.assertEqual(payload["GameDrawNo"], "")
        self.assertEqual(payload["number"], "")
        self.assertEqual(payload["OddEven"], 2)
        self.assertEqual(payload["UpperLower"], 2)
        self.assertEqual(payload["PageIndex"], 2)
        self.assertEqual(payload["TotalRow"], 119)
        self.assertFalse(any("ticket" in key.lower() or "combination" in key.lower() for key in payload))

    def test_standard_game_payloads_use_only_empty_ticket_search_fields(self):
        mega = _api_payload("mega_6_45", {}, "2026-11-10", 0, 0)
        lotto = _api_payload("lotto_5_35", {}, "2026-11-10", 1, 0)
        max3d = _api_payload("max_3d", {}, "2026-11-10", 2, 0)
        max3d_pro = _api_payload("max_3d_pro", {}, "2026-11-10", 3, 0)

        self.assertEqual(mega["Key"], "8290fce2")
        self.assertEqual((len(mega["ArrayNumbers"]), len(mega["ArrayNumbers"][0])), (6, 18))
        self.assertTrue(all(not number for row in mega["ArrayNumbers"] for number in row))
        self.assertEqual(lotto["Key"], "d0ea794f")
        self.assertEqual((len(lotto["ArrayNumbers"]), len(lotto["ArrayNumbers"][0])), (5, 35))
        self.assertEqual(max3d["number01"], "")
        self.assertEqual(max3d["number02"], "")
        self.assertEqual(max3d_pro["GameId"], "7")
        self.assertEqual(max3d_pro["number01"], "")
        self.assertEqual(max3d_pro["number02"], "")
        self.assertNotIn("CheckMulti", max3d_pro)
        self.assertEqual(PRODUCT_LOOKUPS["max_3d_pro"][0], "GameMax3DProCompareWebPart")
        self.assertNotIn("DrawDate", mega)
        self.assertNotIn("DrawDate", max3d_pro)

    def test_render_info_uses_the_ajaxpro_value_as_the_context(self):
        context = {"SiteId": "main.frontend.vi", "SiteURL": "https://vietlott.vn"}
        with patch("scripts.ticket_history._ajaxpro_request", return_value=context):
            self.assertEqual(_render_info("https://vietlott.vn/"), {**context, "SiteLang": "vi"})
        _render_info.cache_clear()

    def test_classifies_vietlott_http_403_for_secondary_fallback(self):
        forbidden = HTTPError("https://vietlott.vn/ajaxpro/", 403, "Forbidden", {}, None)
        with patch("scripts.ticket_history.urllib.request.urlopen", side_effect=forbidden):
            with self.assertRaises(OfficialHistoryBlocked):
                _ajaxpro_request("history", "lookup", {}, "https://vietlott.vn/")

    def test_parses_a_labeled_power_draw_from_the_secondary_archive(self):
        html = """
          <li>Mở thưởng ngày Thứ Bảy, 07-11-2026</li>
          <span class="mega-jackpot-title">Kỳ quay thưởng: <strong>#01421</strong></span>
          <div class="mega-rows">
            <span class="icon_xsmga">05</span><span class="icon_xsmga">19</span>
            <span class="icon_xsmga">20</span><span class="icon_xsmga">26</span>
            <span class="icon_xsmga">44</span><span class="icon_xsmga">53</span>
            <span class="icon_xsmga bgyelow">39</span>
          </div>
        """
        source_url = "https://xoso.net.vn/xo-so-power-655-ngay-7-11-2026.html"

        self.assertEqual(_parse_xoso_draw(html, "power_6_55", "2026-11-07", source_url), {
            "label": "Power 6/55",
            "draw_id": "01421",
            "draw_date": "2026-11-07",
            "source_url": source_url,
            "source_label": "xoso.net.vn",
            "numbers": ["05", "19", "20", "26", "44", "53"],
            "special": "39",
        })

    def test_uses_the_archive_draw_date_not_the_page_latest_date(self):
        html = """
          <h1>Mega 6/45 08/11/2026</h1>
          <p>Mở thưởng ngày Thứ Tư, 11-11-2026</p>
          <h2>XS Mega 08-11-2026</h2>
          <span class="mega-jackpot-title">Kỳ quay thưởng: <strong>#01586</strong></span>
          <div class="mega-rows">
            <span class="icon_xsmga">01</span><span class="icon_xsmga">02</span>
            <span class="icon_xsmga">14</span><span class="icon_xsmga">20</span>
            <span class="icon_xsmga">23</span><span class="icon_xsmga">36</span>
          </div>
        """

        draw = _parse_xoso_draw(
            html,
            "mega_6_45",
            "2026-11-08",
            "https://xoso.net.vn/xo-so-mega-ngay-8-11-2026.html",
        )
        self.assertEqual(draw["draw_id"], "01586")
        self.assertEqual(draw["draw_date"], "2026-11-08")
        self.assertEqual(draw["numbers"], ["01", "02", "14", "20", "23", "36"])
        self.assertEqual(draw["source_label"], "xoso.net.vn")

    def test_uses_the_secondary_archive_when_vietlott_denies_history(self):
        draw = {
            "draw_id": "01421",
            "draw_date": "2026-11-07",
            "source_label": "xoso.net.vn",
        }
        with (
            patch(
                "scripts.ticket_history._lookup_official_draws",
                side_effect=OfficialHistoryBlocked("Vietlott returned HTTP 403."),
            ),
            patch("scripts.ticket_history._lookup_xoso_draws", return_value=[draw]) as fallback,
        ):
            self.assertEqual(lookup_official_draws("power_6_55", "2026-11-07"), [draw])
        fallback.assert_called_once()

    def test_does_not_use_the_secondary_archive_for_other_errors(self):
        with (
            patch("scripts.ticket_history._lookup_official_draws", side_effect=RuntimeError("HTTP 500")),
            patch("scripts.ticket_history._lookup_xoso_draws") as fallback,
            self.assertRaisesRegex(RuntimeError, "HTTP 500"),
        ):
            lookup_official_draws("power_6_55", "2026-11-07")
        fallback.assert_not_called()

    def test_reports_games_without_a_secondary_archive(self):
        with self.assertRaisesRegex(RuntimeError, "No xoso.net.vn historical fallback"):
            _lookup_xoso_draws("lotto_5_35", date(2026, 11, 7), OfficialHistoryBlocked("HTTP 403"))

    def test_parses_all_bingo18_results_from_a_history_page(self):
        results = _parse_history_rows(BINGO_ROW, "bingo_18")

        self.assertEqual(results, [{
            "label": "Bingo18",
            "draw_id": "0195579",
            "draw_date": "2026-11-10",
            "source_url": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/winning-number-bingo18",
            "numbers": ["3", "1", "1"],
            "total": 5,
            "size": "Small",
        }])

    def test_parses_all_keno_numbers_and_public_draw_metadata(self):
        results = _parse_history_rows(KENO_ROW, "keno")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["draw_id"], "0302519")
        self.assertEqual(results[0]["draw_date"], "2026-11-10")
        self.assertEqual(len(results[0]["numbers"]), 20)
        self.assertEqual(results[0]["parity"], "Even (11)")
        self.assertEqual(results[0]["size"], "Big (15)")

    def test_parses_standard_draw_rows_and_max3d_pro_prize_tiers(self):
        def standard_row(path, draw_id, draw_date, numbers):
            spans = "".join(f'<span class="bong_tron">{number}</span>' for number in numbers)
            return (
                f'<table><tr><td>{draw_date}</td><td><a href="/{path}?id={draw_id}">'
                f"{draw_id}</a></td><td>{spans}</td></tr></table>"
            )

        mega = _parse_history_rows(
            standard_row("645", "01586", "08/11/2026", ["01", "02", "14", "20", "23", "36"]),
            "mega_6_45",
        )[0]
        self.assertEqual(mega["draw_id"], "01586")
        self.assertEqual(mega["numbers"], ["01", "02", "14", "20", "23", "36"])
        power = _parse_history_rows(
            standard_row("655", "01422", "10/11/2026", ["01", "02", "21", "38", "39", "51", "12"]),
            "power_6_55",
        )[0]
        self.assertEqual(power["numbers"], ["01", "02", "21", "38", "39", "51"])
        self.assertEqual(power["special"], "12")
        lotto = _parse_history_rows(
            standard_row("535", "01000", "10/11/2026", ["04", "08", "12", "21", "26", "05"]),
            "lotto_5_35",
        )[0]
        self.assertEqual(lotto["numbers"], ["04", "08", "12", "21", "26"])
        self.assertEqual(lotto["special"], "05")

        max3d_pro = _parse_history_rows(MAX3D_PRO_ROW, "max_3d_pro")[0]
        prizes = {
            prize["prize"]: prize["numbers"]
            for prize in max3d_pro["prize_groups"][0]["prizes"]
        }
        self.assertEqual(max3d_pro["draw_id"], "00803")
        self.assertEqual(prizes["Special"], ["900", "390"])
        self.assertEqual(prizes["First"], ["132", "654", "802", "358"])
        self.assertEqual(len(prizes["Fourth"]), 20)
        self.assertEqual(prizes["Fifth"], ["900", "390"])
        self.assertEqual(len(prizes["Sixth"]), 18)

    def test_history_parser_ignores_headers_without_draw_links(self):
        self.assertEqual(
            _parse_history_rows("<table><tr><th>Date</th><th>Result</th></tr></table>", "bingo_18"),
            [],
        )

    def test_rejects_invalid_product_or_noncanonical_date_before_network_access(self):
        with patch("scripts.ticket_history._lookup_official_draws") as lookup:
            with self.assertRaisesRegex(ValueError, "supported Vietlott product"):
                lookup_official_draws("unknown", "2026-11-10")
            with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                lookup_official_draws("keno", "10/11/2026")
            lookup.assert_not_called()

    def test_filters_lookup_results_to_the_requested_draw_date(self):
        _lookup_official_draws.cache_clear()
        pages = [
            {
                "RetNumber": 1,
                "HtmlContent": BINGO_ROW,
            },
        ]
        with (
            patch("scripts.ticket_history._render_info", return_value={"SiteLang": "vi"}),
            patch("scripts.ticket_history._history_page", side_effect=pages) as history_page,
        ):
            result = lookup_official_draws("bingo_18", "2026-11-10")
        _lookup_official_draws.cache_clear()

        self.assertEqual([draw["draw_id"] for draw in result], ["0195579"])
        self.assertEqual(history_page.call_count, 1)

    def test_paginates_standard_history_by_date_without_requesting_ticket_numbers(self):
        def mega_row(draw_id, draw_date):
            return (
                f'<tr><td>{draw_date}</td><td><a href="/645?id={draw_id}">{draw_id}</a></td><td>'
                + "".join(f'<span class="bong_tron">{number:02}</span>' for number in range(1, 7))
                + "</td></tr>"
            )

        page_zero = "<table>" + "".join(
            mega_row(f"{draw_id:05}", "11/11/2026" if draw_id > 101 else "10/11/2026")
            for draw_id in range(108, 100, -1)
        ) + "</table>"
        page_one = "<table>" + mega_row("00100", "10/11/2026") + mega_row("00099", "09/11/2026") + "</table>"
        pages = [
            {"RetNumber": 0, "HtmlContent": page_zero},
            {"RetNumber": 0, "HtmlContent": page_one},
        ]
        _lookup_official_draws.cache_clear()
        with (
            patch("scripts.ticket_history._render_info", return_value={"SiteLang": "vi"}),
            patch("scripts.ticket_history._history_page", side_effect=pages) as history_page,
        ):
            result = lookup_official_draws("mega_6_45", "2026-11-10")
        _lookup_official_draws.cache_clear()

        self.assertEqual([draw["draw_id"] for draw in result], ["00100", "00101"])
        self.assertEqual(history_page.call_count, 2)
        self.assertEqual(
            [call.args[2] for call in history_page.call_args_list],
            [0, 1],
        )


if __name__ == "__main__":
    unittest.main()
