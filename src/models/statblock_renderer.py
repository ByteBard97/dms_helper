"""statblock_renderer.py

Convert creature JSON into statblock5e custom-element HTML.

The function `json_to_statblock()` is intentionally lightweight and
UI-agnostic; it simply returns an HTML *fragment* relying on the custom
Web-Components that are already bundled into `chat_template.html.tpl`.
"""

from __future__ import annotations

from html import escape
from typing import Any, Mapping
import json as _json

__all__ = ["json_to_statblock"]


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def json_to_statblock(data: "str | Mapping[str, Any]") -> str:  # noqa: D401
    """Return an HTML fragment that `<LLMOutputWidget>` understands.

    *data* may be a dict or a JSON-encoded string.  Missing optional keys are
    simply skipped.
    """
    # Parse if string
    if isinstance(data, str):
        try:
            data_dict: Mapping[str, Any] = _json.loads(data)
        except _json.JSONDecodeError:
            return "<p class='error'>Invalid stat-block JSON</p>"
    else:
        data_dict = data

    d = {k: v for k, v in data_dict.items() if v not in (None, "")}

    def esc(key: str, default: str = "") -> str:
        return escape(str(d.get(key, default)))

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    heading = ""
    if "name" in d or {"size", "type", "alignment"} & d.keys():
        name = f"<h1>{esc('name')}</h1>" if "name" in d else ""
        meta_parts = [esc(k) for k in ("size", "type", "alignment") if k in d]
        meta = f"<h2>{escape(', '.join(meta_parts))}</h2>" if meta_parts else ""
        heading = f"<creature-heading>{name}{meta}</creature-heading>"

    # ------------------------------------------------------------------
    # Top-stats section
    # ------------------------------------------------------------------
    def prop(label: str, key: str) -> str:
        return (
            f"<property-line><h4>{label}</h4> <p>{esc(key)}</p></property-line>"  # space after </h4>
            if key in d else ""
        )

    lines: list[str] = [
        prop("Armor Class", "armor_class"),
        prop("Hit Points", "hit_points"),
        prop("Speed", "speed"),
    ]

    abilities_attrs = ""
    if isinstance(d.get("abilities"), Mapping):
        abilities_attrs = " ".join(
            f"data-{ability.lower()}='{escape(str(score))}'"
            for ability, score in d["abilities"].items()
            if ability.lower() in {"str", "dex", "con", "int", "wis", "cha"}
        )
        if abilities_attrs:
            lines.append(f"<abilities-block {abilities_attrs}></abilities-block>")

    # Other common properties
    for label, key in (
        ("Senses", "senses"),
        ("Languages", "languages"),
        ("Challenge", "challenge"),
    ):
        lines.append(prop(label, key))

    top_stats = "".join(filter(None, lines))
    top_stats_html = f"<top-stats>{top_stats}</top-stats>" if top_stats else ""

    # ------------------------------------------------------------------
    # Sections (traits, actions, etc.)
    # ------------------------------------------------------------------
    def section(title: str | None, key: str) -> str:
        entries = d.get(key, [])
        if not entries:
            return ""
        title_html = f"<h3>{escape(title)}</h3>" if title else ""
        blocks = "".join(
            f"<property-block><h4>{escape(item.get('name',''))}.</h4><p>{escape(item.get('desc',''))}</p></property-block>"
            for item in entries
            if isinstance(item, Mapping)
        )
        return f"{title_html}{blocks}" if blocks else ""

    traits_html = section(None, "traits")
    actions_html = section("Actions", "actions")
    reactions_html = section("Reactions", "reactions")
    legendary_html = section("Legendary Actions", "legendary_actions")

    # ------------------------------------------------------------------
    # Combine all parts
    # ------------------------------------------------------------------
    parts = [heading, top_stats_html, traits_html, actions_html, reactions_html, legendary_html]
    content = "".join(p for p in parts if p)
    return f"<stat-block>\n{content}\n</stat-block>" if content else "" 