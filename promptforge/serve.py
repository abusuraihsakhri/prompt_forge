"""
Local web UI server for PromptForge.

Serves the static web UI and provides an API endpoint for optimization.

Usage:
    python -m promptforge.serve
    python -m promptforge.serve --port 8080
"""

import json
import argparse
import http.server
from pathlib import Path

from promptforge.core.pipeline import optimize


# Resolve web directory relative to this file
WEB_DIR = Path(__file__).parent.parent / "web"


class PromptForgeHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for the PromptForge web UI and API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_POST(self):
        """Handle API requests for prompt optimization."""
        if self.path == "/api/optimize":
            self._handle_optimize()
        else:
            self.send_error(404, "Not Found")

    def _handle_optimize(self):
        """Process an optimization request."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 2_000_000:  # 2MB limit
                self._send_json_error(413, "Request body too large (max 2MB)")
                return

            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            prompt = data.get("prompt", "")
            model = data.get("model", "claude")
            aggressiveness = data.get("aggressiveness")

            if not prompt.strip():
                self._send_json_error(400, "Empty prompt")
                return

            # Run optimization
            result = optimize(
                prompt,
                model=model,
                aggressiveness=aggressiveness,
            )

            self._send_json(200, result.to_dict())

        except json.JSONDecodeError:
            self._send_json_error(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_json_error(500, f"Internal error: {str(e)}")

    def _send_json(self, status: int, data: dict):
        """Send a JSON response."""
        response_body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def _send_json_error(self, status: int, message: str):
        """Send a JSON error response."""
        self._send_json(status, {"error": message})

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        """Custom log format."""
        print(f"  [{self.log_date_time_string()}] {format % args}")


def serve(host: str = "127.0.0.1", port: int = 3000):
    """Start the PromptForge web UI server."""
    if not WEB_DIR.exists():
        print(f"Error: Web directory not found at {WEB_DIR}")
        return

    server = http.server.HTTPServer((host, port), PromptForgeHandler)

    print(f"""
  ╔═══════════════════════════════════════════╗
  ║   ⚡ PromptForge Web UI                   ║
  ║   http://{host}:{port:<5}                     ║
  ╚═══════════════════════════════════════════╝
  
  Press Ctrl+C to stop.
    """)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="Start the PromptForge web UI server"
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "-p", "--port", type=int, default=3000,
        help="Port to listen on (default: 3000)"
    )
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
