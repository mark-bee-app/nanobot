#!/usr/bin/env python3
"""Call remote nanobot serve API."""

import argparse
import json
import os
import sys
import urllib.request
from urllib.error import HTTPError


def main():
    parser = argparse.ArgumentParser(description="Call remote nanobot serve")
    parser.add_argument("--url", default=os.environ.get("NANOBOT_SERVE_URL"), help="Remote serve URL (or set NANOBOT_SERVE_URL env)")
    parser.add_argument("--message", "-m", required=True, help="Message to send")
    parser.add_argument("--session-id", "-s", default="", help="Session ID for multi-turn context")
    args = parser.parse_args()

    url = args.url or "http://localhost:8000"
    if not url.startswith("http"):
        url = "http://" + url

    api_url = url.rstrip("/") + "/v1/chat/completions"

    payload = {
        "model": "nanobot",
        "messages": [{"role": "user", "content": args.message}],
    }
    if args.session_id:
        payload["session_id"] = args.session_id

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    choices = data.get("choices", [])
    if not choices:
        error = data.get("error", data)
        print(f"No response: {error}", file=sys.stderr)
        sys.exit(1)

    content = choices[0].get("message", {}).get("content", "")
    print(content)


if __name__ == "__main__":
    main()
