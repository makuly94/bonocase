#!/usr/bin/env python3
"""Скачивает фид и:
1) ограничивает <stock_quantity> до MAX_STOCK (меньшие значения не меняет);
2) если задан MIN_STOCK: товары с остатком МЕНЬШЕ MIN_STOCK скрывает
   (available="false" и stock_quantity=0). Пример: MIN_STOCK=4 скроет товары с остатком 1, 2, 3.
   MIN_STOCK=0 (по умолчанию) ничего не скрывает."""
import os, re, sys, urllib.request

MAX_STOCK = int(os.environ.get("MAX_STOCK", "5"))
MIN_STOCK = int(os.environ.get("MIN_STOCK", "0"))
# Как назвать тег с остатком в итоговом фиде. По умолчанию как в исходнике (stock_quantity).
# Для замены задайте STOCK_TAG=quantity_in_stock
STOCK_TAG = os.environ.get("STOCK_TAG", "stock_quantity").strip() or "stock_quantity"
SRC = os.environ.get("FEED_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
OUT = os.environ.get("OUT_FILE", "feed.xml")
if not SRC:
    sys.exit("Укажи ссылку на фид: переменная FEED_URL или первый аргумент")

if SRC.startswith("http"):
    req = urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=120).read()
else:
    raw = open(SRC, "rb").read()

text = raw.decode("utf-8")  # BOM сохраняется как есть
stats = {"total": 0, "capped": 0, "hidden": 0, "renamed": 0, "tag_skipped": 0}

STOCK_RE = re.compile(r"(<stock_quantity>\s*)(\d+)(\s*</stock_quantity>)")

def fix_offer(m):
    attrs, body = m.group(1), m.group(2)
    q = STOCK_RE.search(body)
    if not q:
        return m.group(0)                      # у товара нет остатка — не трогаем
    stats["total"] += 1
    n = int(q.group(2))
    new_n = n
    if MIN_STOCK and n < MIN_STOCK:            # мало на складе: скрываем
        new_n = 0
        if n > 0:
            stats["hidden"] += 1
        if re.search(r'\bavailable="\w+"', attrs):
            attrs = re.sub(r'\bavailable="\w+"', 'available="false"', attrs)
        else:
            attrs += ' available="false"'
    elif n > MAX_STOCK:                        # много на складе: показываем не больше MAX_STOCK
        new_n = MAX_STOCK
        stats["capped"] += 1
    pre, post = q.group(1), q.group(3)
    if STOCK_TAG != "stock_quantity":
        if "<" + STOCK_TAG + ">" in body:      # такой тег уже есть — не создаём дубль
            stats["tag_skipped"] += 1
        else:
            pre = pre.replace("stock_quantity", STOCK_TAG)
            post = post.replace("stock_quantity", STOCK_TAG)
            stats["renamed"] += 1
    body = body[:q.start()] + pre + str(new_n) + post + body[q.end():]
    return "<offer" + attrs + ">" + body + "</offer>"

new = re.sub(r"<offer\b([^>]*)>(.*?)</offer>", fix_offer, text, flags=re.S)
if stats["total"] == 0:
    sys.exit("В фиде не найдено <stock_quantity>: файл не записан")
open(OUT, "wb").write(new.encode("utf-8"))
print(f"Товаров: {stats['total']}, уменьшено до {MAX_STOCK}: {stats['capped']}, "
      f"скрыто (остаток меньше {MIN_STOCK}): {stats['hidden']}, "
      f"без изменений: {stats['total'] - stats['capped'] - stats['hidden']}"
      + (f"; тег переименован в <{STOCK_TAG}>: {stats['renamed']}" if STOCK_TAG != "stock_quantity" else "")
      + (f" (пропущено, тег уже был: {stats['tag_skipped']})" if stats["tag_skipped"] else ""))
