#!/usr/bin/env python3
"""Test script to debug the plot issue."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import cequalw2 as w2

# Load test data
df = pd.read_csv('test_data.csv')
print(f"Loaded data shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"Data:\n{df}")

# Test the w2.multi_plot function
print("\nTesting w2.multi_plot function...")

try:
    # Create a figure
    fig = plt.figure(figsize=(10, 6))
    
    # Test with just numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    print(f"Numeric columns: {numeric_cols}")
    
    if numeric_cols:
        filtered_data = df[numeric_cols]
        print(f"Filtered data shape: {filtered_data.shape}")
        print(f"Filtered data:\n{filtered_data}")
        
        # Call w2.multi_plot
        w2.multi_plot(filtered_data, fig=fig, figsize=(10, 6))
        print("w2.multi_plot completed successfully")
        
        # Save the plot to see if it worked
        fig.savefig('test_plot_output.png')
        print("Plot saved as test_plot_output.png")
    else:
        print("No numeric columns found")
        
except Exception as e:
    print(f"Error in w2.multi_plot: {e}")
    import traceback
    traceback.print_exc()

plt.close(fig)