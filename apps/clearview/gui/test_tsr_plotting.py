#!/usr/bin/env python3
"""Test script to verify TSR plotting functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import cequalw2 as w2

# Load the new TSR test data
tsr_file = "/Users/todd/GitHub/ecohydrology/CE-QUAL-W2-python/test/data/tsr_1_seg2.csv"
print(f"Loading TSR file: {tsr_file}")

df = pd.read_csv(tsr_file)
print(f"Loaded TSR data shape: {df.shape}")
print(f"Columns: {list(df.columns[:10])}...")  # Show first 10 columns

# Test the column picker logic - simulate what would be suggested
numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
print(f"Number of numeric columns: {len(numeric_columns)}")

# Simulate smart column suggestions
priority_terms = ['temp', 'temperature', 'ph', 'do', 'dissolved', 'oxygen', 
                 'turbidity', 'flow', 'depth', 'nitrate', 'phosphate', 't2', 'elws']

suggested_columns = []
for col in numeric_columns:
    col_lower = col.lower()
    for term in priority_terms:
        if term in col_lower and len(suggested_columns) < 6:
            suggested_columns.append(col)
            break

if len(suggested_columns) < 3:
    # Add first few columns if we don't have enough suggestions
    for col in numeric_columns[:5]:
        if col not in suggested_columns:
            suggested_columns.append(col)
            if len(suggested_columns) >= 5:
                break

print(f"Suggested columns: {suggested_columns}")

# Test plotting with suggested columns
filtered_data = df[suggested_columns]
print(f"Filtered data shape: {filtered_data.shape}")

# Test w2.multi_plot function
print("\nTesting w2.multi_plot with TSR data...")
try:
    fig = plt.figure(figsize=(12, 8))
    w2.multi_plot(filtered_data, fig=fig, figsize=(12, 8))
    print("✓ w2.multi_plot completed successfully")
    
    # Save the plot
    fig.savefig('test_tsr_plot_output.png', dpi=150, bbox_inches='tight')
    print("✓ Plot saved as test_tsr_plot_output.png")
    
except Exception as e:
    print(f"✗ Error in w2.multi_plot: {e}")
    
    # Try fallback matplotlib plotting
    print("Trying fallback matplotlib plotting...")
    try:
        fig.clear()
        num_subplots = len(suggested_columns)
        
        for i, col in enumerate(suggested_columns):
            ax = fig.add_subplot(num_subplots, 1, i+1)
            ax.plot(filtered_data.index, filtered_data[col], label=col)
            ax.set_ylabel(col)
            ax.grid(True)
            if i == len(suggested_columns) - 1:  # Last subplot
                ax.set_xlabel('Index')
        
        fig.tight_layout()
        fig.savefig('test_tsr_fallback_plot.png', dpi=150, bbox_inches='tight')
        print("✓ Fallback plot saved as test_tsr_fallback_plot.png")
        
    except Exception as e2:
        print(f"✗ Error in fallback plotting: {e2}")

plt.close(fig)

print(f"\n✓ TSR plotting test completed!")
print(f"Data summary:")
print(f"  - {df.shape[0]} time steps")
print(f"  - {df.shape[1]} total parameters")  
print(f"  - {len(numeric_columns)} numeric parameters")
print(f"  - {len(suggested_columns)} suggested for plotting")
print(f"This demonstrates how the Smart Plot feature handles large TSR datasets!")