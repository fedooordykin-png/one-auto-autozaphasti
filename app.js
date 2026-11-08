/* One Auto — каталог автозапчастей: поиск по артикулу, загрузка Excel в браузере. */
(function () {
  "use strict";

  var LS_KEY = "oneauto_parts_v1";

  var state = {
    parts: [],       // {art, key, price, brand, qty}
    brands: [],
    source: "",
    query: "",
    brand: ""
  };

  var $ = function (id) { return document.getElementById(id); };
  var searchInput = $("searchInput");
  var brandFilter = $("brandFilter");
  var fileInput = $("fileInput");
  var resultsBody = $("resultsBody");
  var hint = $("hint");
  var counter = $("counter");
  var sourceInfo = $("sourceInfo");
  var message = $("message");
  var resetBtn = $("resetBtn");

  /* ---------- утилиты ---------- */

  function normKey(s) {
    return String(s == null ? "" : s).replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  }

  function parsePrice(v) {
    if (v == null || v === "") return null;
    if (typeof v === "number") return isFinite(v) ? v : null;
    var s = String(v).replace(/[\s\u00a0\u202f]/g, "").replace(",", ".");
    var n = parseFloat(s);
    return isFinite(n) ? n : null;
  }

  function parseQty(v) {
    if (v == null || v === "") return null;
    if (typeof v === "number") return Math.trunc(v);
    var m = String(v).match(/\d+/);
    return m ? parseInt(m[0], 10) : null;
  }

  function fmtPrice(p) {
    if (p == null) return "—";
    var s = p.toFixed(2).replace(/\.?0+$/, "");
    return s.replace(".", ",") + " ₽";
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function highlight(text, query) {
    var safe = esc(text);
    if (!query) return safe;
    var idx = String(text).toUpperCase().indexOf(query.toUpperCase());
    if (idx < 0) return safe;
    return esc(String(text).slice(0, idx)) +
      "<mark>" + esc(String(text).slice(idx, idx + query.length)) + "</mark>" +
      esc(String(text).slice(idx + query.length));
  }

  function showMessage(text, ok) {
    if (!text) { message.hidden = true; return; }
    message.textContent = text;
    message.classList.toggle("ok", !!ok);
    message.hidden = false;
  }

  /* ---------- состояние каталога ---------- */

  function setParts(parts, source) {
    state.parts = parts;
    state.source = source;
    state.brands = [];
    parts.forEach(function (p) {
      if (p.brand && state.brands.indexOf(p.brand) < 0) state.brands.push(p.brand);
    });
    state.brands.sort(function (a, b) { return a.localeCompare(b, "ru"); });

    var prev = brandFilter.value;
    brandFilter.innerHTML = '<option value="">Все бренды</option>';
    state.brands.forEach(function (b) {
      var opt = document.createElement("option");
      opt.value = b;
      opt.textContent = b;
      brandFilter.appendChild(opt);
    });
    brandFilter.value = state.brands.indexOf(prev) >= 0 ? prev : "";
    state.brand = brandFilter.value;

    sourceInfo.textContent = source + " · в каталоге " + parts.length + " позиций";
    var bundled = window.PARTS && window.PARTS.length ? window.PARTS : null;
    resetBtn.hidden = !(bundled && parts !== bundled);
    render();
  }

  function saveToLS(parts, name) {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify({
        name: name,
        ts: Date.now(),
        parts: parts.map(function (p) {
          return [p.art, p.price, p.brand, p.qty];
        })
      }));
    } catch (e) { /* переполнение localStorage — не критично */ }
  }

  function loadFromLS() {
    try {
      var raw = localStorage.getItem(LS_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !Array.isArray(data.parts)) return null;
      var parts = data.parts.map(function (r) {
        return {
          art: String(r[0] == null ? "" : r[0]),
          key: normKey(r[0]),
          price: r[1] == null ? null : r[1],
          brand: r[2] == null ? "" : String(r[2]),
          qty: r[3] == null ? null : r[3]
        };
      }).filter(function (p) { return p.art; });
      if (!parts.length) return null;
      return { parts: parts, name: data.name || "файл" };
    } catch (e) { return null; }
  }

  /* ---------- поиск и отрисовка ---------- */

  function filtered() {
    var q = normKey(state.query);
    var out = [];
    for (var i = 0; i < state.parts.length; i++) {
      var p = state.parts[i];
      if (q && p.key.indexOf(q) < 0) continue;
      if (state.brand && p.brand !== state.brand) continue;
      if (!q && !state.brand) continue; // пустой ввод — не перечисляем всё подряд
      out.push(p);
    }
    return out;
  }

  function badge(qty) {
    if (qty != null && qty > 0) {
      return '<span class="badge in">в наличии, ' + qty + ' шт</span>';
    }
    return '<span class="badge out">нет наличия</span>';
  }

  function render() {
    var rows = filtered();
    var q = state.query.trim();

    resultsBody.innerHTML = "";
    if (!state.parts.length) {
      hint.textContent = "Каталог пуст. Нажмите «Загрузить Excel» и выберите файл прайса.";
      hint.hidden = false;
      counter.textContent = "";
      return;
    }
    if (!rows.length) {
      hint.textContent = q
        ? "По артикулу «" + q + "» ничего не найдено. Проверьте номер или измените запрос."
        : "Введите артикул или выберите бренд — покажем совпадения.";
      hint.hidden = false;
      counter.textContent = "найдено 0";
      return;
    }

    hint.hidden = true;
    counter.textContent = "найдено " + rows.length;

    var html = [];
    var limit = Math.min(rows.length, 500);
    for (var i = 0; i < limit; i++) {
      var p = rows[i];
      html.push(
        "<tr>" +
        '<td class="art">' + highlight(p.art, q) + "</td>" +
        '<td class="brand-cell">' + esc(p.brand || "—") + "</td>" +
        '<td class="price' + (p.price == null ? " none" : "") + '">' + fmtPrice(p.price) + "</td>" +
        "<td>" + badge(p.qty) + "</td>" +
        "</tr>"
      );
    }
    resultsBody.innerHTML = html.join("");
    if (rows.length > limit) {
      hint.textContent = "Показаны первые " + limit + " из " + rows.length + " — уточните артикул.";
      hint.hidden = false;
    }
  }

  /* ---------- загрузка Excel ---------- */

  // aliases: [поле, варианты заголовков]
  var COLUMN_ALIASES = {
    art: ["артикул", "article", "partnumber", "part_number", "номер", "номенклатура"],
    price: ["цена", "цена (файл)", "цена зап", "price", "стоимость", "розница"],
    brand: ["бренд", "brand", "производитель", "manufacturer"],
    qty: ["количество", "кол-во", "колво", "qty", "quantity", "остаток", "наличие"]
  };

  function findColumns(headerRow) {
    var cols = {};
    headerRow.forEach(function (cell, i) {
      var h = String(cell == null ? "" : cell).toLowerCase().replace(/["']/g, "").trim();
      Object.keys(COLUMN_ALIASES).forEach(function (field) {
        if (cols[field] != null) return;
        if (COLUMN_ALIASES[field].indexOf(h) >= 0) cols[field] = i;
      });
    });
    return cols;
  }

  function handleFile(file) {
    if (typeof XLSX === "undefined") {
      showMessage("Библиотека чтения Excel не загрузилась (нет интернета?). Обновите страницу.");
      return;
    }
    var reader = new FileReader();
    reader.onerror = function () { showMessage("Не удалось прочитать файл."); };
    reader.onload = function (e) {
      var parts;
      try {
        var wb = XLSX.read(new Uint8Array(e.target.result), { type: "array" });
        var sheet = wb.Sheets[wb.SheetNames[0]];
        var rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: true, defval: "" });
        if (!rows.length) { showMessage("Файл пуст."); return; }

        var cols = findColumns(rows[0]);
        if (cols.art == null) {
          showMessage("В файле нет колонки «артикул». Нужны заголовки: артикул, цена, бренд, количество.");
          return;
        }
        var warnings = [];
        if (cols.price == null) warnings.push("цена");
        if (cols.brand == null) warnings.push("бренд");
        if (cols.qty == null) warnings.push("количество");

        parts = [];
        for (var r = 1; r < rows.length; r++) {
          var row = rows[r];
          var art = String(row[cols.art] == null ? "" : row[cols.art]).trim().replace(/^"|"$/g, "");
          if (!art) continue;
          parts.push({
            art: art,
            key: normKey(art),
            price: cols.price != null ? parsePrice(row[cols.price]) : null,
            brand: cols.brand != null ? String(row[cols.brand] == null ? "" : row[cols.brand]).trim() : "",
            qty: cols.qty != null ? parseQty(row[cols.qty]) : null
          });
        }
        if (!parts.length) { showMessage("В файле нет ни одной строки с артикулом."); return; }

        setParts(parts, "файл: " + file.name + " (загружен вами)");
        saveToLS(parts, file.name);
        searchInput.value = "";
        state.query = "";
        brandFilter.value = "";
        state.brand = "";
        render();
        showMessage(
          "Загружено " + parts.length + " позиций из «" + file.name + "»." +
          (warnings.length ? " Не найдены колонки: " + warnings.join(", ") + " — они пустуют." : ""),
          true
        );
      } catch (err) {
        showMessage("Не удалось разобрать файл: " + err.message);
      }
    };
    reader.readAsArrayBuffer(file);
  }

  /* ---------- события ---------- */

  var debounceTimer = null;
  searchInput.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      state.query = searchInput.value;
      render();
    }, 80);
  });

  brandFilter.addEventListener("change", function () {
    state.brand = brandFilter.value;
    render();
  });

  fileInput.addEventListener("change", function () {
    if (fileInput.files && fileInput.files[0]) handleFile(fileInput.files[0]);
    fileInput.value = "";
  });

  resetBtn.addEventListener("click", function () {
    try { localStorage.removeItem(LS_KEY); } catch (e) { /* пусто */ }
    if (window.PARTS && window.PARTS.length) {
      setParts(window.PARTS, "данные каталога (прайс.xlsx)");
      showMessage("Возвращён каталог из прайс.xlsx.");
    }
  });

  /* ---------- старт ---------- */

  var saved = loadFromLS();
  if (saved) {
    // свой загруженный прайс переживает перезагрузку страницы
    setParts(saved.parts, "последний файл: " + saved.name + " (из браузера)");
  } else if (window.PARTS && window.PARTS.length) {
    setParts(window.PARTS, "данные каталога (прайс.xlsx)");
  } else {
    sourceInfo.textContent = "Данные каталога не загружены — нажмите «Загрузить Excel»";
    render();
  }
})();
