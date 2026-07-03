# Cookbook — KD-Co-Creation-Loop (Zwei-Kanal-Input)

> KONZ-iil-klickdummy-008. Wie Nicht-Entwickler-Input in einen Klickdummy einfließt,
> ohne die Spec als Source-of-Record (SoR) aufzugeben.

## Prinzip: eine Wahrheit, zwei Eingänge

```
Mermaid-View  ──(Struktur)──┐
                            ├──▶  GitHub  ──▶  Kuratierung  ──▶  Spec (SoR)  ──▶  KD re-gen
Feedback-Widget ─(Inhalt)──┘
```

Die **Spec** (`screens-spec.yaml`) ist und bleibt die einzige Wahrheit. Mermaid und
Widget sind **abgeleitete Eingangskanäle** — kein zweiter SoR. Austauschmedium ist
**GitHub** (rendert Mermaid nativ, `gh` liest zurück), **nicht** iil.pet (dort ist der
Read-back durch Cloudflare Access blockiert).

## Kanal 1 — Mermaid (Struktur: Screen-Flow)

Für Reihenfolge, Übergänge und Rücksprünge des Screen-Flows.

**Dateien im KD-Verzeichnis:**
- `_flow.input.mmd` — der rohe Flow (Editier-Quelle).
- `_flow.view.md` — die von GitHub gerenderte, editierbare Sicht (enthält einen
  ` ```mermaid `-Block). Wird aus der Spec regeneriert, nie von Hand als Wahrheit gepflegt.

**Ablauf:**
1. Mensch öffnet `_flow.view.md` auf GitHub, klickt ✏️, ändert das Diagramm auf einem
   `mmds/<kd>-flow`-Branch, **Commit changes**.
2. Sagt „fertig".
3. Agent liest via `gh` zurück und **difft** gegen die Spec:
   ```
   klickdummy-mermaid-readback <kd>/_flow.view.md <kd>/screens-spec.yaml
   ```
   Ausgabe = Delta (`+ next: a → b`, `- back: c ⤺ d`) — **read-only, kein Auto-Write.**
4. Agent/Mensch gießt die Delta in `screens[].next_screens`/`back_screen` der Spec.
5. KD re-generieren, `_flow.view.md` aus der Spec neu erzeugen.

**Konvention (was der Parser liest):** Knoten = Screen (`id["Label"]`), `A --> B` =
`next_screens`, `A -.zurück.-> B` = `back_screen`. Verkettung `A --> B --> C` erlaubt.

> Bewusst **kein** `mmd→spec`-Parser (KONZ-008 A verworfen): das würde Mermaid zur zweiten
> Wahrheit machen und die Codegen-/RCE-Fläche vergrößern. Der Readback difft nur.

## Kanal 2 — Feedback-Widget (Inhalt/Detail)

Für konkretes, screen-gebundenes Feedback („`area-table`: Zone 20 fehlt").

- Die Shell lädt mit `?feedback=on` das Widget (`snippets/feedback-widget/widget.js`).
- Feedback landet als **GitHub-Issue** (mit `feedback_scope` Klickdummy-vs-Fachanwendung,
  DOM-Snapshot, sichtbarer Element-ID) im `KLICKDUMMY_FEEDBACK_REPO`.
- Agent/Mensch triagiert das Issue und pflegt Inhalt/`parity_acceptance` in die Spec.

## Arbeitsteilung

| Kanal | Wofür | Landet | In die Spec via |
|-------|-------|--------|-----------------|
| **Mermaid** | Struktur (Flow, Reihenfolge, Rücksprünge) | GitHub-Branch | `klickdummy-mermaid-readback` → Delta → `next_screens`/`back_screen` |
| **Widget** | Inhalt/Detail pro Screen | GitHub-Issue | Triage → `parity_acceptance`/`local_entities` |

Danach der übliche Loop: Spec → Shell → `klickdummy-infer-asserts` (Präsenz/Zähl-Asserts)
→ `klickdummy-gen-e2e` → `klickdummy-parity-gate` (Phase A gegen Renderer #1, Phase C gegen
die echte App). Off-Ramp je Screen bei `parity-grün`.
