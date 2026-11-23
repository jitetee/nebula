#!/usr/bin/env python3
"""Tiny OpenAI-compatible server for tests: python3 tools/mock_ai_server.py PORT. Replies 'MOCK: <last user line>'."""
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        last = [m for m in b["messages"] if m["role"] == "user"][-1]["content"].strip().splitlines()[-1]
        out = json.dumps({"choices": [{"message": {"role": "assistant", "content": "MOCK: " + last[:80]}, "finish_reason": "stop"}],
                          "usage": {"total_tokens": 5}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
