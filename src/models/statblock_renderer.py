"""statblock_renderer.py

Model-layer helper that converts a creature/stat-block JSON structure into
ready-to-embed HTML.  This module is UI-agnostic (no Qt imports) so it can be
unit-tested in isolation and reused by any view/controller.

The expected JSON schema is loosely based on the 5e SRD monster format:

{
  "name": "Goblin",
  "size": "Small",
  "type": "humanoid",
  "alignment": "neutral evil",
  "armor_class": 15,
  "hit_points": 7,
  "speed": "30 ft.",
  "abilities": { "str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8 },
  "senses": "darkvision 60 ft.",
  "languages": "Common, Goblin",
  "challenge": "1/4 (50 XP)",
  "traits": [
      {"name": "Nimble Escape", "desc": "The goblin can take the Disengage..."}
  ],
  "actions": [
      {"name": "Scimitar", "desc": "Melee Weapon Attack: +4 to hit..."},
      {"name": "Shortbow", "desc": "Ranged Weapon Attack: +4 to hit..."}
  ]
}

Only fields present in the input will be rendered; missing ones are skipped.
"""

from __future__ import annotations

from html import escape
from typing import Any, Dict, Mapping

__all__ = ["json_to_statblock_html"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def json_to_statblock_html(data: "str | Mapping[str, Any]") -> str:  # noqa: D401
    """Convert *data* to an HTML stat-block.

    Parameters
    ----------
    data:
        Either a JSON-encoded :class:`str` or a pre-parsed mapping representing
        a creature/monster stat-block.

    Returns
    -------
    str
        A **self-contained** HTML fragment (no external CSS) that callers can
        insert into the web-view.  The consuming view may still add a global
        stylesheet for nicer styling.
    """
    if isinstance(data, str):
        import json as _json  # local import to keep top-level light
        data_dict: Dict[str, Any] = _json.loads(data)
    else:
        data_dict = dict(data)  # shallow copy to ensure mutability

    # Helper: fetch & HTML-escape value if present
    def _val(key: str, default: str = "") -> str:  # noqa: D401
        return escape(str(data_dict.get(key, default)))

    # --- Header (Name & basic meta) -----------------------------------
    name_html = f"<h2 class='sb-name'>{_val('name')}</h2>" if "name" in data_dict else ""

    meta_parts: list[str] = []
    for k in ("size", "type", "alignment"):
        if k in data_dict:
            meta_parts.append(_val(k))
    meta_html = (
        f"<p class='sb-meta'>{', '.join(meta_parts)}</p>" if meta_parts else ""
    )

    # --- Core stats table --------------------------------------------
    def _row(label: str, key: str) -> str:  # noqa: D401
        return (
            f"<tr><th>{label}</th><td>{_val(key)}</td></tr>" if key in data_dict else ""
        )

    table_rows = "".join(
        _row(label, key)
        for label, key in (
            ("Armor Class", "armor_class"),
            ("Hit Points", "hit_points"),
            ("Speed", "speed"),
            ("Senses", "senses"),
            ("Languages", "languages"),
            ("Challenge", "challenge"),
        )
    )
    stats_table_html = (
        f"<table class='sb-stats'>{table_rows}</table>" if table_rows else ""
    )

    # --- Abilities ----------------------------------------------------
    ability_html = ""
    if "abilities" in data_dict and isinstance(data_dict["abilities"], Mapping):
        ab = data_dict["abilities"]
        ability_cells = "".join(
            f"<th>{attr.upper()}</th><td>{escape(str(val))}</td>"
            for attr, val in ab.items()
        )
        ability_html = f"<table class='sb-abilities'><tr>{ability_cells}</tr></table>"

    # --- Traits / Actions helpers -------------------------------------
    def _section(title: str, key: str) -> str:  # noqa: D401
        entries = data_dict.get(key, [])
        if not entries:
            return ""
        li_blocks = "".join(
            f"<li><strong>{escape(item.get('name', ''))}.</strong> {escape(item.get('desc', ''))}</li>"
            for item in entries
            if isinstance(item, Mapping)
        )
        return f"<h3>{title}</h3><ul class='sb-{key}'>{li_blocks}</ul>"

    traits_html = _section("Traits", "traits")
    actions_html = _section("Actions", "actions")

    # --- Combine ------------------------------------------------------
    html_parts = [
        "<div class='statblock'>",
        name_html,
        meta_html,
        stats_table_html,
        ability_html,
        traits_html,
        actions_html,
        "</div>",
    ]
    return "\n".join(part for part in html_parts if part) 