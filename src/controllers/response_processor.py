"""response_processor.py

Controller/service that converts raw markdown (possibly containing JSON
stat-blocks) into safe HTML for the view layer.

Workflow
========
1. Detect fenced JSON blocks (```json … ```), attempt to parse them.
2. If a block parses as a stat-block (heuristic: has "name" and "hit_points"),
   render it via models.statblock_renderer and replace the fenced block with
   the resulting HTML.
3. Pass the (potentially modified) markdown through
   models.markdown_utils.markdown_to_html_fragment to get final HTML.

This module is UI-agnostic; callers (LLMController, tests) can use it directly.
"""

from __future__ import annotations

import re
import json
from typing import List, Tuple

from models.markdown_utils import markdown_to_html_fragment
from models.statblock_renderer import json_to_statblock_html

__all__ = ["convert_markdown_to_html"]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_markdown_to_html(markdown: str) -> str:  # noqa: D401
    """Convert *markdown* to HTML, expanding JSON stat-blocks.

    Parameters
    ----------
    markdown:
        Raw markdown text returned by the LLM.

    Returns
    -------
    str
        HTML fragment ready for insertion in the web view.
    """
    processed_md = _replace_statblocks(markdown)
    return markdown_to_html_fragment(processed_md)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)


def _replace_statblocks(md: str) -> str:  # noqa: D401
    """Replace JSON stat-block fences with rendered HTML."""

    def _sub(match: re.Match[str]) -> str:  # noqa: D401
        json_text = match.group(1)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return match.group(0)  # Leave untouched if not valid JSON

        # Heuristic: treat as monster stat-block if common keys present
        if not (isinstance(data, dict) and {"name", "hit_points"} <= data.keys()):
            return match.group(0)

        rendered = json_to_statblock_html(data)
        return rendered

    return _FENCE_RE.sub(_sub, md) 