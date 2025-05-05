"""class_statblock_renderer.py

Render a creature JSON dict into a class-based stat-block HTML snippet that
relies on the `.statblock5e-*` CSS rules from `dnd_style.css`.

Unlike the Web-Component variant, this implementation is *pure HTML* and needs
no JavaScript. It uses a `$placeholder` template embedded as a constant string
for fast substitution.
"""

from __future__ import annotations

import json
from html import escape
from string import Template
from typing import Any, Mapping

__all__ = ["json_to_statblock"]


class _StatblockTemplate(Template):
    # Use `$` placeholders without needing `$$` to escape newlines
    delimiter = "$"


# Single static template (copied from statblock_class_template.html.tpl)
_TEMPLATE_STR = """
<div class="statblock5e-bar"></div>
<div class="statblock5e-content">
  <div class="statblock5e-creature-heading">
    <h1>$name</h1>
    <h2>$subtitle</h2>
  </div>

  <div class="statblock5e-top-stats">
    $top_stats
  </div>

  $traits

  <h3>Actions</h3>
  $actions

  $reactions
  $legendary
</div>
<div class="statblock5e-bar"></div>
"""
_TEMPLATE = _StatblockTemplate(_TEMPLATE_STR)


def json_to_statblock(data: "str | Mapping[str, Any]") -> str:  # noqa: D401
    """Return filled-in stat-block HTML from a dict or JSON string."""
    if isinstance(data, str):
        data_dict = json.loads(data)
    else:
        data_dict = dict(data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def html(val: Any) -> str:
        return escape(str(val))

    # Build subtitle (size, type, alignment)
    subtitle_parts = [html(data_dict.get(k)) for k in ("size", "type", "alignment") if k in data_dict]
    subtitle = ", ".join(part for part in subtitle_parts if part)

    # Top-stats lines (Armor Class, HP, Speed)
    def prop_line(label: str, key: str) -> str:
        if key not in data_dict:
            return ""
        return (
            f"<div class='statblock5e-property-line'><h4>{label}</h4> <p>{html(data_dict[key])}</p></div>"
        )

    top_lines = [
        prop_line("Armor Class", "armor_class"),
        prop_line("Hit Points", "hit_points"),
        prop_line("Speed", "speed"),
    ]

    # Abilities table
    abilities_html = ""
    if isinstance(data_dict.get("abilities"), Mapping):
        ab = data_dict["abilities"]
        ability_row = " ".join(
            f"<td>{html(score)}</td>" for score in (
                ab.get("str", "–"),
                ab.get("dex", "–"),
                ab.get("con", "–"),
                ab.get("int", "–"),
                ab.get("wis", "–"),
                ab.get("cha", "–"),
            )
        )
        abilities_html = (
            "<div class='statblock5e-abilities-table'><table>"
            "<tr><th>STR</th><th>DEX</th><th>CON</th><th>INT</th><th>WIS</th><th>CHA</th></tr>"
            f"<tr>{ability_row}</tr></table></div>"
        )
    top_lines.append(abilities_html)

    # Other common property lines
    for label, key in (
        ("Senses", "senses"),
        ("Languages", "languages"),
        ("Challenge", "challenge"),
    ):
        top_lines.append(prop_line(label, key))

    top_stats_html = "\n".join(filter(None, top_lines))

    # Section helper (traits/actions etc.)
    def build_blocks(key: str) -> str:
        entries = data_dict.get(key, [])
        blocks: list[str] = []
        for item in entries:
            if not isinstance(item, Mapping):
                continue
            blocks.append(
                "<div class='statblock5e-property-block'>"
                f"<h4>{html(item.get('name',''))}.</h4> "
                f"<p>{html(item.get('desc',''))}</p>"
                "</div>"
            )
        return "\n".join(blocks)

    traits_html = build_blocks("traits")
    actions_html = build_blocks("actions")
    reactions_html = ("<h3>Reactions</h3>\n" + build_blocks("reactions")) if data_dict.get("reactions") else ""
    legendary_html = (
        "<h3>Legendary Actions</h3>\n" + build_blocks("legendary_actions")
        if data_dict.get("legendary_actions") else ""
    )

    # Substitute into template
    filled = _TEMPLATE.safe_substitute(
        name=html(data_dict.get("name", "Unknown")),
        subtitle=subtitle,
        top_stats=top_stats_html,
        traits=traits_html,
        actions=actions_html,
        reactions=reactions_html,
        legendary=legendary_html,
    )
    return filled 