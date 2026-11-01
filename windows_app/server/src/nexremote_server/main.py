"""Entry point: wires the database, certificate, protocol server and control API together."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import logging.handlers
import signal
import sys
import time

import psutil
import uvicorn

from nexremote_server import __version__
from nexremote_server.api.control import create_control_app
from nexremote_server.config import Config, parse_args
from nexremote_server.core.context import AppContext
from nexremote_server.core.server import EmbeddedServer, ServerManager
from nexremote_server.db.engine import EventLog, SettingsStore, TrustedDeviceStore, create_db_engine
from nexremote_server.db.legacy_import import import_legacy
from nexremote_server.net.certs import ensure_certificate

log = logging.getLogger("nexremote")
LOG_RETENTION_DAYS = 30


def setup_logging(config: Config) -> None:
    root = logging.getLogger()
    root.setLevel(config.log_level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        config.logs_dir / "nexremote.log", when="midnight", backupCount=LOG_RETENTION_DAYS, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    if sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(console)
    for noisy in ("uvicorn.error", "websockets", "comtypes"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def build_context(config: Config) -> AppContext:
    fresh_db = not config.db_path.exists()
    engine = create_db_engine(config.db_path)
    settings = SettingsStore(engine)
    trusted = TrustedDeviceStore(engine)
    if import_legacy(config.data_dir, settings, trusted, fresh_db):
        log.info("migrated data from the previous NexRemote host")
    cert = ensure_certificate(config.certs_dir)
    current = settings.current
    if (
        current.certificate_fingerprint != cert.fingerprint
        or current.certificate_thumbprint != cert.thumbprint
    ):
        settings.update(certificate_fingerprint=cert.fingerprint, certificate_thumbprint=cert.thumbprint)
    return AppContext(config, settings, trusted, EventLog(engine), cert)


async def _watch_parent(parent_pid: int, shutdown: asyncio.Event) -> None:
    while not shutdown.is_set():
        if not psutil.pid_exists(parent_pid):
            log.info("parent process %d exited; shutting down", parent_pid)
            shutdown.set()
            return
        await asyncio.sleep(2)


async def run(config: Config, parent_pid: int | None = None) -> None:
    ctx = build_context(config)
    manager = ServerManager(ctx)
    shutdown = asyncio.Event()

    control = EmbeddedServer(
        uvicorn.Config(
            create_control_app(ctx, manager, config.control_token, shutdown),
            host=config.control_host,
            port=config.control_port,
            lifespan="off",
            log_config=None,
            access_log=False,
            ws="websockets-sansio",
            ws_per_message_deflate=False,
        )
    )
    control_task = asyncio.create_task(control.serve())

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, ValueError):
            loop.add_signal_handler(sig, shutdown.set)
    if sys.platform == "win32":
        signal.signal(signal.SIGINT, lambda *_: loop.call_soon_threadsafe(shutdown.set))
    if parent_pid:
        asyncio.create_task(_watch_parent(parent_pid, shutdown))

    started_at = time.monotonic()
    while not control.started and not control_task.done():
        await asyncio.sleep(0.02)
    if control_task.done():
        raise SystemExit(f"control API could not bind 127.0.0.1:{config.control_port}")
    log.info(
        "NexRemote host %s ready (control API on %s:%d, data %s) in %.2fs",
        __version__, config.control_host, config.control_port, config.data_dir, time.monotonic() - started_at,
    )  # fmt: skip
    # Electron waits for this line on stdout before talking to the control API.
    print(f"NEXREMOTE_READY {config.control_port}", flush=True)

    if config.autostart_server:
        ok, reason = await manager.start()
        if not ok:
            log.info("protocol server not started: %s", reason)

    await shutdown.wait()
    log.info("shutting down")
    await manager.stop()
    control.should_exit = True
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(control_task, 5)


def cli(argv: list[str] | None = None) -> None:
    import argparse

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--parent-pid", type=int, default=None)
    known, rest = pre.parse_known_args(argv)
    config = parse_args(rest)
    config.ensure_dirs()
    setup_logging(config)
    try:
        asyncio.run(run(config, known.parent_pid))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
