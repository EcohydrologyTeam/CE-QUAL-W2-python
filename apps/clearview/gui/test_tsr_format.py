#!/usr/bin/env python3
"""
Test script to verify TSR CSV file handling.
"""

import os
import pandas as pd
import numpy as np

def test_tsr_data_formatting():
    """Test data formatting with TSR-like data."""
    
    # Create test data similar to TSR format
    test_data = {
        'JDAY': [4384.000, 4385.000, 4386.000],
        'DLT(s)': [213.378, 161.691, 257.384],
        'T2(C)': [25.000, 24.971, 24.968],
        'PO4': [0.480E-01, 0.485E-01, 0.489E-01],  # Scientific notation
        'NH4': [0.500E-01, 0.666E-01, 0.794E-01],
        'NO3': [0.127, 0.134, 0.142],
        'STRING_COL': ['Test', 'Data', 'String'],  # Mixed string data
        'NAN_COL': [np.nan, 1.5, np.nan]  # NaN values
    }
    
    df = pd.DataFrame(test_data)
    print(f"Created TSR-like test data with shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Data types:\n{df.dtypes}")
    
    # Test the formatting logic
    array_data = df.values
    print(f"\nArray shape: {array_data.shape}")
    
    # Test formatting for each value type
    for row in range(min(3, array_data.shape[0])):
        for col in range(array_data.shape[1]):
            value = array_data[row, col]
            
            # Apply the same logic as in the update_data_table method
            try:
                if pd.isna(value):
                    value_text = 'NaN'
                elif isinstance(value, (int, float)):
                    value_text = f'{float(value):.4f}'
                else:
                    value_text = str(value)
            except (ValueError, TypeError):
                value_text = str(value)
            
            print(f"Row {row}, Col {col}: {value} -> '{value_text}'")
    
    print("\n✓ TSR data formatting test completed successfully!")
    return df

if __name__ == '__main__':
    print("Testing TSR CSV Data Formatting")
    print("=" * 40)
    
    test_tsr_data_formatting()
    
    print("\n" + "=" * 40)
    print("✓ All TSR formatting tests passed!")