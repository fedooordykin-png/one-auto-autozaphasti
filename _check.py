# -*- coding: utf-8 -*-
"""Быстрая проверка сайта в браузере: поиск, цены, загрузка Excel."""
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/"
FAILS = []


def check(name, cond, extra=""):
    print(("OK  " if cond else "FAIL") + " " + name + (" | " + extra if extra else ""))
    if not cond:
        FAILS.append(name)


def rows(page):
    return page.locator("#resultsBody tr").count()


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        r"C:\Users\Фёдор\python\.zzap_profile", channel="msedge",
        headless=True, viewport={"width": 1366, "height": 900})
    page = ctx.new_page() if not ctx.pages else ctx.pages[0]
    page.goto(URL, wait_until="load", timeout=60000)

    check("title", "One Auto" in page.title(), page.title())
    src = page.locator("#sourceInfo").inner_text()
    check("каталог из data.js", "прайс.xlsx" in src and "1637" in src, src)
    check("подсказка до поиска", "Введите артикул" in page.locator("#hint").inner_text())

    # 1. точный артикул с дефисом
    page.fill("#searchInput", "04466-60161")
    page.wait_for_timeout(300)
    n1 = rows(page)
    check("поиск 04466-60161", n1 >= 1, "rows=%d" % n1)
    first_art = page.locator("#resultsBody tr:first-child td:first-child").inner_text()
    check("артикул в ответе", "04466" in first_art, first_art)

    # 2. тот же артикул без дефиса
    page.fill("#searchInput", "0446660161")
    page.wait_for_timeout(300)
    n2 = rows(page)
    check("поиск без дефиса", n2 >= 1, "rows=%d" % n2)

    # 3. частичный
    page.fill("#searchInput", "04466")
    page.wait_for_timeout(300)
    n3 = rows(page)
    check("частичный 04466", n3 >= 3, "rows=%d" % n3)

    # 4. латиница в артикуле
    page.fill("#searchInput", "8118533D31")
    page.wait_for_timeout(300)
    n4 = rows(page)
    check("латиница 8118533D31", n4 >= 1, "rows=%d" % n4)

    # 5. цена с запятой + бейдж наличия
    page.fill("#searchInput", "04466-02430")
    page.wait_for_timeout(300)
    price_txt = page.locator("#resultsBody tr:first-child td.price").inner_text()
    check("цена с запятой", "₽" in price_txt and "," in price_txt, price_txt)
    badge_txt = page.locator("#resultsBody tr:first-child td:last-child").inner_text()
    check("бейдж наличия", badge_txt.strip() in ("в наличии", "нет наличия") or "шт" in badge_txt, badge_txt)

    # 6. ничего не найдено
    page.fill("#searchInput", "ZZZZ-999")
    page.wait_for_timeout(300)
    hint = page.locator("#hint").inner_text()
    check("сообщение не найдено", "ничего не найдено" in hint, hint)

    # 7. фильтр бренда
    page.fill("#searchInput", "")
    page.wait_for_timeout(200)
    brands = page.locator("#brandFilter option").count()
    check(" бренды в фильтре", brands > 5, "options=%d" % brands)

    # 8. загрузка шаблона Excel (пустой шаблон — 0 строк, ожидаем внятную ошибку)
    page.set_input_files("#fileInput", r"C:\Users\Фёдор\python\site\шаблон_прайса.xlsx")
    page.wait_for_timeout(600)
    msg = page.locator("#message").inner_text()
    check("загрузка шаблона обработана", msg != "", msg)

    # 9. скриншот
    page.fill("#searchInput", "04466")
    page.wait_for_timeout(300)
    page.screenshot(path=r"C:\Users\Фёдор\python\site\_check.png", full_page=True)
    print("скриншот: site\\_check.png")

    ctx.close()

    # --- отдельная чистая сессия: цикл загрузки прайс.xlsx ---
    browser = p.chromium.launch(channel="msedge", headless=True)
    page2 = browser.new_page(viewport={"width": 1366, "height": 900})
    page2.goto(URL, wait_until="load", timeout=60000)
    src0 = page2.locator("#sourceInfo").inner_text()
    check("чистый старт: каталог data.js", "прайс.xlsx" in src0, src0)
    check("кнопка сброса скрыта", not page2.locator("#resetBtn").is_visible())

    page2.set_input_files("#fileInput", r"C:\Users\Фёдор\python\прайс.xlsx")
    page2.wait_for_timeout(800)
    src1 = page2.locator("#sourceInfo").inner_text()
    check("прайс.xlsx загружен", "прайс.xlsx (загружен вами)" in src1 and "1637" in src1, src1)
    msg1 = page2.locator("#message").inner_text()
    check("сообщение об успехе", "Загружено 1637" in msg1, msg1)
    check("кнопка сброса видна", page2.locator("#resetBtn").is_visible())

    page2.reload(wait_until="load")
    page2.wait_for_timeout(400)
    src2 = page2.locator("#sourceInfo").inner_text()
    check("после F5 данные из localStorage", "из браузера" in src2, src2)

    page2.click("#resetBtn")
    page2.wait_for_timeout(300)
    src3 = page2.locator("#sourceInfo").inner_text()
    check("сброс к каталогу data.js", "данные каталога" in src3, src3)

    browser.close()
    print()
print()
if FAILS:
    print("ПРОВАЛЫ:", "; ".join(FAILS))
    sys.exit(1)
print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
