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

__all__ = ["json_to_statblock"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def json_to_statblock(data: "str | Mapping[str, Any]") -> str:  # noqa: D401
    """Convert *data* to an HTML stat-block using statblock5e custom elements.

    Parameters
    ----------
    data:
        Either a JSON-encoded :class:`str` or a pre-parsed mapping representing
        a creature/monster stat-block.

    Returns
    -------
    str
        An HTML fragment using statblock5e custom elements (`<stat-block>`,
        `<creature-heading>`, `<property-line>`, etc.). The consuming view MUST
        have the statblock5e web components loaded (e.g., via inlined script
        in the template).
    """
    if isinstance(data, str):
        import json as _json  # local import to keep top-level light
        try:
            data_dict: Dict[str, Any] = _json.loads(data)
        except _json.JSONDecodeError:
            # Handle invalid JSON gracefully
            return "<p class='error'>Error: Invalid statblock JSON data.</p>"
    else:
        data_dict = dict(data)  # shallow copy to ensure mutability

    # Helper: fetch & HTML-escape value if present
    def _val(key: str, default: str = "") -> str:
        return escape(str(data_dict.get(key, default)))

    # Helper: Generate a <property-line> element
    def _prop_line(label: str, key: str, format_val=None) -> str:
        if key not in data_dict:
            return ""
        value = _val(key)
        if format_val:
            value = format_val(value)
        return f"<property-line><h4>{label}</h4> <p>{value}</p></property-line>"

    # --- Header (<creature-heading>) -----------------------------------
    name_html = f"<h1>{_val('name')}</h1>" if "name" in data_dict else ""
    meta_parts: list[str] = []
    for k in ("size", "type", "alignment"):
        if k in data_dict:
            meta_part = _val(k)
            if meta_part: # Ensure empty strings aren't added
                meta_parts.append(meta_part)
    meta_html = f"<h2>{escape(', '.join(meta_parts))}</h2>" if meta_parts else ""
    heading_html = f"<creature-heading>{name_html}{meta_html}</creature-heading>" if name_html or meta_html else ""


    # --- Top Stats (<top-stats>) ----------------------------------------
    top_stats_lines: list[str] = []
    top_stats_lines.append(_prop_line("Armor Class", "armor_class"))
    top_stats_lines.append(_prop_line("Hit Points", "hit_points"))
    top_stats_lines.append(_prop_line("Speed", "speed"))

    # Abilities block
    ability_attrs = ""
    if "abilities" in data_dict and isinstance(data_dict["abilities"], Mapping):
        ab = data_dict["abilities"]
        ability_attrs = " ".join(
            f"data-{attr.lower()}='{escape(str(score))}'"
            for attr, score in ab.items()
            if attr.lower() in ["str", "dex", "con", "int", "wis", "cha"] # Only valid attrs
        )
    if ability_attrs:
        top_stats_lines.append(f"<abilities-block {ability_attrs}></abilities-block>")

    # Other top stats
    top_stats_lines.append(_prop_line("Skills", "skills")) # Assuming skills might exist
    top_stats_lines.append(_prop_line("Damage Vulnerabilities", "damage_vulnerabilities"))
    top_stats_lines.append(_prop_line("Damage Resistances", "damage_resistances"))
    top_stats_lines.append(_prop_line("Damage Immunities", "damage_immunities"))
    top_stats_lines.append(_prop_line("Condition Immunities", "condition_immunities"))
    top_stats_lines.append(_prop_line("Senses", "senses"))
    top_stats_lines.append(_prop_line("Languages", "languages"))
    top_stats_lines.append(_prop_line("Challenge", "challenge"))

    # Filter out empty lines before joining
    valid_top_stats_lines = [line for line in top_stats_lines if line]
    top_stats_html = f"<top-stats>{''.join(valid_top_stats_lines)}</top-stats>" if valid_top_stats_lines else ""


    # --- Traits / Actions (<property-block>) ----------------------------
    def _section(title: str | None, key: str) -> str:
        entries = data_dict.get(key, [])
        if not entries:
            return ""

        # Add title if provided (e.g., "Actions")
        title_html = f"<h3>{escape(title)}</h3>" if title else ""

        property_blocks = "".join(
            (
                f"<property-block>"
                f"<h4>{escape(item.get('name', ''))}.</h4> "
                f"<p>{escape(item.get('desc', ''))}</p>"
                f"</property-block>"
            )
            for item in entries
            if isinstance(item, Mapping) and (item.get('name') or item.get('desc')) # Ensure block isn't empty
        )
        return f"{title_html}{property_blocks}" if property_blocks else ""

    # Assume 'special_abilities' might be used for traits without a title
    traits_html = _section(None, "special_abilities") + _section(None, "traits")
    actions_html = _section("Actions", "actions")
    reactions_html = _section("Reactions", "reactions")
    legendary_actions_html = _section("Legendary Actions", "legendary_actions")


    # --- Combine into <stat-block> ------------------------------------
    # Ensure we don't create an empty stat-block if data is sparse
    if not heading_html and not top_stats_html and not traits_html and not actions_html and not reactions_html and not legendary_actions_html:
        return "" # Return empty if no content was generated

    html_parts = [
        "<stat-block>",
        heading_html,
        top_stats_html,
        traits_html, # Traits often come before actions
        actions_html,
        reactions_html,
        legendary_actions_html,
        "</stat-block>",
    ]
    # Filter out empty strings before joining
    return "\\n".join(part for part in html_parts if part) 