#!/usr/bin/env python3
"""Скачивает фид и ограничивает <stock_quantity> до MAX_STOCK (меньшие значения не меняет)."""
import os, re, sys, urllib.request

MAX_STOCK = int(os.environ.get("MAX_STOCK", "5"))
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
changed = total = 0

def fix(m):
    global changed, total
    total += 1
    n = int(m.group(2))
    if n > MAX_STOCK:
        changed += 1
        n = MAX_STOCK
    return f"{m.group(1)}{n}{m.group(3)}"

new = re.sub(r"(<stock_quantity>\s*)(\d+)(\s*</stock_quantity>)", fix, text)
if total == 0:
    sys.exit("В фиде не найдено <stock_quantity>: файл не записан")
open(OUT, "wb").write(new.encode("utf-8"))
print(f"Товаров: {total}, уменьшено до {MAX_STOCK}: {changed}, без изменений: {total-changed}")
