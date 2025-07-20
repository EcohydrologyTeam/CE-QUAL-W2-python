#!/usr/bin/env python3
"""Test scientific notation conversion."""

import pandas as pd
import numpy as np

# Test the fallback loader logic
test_data = {
    'JDAY': [4384.000, 4385.000],
    'PO4': ['0.480E-01', '0.485E-01'],  # String scientific notation
}
df = pd.DataFrame(test_data)
print('Before conversion:')
print(df.dtypes)

# Apply the conversion logic
for col in df.columns:
    if col != df.columns[0]:
        try:
            df[col] = pd.to_numeric(df[col], errors='ignore')
        except Exception:
            pass

print('After conversion:')
print(df.dtypes)
print('Values:')
print(df)