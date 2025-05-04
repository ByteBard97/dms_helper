#!/usr/bin/env python3
"""Widget encapsulating the left-hand LLM output pane.

This dedicated widget is responsible solely for rendering the assistant's
markdown/HTML output.  Isolating it into its own module keeps the main window
leaner and paves the way for further feature additions (e.g., custom CSS,
browser settings) without cluttering other UI code.

The widget *does not* concern itself with application logic – it exposes a
simple :py:meth:`append_html` helper that callers can use to inject already
converted HTML fragments.
"""

from __future__ import annotations

from pathlib import Path
import re

from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QWidget  # For type hints
from PyQt5.QtCore import pyqtSlot

from config_manager import ConfigManager

# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class LLMOutputWidget(QWebEngineView):
    """A standalone widget for displaying LLM suggestions/output.

    Parameters
    ----------
    config_manager:
        Shared :class:`~config_manager.ConfigManager` instance for accessing
        application-wide settings such as CSS paths.
    parent:
        Standard Qt parent.  Defaults to *None*.
    """

    def __init__(self, config_manager: ConfigManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.config = config_manager

        # ------------------------------------------------------------------
        # Initial web-view configuration
        # ------------------------------------------------------------------
        settings = self.settings()
        settings.setAttribute(settings.WebAttribute.WebGLEnabled, False)
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, False)

        # Load initial blank/placeholder page so the view is never empty.
        template_path = Path(__file__).with_suffix("").parent / "templates" / "chat_template.html.tpl"
        if template_path.is_file():
            template_text = template_path.read_text(encoding="utf-8")
        else:
            # Fallback minimal HTML if template missing
            template_text = "<html><body><p>Template missing.</p></body></html>"

        # Currently we rely on external CSS (dnd_style.css) to define colours.
        # Keep only background colour if we need it for fallback; omit text colour
        substitutions = {
            "background_color": "#000000",
        }

        def _replace(match: re.Match[str]) -> str:  # type: ignore[type-var]
            key = match.group(1)
            return substitutions.get(key, match.group(0))

        rendered_html = re.sub(r"\{\{\s*(\w+)\s*\}\}", _replace, template_text)

        self.setHtml(rendered_html, baseUrl=QUrl("file:///"))

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def append_html(self, html_fragment: str) -> None:
        """Appends an *already converted* HTML fragment to the view."""
        # Encode as JSON string so it can safely be inserted via JavaScript.
        from json import dumps as _dumps  # Local import to avoid global cost

        safe_html = _dumps(html_fragment)
        script = (
            """
            var body = document.body;
            var container = document.createElement('div');
            container.innerHTML = {safe_html};
            while (container.firstChild) {{
                body.appendChild(container.firstChild);
            }}
            window.scrollTo(0, document.body.scrollHeight);
            """
        ).format(safe_html=safe_html)

        self.page().runJavaScript(script)

    # Streaming-related slots ------------------------------------------------
    @pyqtSlot(str)
    def handle_stream_started(self, stream_id: str) -> None:  # noqa: D401
        """Begin a new streamed response block.

        A dedicated `<div>` with id `stream_<stream_id>` is appended to the
        document body; subsequent chunks for this stream are inserted into that
        container so they appear as a single contiguous message.
        """
        script = (
            """
            (function() {
              var body = document.body;
              var existing = document.getElementById('stream_' + {sid});
              if (!existing) {
                var container = document.createElement('div');
                container.id = 'stream_' + {sid};
                body.appendChild(container);
              }
              window.scrollTo(0, document.body.scrollHeight);
            })();
            """
        ).format(sid=_js_str(stream_id))
        self.page().runJavaScript(script)

    @pyqtSlot(str, str)
    def handle_response_chunk_received(self, stream_id: str, html_chunk: str) -> None:  # noqa: D401
        """Append an HTML fragment to the active stream container."""
        safe_chunk = json_dumps(html_chunk)
        script = (
            """
            (function() {
              var container = document.getElementById('stream_' + {sid});
              if (!container) {
                container = document.createElement('div');
                container.id = 'stream_' + {sid};
                document.body.appendChild(container);
              }
              container.insertAdjacentHTML('beforeend', {chunk});
              window.scrollTo(0, document.body.scrollHeight);
            })();
            """
        ).format(sid=_js_str(stream_id), chunk=safe_chunk)
        self.page().runJavaScript(script)

    @pyqtSlot(str, str)
    def handle_stream_finished(self, stream_id: str, final_html: str) -> None:  # noqa: D401
        """Finalize the stream container, replacing its contents with *final_html*.

        This lets the LLM stream show progressively but be replaced by the
        formatted final markdown once complete, avoiding duplication.
        """
        safe_final = json_dumps(final_html)
        script = (
            """
            (function() {
              var container = document.getElementById('stream_' + {sid});
              if (!container) {
                 container = document.createElement('div');
                 container.id = 'stream_' + {sid};
                 document.body.appendChild(container);
              }
              container.innerHTML = '';
              container.insertAdjacentHTML('beforeend', {html});
              window.scrollTo(0, document.body.scrollHeight);
            })();
            """
        ).format(sid=_js_str(stream_id), html=safe_final)
        self.page().runJavaScript(script)

    # Convenience appenders ---------------------------------------------
    def append_user_input_html(self, html_fragment: str) -> None:
        self.append_html(html_fragment)

    def append_dm_action_html(self, html_fragment: str) -> None:
        self.append_html(html_fragment)

    def append_error_html(self, html_fragment: str) -> None:
        self.append_html(f"<div class='error'>{html_fragment}</div>")

# ---------------------------------------------------------------------------
# Internal helpers (kept bottom to avoid polluting public API)
# ---------------------------------------------------------------------------

def json_dumps(val: str) -> str:  # noqa: D401
    from json import dumps as _dumps
    return _dumps(val)

def _js_str(py_str: str) -> str:  # noqa: D401
    """Return a JSON-encoded JS string literal for *py_str*."""
    return json_dumps(py_str) 