"""
Dual-stack dev server launcher.

Why this exists: the documented `uvicorn app.main:app` binds IPv4 (127.0.0.1) only, but macOS
resolves `localhost` to IPv6 `::1` first — so the iOS Simulator (which calls http://localhost:8000)
fails to connect with `nw_endpoint_flow_failed [::1.8000]`. This binds a DUAL-STACK socket
(IPV6_V6ONLY=0) so both `::1` and `127.0.0.1` are served, and the Simulator, web dashboard, and
curl all work.

Usage:
    cd backend && python run_dev.py          # serves :8000 on both loopbacks
    PORT=9000 python run_dev.py              # custom port

Note: no hot-reload here (uvicorn's reloader doesn't compose with a pre-bound socket). For an
IPv4-only reload loop use `uvicorn app.main:app --reload`; for Simulator dev use this or
`uvicorn app.main:app --host ::`.
"""
import asyncio
import os
import socket

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))

    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # accept IPv4-mapped connections too
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("::", port))

    server = uvicorn.Server(uvicorn.Config("app.main:app", log_level="info"))
    asyncio.run(server.serve(sockets=[sock]))


if __name__ == "__main__":
    main()
