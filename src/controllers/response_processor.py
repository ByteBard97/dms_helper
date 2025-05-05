"""response_processor.py

Controller/service that converts raw markdown (possibly containing JSON
stat-blocks) into safe HTML for the view layer.

Workflow
========
1. Detect fenced JSON blocks (```json … ```), attempt to parse them.
2. If a block parses as a stat-block (heuristic: must have "name" and at
   least one key like "hit_points", "armor_class", or "abilities"), render
   it via ``models.class_statblock_renderer.json_to_statblock`` and replace the
   fenced block with the resulting HTML.
3. Pass the (potentially modified) markdown through
   ``models.markdown_utils.markdown_to_html_fragment`` to get final HTML.

This module is UI-agnostic; callers (e.g. LLMController, unit tests) can use
it directly.
"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Any

from models.markdown_utils import markdown_to_html_fragment
from models.class_statblock_renderer import json_to_statblock

__all__ = ["convert_markdown_to_html", "extract_statblock_html"]

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_markdown_to_html(markdown: str) -> str:  # noqa: D401
    """Convert *markdown* to HTML, expanding any JSON stat-blocks."""
    processed_md = _replace_statblocks(markdown)
    return markdown_to_html_fragment(processed_md)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _replace_statblocks(md: str) -> str:  # noqa: D401
    """Replace fenced JSON blocks with rendered stat-block HTML."""

    def _sub(match: re.Match[str]) -> str:  # noqa: D401
        json_text = match.group(1)
        try:
            data: Any = json.loads(json_text)
        except json.JSONDecodeError:
            return match.group(0)  # leave untouched if not valid JSON

        # Minimal heuristic to detect a creature stat-block
        if not (
            isinstance(data, dict)
            and "name" in data
            and any(k in data for k in ("hit_points", "armor_class", "abilities"))
        ):
            return match.group(0)

        return json_to_statblock(data)

    return _FENCE_RE.sub(_sub, md)


# ---- Convenience: extract first stat-block as HTML (optional) --------

def extract_statblock_html(markdown: str) -> str | None:
    """Return rendered HTML for the *first* fenced JSON block, or ``None``."""
    match = _FENCE_RE.search(markdown)
    if not match:
        return None
    try:
        data = json.loads(textwrap.dedent(match.group(1)).strip())
        if not (
            isinstance(data, dict)
            and "name" in data
            and any(k in data for k in ("hit_points", "armor_class", "abilities"))
        ):
            return None
        return json_to_statblock(data)
    except json.JSONDecodeError:
        return None 