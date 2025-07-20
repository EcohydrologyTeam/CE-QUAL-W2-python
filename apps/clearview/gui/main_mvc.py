"""
ClearView application with MVC architecture.

This is the main entry point for the refactored ClearView application
that uses a clean Model-View-Controller architecture for better
maintainability and extensibility.
"""

import sys
import os
import PyQt6.QtWidgets as qtw
import PyQt6.QtCore as qtc

from controllers import ClearViewController


def main():
    """Main application entry point."""
    app = qtw.QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName('ClearView')
    app.setApplicationVersion('2.0.0')
    app.setOrganizationName('ERDC')
    app.setOrganizationDomain('erdc.usace.army.mil')
    
    # Create and show controller (which creates model and view)
    controller = ClearViewController()
    controller.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()