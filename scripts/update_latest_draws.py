#!/usr/bin/env python3
"""Refresh Drawlog's public latest-draw snapshot from Vietlott's homepage."""

from __future__ import annotations

import json
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "latest-results.js"
SOURCE_URL = "https://vietlott.vn/"
MAX_RESPONSE_BYTES = 2_000_000
SOURCE_RETRIES = 3
GAME_ORDER = (
    "lotto_5_35",
    "max_3d_pro",
    "max_3d",
    "power_6_55",
    "mega_6_45",
    "bingo_18",
    "keno",
)
GAME_INFO = {
    "lotto_5_35": ("Lotto 5/35", "535.html"),
    "max_3d_pro": ("Max 3D Pro", "max-3Dpro.html"),
    "max_3d": ("Max 3D", "max-3D.html"),
    "power_6_55": ("Power 6/55", "655.html"),
    "mega_6_45": ("Mega 6/45", "645.html"),
    "bingo_18": ("Bingo18", "winning-number-bingo18"),
    "keno": ("Keno", "winning-number-keno"),
}
CARD_ALT_IDS = {
    "lotto 5/35": "lotto_5_35",
    "max3d pro": "max_3d_pro",
    "max 3d": "max_3d",
    "power 6/55": "power_6_55",
    "mega 6/45": "mega_6_45",
}
MODE_IDS = {
    "divMax3D": "Max 3D",
    "divMax3DPlus": "Max 3D+",
    "divMax3DProPlus": "Max 3D Pro+",
    "divMax3DPro": "Max 3D Pro",
}
BIG_SMALL = {
    "lớn": "Big",
    "hòa": "Tie",
    "nhỏ": "Small",
}
EVEN_ODD = {"chẵn": "Even", "lẻ": "Odd"}
PRIZE_LABELS = {
    "giải đặc biệt": "Special",
    "giải nhất": "First",
    "giải nhì": "Second",
    "giải ba": "Third",
    "giải tư": "Fourth",
    "giải năm": "Fifth",
    "giải sáu": "Sixth",
    "giải bảy": "Seventh",
}


class VietlottHomepageParser(HTMLParser):
    def __init__(self, detail_game_id: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.detail_game_id = detail_game_id
        self.cards: list[dict[str, Any]] = []
        self.result_rows: list[dict[str, Any]] = []
        self.card: dict[str, Any] | None = None
        self.card_div_depth = 0
        self.mode_stack: list[tuple[int, str]] = []
        self.heading_parts: list[str] | None = None
        self.span: dict[str, Any] | None = None
        self.row: dict[str, Any] | None = None
        self.cell: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "div":
            is_result_card = "box_kqtt" in classes
            is_detail_content = bool(
                self.detail_game_id
                and classes.intersection({"box_kqtt_nd_chinh", "box_kqtt_nd_chinh_home"})
            )
            if self.card is None and (is_result_card or is_detail_content):
                alt = GAME_INFO[self.detail_game_id][0] if self.detail_game_id else ""
                self.card = {"alt": alt, "heading": "", "text_parts": [], "balls": [], "prizes": []}
                self.card_div_depth = 1
                self.mode_stack = []
            elif self.card is not None:
                self.card_div_depth += 1
                mode = MODE_IDS.get(attributes.get("id") or "")
                if mode:
                    self.mode_stack.append((self.card_div_depth, mode))

        if self.card is not None:
            if tag == "img":
                self.card["alt"] = attributes.get("alt") or self.card["alt"]
            elif tag == "h5":
                self.heading_parts = []
            elif tag == "span":
                if "bong_tron" in classes:
                    self.span = {"type": "ball", "parts": []}
                elif classes.intersection({"large", "red"}) and self.cell is not None:
                    self.span = {"type": "prize_number", "parts": []}

        if tag == "tr" and self.row is None:
            self.row = {"cells": [], "hrefs": []}
        elif tag in ("td", "th") and self.row is not None and self.cell is None:
            self.cell = {"parts": [], "numbers": []}
        elif tag == "a" and self.row is not None and attributes.get("href"):
            self.row["hrefs"].append(attributes["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self.span is not None:
            value = "".join(self.span["parts"]).strip()
            if value.isdigit():
                if self.span["type"] == "ball" and self.card is not None:
                    self.card["balls"].append(value)
                elif self.span["type"] == "prize_number" and self.cell is not None:
                    self.cell["numbers"].append(value)
            self.span = None
        elif tag == "h5" and self.heading_parts is not None:
            if self.card is not None:
                heading = " ".join("".join(self.heading_parts).split())
                if re.search(r"#\s*\d+.*\d{2}/\d{2}/\d{4}", heading):
                    self.card["heading"] = heading
            self.heading_parts = None
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.cell["text"] = " ".join("".join(self.cell["parts"]).split())
            self.row["cells"].append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            has_quick_draw_link = any(
                "view-detail-bingo18-result" in url or "view-detail-keno-result" in url
                for url in self.row["hrefs"]
            )
            if self.card is not None and not has_quick_draw_link:
                self._finish_prize_row()
            else:
                self._finish_result_row()
            self.row = None
            self.cell = None
        elif tag == "div" and self.card is not None:
            if self.mode_stack and self.mode_stack[-1][0] == self.card_div_depth:
                self.mode_stack.pop()
            self.card_div_depth -= 1
            if self.card_div_depth == 0:
                self.cards.append(self.card)
                self.card = None
                self.mode_stack = []

    def handle_data(self, data: str) -> None:
        if self.card is not None:
            self.card["text_parts"].append(data)
        if self.heading_parts is not None:
            self.heading_parts.append(data)
        if self.span is not None:
            self.span["parts"].append(data)
        if self.cell is not None:
            self.cell["parts"].append(data)

    def _finish_prize_row(self) -> None:
        if self.card is None or self.row is None or len(self.row["cells"]) < 2:
            return
        first, second = self.row["cells"][:2]
        if first["text"].lower().startswith("giải") and second["numbers"]:
            mode = self.mode_stack[-1][1] if self.mode_stack else "Main"
            self.card["prizes"].append({
                "mode": mode,
                "prize": first["text"],
                "numbers": second["numbers"],
            })

    def _finish_result_row(self) -> None:
        if self.row is None:
            return
        urls = self.row["hrefs"]
        game_id = None
        if any("view-detail-bingo18-result" in url for url in urls):
            game_id = "bingo_18"
        elif any("view-detail-keno-result" in url for url in urls):
            game_id = "keno"
        if game_id:
            self.result_rows.append({"game_id": game_id, "cells": self.row["cells"], "hrefs": urls})


def _draw_metadata(heading: str) -> tuple[str, str]:
    match = re.search(r"#\s*(\d+)\s*ngày\s*(\d{2}/\d{2}/\d{4})", heading, re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not read the draw number and date from heading: {heading!r}")
    draw_date = datetime.strptime(match.group(2), "%d/%m/%Y").date().isoformat()
    return match.group(1), draw_date


def _base_result(game_id: str, draw_id: str, draw_date: str) -> dict[str, Any]:
    label, path = GAME_INFO[game_id]
    return {
        "label": label,
        "draw_id": draw_id,
        "draw_date": draw_date,
        "source_url": f"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/{path}",
    }


def _parse_product_cards(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for card in cards:
        game_id = CARD_ALT_IDS.get(card["alt"].strip().lower())
        if not game_id or game_id in results:
            continue
        if game_id in ("bingo_18", "keno"):
            continue
        card_text = " ".join(card["text_parts"])
        draw_id, draw_date = _draw_metadata(card["heading"] or card_text)
        result = _base_result(game_id, draw_id, draw_date)
        if game_id == "lotto_5_35":
            if len(card["balls"]) != 6:
                raise ValueError("Lotto 5/35 must publish five main numbers and one special number.")
            if (
                not _valid_unique_range(card["balls"][:5], 1, 35)
                or not _valid_range(card["balls"][5], 1, 12)
            ):
                raise ValueError("Lotto 5/35 published numbers are outside the official ranges.")
            result["numbers"] = card["balls"][:5]
            result["special"] = card["balls"][5]
        elif game_id == "power_6_55":
            if len(card["balls"]) != 7:
                raise ValueError("Power 6/55 must publish six main numbers and one special number.")
            if (
                not _valid_unique_range(card["balls"][:6], 1, 55)
                or not _valid_range(card["balls"][6], 1, 55)
            ):
                raise ValueError("Power 6/55 published numbers are outside the official ranges.")
            result["numbers"] = card["balls"][:6]
            result["special"] = card["balls"][6]
        elif game_id == "mega_6_45":
            if len(card["balls"]) != 6:
                raise ValueError("Mega 6/45 must publish six numbers.")
            if not _valid_unique_range(card["balls"], 1, 45):
                raise ValueError("Mega 6/45 published numbers are outside the official range.")
            result["numbers"] = card["balls"]
        else:
            if not card["prizes"]:
                raise ValueError(f"{result['label']} did not include any published prize numbers.")
            grouped: dict[str, list[dict[str, Any]]] = {}
            for prize in card["prizes"]:
                if any(not re.fullmatch(r"\d{3}", number) for number in prize["numbers"]):
                    raise ValueError(f"{result['label']} published a malformed three-digit result.")
                grouped.setdefault(prize["mode"], []).append({
                    "prize": PRIZE_LABELS.get(prize["prize"].strip().lower(), prize["prize"]),
                    "numbers": prize["numbers"],
                })
            result["prize_groups"] = [
                {"mode": mode, "prizes": prizes}
                for mode, prizes in grouped.items()
            ]
        results[game_id] = result
    return results


def _parse_quick_results(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        game_id = row["game_id"]
        cells = row["cells"]
        if len(cells) < 3:
            continue
        hrefs = row["hrefs"]
        id_matches = [re.search(r"[?&]id=(\d+)", url) for url in hrefs]
        id_match = next((match for match in id_matches if match), None)
        if not id_match:
            raise ValueError(f"{GAME_INFO[game_id][0]} result row has no draw ID.")
        date_match = re.search(r"\d{2}/\d{2}/\d{4}", cells[0]["text"])
        if not date_match:
            raise ValueError(f"{GAME_INFO[game_id][0]} result row has no draw date.")
        draw_date = datetime.strptime(date_match.group(), "%d/%m/%Y").date().isoformat()
        numbers = re.findall(r"(?<!\d)\d{1,2}(?!\d)", cells[1]["text"])
        result = _base_result(game_id, id_match.group(1), draw_date)

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
        else:
            if len(numbers) != 20 or len(set(numbers)) != 20:
                raise ValueError("Keno must publish twenty different numbers.")
            if any(not 1 <= int(number) <= 80 for number in numbers):
                raise ValueError("Keno numbers must be from 1 to 80.")
            result["numbers"] = numbers
            if len(cells) > 2:
                result["parity"] = _translate_category(cells[2]["text"], EVEN_ODD)
            if len(cells) > 3:
                result["size"] = _translate_category(cells[3]["text"], BIG_SMALL)
        previous = latest.get(game_id)
        if previous is None or int(result["draw_id"]) > int(previous["draw_id"]):
            latest[game_id] = result
    return latest


def _valid_range(value: str, minimum: int, maximum: int) -> bool:
    return value.isdigit() and minimum <= int(value) <= maximum


def _valid_unique_range(numbers: list[str], minimum: int, maximum: int) -> bool:
    return len(set(numbers)) == len(numbers) and all(
        _valid_range(number, minimum, maximum) for number in numbers
    )


def _translate_category(value: str, translations: dict[str, str]) -> str:
    lowered = value.strip().lower()
    for vietnamese, english in translations.items():
        if lowered.startswith(vietnamese):
            count = re.search(r"\((\d+)\)", value)
            return f"{english} ({count.group(1)})" if count else english
    return value.strip()


def parse_homepage(html: str) -> dict[str, Any]:
    parser = VietlottHomepageParser()
    parser.feed(html)
    parser.close()

    results = _parse_product_cards(parser.cards)
    results.update(_parse_quick_results(parser.result_rows))
    missing = [GAME_INFO[game_id][0] for game_id in GAME_ORDER if game_id not in results]
    if missing:
        raise ValueError(f"Vietlott homepage is missing results for: {', '.join(missing)}.")
    return {
        "source_url": SOURCE_URL,
        "products": [results[game_id] for game_id in GAME_ORDER],
    }


def render_results_script(results: dict[str, Any]) -> str:
    payload = json.dumps(results, ensure_ascii=False, indent=2)
    return (
        "(function (root) {\n"
        '  "use strict";\n'
        f"  root.DrawlogResults = {payload};\n"
        "})(globalThis);\n"
    )


class ThirdPartyTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, Any]]] = []
        self.row: list[dict[str, Any]] | None = None
        self.cell: dict[str, Any] | None = None
        self.number_span = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "tr" and self.row is None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None and self.cell is None:
            self.cell = {"parts": [], "numbers": []}
        elif tag == "span" and self.cell is not None:
            self.number_span = any(value.startswith("number_item") for value in classes)

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["parts"].append(data)
            if self.number_span and data.strip().isdigit():
                self.cell["numbers"].append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self.number_span = False
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.cell["text"] = " ".join("".join(self.cell["parts"]).split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None


class OfficialDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[str] = []
        self.heading_parts: list[str] | None = None
        self.rows: list[list[dict[str, Any]]] = []
        self.row: list[dict[str, Any]] | None = None
        self.cell: dict[str, Any] | None = None
        self.number_span = False
        self.draw_numbers: list[str] = []
        self.draw_number_span = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag in ("h5", "h3") and self.heading_parts is None:
            self.heading_parts = []
        if tag == "tr" and self.row is None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None and self.cell is None:
            self.cell = {"parts": [], "numbers": []}
        if tag == "span":
            self.draw_number_span = "bong_tron" in classes
            self.number_span = self.cell is not None and bool(classes.intersection({"red", "large"}))

    def handle_data(self, data: str) -> None:
        if self.heading_parts is not None:
            self.heading_parts.append(data)
        if self.cell is not None:
            self.cell["parts"].append(data)
            if self.number_span and data.strip().isdigit():
                self.cell["numbers"].append(data.strip())
        if self.draw_number_span and data.strip().isdigit():
            self.draw_numbers.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self.number_span = False
            self.draw_number_span = False
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.cell["text"] = " ".join("".join(self.cell["parts"]).split())
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag in ("h5", "h3") and self.heading_parts is not None:
            self.headings.append(" ".join("".join(self.heading_parts).split()))
            self.heading_parts = None


def _iso_date(value: str) -> str:
    for date_format in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unsupported draw date: {value!r}")


def parse_official_product_page(html: str, game_id: str) -> dict[str, Any]:
    if game_id in ("bingo_18", "keno"):
        parser = VietlottHomepageParser()
        parser.feed(html)
        parser.close()
        result = _parse_quick_results(parser.result_rows).get(game_id)
        if result is None:
            raise ValueError(f"The official product page did not contain a valid {GAME_INFO[game_id][0]} result.")
        return result

    parser = OfficialDetailParser()
    parser.feed(html)
    parser.close()
    heading = next(
        (value for value in parser.headings if re.search(r"#\s*\d+.*\d{2}/\d{2}/\d{4}", value)),
        None,
    )
    if heading is None:
        raise ValueError(f"The official {GAME_INFO[game_id][0]} page has no draw heading.")
    draw_id, draw_date = _draw_metadata(heading)
    result = _base_result(game_id, draw_id, draw_date)

    if game_id in ("lotto_5_35", "power_6_55", "mega_6_45"):
        count = {"lotto_5_35": 6, "power_6_55": 7, "mega_6_45": 6}[game_id]
        numbers = parser.draw_numbers
        if len(numbers) < count:
            raise ValueError(f"The official {GAME_INFO[game_id][0]} page has too few draw numbers.")
        numbers = numbers[:count]
        if game_id == "lotto_5_35":
            if not _valid_unique_range(numbers[:5], 1, 35) or not _valid_range(numbers[5], 1, 12):
                raise ValueError("The official Lotto 5/35 numbers failed validation.")
            result["numbers"], result["special"] = numbers[:5], numbers[5]
        elif game_id == "power_6_55":
            if not _valid_unique_range(numbers[:6], 1, 55) or not _valid_range(numbers[6], 1, 55):
                raise ValueError("The official Power 6/55 numbers failed validation.")
            result["numbers"], result["special"] = numbers[:6], numbers[6]
        else:
            if not _valid_unique_range(numbers, 1, 45):
                raise ValueError("The official Mega 6/45 numbers failed validation.")
            result["numbers"] = numbers
        return result

    prizes = []
    for row in parser.rows:
        if len(row) < 2 or not row[0]["text"].lower().startswith("giải"):
            continue
        values = row[1]["numbers"]
        if values and all(re.fullmatch(r"\d{3}", value) for value in values):
            prizes.append({
                "prize": PRIZE_LABELS.get(row[0]["text"].strip().lower(), row[0]["text"]),
                "numbers": values,
            })
    if not prizes:
        raise ValueError(f"The official {GAME_INFO[game_id][0]} page has no validated prize numbers.")
    result["prize_groups"] = [{
        "mode": "Max 3D Pro" if game_id == "max_3d_pro" else "Max 3D",
        "prizes": prizes,
    }]
    return result


def _third_party_section(page: str, start: str, end: str) -> str:
    start_index = page.find(start)
    if start_index < 0:
        raise ValueError(f"Third-party page is missing the {start!r} section.")
    end_index = page.find(end, start_index + len(start))
    if end_index < 0:
        raise ValueError(f"Third-party page is missing the section boundary {end!r}.")
    return page[start_index:end_index]


def _draw_metadata_from_section(section: str) -> tuple[str, str]:
    match = re.search(r"#\s*(\d+)\s*ngày\s*(\d{2}[/-]\d{2}[/-]\d{4})", section, re.IGNORECASE)
    if not match:
        match = re.search(r"Kỳ quay thưởng:\s*<strong>#\s*(\d+)</strong>", section, re.IGNORECASE)
        date = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", section)
        if not match or not date:
            raise ValueError("Third-party result is missing its draw ID or date.")
        return match.group(1).lstrip("0") or "0", _iso_date(date.group())
    return match.group(1).lstrip("0") or "0", _iso_date(match.group(2))


def _parse_xoso_third_party(page: str) -> dict[str, dict[str, Any]]:
    source_url = "https://xoso.net.vn/xs-vietlott.html"
    results: dict[str, dict[str, Any]] = {}

    keno_id = re.search(r'id="kq-ky-pre">\s*#(\d+)', page)
    keno_date = re.search(r'id="titleKeno"[^>]*>[^<]*?(\d{2}/\d{2}/\d{4})', page)
    if keno_id or keno_date:
        if not keno_id or not keno_date:
            raise ValueError("Third-party Keno result is missing its draw ID or date.")
        keno_numbers = {
            int(index): value
            for index, value in re.findall(r'id="ball_(\d+)"[^>]*>(\d{1,2})</span>', page)
        }
        numbers = [keno_numbers[index] for index in sorted(keno_numbers)]
        if len(numbers) != 20 or not _valid_unique_range(numbers, 1, 80):
            raise ValueError("Third-party Keno numbers failed validation.")
        results["keno"] = {
            **_base_result("keno", keno_id.group(1).lstrip("0") or "0", _iso_date(keno_date.group(1))),
            "source_url": source_url,
            "source_label": "xoso.net.vn",
            "numbers": numbers,
        }

    sections = (
        ("mega_6_45", "XS Mega", "Xổ số Power"),
        ("power_6_55", "Xổ số Power", "XS Max 3D Thứ"),
        ("max_3d", "XS Max 3D Thứ", "Xổ số Max 3D Pro"),
        ("max_3d_pro", "Xổ số Max 3D Pro", "Thông Tin Về"),
    )
    for game_id, start, end in sections:
        if start not in page:
            continue
        section = _third_party_section(page, start, end)
        draw_id, draw_date = _draw_metadata_from_section(section)
        if game_id in ("mega_6_45", "power_6_55"):
            numbers = re.findall(r'class="icon_xsmga[^"]*"[^>]*>(\d{1,2})</span>', section)
            required = 6 if game_id == "mega_6_45" else 7
            maximum = 45 if game_id == "mega_6_45" else 55
            if len(numbers) != required or not _valid_unique_range(numbers[:6], 1, maximum):
                raise ValueError(f"Third-party {GAME_INFO[game_id][0]} numbers failed validation.")
            result = _base_result(game_id, draw_id, draw_date)
            result["numbers"] = numbers[:6]
            if game_id == "power_6_55":
                if not _valid_range(numbers[6], 1, 55):
                    raise ValueError("Third-party Power 6/55 special number failed validation.")
                result["special"] = numbers[6]
        else:
            table_parser = ThirdPartyTableParser()
            table_parser.feed(section)
            table_parser.close()
            prizes = []
            accepted_labels = {"đb", "đặc biệt", "g1", "g2", "g3", "gkk"}
            for row in table_parser.rows:
                if len(row) < 2 or row[0]["text"].strip().lower() not in accepted_labels:
                    continue
                values = row[1]["numbers"]
                if values and all(re.fullmatch(r"\d{3}", value) for value in values):
                    prizes.append({
                        "prize": {
                            "đb": "Special",
                            "đặc biệt": "Special",
                            "g1": "First",
                            "g2": "Second",
                            "g3": "Third",
                            "gkk": "Consolation",
                        }[row[0]["text"].strip().lower()],
                        "numbers": values,
                    })
            if not prizes:
                raise ValueError(f"Third-party {GAME_INFO[game_id][0]} prize table was empty.")
            result = _base_result(game_id, draw_id, draw_date)
            result["prize_groups"] = [{"mode": GAME_INFO[game_id][0].replace(" ", ""), "prizes": prizes}]
        result["source_url"] = source_url
        result["source_label"] = "xoso.net.vn"
        results[game_id] = result
    return results


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        },
    )
    for attempt in range(SOURCE_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"{url} returned HTTP {response.status}.")
                content = response.read(MAX_RESPONSE_BYTES + 1)
            if len(content) > MAX_RESPONSE_BYTES:
                raise RuntimeError(f"{url} exceeded {MAX_RESPONSE_BYTES} bytes.")
            return content.decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == SOURCE_RETRIES - 1:
                raise RuntimeError(f"Could not fetch {url}: HTTP {error.code}.") from error
            time.sleep(2**attempt)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
            if attempt == SOURCE_RETRIES - 1:
                raise RuntimeError(f"Could not fetch {url}: {error}") from error
            time.sleep(2**attempt)
    raise RuntimeError(f"Could not fetch {url}.")


def fetch_homepage() -> str:
    return _fetch_url(SOURCE_URL)


def _read_previous_snapshot() -> dict[str, Any]:
    source = OUTPUT.read_text(encoding="utf-8")
    match = re.search(r"root\.DrawlogResults\s*=\s*(\{.*\});\s*\}\)\(globalThis\);", source, re.DOTALL)
    if not match:
        raise ValueError("The existing results snapshot has an unknown format.")
    return json.loads(match.group(1))


def _result_content(result: dict[str, Any]) -> str:
    return json.dumps(result, sort_keys=True, ensure_ascii=False)


def _is_plausible_fallback(result: dict[str, Any], previous: dict[str, Any]) -> bool:
    if result["draw_date"] < previous["draw_date"]:
        return False
    result_id = int(result["draw_id"])
    previous_id = int(previous["draw_id"])
    if result_id < previous_id:
        return False
    if result_id == previous_id:
        result_data = {
            key: value
            for key, value in result.items()
            if key not in {"draw_id", "source_url", "source_label", "stale"}
        }
        previous_data = {
            key: value
            for key, value in previous.items()
            if key not in {"draw_id", "source_url", "source_label", "stale"}
        }
        return result_data == previous_data
    return True


def update_snapshot() -> Path:
    previous = _read_previous_snapshot()
    previous_products = {item["label"]: item for item in previous["products"]}
    fetched: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    try:
        parsed = parse_homepage(fetch_homepage())
        fetched.update({item["label"]: item for item in parsed["products"]})
    except Exception as error:
        failures.append(f"official homepage: {error}")

    for game_id, (label, path) in GAME_INFO.items():
        if label in fetched:
            continue
        try:
            page = _fetch_url(f"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/{path}")
            fetched[label] = parse_official_product_page(page, game_id)
        except Exception as error:
            failures.append(f"{label} official page: {error}")

    if len(fetched) < len(GAME_ORDER):
        try:
            third_party = _parse_xoso_third_party(_fetch_url("https://xoso.net.vn/xs-vietlott.html"))
            for game_id, result in third_party.items():
                label = GAME_INFO[game_id][0]
                if label not in fetched:
                    if _is_plausible_fallback(result, previous_products[label]):
                        fetched[label] = result
                    else:
                        failures.append(
                            f"{label}: rejected xoso.net.vn result {result['draw_id']} "
                            f"({result['draw_date']}) because it conflicts with or predates "
                            f"the last verified draw {previous_products[label]['draw_id']} "
                            f"({previous_products[label]['draw_date']})"
                        )
        except Exception as error:
            failures.append(f"xoso.net.vn: {error}")

    products = []
    for game_id in GAME_ORDER:
        label = GAME_INFO[game_id][0]
        result = fetched.get(label)
        if result is None:
            result = dict(previous_products[label])
            result["stale"] = True
            failures.append(f"{label}: retaining last verified draw {result['draw_id']}")
        else:
            result["stale"] = False
            result.setdefault("source_label", "Vietlott")
        products.append(result)

    changed = any(
        _result_content(next_result) != _result_content(previous_products[next_result["label"]])
        for next_result in products
    )
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if changed else previous.get("updated_at")
    payload = {
        "source_url": SOURCE_URL,
        "updated_at": updated_at,
        "products": products,
    }
    OUTPUT.write_text(render_results_script(payload), encoding="utf-8")
    for failure in failures:
        print(f"::warning::{failure}")
    if failures and not any(item.get("stale") for item in products):
        print("All products were fetched and validated; one or more sources required fallback.")
    print(f"Updated latest Vietlott draws in {OUTPUT.relative_to(ROOT)}.")
    return OUTPUT


if __name__ == "__main__":
    output = update_snapshot()
    print(f"Updated latest Vietlott draws in {output.relative_to(ROOT)}.")
