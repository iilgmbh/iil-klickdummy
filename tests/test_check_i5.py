"""Tests für `klickdummy-i5` (iilgmbh/iil-klickdummy#232, dev-hub#320 Welle 3)
— Laufzeit-Gate gegen fremde Skripte/Stylesheets, Tailwind-Farbklassen und
fehlende `tokens.css` neben `kd-nav.js`.
"""

from __future__ import annotations

import pathlib

import pytest

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


_GENERATED_TOKENS_STYLE_BLOCK = (
    "<style>\n"
    '/* tokens.css \u2014 generiert aus design-hub-Profil "iil-extern" '
    "(schema_version 1) \u00b7 nicht von Hand editieren */\n"
    "/* Generator: iil-klickdummy klickdummy-tokens 1.39.0 */\n"
    ":root {\n"
    "  --kd-primary: #1a3a6c;\n"
    "  --kd-text: #1f2937;\n"
    "}\n"
    "</style>"
)


def _sitemap_html(extra_style: str = "") -> str:
    return (
        "<!DOCTYPE html><html><head>"
        f"{_GENERATED_TOKENS_STYLE_BLOCK}"
        f"{extra_style}"
        "</head><body>Sitemap</body></html>"
    )


def test_should_pass_sitemap_with_embedded_generated_tokens_block(tmp_path):
    """`sitemap/index.html` bettet `tokens.css` roh als ersten <style>-Block
    ein (dev-hub#320 Welle 0, Generator-Kopfzeile erkennbar) — dieser eine
    Block wird ausgeblendet, der Rest der Datei bleibt grün."""
    kd = tmp_path / "klickdummy"
    (kd / "sitemap").mkdir(parents=True)
    (kd / "sitemap" / "index.html").write_text(_sitemap_html(), encoding="utf-8")

    assert check_i5.main([str(kd)]) == 0


def test_should_flag_hand_set_hex_in_own_sitemap_style_block(tmp_path):
    """Eine von Hand in einen EIGENEN <style>-Block der Sitemap gesetzte
    Farbe darf nicht durchrutschen — nur der Generator-Block wird
    ausgeblendet, nicht die ganze Datei; genau 1 Treffer erwartet."""
    kd = tmp_path / "klickdummy"
    (kd / "sitemap").mkdir(parents=True)
    own_style = "<style>.custom{color:#ff0000}</style>"
    (kd / "sitemap" / "index.html").write_text(
        _sitemap_html(extra_style=own_style), encoding="utf-8"
    )

    findings = check_i5.check_hex_colours_file(kd / "sitemap" / "index.html")

    assert len(findings) == 1
    assert "#ff0000" in findings[0][1]


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


# ----------------------------------------------------------------------------
# Regel-2-Ausnahme: token-gemapptes Tailwind (dev-hub#320 Welle 4, #234-Folge)
# ----------------------------------------------------------------------------

_TAILWIND_TOKENS_JS_MINIMAL = (
    "(function(){window.tailwind=window.tailwind||{};"
    "window.tailwind.config={theme:{extend:{colors:{"
    "indigo: 'var(--kd-primary)',"
    "blue: 'var(--kd-primary)'"
    "}}}};})();"
)


def test_should_pass_tailwind_colour_class_when_family_mapped_in_tokens_js(tmp_path):
    kd = tmp_path / "klickdummy"
    (kd / "_shared").mkdir(parents=True)
    (kd / "_shared" / "tailwind-tokens.js").write_text(
        _TAILWIND_TOKENS_JS_MINIMAL, encoding="utf-8"
    )
    (kd / "_shared" / "tailwind.js").write_text("/* vendored */", encoding="utf-8")
    (kd / "screen.html").write_text(
        '<html><head><script src="_shared/tailwind-tokens.js"></script>'
        '<script src="_shared/tailwind.js"></script></head>'
        '<body><div class="bg-indigo-700">hi</div></body></html>',
        encoding="utf-8",
    )
    assert check_i5.main([str(kd)]) == 0


def test_should_fail_with_family_name_when_tailwind_family_not_mapped(tmp_path, capsys):
    kd = tmp_path / "klickdummy"
    (kd / "_shared").mkdir(parents=True)
    (kd / "_shared" / "tailwind-tokens.js").write_text(
        _TAILWIND_TOKENS_JS_MINIMAL, encoding="utf-8"
    )
    (kd / "_shared" / "tailwind.js").write_text("/* vendored */", encoding="utf-8")
    (kd / "screen.html").write_text(
        '<html><head><script src="_shared/tailwind-tokens.js"></script>'
        '<script src="_shared/tailwind.js"></script></head>'
        '<body><div class="bg-emerald-500">hi</div></body></html>',
        encoding="utf-8",
    )
    rc = check_i5.main([str(kd)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "emerald" in out


def test_should_fail_when_tailwind_js_loaded_before_tokens_mapping(tmp_path, capsys):
    kd = tmp_path / "klickdummy"
    (kd / "_shared").mkdir(parents=True)
    (kd / "_shared" / "tailwind-tokens.js").write_text(
        _TAILWIND_TOKENS_JS_MINIMAL, encoding="utf-8"
    )
    (kd / "_shared" / "tailwind.js").write_text("/* vendored */", encoding="utf-8")
    (kd / "screen.html").write_text(
        '<html><head><script src="_shared/tailwind.js"></script>'
        '<script src="_shared/tailwind-tokens.js"></script></head>'
        '<body><div class="bg-indigo-700">hi</div></body></html>',
        encoding="utf-8",
    )
    rc = check_i5.main([str(kd)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "Mapping nicht geladen" in out


def test_should_flag_tailwind_colour_class_as_before_without_mapping_file(tmp_path):
    """Ohne `_shared/tailwind-tokens.js` im Baum bleibt Regel 2 wie bisher —
    jede Tailwind-Farbklasse ein Fehler (kein stiller Freifahrtschein)."""
    kd = tmp_path / "klickdummy"
    kd.mkdir()
    (kd / "screen.html").write_text(
        '<html><body><div class="bg-indigo-700">hi</div></body></html>',
        encoding="utf-8",
    )
    assert check_i5.main([str(kd)]) == 1


def test_should_have_zero_hex_in_bundled_tailwind_tokens_snippet():
    """Das ausgelieferte Snippet selbst darf kein Hex enthalten — nur
    `var(--kd-*)`-Referenzen (Analogie zu `kd-nav.js`)."""
    from importlib.resources import files

    snippet = files("iil_klickdummy") / "snippets" / "_shared" / "tailwind-tokens.js"
    findings = check_i5.check_hex_colours_file(pathlib.Path(str(snippet)))
    text = snippet.read_text(encoding="utf-8")
    assert findings == []
    assert "var(--kd-" in text


# ----------------------------------------------------------------------------
# 3-Shade-Band-Karte (iilgmbh/iil-klickdummy#238, dev-hub#320 Welle-4-
# Folgebefund) — jede der 22 Familien deckt alle 11 Stufen ab, und
# `bg-<f>-100`/`text-<f>-700` derselben Familie zeigen auf verschiedene
# Tokens (Positivkontrolle gegen Ton-in-Ton-Badges).
# ----------------------------------------------------------------------------

_SHADES = (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)


def _evaluate_bundled_tailwind_colors():
    """Führt das ausgelieferte Snippet mit Node aus und liest die
    `window.tailwind.config.theme.extend.colors`-Struktur als JSON zurück
    — kein Nachbau der `shadeMap`-Logik in Python (Drift-Gefahr), sondern
    ein echter Lauf des ausgelieferten Codes."""
    import json
    import shutil
    import subprocess
    from importlib.resources import files

    if shutil.which("node") is None:
        pytest.skip("node nicht verfügbar")

    snippet = files("iil_klickdummy") / "snippets" / "_shared" / "tailwind-tokens.js"
    snippet_text = snippet.read_text(encoding="utf-8")
    script = (
        "var window = globalThis;\n"
        + snippet_text
        + "\nprocess.stdout.write(JSON.stringify("
        "window.tailwind.config.theme.extend.colors));"
    )
    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_should_define_all_eleven_shades_for_every_family():
    colors = _evaluate_bundled_tailwind_colors()
    assert set(colors.keys()) == set(check_i5.TAILWIND_COLOUR_FAMILIES)
    for family, shade_map in colors.items():
        defined = {int(s) for s in shade_map.keys()}
        assert defined == set(_SHADES), f"{family}: {sorted(defined)}"
        for shade, token in shade_map.items():
            assert token, f"{family}-{shade}: leerer Token"
            assert "var(--kd-" in token, f"{family}-{shade}: kein Token: {token!r}"


def test_should_map_light_and_dark_shade_to_different_tokens_per_family():
    """Positivkontrolle gegen Ton-in-Ton: `bg-<f>-100` (hell) und
    `text-<f>-700` (dunkel) derselben Familie müssen verschiedene Tokens
    ergeben — sonst wird ein Status-Badge (Hintergrund + Text) unlesbar."""
    colors = _evaluate_bundled_tailwind_colors()
    for family, shade_map in colors.items():
        light = shade_map["100"]
        dark = shade_map["700"]
        assert light != dark, f"{family}: bg-100 == text-700 ({light!r})"
