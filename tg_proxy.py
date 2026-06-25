#!/usr/bin/env python3
"""Минимальный HTTP CONNECT-прокси для туннелирования Telegram Bot API через хост."""

import asyncio
import logging
import os
import resource

# WARNING только — INFO-уровень (каждый CONNECT) забивает syslog гигабайтами
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tg_proxy")

# Поднимаем лимит FD программно (до hard limit)
try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
except Exception as e:
    logger.warning(f"Не удалось поднять лимит FD: {e}")


async def relay(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle(client_r, client_w):
    try:
        line = await asyncio.wait_for(client_r.readline(), timeout=10)
        if not line:
            client_w.close()
            return
        parts = line.decode(errors="replace").split()
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            client_w.close()
            return
        host_port = parts[1].rsplit(":", 1)
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 443
        # drain headers
        while True:
            h = await asyncio.wait_for(client_r.readline(), timeout=5)
            if h in (b"\r\n", b"\n", b""):
                break
        srv_r, srv_w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=15)
        client_w.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await client_w.drain()
        await asyncio.gather(relay(client_r, srv_w), relay(srv_r, client_w))
    except Exception as e:
        logger.debug(f"handle error: {e}")
        try:
            client_w.close()
        except Exception:
            pass


async def main():
    port = int(os.getenv("PROXY_PORT", "3128"))
    # Слушаем ТОЛЬКО на Docker bridge (172.18.0.1) — недоступен из интернета.
    # Ранее был 0.0.0.0, что открывало открытый прокси для спамеров (инцидент 2026-06-25).
    bind_host = os.getenv("PROXY_HOST", "172.18.0.1")
    srv = await asyncio.start_server(handle, bind_host, port)
    logger.warning(f"tg_proxy: запуск на {bind_host}:{port}")
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
