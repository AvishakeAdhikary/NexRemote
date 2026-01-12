"""
NexRemote - Windows Application
Main entry point
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from utils.logger import setup_logger

def main():
    # Set up logging
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Starting NexRemote - Windows Application")
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("NexRemote")
    app.setOrganizationName("Neural Nexus Studios")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()