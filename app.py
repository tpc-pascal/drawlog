import json
import logging
import re
from pathlib import Path
from typing import Any

import gradio as gr
import spaces

from scripts.ticket_history import lookup_official_draws


ROOT = Path(__file__).resolve().parent
LOGGER = logging.getLogger(__name__)
BODY_PATTERN = re.compile(r"<body(?:\s[^>]*)?>(.*?)</body\s*>", re.IGNORECASE | re.DOTALL)
GRADIO_CSS = """
.gradio-container {
  max-width: none !important;
  padding: 0 !important;
}

.gradio-container > .main {
  padding: 0 !important;
}

#drawlog-app input,
#drawlog-app select {
  border-color: var(--border) !important;
  background: #101310 !important;
  color: var(--text) !important;
}

#drawlog-app a {
  color: inherit !important;
  text-decoration: none !important;
}

#drawlog-app .ticket-check-verified a {
  color: var(--green) !important;
  text-decoration: underline !important;
}

#drawlog-app .button-quiet {
  border-color: var(--border) !important;
  background: transparent !important;
  color: #d1d7cd !important;
}

#drawlog-app .button-primary {
  border-color: var(--green) !important;
  background: var(--green) !important;
  color: #151a11 !important;
}

#drawlog-app .button-primary:hover {
  background: var(--green-strong) !important;
}

#drawlog-app .remove-set {
  border: 0 !important;
  background: transparent !important;
  color: var(--muted) !important;
}
"""


@spaces.GPU
def zero_gpu_compatibility_marker() -> None:
    return None


def build_styles() -> str:
    styles = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
    return f"{styles}\n{GRADIO_CSS}"


def build_javascript() -> str:
    scripts = [
        (ROOT / "web" / filename).read_text(encoding="utf-8")
        for filename in ("games.js", "csv.js", "latest-results.js", "ticket-check.js", "app.js")
    ]
    return f"""() => {{
      const scripts = {json.dumps(scripts)};
      let attempts = 0;
      const initialize = () => {{
        if (!document.getElementById("ticket-form")) {{
          attempts += 1;
          if (attempts < 200) {{
            window.setTimeout(initialize, 25);
          }} else {{
            console.error("Drawlog could not find its ticket form.");
          }}
          return;
        }}
        scripts.forEach((source) => new Function(source)());
      }};
      initialize();
    }}"""


def lookup_official_draws_api(game_id: str, draw_date: str) -> dict[str, Any]:
    try:
        return {"draws": lookup_official_draws(game_id, draw_date), "error": None}
    except Exception as error:
        LOGGER.exception("Draw history lookup failed for %s on %s", game_id, draw_date)
        return {"draws": [], "error": f"{type(error).__name__}: {error}"}


def build_app() -> gr.Blocks:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    body = BODY_PATTERN.search(html)
    if body is None:
        raise ValueError("index.html must contain a body element")

    with gr.Blocks(title="Drawlog — Ticket tracker", analytics_enabled=False) as demo:
        gr.HTML(body.group(1), elem_id="drawlog-app", show_label=False, container=False)
        gr.api(
            lookup_official_draws_api,
            api_name="lookup_official_draws",
            api_visibility="undocumented",
            time_limit=120,
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        css=build_styles(),
        js=build_javascript(),
    )
