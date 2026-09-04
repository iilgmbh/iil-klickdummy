"""Tests für `klickdummy-i5` (iilgmbh/iil-klickdummy#232, dev-hub#320 Welle 3)
— Laufzeit-Gate gegen fremde Skripte/Stylesheets, Tailwind-Farbklassen und
fehlende `tokens.css` neben `kd-nav.js`.
"""

from __future__ import annotations

from iil_klickdummy import check_i5


def test_should_detect_cdn_script_tag(tmp_path):
    kd = tmp_path / "klickdummy"
    kd.mkdir()
    (kd / "screen.html").write_text(
        '<html><head><script src="https://cdn.tailwindcss.com"></script>'
        "</head><body>ok</body></html>",
        encoding="utf-8",
    )
    assert check_i5.main([str(kd)]) == 1


def test_should_detect_cdn_link_tag(tmp_path):
    kd = tmp_path / "klickdummy"
    kd.mkdir()
    (kd / "screen.html").write_text(
        '<html><head><link href="https://unpkg.com/lucide/style.css"></head>'
        "<body>ok</body></html>",
        encoding="utf-8",
    )
    assert check_i5.main([str(kd)]) == 1


def test_should_detect_tailwind_colour_class(tmp_path):
    kd = tmp_path / "klickdummy"
    kd.mkdir()
    (kd / "screen.html").write_text(
        '<html><body><div class="text-blue-600">hi</div></body></html>',
        encoding="utf-8",
    )
    rc = check_i5.main([str(kd)])
    assert rc == 1


def test_should_pass_clean_directory_including_sitemap_subfolder(tmp_path):
    kd = tmp_path / "klickdummy"
    (kd / "sitemap").mkdir(parents=True)
    (kd / "screen.html").write_text(
        '<html><body><div class="text-kd-primary" style="color:var(--kd-primary)">'
        "hi</div></body></html>",
        encoding="utf-8",
    )
    (kd / "sitemap" / "index.html").write_text(
        "<html><body>Sitemap</body></html>", encoding="utf-8"
    )
    assert check_i5.main([str(kd)]) == 0


def test_should_ignore_dist_and_detect_missing_tokens_css_next_to_kd_nav(tmp_path):
    kd = tmp_path / "klickdummy"
    (kd / "dist").mkdir(parents=True)
    (kd / "dist" / "screen.html").write_text(
        '<html><head><script src="https://evil.example/x.js"></script></head>'
        "<body>build output, muss ignoriert werden</body></html>",
        encoding="utf-8",
    )
    (kd / "_shared").mkdir()
    (kd / "_shared" / "kd-nav.js").write_text("// kd-nav.js", encoding="utf-8")
    # bewusst KEINE tokens.css daneben -> Regel (3) muss greifen
    (kd / "screen.html").write_text(
        "<html><body>clean screen</body></html>", encoding="utf-8"
    )
    rc = check_i5.main([str(kd)])
    assert rc == 1

    # Positivkontrolle: legt man tokens.css dazu, wird derselbe Baum grün.
    (kd / "_shared" / "tokens.css").write_text(":root {}", encoding="utf-8")
    assert check_i5.main([str(kd)]) == 0


def test_should_detect_hex_colour_in_css_and_js(tmp_path):
    """Regel (4): literale Hex-Farbwerte außerhalb der Token-Dateien in
    *.css und *.js sind ein Fehler — drei- UND sechsstellig."""
    kd = tmp_path / "klickdummy"
    kd.mkdir()
    (kd / "screen.css").write_text(
        ".x{color:#1a3a6c}\n.y{color:#abc}\n", encoding="utf-8"
    )
    (kd / "shell.js").write_text("const c = '#a1b2c3';\n", encoding="utf-8")

    rc = check_i5.main([str(kd)])

    assert rc == 1
    findings_css = check_i5.check_hex_colours_file(kd / "screen.css")
    findings_js = check_i5.check_hex_colours_file(kd / "shell.js")
    assert len(findings_css) == 2
    assert len(findings_js) == 1


def test_should_exempt_tokens_and_semantic_css_from_hex_rule(tmp_path):
    """`_shared/tokens.css` und `_shared/semantic.css` (bzw. `assets/…`) sind
    die Quelle der Hex-Werte, kein Verstoß — Baum bleibt grün."""
    kd = tmp_path / "klickdummy"
    (kd / "_shared").mkdir(parents=True)
    (kd / "_shared" / "tokens.css").write_text(
        ":root{--kd-primary:#1a3a6c}", encoding="utf-8"
    )
    (kd / "_shared" / "semantic.css").write_text(".btn{color:#abc}", encoding="utf-8")
    (kd / "assets").mkdir()
    (kd / "assets" / "tokens.css").write_text(
        ":root{--kd-primary:#1a3a6c}", encoding="utf-8"
    )
    (kd / "assets" / "semantic.css").write_text(".btn{color:#abc}", encoding="utf-8")

    assert check_i5.main([str(kd)]) == 0


def test_should_exempt_sitemap_index_html_from_hex_rule(tmp_path):
    """`sitemap/index.html` bettet `tokens.css` roh als ersten <style>-Block
    ein (dev-hub#320 Welle 0) — dieselbe Tokens-Quelle wie tokens.css, kein
    Verstoß."""
    kd = tmp_path / "klickdummy"
    (kd / "sitemap").mkdir(parents=True)
    (kd / "sitemap" / "index.html").write_text(
        "<style>:root{--kd-primary:#1a3a6c}</style><body>Sitemap</body>",
        encoding="utf-8",
    )

    assert check_i5.main([str(kd)]) == 0


def test_should_not_flag_issue_reference_or_css_anchor_as_hex_colour(tmp_path):
    """Negativkontrollen: `#320`/`#232` (Issue-Refs, rein numerisch) und
    `#fb-fab` (CSS-Anker, kein zusammenhängender Hex-Lauf) sind keine
    Hex-Farbwerte — Regel (4) darf hier nicht anschlagen."""
    kd = tmp_path / "klickdummy"
    kd.mkdir()
    (kd / "screen.html").write_text(
        '<!-- siehe Issue #320 und #232 -->\n<a href="#fb-fab">Fabrik</a>\n',
        encoding="utf-8",
    )

    assert check_i5.main([str(kd)]) == 0


def test_should_ignore_hex_colours_under_dist_and_archive(tmp_path):
    """`dist/`/`_archiv/`/`archive/` sind Build-Output/Altstand — Regel (4)
    greift dort nicht, analog zu Regel (1)-(3)."""
    kd = tmp_path / "klickdummy"
    (kd / "dist").mkdir(parents=True)
    (kd / "dist" / "bundle.css").write_text(".x{color:#1a3a6c}", encoding="utf-8")
    (kd / "_archiv").mkdir()
    (kd / "_archiv" / "old.js").write_text("const c='#abc';", encoding="utf-8")

    assert check_i5.main([str(kd)]) == 0
