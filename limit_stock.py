#!/usr/bin/env python3
"""Подготавливает фид для Rozetka: скрывает точный остаток и меняет имя тега."""

import os
import re
import sys
import urllib.request


MAX_STOCK = 5
MIN_STOCK = 5
STOCK_TAG = "quantity_in_stock"

SRC = os.environ.get("FEED_URL") or (
    sys.argv[1] if len(sys.argv) > 1 else None
)
OUT = os.environ.get("OUT_FILE", "feed.xml")

if not SRC:
    sys.exit("Не задан FEED_URL и не передана ссылка на фид аргументом")


if SRC.startswith(("http://", "https://")):
    request = urllib.request.Request(
        SRC,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
else:
    with open(SRC, "rb") as source_file:
        raw = source_file.read()


text = raw.decode("utf-8-sig")

# Ищем остаток внутри каждого offer.
offer_re = re.compile(r"(<offer\b[^>]*>)(.*?)(</offer>)", re.DOTALL)
stock_re = re.compile(
    r"<stock_quantity>(\s*)(\d+)(\s*)</stock_quantity>"
)

stats = {"processed": 0, "available": 0, "hidden": 0}


def update_offer(match):
    opening, body, closing = match.groups()
    stock = stock_re.search(body)

    # Если у товара нет числового stock_quantity, оставляем его без изменений.
    if not stock:
        return match.group(0)

    real_stock = int(stock.group(2))
    available = real_stock >= MIN_STOCK
    displayed_stock = MAX_STOCK if available else 0

    replacement = (
        f"<{STOCK_TAG}>{stock.group(1)}"
        f"{displayed_stock}{stock.group(3)}</{STOCK_TAG}>"
    )
    body = body[:stock.start()] + replacement + body[stock.end():]

    # Для товаров ниже порога устанавливаем available="false".
    if not available:
        if re.search(r'\bavailable="[^"]*"', opening):
            opening = re.sub(
                r'\bavailable="[^"]*"',
                'available="false"',
                opening,
            )
        else:
            opening = opening[:-1] + ' available="false">'

        stats["hidden"] += 1
    else:
        stats["available"] += 1

    stats["processed"] += 1
    return opening + body + closing


result = offer_re.sub(update_offer, text)

if stats["processed"] == 0:
    sys.exit(
        "Не найдено ни одного <stock_quantity> внутри <offer>. "
        "Файл не записан."
    )

with open(OUT, "w", encoding="utf-8") as output_file:
    output_file.write(result)

print(
    f"Обработано товаров: {stats['processed']}; "
    f"остаток 5 в фиде: {stats['available']}; "
    f"помечено как недоступные: {stats['hidden']}; "
    f"файл: {OUT}"
)
