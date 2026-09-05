"""Keep the Render free-tier backend awake: pings /health every 10 minutes.

Render sleeps web services after ~15 minutes without traffic; the next
request then pays a 30-60 s cold start. Run this in any terminal and leave
it open while you need instant responses.

Usage:
    python scripts/keep_alive.py [url] [interval_seconds]
"""

from __future__ import annotations

import sys
import time
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "https://lumen-promptwars.onrender.com/health"
INTERVAL = int(sys.argv[2]) if len(sys.argv) > 2 else 600


def ping() -> str:
    try:
        with urllib.request.urlopen(URL, timeout=30) as resp:
            return f"{resp.status} {resp.read()[:80].decode(errors='replace')}"
    except Exception as exc:  # keep looping through blips, report them
        return f"MISS {type(exc).__name__}: {str(exc)[:100]}"


def main() -> None:
    print(f"keep-alive -> {URL} every {INTERVAL}s (Ctrl+C to stop)", flush=True)
    while True:
        print(f"{time.strftime('%H:%M:%S')} {ping()}", flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
