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
import logging

from models.markdown_utils import markdown_to_html_fragment
from models.class_statblock_renderer import json_to_statblock
from log_manager import LogManager

__all__ = ["convert_markdown_to_html", "extract_statblock_html"]

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Use the application-level logger so that debug output respects LogManager's configuration.
_LOGGER = LogManager.get_app_logger()
_LOGGER.setLevel(logging.DEBUG)

def convert_markdown_to_html(markdown: str) -> str:  # noqa: D401
    """Convert *markdown* to HTML, expanding any JSON stat-blocks."""
    # _LOGGER.debug("[convert_markdown_to_html] Received markdown (length=%s):\n%s", len(markdown), markdown)

    processed_md = _replace_statblocks(markdown)
    processed_md = _normalize_tables(processed_md)

    # _LOGGER.debug("[convert_markdown_to_html] Preprocessed markdown (length=%s):\n%s", len(processed_md), processed_md)

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

# ---------------------------------------------------------------------------
# Table normalisation & wrapping
# ---------------------------------------------------------------------------

_TABLE_LINE_RE = re.compile(r"^\|.*\|.*\|?")


def _normalize_tables(md: str) -> str:  # noqa: D401
    """Fix common LLM pipe issues and wrap tables in <div class="table-5e">."""

    logger = _LOGGER

    # _LOGGER.debug("[TableNormalizer] Raw input (length=%s):\n%s", len(md), md)

    # 1. Ensure any existing <div class="table-5e"> has the markdown attribute so that
    #    Python-Markdown processes its inner text.
    md = re.sub(
        r'(<div\s+class="table-5e"(?![^>]*markdown="1"))',
        r'\1 markdown="1"',
        md,
        flags=re.IGNORECASE,
    )

    # 2. Replace occurrences like '| |' (pipe, optional spaces, pipe) with a newline pipe.
    fixed_md = re.sub(r"\|\s*\|", "|\n|", md)
    if fixed_md != md:
        # _LOGGER.debug("[TableNormalizer] Applied pipe-newline fix to table block.")
        md = fixed_md

    lines = md.splitlines()
    output: list[str] = []
    table_buffer: list[str] = []

    in_existing_wrapper = False  # Tracks if we're already inside a provided .table-5e div

    def flush_table():
        nonlocal table_buffer, in_existing_wrapper
        if table_buffer:
            table_markdown = "\n".join(table_buffer)
            if in_existing_wrapper:
                # We are already within a <div class="table-5e" markdown="1">, so just
                # append the table markdown without adding another wrapper.
                output.append(table_markdown)
            else:
                # Add our own wrapper with markdown="1" so that it renders.
                output.append(
                    "<div class=\"table-5e\" markdown=\"1\">\n" + table_markdown + "\n</div>"
                )
            table_buffer = []

    for line in lines:
        stripped = line.strip()

        # Track entry/exit of existing wrapper divs to avoid double wrapping
        if stripped.lower().startswith("<div class=\"table-5e\""):
            in_existing_wrapper = True
            output.append(stripped)  # keep the div line as-is
            continue
        if stripped.lower() == "</div>" and in_existing_wrapper:
            flush_table()  # flush any buffered table before closing wrapper
            in_existing_wrapper = False
            output.append(stripped)
            continue

        if _TABLE_LINE_RE.match(stripped):
            # Fix extra leading pipes like '| | ...' => '| ...'
            fixed = re.sub(r"^\|\s*\|", "|", stripped)
            table_buffer.append(fixed)
        else:
            flush_table()
            output.append(line)

    flush_table()
    result = "\n".join(output)
    if result != md:
        # _LOGGER.debug("[TableNormalizer] Wrapped %s table line(s) in .table-5e div.", len(result.splitlines()) - len(lines))
        md = result

    # _LOGGER.debug("[TableNormalizer] Result after normalization (length=%s):\n%s", len(result), result)
    return md 