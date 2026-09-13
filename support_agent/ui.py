from __future__ import annotations

import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from .contracts import AgentRequest
from .factory import build_agent

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>AmazonHelp AI support agent</title><style>
:root { color-scheme: light; font-family: Inter, system-ui, sans-serif; }
body { margin: 0; background: #f5f7fb; color: #182230; }
main { max-width: 900px; margin: 48px auto; padding: 0 20px; }
.card { background: white; border: 1px solid #dbe2ea; border-radius: 16px; padding: 24px; margin: 18px 0; box-shadow: 0 8px 24px #1b2a3a10; }
textarea { box-sizing: border-box; width: 100%; min-height: 130px; padding: 14px; border: 1px solid #9aa9ba; border-radius: 10px; font: inherit; }
button { background: #1264a3; color: white; border: 0; border-radius: 9px; padding: 11px 18px; font-weight: 700; cursor: pointer; }
.pill { display: inline-block; padding: 6px 10px; border-radius: 999px; background: #e7eef7; margin-right: 8px; font-size: 13px; }
.escalate { background: #fff0dd; color: #7a3e00; } .auto { background: #e4f6e9; color: #175c2c; }
.muted { color: #5b6877; } .evidence { border-left: 3px solid #86a6c3; padding-left: 14px; }
</style></head><body><main><h1>AmazonHelp AI support agent</h1>
<p class="muted">Enter a customer message to generate an intent, reply draft, routing decision, and supporting examples.</p>
<form class="card" method="post"><label for="message"><strong>Customer message</strong></label><br><br>
<textarea id="message" name="message" maxlength="2000" required>__MESSAGE__</textarea><br><br>
<button type="submit">Generate response</button></form>__RESULT__</main></body></html>"""


def render_page(message: str, result: str) -> str:
    return PAGE.replace("__MESSAGE__", message).replace("__RESULT__", result)


def render_result(result) -> str:
    route_class = "auto" if result.route.value == "AUTO_HANDLE" else "escalate"
    evidence = "".join(
        f'<div class="evidence"><strong>{html.escape(case.case_id)}</strong>'
        f'<p>{html.escape(case.problem_excerpt)}</p><p class="muted">{html.escape(case.response_excerpt)}</p></div>'
        for case in result.evidence
    ) or '<p class="muted">No usable evidence retrieved.</p>'
    return f"""<section class="card"><h2>Agent result</h2>
    <p><strong>Intent:</strong> <span class="pill">{html.escape(result.intent)}</span></p>
    <h3>Draft reply</h3><p>{html.escape(result.draft)}</p>
    <p><strong>Decision:</strong> <span class="pill {route_class}">{result.route.value}</span></p>
    <p><strong>Reason:</strong> {html.escape(result.reason)}</p>
    <h3>Similar historical cases</h3>{evidence}</section>"""


def handler_factory(agent):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = render_page("", "").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = min(int(self.headers.get("Content-Length", "0")), 16_384)
            values = parse_qs(self.rfile.read(length).decode("utf-8"))
            message = values.get("message", [""])[0]
            try:
                result = agent.run(AgentRequest("AmazonHelp", message))
                result_html = render_result(result)
            except ValueError as exc:
                result_html = f'<section class="card escalate">{html.escape(str(exc))}</section>'
            body = render_page(html.escape(message), result_html).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(build_agent(args.root)))
    print(f"Support agent: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
