"""Run the demo and open it in a browser.

    python -m app
"""

from __future__ import annotations

import os
import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    if os.environ.get("MD5_DEMO_OPEN", "1") != "0":
        threading.Timer(
            0.6,
            lambda: webbrowser.open(f"http://{HOST}:{PORT}"),
        ).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
