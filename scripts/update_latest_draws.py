#!/usr/bin/env python3
"""Refresh Drawlog's public latest-draw snapshot from Vietlott's homepage."""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "latest-results.js"
SOURCE_URL = "https://vietlott.vn/"
MAX_RESPONSE_BYTES = 2_000_000
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
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
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
            if self.card is None and "box_kqtt" in classes:
                self.card = {"alt": "", "heading": "", "text_parts": [], "balls": [], "prizes": []}
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
                elif "large" in classes and self.cell is not None:
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


def fetch_homepage() -> str:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Drawlog/1.0 (+https://github.com/tpc-pascal/drawlog)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Vietlott returned HTTP {response.status}.")
        html = response.read(MAX_RESPONSE_BYTES + 1)
    if len(html) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"Vietlott homepage exceeded {MAX_RESPONSE_BYTES} bytes.")
    return html.decode("utf-8")


def update_snapshot() -> Path:
    results = parse_homepage(fetch_homepage())
    OUTPUT.write_text(render_results_script(results), encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    output = update_snapshot()
    print(f"Updated latest Vietlott draws in {output.relative_to(ROOT)}.")
