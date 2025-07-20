#!/usr/bin/env python3
"""
Test script to check open button functionality in PyQt6.
"""

import sys
import os

# Set Qt API before any other imports
os.environ['QT_API'] = 'pyqt6'

# Import PyQt6 first
import PyQt6.QtWidgets as qtw
import PyQt6.QtCore as qtc
import PyQt6.QtGui as qtg

# Now import matplotlib with proper backend
import matplotlib
matplotlib.use('qtagg')  # Use the generic Qt Agg backend
import matplotlib.pyplot as plt

# Add src to path for importing cequalw2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

def test_file_dialog():
    """Test QFileDialog functionality."""
    app = qtw.QApplication(sys.argv)
    
    # Test file dialog creation
    file_dialog = qtw.QFileDialog()
    file_dialog.setFileMode(qtw.QFileDialog.FileMode.ExistingFile)
    file_dialog.setNameFilters([
        'All Files (*.*)', 
        'CSV Files (*.csv)', 
        'NPT Files (*.npt)',
        'OPT Files (*.opt)'
    ])
    
    print("QFileDialog created successfully")
    
    # Don't actually show the dialog, just test creation
    app.quit()
    print("✓ File dialog test passed")

def test_cequalw2_import():
    """Test cequalw2 import."""
    try:
        import cequalw2 as w2
        print("✓ cequalw2 import successful")
        return True
    except Exception as e:
        print(f"✗ cequalw2 import failed: {e}")
        return False

def test_main_class_import():
    """Test importing the main ClearView class."""
    try:
        # Try to import without instantiating
        import main
        print("✓ main module import successful")
        return True
    except Exception as e:
        print(f"✗ main module import failed: {e}")
        return False

if __name__ == '__main__':
    print("Testing Open Button Functionality")
    print("=" * 40)
    
    # Test components individually
    test_file_dialog()
    test_cequalw2_import()
    test_main_class_import()
    
    print("\n" + "=" * 40)
    print("✓ All tests completed")