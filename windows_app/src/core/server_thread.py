"""
ServerThread — runs the asyncio NexRemoteServer in a dedicated QThread.
Extracted from main.py to avoid circular imports.
"""
import asyncio
import logging
from PyQt6.QtCore import QThread

logger = logging.getLogger(__name__)


class ServerThread(QThread):
    """Thread to run async server. Owned by MainWindow for start/stop control."""

    def __init__(self, server):
        super().__init__()
        self.server = server
        self.loop: asyncio.AbstractEventLoop | None = None

    def run(self):
        """Run the asyncio event loop — exits cleanly when loop.stop() is called."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.server.start())
        except (asyncio.CancelledError, RuntimeError) as e:
            # RuntimeError('Event loop stopped before Future completed.') is the
            # expected outcome when stop() calls loop.stop() externally.
            # Don't log it as an error — it's intentional.
            if "Event loop stopped before Future completed" not in str(e):
                logger.error(f"Server loop error: {e}", exc_info=True)
        finally:
            self._drain_and_close()

    def _drain_and_close(self):
        """Cancel all pending tasks and close the loop cleanly."""
        try:
            # Collect all tasks still attached to this loop
            pending = asyncio.all_tasks(self.loop)
            if pending:
                for task in pending:
                    task.cancel()
                # Run the loop briefly so cancelled tasks can clean up
                # (they raise CancelledError and release resources)
                self.loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        except Exception as e:
            logger.debug(f"Task drain warning (non-fatal): {e}")
        finally:
            try:
                self.loop.close()
            except Exception:
                pass

    def stop(self):
        """
        Signal the asyncio event loop to stop from the Qt/main thread.
        After this, run_until_complete raises RuntimeError which we catch in run().
        """
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
