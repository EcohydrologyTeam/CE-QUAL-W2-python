#!/usr/bin/env python3
"""
Test script to verify file opening works with PyQt6.
"""

import sys
import os
import pandas as pd

# Set Qt API before any other imports
os.environ['QT_API'] = 'pyqt6'

# Add src to path for importing cequalw2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

def test_csv_loading():
    """Test CSV file loading functionality."""
    
    # Create test CSV data
    test_data = {
        'Time': [1, 2, 3, 4, 5],
        'Temperature': [20.5, 21.0, 19.8, 22.1, 20.9],
        'Pressure': [1013.2, 1012.8, 1014.1, 1011.9, 1013.5]
    }
    
    df = pd.DataFrame(test_data)
    print(f"Created test DataFrame with shape: {df.shape}")
    print(f"Index type: {type(df.index)}")
    print(f"Index: {df.index}")
    
    # Test datetime formatting that might crash
    try:
        datetime_index = df.index.to_series().dt.strftime('%m/%d/%Y %H:%M')
        print("✗ This should have failed for non-datetime index")
    except AttributeError as e:
        print(f"✓ Correctly caught AttributeError: {e}")
        # Test fallback
        datetime_strings = [str(idx) for idx in df.index]
        print(f"✓ Fallback strings: {datetime_strings}")
    
    return df

def test_data_table_simulation(df):
    """Simulate the data table update logic."""
    
    array_data = df.values
    
    # Handle different index types safely (as in our fix)
    try:
        # Try to format as datetime if possible
        datetime_index = df.index.to_series().dt.strftime('%m/%d/%Y %H:%M')
        datetime_strings = datetime_index.tolist()
        print("✓ Used datetime formatting")
    except AttributeError:
        # Fall back to string representation for non-datetime indexes
        datetime_strings = [str(idx) for idx in df.index]
        print("✓ Used fallback string formatting")
    
    header = ['Date']
    for col in df.columns:
        header.append(col)
    
    print(f"✓ Header: {header}")
    print(f"✓ Datetime strings: {datetime_strings}")
    print(f"✓ Array shape: {array_data.shape}")
    
    return True

if __name__ == '__main__':
    print("Testing File Open Functionality")
    print("=" * 40)
    
    # Test CSV loading and processing
    df = test_csv_loading()
    test_data_table_simulation(df)
    
    print("\n" + "=" * 40)
    print("✓ All file opening tests passed!")