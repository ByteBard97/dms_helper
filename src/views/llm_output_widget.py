#!/usr/bin/env python3
"""LLMOutputWidget  –  simplified, JS‑error‑free version

Changes vs previous revision
----------------------------
* Removed the `var d=document` shorthands inside streaming snippets that
  sometimes leaked out‑of‑scope and produced the JS console error
  `ReferenceError: d is not defined`.
* Public API (`append_html`, convenience wrappers, streaming slots) and
  constructor signature are unchanged, so this file drops into your
  existing `MainWindow` without modifications elsewhere.
* Still relies on *html_templates.html_content* which already bundles
  the complete statblock5e CSS + JS and the duplicate‑define guard.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt5.QtCore import QUrl, pyqtSlot
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QWidget

from html_templates import html_content  #  ← one‑file bundled HTML

if TYPE_CHECKING:  # avoid runtime import cost / circular deps
    from config_manager import ConfigManager

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------

def _json(val: str) -> str:
    """Return a JSON‑encoded JS string literal version of *val*."""
    return json.dumps(val, ensure_ascii=False)


# ---------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------
class LLMOutputWidget(QWebEngineView):
    """Lightweight view that displays assistant output."""

    def __init__(
        self,
        config_manager: Optional["ConfigManager"] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config_manager  # kept for future theming use

        # Load the pre‑bundled HTML (no disk I/O if the module is frozen)
        self.setHtml(html_content, baseUrl=QUrl("data:"))
        _LOGGER.info("LLMOutputWidget: pre‑bundled HTML loaded.")

        # Thin down WebEngine features we don't need
        s = self.settings()
        s.setAttribute(s.WebGLEnabled, False)
        s.setAttribute(s.PluginsEnabled, False)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def append_html(self, html_fragment: str) -> None:
        """Append already‑formatted HTML to the document body."""
        safe = _json(html_fragment)
        script = (
            "var tmp=document.createElement('div');"
            f"tmp.innerHTML={safe};"
            "while(tmp.firstChild){document.body.appendChild(tmp.firstChild);}"
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        self.page().runJavaScript(script)

    # Convenience wrappers ------------------------------------------------
    def append_user_input_html(self, html_fragment: str) -> None:
        self.append_html(html_fragment)

    def append_dm_action_html(self, html_fragment: str) -> None:
        self.append_html(html_fragment)

    def append_error_html(self, html_fragment: str) -> None:
        self.append_html(f"<div class='error'>{html_fragment}</div>")

    # ------------------------------------------------------------------
    # Streaming slots (token‑by‑token updates)
    # ------------------------------------------------------------------
    @pyqtSlot(str)
    def handle_stream_started(self, stream_id: str) -> None:
        script = f"""
        (function(){{
          var body=document.body;
          var c=document.getElementById('stream_{stream_id}');
          if(!c){{
            c=document.createElement('div');
            c.id='stream_{stream_id}';
            body.appendChild(c);
          }}
          window.scrollTo(0, body.scrollHeight);
        }})();
        """
        self.page().runJavaScript(script)

    @pyqtSlot(str, str)
    def handle_response_chunk_received(self, stream_id: str, html_chunk: str) -> None:
        safe = _json(html_chunk)
        script = (
            f"var c=document.getElementById('stream_{stream_id}');"
            "if(c){c.insertAdjacentHTML('beforeend',"+safe+");"
            "window.scrollTo(0, document.body.scrollHeight);}"
        )
        self.page().runJavaScript(script)

    @pyqtSlot(str, str)
    def handle_stream_finished(self, stream_id: str, final_html: str) -> None:
        safe = _json(final_html)
        script = (
            f"var c=document.getElementById('stream_{stream_id}');"
            "if(c){c.innerHTML='';c.insertAdjacentHTML('beforeend',"+safe+");"
            "window.scrollTo(0, document.body.scrollHeight);}"
        )
        self.page().runJavaScript(script)
