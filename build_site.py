# -*- coding: utf-8 -*-
r"""
build_site.py — генерирует шаблон прайса, при отсутствии .xlsx собирает его
из CSV и обновляет data.js для статического сайта.

Запуск:  python site\build_site.py

Шаги:
  1) если нет site\шаблон_прайса.xlsx  — создаётся шаблон (артикул, цена, бренд, количество)
  2) если нет прайс.xlsx               — собирается из прайс зап_цена зап.csv
                                          (фолбэк: прайс зап.csv)
  3) прайс.xlsx                        — читается и переписывается site\data.js

Прайс.xlsx руками не трогаем — это ваш рабочий файл прайса.
"""
import csv
import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
TEMPLATE = SITE / "шаблон_прайса.xlsx"
PRICE_XLSX = ROOT / "прайс.xlsx"
DATA_JS = SITE / "data.js"

SRC_MERGED = ROOT / "прайс зап_цена зап.csv"
SRC_BASE = ROOT / "прайс зап.csv"

HEADERS = ["артикул", "цена", "бренд", "количество"]


def norm_key(article):
    """04466-60161 -> 0446660161: ключ совпадения для поиска."""
    return re.sub(r"[^A-Za-z0-9]", "", str(article)).upper()


def parse_price(value):
    """'585,1' / '1 200,00' / 585.1 -> float | None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().strip('"').replace("\xa0", " ").replace(" ", "")
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_qty(value):
    """'5 шт.' / 5 / '' -> int | None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else None


def brand_from_note(note):
    """'производитель: DAIHATSU' -> 'DAIHATSU'."""
    if not note:
        return ""
    m = re.search(r"производитель\s*:\s*(.+)", str(note), re.IGNORECASE)
    return m.group(1).strip() if m else ""


def ensure_template():
    if TEMPLATE.exists():
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "прайс"
    ws.append(HEADERS)
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 12
    wb.save(TEMPLATE)
    print(f"создан шаблон: {TEMPLATE}")


def rows_from_merged():
    """прайс зап_цена зап.csv (utf-8-sig, ';') -> [(арт, цена, бренд, кол-во)]"""
    out = []
    with open(SRC_MERGED, encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)  # заголовок
        for rec in reader:
            art = (rec[0] if rec else "").strip().strip('"')
            if not art:
                continue
            fprice = parse_price(rec[1] if len(rec) > 1 else "")
            note = (rec[3] if len(rec) > 3 else "").strip()
            out.append((art, fprice, brand_from_note(note), None))
    return out


def rows_from_base():
    """прайс зап.csv (cp1251, ';', 2 строки шапки) -> [(арт, цена, бренд, кол-во)]"""
    out = []
    with open(SRC_BASE, encoding="cp1251", errors="replace", newline="") as f:
        for i, rec in enumerate(csv.reader(f, delimiter=";")):
            if i < 2:
                continue
            art = (rec[0] if rec else "").strip().strip('"')
            if not art or re.search(r"[^\x20-\x7e]", art):
                continue
            price = parse_price(rec[1] if len(rec) > 1 else "")
            out.append((art, price, "", None))
    return out


def ensure_price_xlsx():
    if PRICE_XLSX.exists():
        print(f"есть: {PRICE_XLSX.name} (не трогаю)")
        return
    if SRC_MERGED.exists():
        rows = rows_from_merged()
    elif SRC_BASE.exists():
        rows = rows_from_base()
    else:
        print("нет источника CSV — создаю пустой шаблон прайс.xlsx", file=sys.stderr)
        rows = []
    wb = Workbook()
    ws = wb.active
    ws.title = "прайс"
    ws.append(HEADERS)
    for art, price, brand, qty in rows:
        ws.append([art, price, brand, qty])
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 12
    wb.save(PRICE_XLSX)
    print(f"собран {PRICE_XLSX.name}: {len(rows)} строк")


def load_price_rows():
    """прайс.xlsx -> [(арт, цена|None, бренд, кол-во|None)]"""
    wb = load_workbook(PRICE_XLSX, read_only=True, data_only=True)
    ws = wb.active
    out = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # заголовок
        art = str(row[0]).strip() if row and row[0] is not None else ""
        if not art:
            continue
        out.append((
            art,
            parse_price(row[1] if len(row) > 1 else None),
            str(row[2]).strip() if len(row) > 2 and row[2] is not None else "",
            parse_qty(row[3] if len(row) > 3 else None),
        ))
    wb.close()
    return out


def write_data_js():
    rows = load_price_rows()
    parts = [
        {
            "art": art,
            "key": norm_key(art),
            "price": price,
            "brand": brand,
            "qty": qty,
        }
        for art, price, brand, qty in rows
    ]
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    DATA_JS.write_text(
        "// Сгенерировано build_site.py — руками не редактировать\n"
        f"window.PARTS = {payload};\n",
        encoding="utf-8",
    )
    print(f"записан {DATA_JS}: {len(parts)} записей")


def main():
    ensure_template()
    ensure_price_xlsx()
    write_data_js()
    print("ГОТОВО")


if __name__ == "__main__":
    main()
