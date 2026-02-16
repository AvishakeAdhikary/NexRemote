"""
NexRemote - Windows Application
Main entry point
"""
import sys
import os
import asyncio
import signal
import atexit
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread
from ui.main_window import MainWindow
from core.server import NexRemoteServer
from utils.logger import setup_logger
from utils.config import Config
from security.firewall_config import configure_firewall

logger = setup_logger()

class ServerThread(QThread):
    """Thread to run async server"""
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.loop = None
        
    def run(self):
        """Run the asyncio event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.server.start())
        except asyncio.CancelledError:
            pass
        finally:
            # Cancel all remaining tasks
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            # Let cancelled tasks finish
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()
    
    def stop(self):
        """Stop the asyncio event loop from another thread"""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

def main():
    """Application entry point"""
    try:
        # Initialize Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("NexRemote")
        app.setOrganizationName("NeuralNexusStudios")
        
        # Prevent Qt from keeping the app alive if all windows are hidden
        app.setQuitOnLastWindowClosed(False)
        
        # Load configuration
        config = Config()
        
        # Configure Windows Firewall
        logger.info("Configuring firewall rules...")
        if not configure_firewall():
            logger.warning("Failed to configure firewall automatically. Manual configuration may be needed.")
        
        # Initialize server
        server = NexRemoteServer(config)
        
        # Create main window
        main_window = MainWindow(server, config)
        main_window.show()
        
        # Start server in separate thread
        server_thread = ServerThread(server)
        server_thread.start()
        
        logger.info("Application started successfully")
        
        # Register cleanup
        def cleanup():
            logger.info("Shutting down...")
            server.stop()
            server_thread.stop()
            server_thread.quit()
            if not server_thread.wait(5000):  # 5 second timeout
                logger.warning("Server thread did not stop in time, terminating")
                server_thread.terminate()
                server_thread.wait(2000)
        
        atexit.register(cleanup)
        app.aboutToQuit.connect(cleanup)
        
        # Execute application
        exit_code = app.exec()
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        os._exit(1)

if __name__ == "__main__":
    main()