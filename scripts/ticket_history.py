"""Look up official Vietlott draw results using only a game and draw date."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from functools import lru_cache
from html.parser import HTMLParser
from typing import Any

from scripts.update_latest_draws import (
    BIG_SMALL,
    EVEN_ODD,
    GAME_INFO,
    MAX_RESPONSE_BYTES,
    _base_result,
    _valid_range,
    _valid_unique_range,
    _translate_category,
    PRIZE_LABELS,
)


AJAXPRO_URL = "https://vietlott.vn/ajaxpro/"
XOSO_ARCHIVE_URLS = {
    "mega_6_45": "https://xoso.net.vn/xo-so-mega-ngay-{draw_date}.html",
    "power_6_55": "https://xoso.net.vn/xo-so-power-655-ngay-{draw_date}.html",
}
PAGE_SIZE = 6
MAX_DRAWS_PER_DAY = 500
MAX_HISTORY_PAGES = 500
PRODUCT_LOOKUPS = {
    "lotto_5_35": (
        "Game535CompareWebPart",
        "d0ea794f",
        "winning-number-535",
    ),
    "max_3d_pro": (
        "GameMax3DProCompareWebPart",
        "7",
        "winning-number-max-3Dpro",
    ),
    "max_3d": (
        "GameMax3DCompareWebPart",
        "5",
        "winning-number-max-3d",
    ),
    "power_6_55": (
        "Game655CompareWebPart",
        "23bbd667",
        "winning-number-655",
    ),
    "mega_6_45": (
        "Game645CompareWebPart",
        "8290fce2",
        "winning-number-645",
    ),
    "bingo_18": (
        "GameBingoCompareWebPart",
        "8",
        "winning-number-bingo18",
    ),
    "keno": (
        "GameKenoCompareWebPart",
        "6",
        "winning-number-keno",
    ),
}


class OfficialHistoryBlocked(RuntimeError):
    pass


class HistoryRowsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, Any]] = []
        self.row: dict[str, Any] | None = None
        self.cell: dict[str, Any] | None = None
        self.number_span = False
        self.prize_heading_parts: list[str] | None = None
        self.prize_label: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "tr" and self.row is None:
            self.row = {"cells": [], "hrefs": []}
        elif tag in ("td", "th") and self.row is not None and self.cell is None:
            self.cell = {"parts": [], "numbers": [], "prize_digits": {}}
        elif tag == "h5" and self.row is not None:
            self.prize_heading_parts = []
        elif tag == "a" and self.row is not None and attributes.get("href"):
            self.row["hrefs"].append(attributes["href"])
        elif tag == "span" and self.cell is not None:
            self.number_span = any(name.startswith("bong_tron") for name in classes)

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["parts"].append(data)
            if self.number_span and data.strip().isdigit():
                self.cell["numbers"].append(data.strip())
                if self.prize_label:
                    self.cell["prize_digits"].setdefault(self.prize_label, []).append(data.strip())
        if self.prize_heading_parts is not None:
            self.prize_heading_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self.number_span = False
        elif tag == "h5" and self.prize_heading_parts is not None:
            self.prize_label = " ".join("".join(self.prize_heading_parts).split()).lower()
            self.prize_heading_parts = None
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.cell["text"] = " ".join("".join(self.cell["parts"]).split())
            self.row["cells"].append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row["cells"]:
                self.rows.append(self.row)
            self.row = None
            self.prize_label = None


def _ajaxpro_request(
    endpoint: str,
    method: str,
    payload: dict[str, Any],
    referer: str,
) -> dict[str, Any]:
    url = f"{AJAXPRO_URL}{endpoint}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
            "Content-Type": "text/plain; charset=UTF-8",
            "X-AjaxPro-Method": method,
            "Referer": referer,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
        if len(content) > MAX_RESPONSE_BYTES:
            raise RuntimeError(f"{url} exceeded {MAX_RESPONSE_BYTES} bytes.")
        data = json.loads(content.decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 403:
            raise OfficialHistoryBlocked("Vietlott history lookup was denied with HTTP 403.") from error
        raise RuntimeError(f"Vietlott history lookup failed with HTTP {error.code}.") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach Vietlott history lookup: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Vietlott history lookup returned invalid JSON.") from error

    if "error" in data:
        detail = data["error"]
        raise RuntimeError(detail.get("Message") or "Vietlott history lookup failed.")
    value = data.get("value")
    if not isinstance(value, dict):
        raise RuntimeError("Vietlott history lookup returned an unexpected response.")
    return value


@lru_cache(maxsize=1)
def _render_info(referer: str) -> dict[str, Any]:
    info = _ajaxpro_request(
        "Vietlott.Utility.WebEnvironments,Vietlott.Utility.ashx",
        "ServerSideFrontEndCreateRenderInfo",
        {"SiteId": "main.frontend.vi"},
        referer,
    )
    if not isinstance(info, dict):
        raise RuntimeError("Vietlott did not return the required site context.")
    info["SiteLang"] = "vi"
    return info


def _draw_date_from_row(row: dict[str, Any]) -> str | None:
    text = " ".join(cell["text"] for cell in row["cells"])
    match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    if not match:
        return None
    return datetime.strptime(match.group(), "%d/%m/%Y").date().isoformat()


def _draw_id_from_row(row: dict[str, Any]) -> tuple[str | None, str | None]:
    for href in row["hrefs"]:
        match = re.search(r"[?&]id=([^&\"']+)", href)
        if match:
            return urllib.parse.unquote(match.group(1)), href
    return None, None


def _quick_result_from_row(
    row: dict[str, Any],
    game_id: str,
    draw_id: str,
    draw_date: str,
) -> dict[str, Any]:
    cells = row["cells"]
    if len(cells) < 3:
        raise ValueError(f"{GAME_INFO[game_id][0]} result row is incomplete.")

    result = _base_result(game_id, draw_id, draw_date)
    numbers = cells[1]["numbers"]
    if game_id == "bingo_18":
        if len(numbers) != 3 or any(not 1 <= int(number) <= 6 for number in numbers):
            raise ValueError("Bingo18 must publish three dice values from 1 to 6.")
        total = int(cells[2]["text"])
        if total != sum(map(int, numbers)):
            raise ValueError("Bingo18 published total does not match its three dice values.")
        result["numbers"] = numbers
        result["total"] = total
        if len(cells) > 3:
            result["size"] = _translate_category(cells[3]["text"], BIG_SMALL)
    elif game_id == "keno":
        if len(numbers) != 20 or len(set(numbers)) != 20:
            raise ValueError("Keno must publish twenty different numbers.")
        if any(not 1 <= int(number) <= 80 for number in numbers):
            raise ValueError("Keno numbers must be from 1 to 80.")
        result["numbers"] = numbers
        if len(cells) > 2:
            result["parity"] = _translate_category(cells[2]["text"], EVEN_ODD)
        if len(cells) > 3:
            result["size"] = _translate_category(cells[3]["text"], BIG_SMALL)
    else:
        expected = {"mega_6_45": 6, "power_6_55": 7, "lotto_5_35": 6}[game_id]
        numbers = cells[2]["numbers"] if len(cells) > 2 else []
        if len(numbers) != expected:
            raise ValueError(f"{GAME_INFO[game_id][0]} must publish {expected} draw numbers.")
        if game_id == "mega_6_45":
            if not _valid_unique_range(numbers, 1, 45):
                raise ValueError("Mega 6/45 numbers failed validation.")
            result["numbers"] = numbers
        elif game_id == "power_6_55":
            if not _valid_unique_range(numbers[:6], 1, 55) or not _valid_range(numbers[6], 1, 55):
                raise ValueError("Power 6/55 numbers failed validation.")
            result["numbers"], result["special"] = numbers[:6], numbers[6]
        else:
            if not _valid_unique_range(numbers[:5], 1, 35) or not _valid_range(numbers[5], 1, 12):
                raise ValueError("Lotto 5/35 numbers failed validation.")
            result["numbers"], result["special"] = numbers[:5], numbers[5]
    return result


def _three_digit_prizes(
    row: dict[str, Any],
    game_id: str,
    draw_id: str,
    draw_date: str,
) -> dict[str, Any]:
    if not row["cells"]:
        raise ValueError(f"{GAME_INFO[game_id][0]} result row is incomplete.")
    source_prizes = row["cells"][-1]["prize_digits"]
    prizes: dict[str, list[str]] = {}
    expected_counts = {
        "giải đặc biệt": 2,
        "giải nhất": 4,
        "giải nhì": 6,
        "giải ba": 8,
    }
    for source_label, expected_count in expected_counts.items():
        digits = source_prizes.get(source_label, [])
        if len(digits) != expected_count * 3 or any(not value.isdigit() for value in digits):
            raise ValueError(f"{GAME_INFO[game_id][0]} published an invalid {source_label} result.")
        prizes[PRIZE_LABELS[source_label]] = [
            "".join(digits[index:index + 3])
            for index in range(0, len(digits), 3)
        ]

    if any(not re.fullmatch(r"\d{3}", number) for values in prizes.values() for number in values):
        raise ValueError(f"{GAME_INFO[game_id][0]} published a malformed three-digit result.")

    if game_id == "max_3d_pro":
        main_prizes = prizes["First"] + prizes["Second"] + prizes["Third"]
        prizes.update({
            "Fourth": prizes["Special"] + main_prizes,
            "Fifth": list(prizes["Special"]),
            "Sixth": main_prizes,
        })

    result = _base_result(game_id, draw_id, draw_date)
    result["prize_groups"] = [{
        "mode": GAME_INFO[game_id][0],
        "prizes": [
            {"prize": prize, "numbers": values}
            for prize, values in prizes.items()
        ],
    }]
    return result


def _parse_history_rows(html: str, game_id: str) -> list[dict[str, Any]]:
    parser = HistoryRowsParser()
    parser.feed(html)
    parser.close()

    results: list[dict[str, Any]] = []
    for row in parser.rows:
        archive_id, _ = _draw_id_from_row(row)
        draw_date = _draw_date_from_row(row)
        if archive_id is None or draw_date is None:
            continue
        draw_match = re.search(
            r"#\s*(\d+)",
            " ".join(cell["text"] for cell in row["cells"]),
        )
        draw_id = draw_match.group(1) if draw_match else archive_id
        if game_id in ("bingo_18", "keno"):
            result = _quick_result_from_row(row, game_id, draw_id, draw_date)
            results.append(result)
        elif game_id in ("max_3d", "max_3d_pro"):
            results.append(_three_digit_prizes(row, game_id, draw_id, draw_date))
        elif game_id in ("mega_6_45", "power_6_55", "lotto_5_35"):
            results.append(_quick_result_from_row(row, game_id, draw_id, draw_date))
        else:
            raise ValueError(f"Unsupported historical result parser for {game_id}.")
    return results


def _api_payload(
    game_id: str,
    render_info: dict[str, Any],
    draw_date: str,
    page_index: int,
    total_rows: int,
) -> dict[str, Any]:
    _, game_key_or_id, _ = PRODUCT_LOOKUPS[game_id]
    if game_id in ("lotto_5_35", "power_6_55", "mega_6_45"):
        row_count, column_count = {
            "lotto_5_35": (5, 35),
            "power_6_55": (5, 18),
            "mega_6_45": (6, 18),
        }[game_id]
        return {
            "ORenderInfo": render_info,
            "Key": game_key_or_id,
            "GameDrawId": "",
            "ArrayNumbers": [[""] * column_count for _ in range(row_count)],
            "CheckMulti": False,
            "PageIndex": page_index,
        }
    if game_id == "max_3d_pro":
        return {
            "ORenderInfo": render_info,
            "GameId": game_key_or_id,
            "GameDrawId": "",
            "number01": "",
            "number02": "",
            "PageIndex": page_index,
        }
    if game_id == "max_3d":
        return {
            "ORenderInfo": render_info,
            "GameId": game_key_or_id,
            "GameDrawId": "",
            "number01": "",
            "number02": "",
            "CheckMulti": 0,
            "PageIndex": page_index,
        }
    payload: dict[str, Any] = {
        "ORenderInfo": render_info,
        "GameId": game_key_or_id,
        "GameDrawNo": "",
        "number": "",
        "DrawDate": datetime.strptime(draw_date, "%Y-%m-%d").strftime("%d/%m/%Y"),
        "PageIndex": page_index,
        "TotalRow": total_rows,
    }
    if game_id == "keno":
        payload.update({
            "ProcessType": 0,
            "OddEven": 2,
            "UpperLower": 2,
        })
    return payload


def _history_page(
    game_id: str,
    draw_date: str,
    page_index: int,
    total_rows: int,
    referer: str,
    render_info: dict[str, Any],
) -> dict[str, Any]:
    method_class, _, _ = PRODUCT_LOOKUPS[game_id]
    response = _ajaxpro_request(
        f"Vietlott.PlugIn.WebParts.{method_class},Vietlott.PlugIn.WebParts.ashx",
        "ServerSideDrawResult",
        _api_payload(game_id, render_info, draw_date, page_index, total_rows),
        referer,
    )
    if response.get("Error"):
        raise RuntimeError(response.get("InfoMessage") or "Vietlott rejected the history lookup.")
    if not isinstance(response.get("HtmlContent"), str):
        raise RuntimeError("Vietlott history lookup omitted its result rows.")
    return response


@lru_cache(maxsize=32)
def _lookup_official_draws(game_id: str, draw_date: str) -> tuple[dict[str, Any], ...]:
    _, _, page_name = PRODUCT_LOOKUPS[game_id]
    referer = f"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/{page_name}"
    render_info = _render_info(referer)
    results: list[dict[str, Any]] = []
    if game_id in ("bingo_18", "keno"):
        first_page = _history_page(game_id, draw_date, 0, 0, referer, render_info)
        total_rows = int(first_page.get("RetNumber") or 0)
        if total_rows > MAX_DRAWS_PER_DAY:
            raise RuntimeError(
                f"Vietlott returned {total_rows} draws for one date; refusing an unexpectedly large lookup."
            )
        page_count = (total_rows + PAGE_SIZE - 1) // PAGE_SIZE
        pages = [first_page]
        pages.extend(
            _history_page(game_id, draw_date, page_index, total_rows, referer, render_info)
            for page_index in range(1, page_count)
        )
        for page in pages:
            results.extend(
                result
                for result in _parse_history_rows(page["HtmlContent"], game_id)
                if result["draw_date"] == draw_date
            )
    else:
        # These APIs list newest-first pages but do not accept a draw-date filter.
        previous_page_oldest: str | None = None
        for page_index in range(MAX_HISTORY_PAGES):
            page = _history_page(game_id, draw_date, page_index, 0, referer, render_info)
            page_results = _parse_history_rows(page["HtmlContent"], game_id)
            if not page_results:
                if page_index == 0:
                    raise RuntimeError("Vietlott returned no parsable historical result rows.")
                break
            page_dates = [result["draw_date"] for result in page_results]
            if page_dates != sorted(page_dates, reverse=True):
                raise RuntimeError("Vietlott returned historical results out of date order.")
            if previous_page_oldest and page_dates[0] > previous_page_oldest:
                raise RuntimeError("Vietlott returned historical pages out of date order.")
            results.extend(
                result for result in page_results
                if result["draw_date"] == draw_date
            )
            previous_page_oldest = page_dates[-1]
            if previous_page_oldest < draw_date:
                break
        else:
            raise RuntimeError(
                f"Vietlott history exceeded the {MAX_HISTORY_PAGES}-page lookup limit."
            )

    unique = {
        result["draw_id"]: result
        for result in results
    }
    return tuple(
        unique[key]
        for key in sorted(
            unique,
            key=lambda value: (0, int(value)) if value.isdigit() else (1, value),
        )
    )


def lookup_official_draws(game_id: str, draw_date: str) -> list[dict[str, Any]]:
    """Return public draw data for one product and date; ticket details are never accepted."""
    if game_id not in PRODUCT_LOOKUPS:
        raise ValueError("Select a supported Vietlott product.")
    try:
        parsed_date = date.fromisoformat(draw_date)
    except (TypeError, ValueError) as error:
        raise ValueError("Draw date must use YYYY-MM-DD.") from error
    if parsed_date.isoformat() != draw_date:
        raise ValueError("Draw date must use YYYY-MM-DD.")
    try:
        return [dict(result) for result in _lookup_official_draws(game_id, draw_date)]
    except OfficialHistoryBlocked as official_error:
        return _lookup_xoso_draws(game_id, parsed_date, official_error)


def _parse_xoso_draw(html: str, game_id: str, draw_date: str, source_url: str) -> dict[str, Any]:
    plain_text = re.sub(r"<[^>]+>", " ", html)
    plain_text = " ".join(plain_text.split())
    draw_match = re.search(r"Kỳ quay thưởng:\s*#\s*(\d+)", plain_text, re.IGNORECASE)
    if draw_match is None:
        raise RuntimeError("xoso.net.vn did not provide a dated draw number.")
    date_matches = list(re.finditer(r"\d{1,2}[-/]\d{1,2}[-/]\d{4}", plain_text[:draw_match.start()]))
    if not date_matches:
        raise RuntimeError("xoso.net.vn did not provide a date for the draw.")
    result_date = datetime.strptime(
        date_matches[-1].group().replace("/", "-"),
        "%d-%m-%Y",
    ).date().isoformat()
    if result_date != draw_date:
        raise RuntimeError("xoso.net.vn returned a result for a different date.")

    raw_numbers = re.findall(
        r'<span\s+class="(icon_xsmga[^"]*)"[^>]*>\s*(\d{1,2})\s*</span>',
        html,
        re.IGNORECASE,
    )
    numbers = [number for _, number in raw_numbers]
    draw_id = draw_match.group(1)
    result = _base_result(game_id, draw_id, draw_date)
    result["source_url"] = source_url
    result["source_label"] = "xoso.net.vn"

    if game_id == "mega_6_45":
        if len(numbers) != 6 or not _valid_unique_range(numbers, 1, 45):
            raise RuntimeError("xoso.net.vn published an invalid Mega 6/45 draw.")
        result["numbers"] = numbers
    elif game_id == "power_6_55":
        if (
            len(numbers) != 7
            or not _valid_unique_range(numbers[:6], 1, 55)
            or not _valid_range(numbers[6], 1, 55)
            or "bgyelow" not in raw_numbers[6][0]
        ):
            raise RuntimeError("xoso.net.vn published an invalid Power 6/55 draw.")
        result["numbers"], result["special"] = numbers[:6], numbers[6]
    else:
        raise RuntimeError(f"xoso.net.vn fallback is not available for {GAME_INFO[game_id][0]}.")
    return result


def _lookup_xoso_draws(
    game_id: str,
    draw_date: date,
    official_error: OfficialHistoryBlocked,
) -> list[dict[str, Any]]:
    template = XOSO_ARCHIVE_URLS.get(game_id)
    if template is None:
        raise RuntimeError(
            f"{official_error} No xoso.net.vn historical fallback is available for {GAME_INFO[game_id][0]}."
        ) from official_error

    source_url = template.format(
        draw_date=f"{draw_date.day}-{draw_date.month}-{draw_date.year}",
    )
    request = urllib.request.Request(
        source_url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"xoso.net.vn historical lookup failed with HTTP {error.code}.") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach xoso.net.vn historical results: {error}") from error
    if len(content) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"xoso.net.vn response exceeded {MAX_RESPONSE_BYTES} bytes.")

    result = _parse_xoso_draw(content.decode("utf-8"), game_id, draw_date.isoformat(), source_url)
    return [result]
