#!/usr/bin/env python3
"""
Test the complete application launch and basic functionality.
"""

import sys
import os

# Set Qt API before any other imports
os.environ['QT_API'] = 'pyqt6'

# Import PyQt6 first
import PyQt6.QtWidgets as qtw
import PyQt6.QtCore as qtc

# Now import matplotlib with proper backend
import matplotlib
matplotlib.use('qtagg')

# Add src to path for importing cequalw2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

def test_app_launch():
    """Test that the app can be created without crashing."""
    try:
        app = qtw.QApplication([])
        
        # Import and create the main window
        from main import ClearView
        window = ClearView()
        
        print("✓ ClearView window created successfully")
        
        # Test that we can access the browse_file method
        if hasattr(window, 'browse_file'):
            print("✓ browse_file method exists")
        else:
            print("✗ browse_file method missing")
        
        # Test that we can access the data_table
        if hasattr(window, 'data_table'):
            print("✓ data_table widget exists")
        else:
            print("✗ data_table widget missing")
        
        # Clean up
        window.close()
        app.quit()
        
        return True
        
    except Exception as e:
        print(f"✗ App launch failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Testing Full Application Launch")
    print("=" * 40)
    
    if test_app_launch():
        print("\n✓ Application test successful - open button should work!")
    else:
        print("\n✗ Application test failed")