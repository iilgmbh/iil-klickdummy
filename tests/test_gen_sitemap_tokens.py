"""klickdummy-gen-sitemap — Tokens statt CDN (dev-hub#320 Welle 0).

Deckt: Sitemap laedt kein fremdes Skript/Stylesheet mehr (CDN-Guard), die drei
Tokens-Quellen (`--tokens-css`, `--profile`, IIL-Fallback via `--design-hub`)
und dass der Generator ohne alle drei Optionen und ohne design-hub sauber mit
Exit 2 abbricht statt eine Sitemap ohne jede Farbe zu schreiben.

Positivkontrolle fuer den fehlenden Laufzeit-Check (siehe Bericht): es gibt in
diesem Paket (I1-I4, klickdummy-sitemap-drift) noch KEINEN Gate, der ein
`<script src="https://...">`/`<link ... href="https://...">` in der
generierten Sitemap automatisch ablehnt — dieser Test ist der einzige
Wächter dafür, bis ein I-Check das übernimmt.
"""

from __future__ import annotations

import pathlib
import re

import yaml


def _write_spec(kd_root: pathlib.Path, name: str, spec: dict) -> None:
    d = kd_root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "screens-spec.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False), encoding="utf-8"
    )
    (d / "index.html").write_text("<html></html>", encoding="utf-8")


def _root_spec(spec_id: str, title: str) -> dict:
    return {
        "spec_id": spec_id,
        "title": title,
        "spec_role": "root",
        "class": "mock",
        "off_ramp": {"status_overall": "Phase A"},
        "screens": [{"id": "s1", "off_ramp_status": "static"}],
    }


_MINIMAL_TOKENS_CSS = (
    ":root {\n"
    '  --kd-font-primary: "Inter", sans-serif;\n'
    "  --kd-primary: #52534D;\n"
    "  --kd-text: #1F2937;\n"
    "  --kd-bg-light: #F5F5F4;\n"
    "  --kd-border: #E0DFD9;\n"
    "}\n"
)


def _minimal_profile() -> dict:
    return {
        "name": "acme-profile",
        "schema_version": 1,
        "fonts": {"primary": "Inter", "fallbacks": ["sans-serif"]},
        "colours": {
            "primary": "#52534D",
            "text": "#1F2937",
            "bg_light": "#F5F5F4",
            "border": "#E0DFD9",
        },
    }


_URL_IN_SRC_HREF_RE = re.compile(
    r'<(?:script|link)\b[^>]*\b(?:src|href)="https?://', re.IGNORECASE
)
_TAILWIND_COLOR_CLASS_RE = re.compile(
    r"\b(?:text|bg|border)-(?:orange|amber|gray|zinc|green|red)-\d{2,3}\b"
)


def test_should_not_reference_any_external_script_or_stylesheet(tmp_path):
    """Kernanforderung dev-hub#320 Welle 0: kein `<script src="https://...">`
    und kein `<link ... href="https://...">` mehr in der Sitemap — bisher
    Tailwind-CDN + unpkg/lucide."""
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))

    gen_sitemap.generate(
        tmp_path,
        adr_local="acme:ADR-001",
        repo_name="acme",
        tokens_css=_MINIMAL_TOKENS_CSS,
    )
    html = (kd_root / "sitemap" / "index.html").read_text(encoding="utf-8")

    assert not _URL_IN_SRC_HREF_RE.search(html), "externes Skript/Stylesheet gefunden"
    assert "cdn.tailwindcss.com" not in html
    assert "unpkg.com" not in html


def test_should_not_emit_tailwind_color_utility_classes(tmp_path):
    """Farben kommen ausschließlich aus `--kd-*`-Tokens, keine
    Tailwind-Utility-Klassen mehr (text-orange-600 etc.)."""
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))
    _write_spec(
        kd_root,
        "lonely",
        {**_root_spec("acme:klickdummy-spec-lonely", "Lonely"), "spec_role": "branch"},
    )

    gen_sitemap.generate(
        tmp_path,
        adr_local="acme:ADR-001",
        repo_name="acme",
        tokens_css=_MINIMAL_TOKENS_CSS,
    )
    html = (kd_root / "sitemap" / "index.html").read_text(encoding="utf-8")

    assert not _TAILWIND_COLOR_CLASS_RE.search(html)
    assert "var(--kd-primary)" in html


def test_should_embed_tokens_css_file_verbatim_as_first_style_block(tmp_path):
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))
    tokens_css_path = tmp_path / "tokens.css"
    tokens_css_path.write_text(_MINIMAL_TOKENS_CSS, encoding="utf-8")

    rc = gen_sitemap.main(
        [str(tmp_path), "acme:ADR-001", "acme", "--tokens-css", str(tokens_css_path)]
    )
    html = (kd_root / "sitemap" / "index.html").read_text(encoding="utf-8")

    assert rc == 0
    assert "--kd-primary: #52534D;" in html
    # Tokens-Block steht vor dem Layout-Block (erster <style>-Tag).
    assert html.index("--kd-primary: #52534D;") < html.index(".kd-topbar")


def test_should_generate_tokens_from_profile_and_expose_kd_primary(tmp_path):
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        yaml.safe_dump(_minimal_profile(), sort_keys=False), encoding="utf-8"
    )

    rc = gen_sitemap.main(
        [str(tmp_path), "acme:ADR-001", "acme", "--profile", str(profile_path)]
    )
    html = (kd_root / "sitemap" / "index.html").read_text(encoding="utf-8")

    assert rc == 0
    assert "--kd-primary: #52534D;" in html


def test_should_exit_2_with_message_when_iil_fallback_has_no_design_hub(
    tmp_path, capsys
):
    """Ohne --tokens-css/--profile und ohne design-hub-Checkout unter
    --design-hub: Exit 2, kein Artefakt geschrieben."""
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))
    missing_design_hub = tmp_path / "no-such-design-hub"

    rc = gen_sitemap.main(
        [str(tmp_path), "acme:ADR-001", "acme", "--design-hub", str(missing_design_hub)]
    )

    assert rc == 2
    err = capsys.readouterr().err
    assert "design-hub" in err
    assert "--tokens-css oder --profile" in err
    assert not (kd_root / "sitemap" / "index.html").exists()


def test_should_keep_two_runs_byte_identical_with_tokens(tmp_path):
    from iil_klickdummy import gen_sitemap

    kd_root = tmp_path / "klickdummy"
    _write_spec(kd_root, "hub", _root_spec("acme:klickdummy-spec-hub", "Hub"))

    gen_sitemap.generate(
        tmp_path,
        adr_local="acme:ADR-001",
        repo_name="acme",
        tokens_css=_MINIMAL_TOKENS_CSS,
    )
    first = (kd_root / "sitemap" / "index.html").read_text(encoding="utf-8")

    gen_sitemap.generate(
        tmp_path,
        adr_local="acme:ADR-001",
        repo_name="acme",
        tokens_css=_MINIMAL_TOKENS_CSS,
    )
    second = (kd_root / "sitemap" / "index.html").read_text(encoding="utf-8")

    assert first == second
