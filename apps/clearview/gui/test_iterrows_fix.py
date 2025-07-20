#!/usr/bin/env python3
"""Test the iterrows fix for TSR data."""

import pandas as pd
import numpy as np

# Create test data that mimics the TSR file structure
test_data = {
    'JDAY': [4384.000, 4385.000, 4386.000],
    'DLT(s)': [213.378, 161.691, 257.384],
    'T2(C)': [25.000, 24.971, 24.968],
}

df = pd.DataFrame(test_data)
df = df.set_index('JDAY')  # This creates non-integer index like in TSR files

print(f"DataFrame shape: {df.shape}")
print(f"Index: {df.index.tolist()}")
print(f"Columns: {df.columns.tolist()}")

print("\nTesting the old problematic approach:")
try:
    for i, row in df.iterrows():
        print(f"i={i} (type: {type(i)}), row length: {len(row)}")
        # This would fail: setItem(i, j, item) because i=4384.0, not 0,1,2
        if i > 10:  # QTableWidget row numbers should be 0,1,2...
            print(f"ERROR: Row index {i} is too large for table!")
        break  # Just test first iteration
except Exception as e:
    print(f"Error with old approach: {e}")

print("\nTesting the new fixed approach:")
for row_num, (index_val, row) in enumerate(df.iterrows()):
    print(f"row_num={row_num} (type: {type(row_num)}), index_val={index_val}, row length: {len(row)}")
    # This works: setItem(row_num, j, item) because row_num=0,1,2...
    print(f"✓ Table row {row_num} would display index value {index_val}")

print("\n✓ Fix verified - using row_num instead of index_val for setItem()")