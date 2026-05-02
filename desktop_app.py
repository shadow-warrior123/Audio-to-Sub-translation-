from __future__ import annotations

import socket
import sys
import threading
import time
from contextlib import closing

import uvicorn


HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/app/"


def main() -> None:
    try:
        import webview
    except ImportError:
        print("pywebview is not installed. Run: python -m pip install -r requirements.txt")
        raise

    server = uvicorn.Server(
        uvicorn.Config(
            "app.main:app",
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=False,
        )
    )

    if not _port_is_open(HOST, PORT):
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        _wait_for_port(HOST, PORT)

    window = webview.create_window(
        "Anime Subtitle Studio",
        URL,
        width=1180,
        height=820,
        min_size=(900, 680),
    )

    def on_closed() -> None:
        server.should_exit = True

    window.events.closed += on_closed
    webview.start()


def _port_is_open(host: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_is_open(host, port):
            return
        time.sleep(0.2)
    print(f"Timed out waiting for backend at http://{host}:{port}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
