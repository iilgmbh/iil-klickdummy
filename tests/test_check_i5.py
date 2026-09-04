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
