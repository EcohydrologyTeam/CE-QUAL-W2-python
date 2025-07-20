#!/usr/bin/env python3
"""
Simple test of MVC components without PyQt5 dependencies.
"""

import sys
import os

# Add path for cequalw2 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

def test_data_model():
    """Test DataModel class."""
    from models import DataModel
    
    model = DataModel()
    print("✓ DataModel imported and instantiated successfully")
    
    # Test basic properties
    assert model.df is None
    assert model.filename == ""
    assert model.model_year is None
    assert model.recent_files == []
    print("✓ DataModel initial state verified")

def test_imports():
    """Test that MVC modules can be imported."""
    try:
        import models
        print("✓ models module imported successfully")
        
        # Test cequalw2 import
        import cequalw2 as w2
        print("✓ cequalw2 module imported successfully")
        print(f"Available functions: {[name for name in dir(w2) if not name.startswith('_')]}")
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("Testing MVC structure...")
    
    if test_imports():
        test_data_model()
        print("\n✓ All MVC tests passed!")
    else:
        print("\n✗ Tests failed")
        sys.exit(1)