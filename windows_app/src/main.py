"""
NexRemote - Windows Application
Main entry point
"""
import sys
import asyncio
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
        
    def run(self):
        """Run the asyncio event loop"""
        asyncio.run(self.server.start())

def main():
    """Application entry point"""
    try:
        # Initialize Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("NexRemote")
        app.setOrganizationName("NeuralNexusStudios")
        
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
        
        # Execute application
        exit_code = app.exec()
        
        # Cleanup
        logger.info("Shutting down...")
        server.stop()
        server_thread.quit()
        server_thread.wait()
        
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()