"""Entry point for ClearView applications."""

import sys
from pathlib import Path


def main():
    """Launch ClearView PyQt6 GUI application."""
    # Add apps directory to path so we can import from it
    apps_dir = Path(__file__).parent.parent.parent.parent / "apps"
    sys.path.insert(0, str(apps_dir))
    
    from clearview.gui.main import main as gui_main
    gui_main()


def web_main():
    """Launch ClearView web application."""
    # Add apps directory to path so we can import from it
    apps_dir = Path(__file__).parent.parent.parent.parent / "apps"
    sys.path.insert(0, str(apps_dir))
    
    from clearview.web.main import main as web_main_func
    web_main_func()


if __name__ == "__main__":
    main()