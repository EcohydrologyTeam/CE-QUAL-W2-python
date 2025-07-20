#!/usr/bin/env python3
"""
Test script for advanced plotting functionality.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add path for cequalw2 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Import models
from models import DataModel, PlotConfiguration, PlotType, PlotStyle

def create_test_data():
    """Create comprehensive test data for plotting."""
    np.random.seed(42)
    
    # Create time series data
    n_points = 100
    time = np.linspace(0, 10, n_points)
    
    data = {
        'time': time,
        'temperature': 20 + 10 * np.sin(time) + np.random.normal(0, 2, n_points),
        'pressure': 1013 + 50 * np.cos(time * 0.5) + np.random.normal(0, 5, n_points),
        'humidity': 60 + 20 * np.sin(time * 1.2) + np.random.normal(0, 3, n_points),
        'wind_speed': 5 + 3 * np.abs(np.sin(time * 2)) + np.random.normal(0, 1, n_points),
        'dissolved_oxygen': 8 + 2 * np.sin(time * 0.8) + np.random.normal(0, 0.5, n_points),
        'ph': 7.2 + 0.5 * np.sin(time * 0.3) + np.random.normal(0, 0.1, n_points),
        'turbidity': np.abs(10 + 5 * np.sin(time * 1.5) + np.random.normal(0, 2, n_points)),
        'category': np.random.choice(['A', 'B', 'C'], n_points),
        'quality_score': np.random.randint(1, 101, n_points)
    }
    
    return pd.DataFrame(data)

def test_basic_plotting():
    """Test basic plotting functionality."""
    print("Testing Basic Plotting Functionality...")
    print("=" * 50)
    
    model = DataModel()
    model.df = create_test_data()
    
    print(f"Created test data with shape: {model.df.shape}")
    print(f"Columns: {list(model.df.columns)}")
    
    # Test plot recommendations
    print("\n1. Testing plot recommendations...")
    recommendations = model.get_plot_recommendations()
    
    for plot_type, columns in recommendations.items():
        print(f"   {plot_type}: {columns}")
    
    print("✓ Plot recommendations test completed")
    return model

def test_all_plot_types(model):
    """Test all available plot types."""
    print("\n" + "=" * 50)
    print("Testing All Plot Types...")
    print("=" * 50)
    
    # Test configurations for each plot type
    test_configs = [
        # Line Plot
        PlotConfiguration(
            plot_type=PlotType.LINE,
            y_columns=['temperature', 'pressure'],
            title='Temperature and Pressure Over Time',
            xlabel='Index',
            ylabel='Values',
            grid=True,
            legend=True
        ),
        
        # Scatter Plot
        PlotConfiguration(
            plot_type=PlotType.SCATTER,
            x_column='temperature',
            y_columns=['humidity'],
            title='Temperature vs Humidity',
            xlabel='Temperature',
            ylabel='Humidity',
            grid=True
        ),
        
        # Bar Plot
        PlotConfiguration(
            plot_type=PlotType.BAR,
            y_columns=['wind_speed'],
            title='Wind Speed Distribution',
            xlabel='Sample',
            ylabel='Wind Speed (m/s)',
            grid=True
        ),
        
        # Histogram
        PlotConfiguration(
            plot_type=PlotType.HISTOGRAM,
            y_columns=['dissolved_oxygen'],
            title='Dissolved Oxygen Distribution',
            xlabel='Dissolved Oxygen (mg/L)',
            ylabel='Frequency',
            grid=True
        ),
        
        # Box Plot
        PlotConfiguration(
            plot_type=PlotType.BOX,
            y_columns=['temperature', 'humidity', 'wind_speed'],
            title='Environmental Variables Distribution',
            ylabel='Values',
            grid=True
        ),
        
        # Area Plot
        PlotConfiguration(
            plot_type=PlotType.AREA,
            y_columns=['turbidity'],
            title='Turbidity Over Time (Area)',
            xlabel='Index',
            ylabel='Turbidity (NTU)',
            grid=True,
            alpha=0.7
        ),
        
        # Step Plot
        PlotConfiguration(
            plot_type=PlotType.STEP,
            y_columns=['ph'],
            title='pH Levels (Step Plot)',
            xlabel='Index',
            ylabel='pH',
            grid=True
        ),
        
        # Correlation Matrix
        PlotConfiguration(
            plot_type=PlotType.CORRELATION,
            title='Environmental Variables Correlation',
            grid=False
        ),
        
        # Heatmap
        PlotConfiguration(
            plot_type=PlotType.HEATMAP,
            title='Data Correlation Heatmap',
            grid=False
        )
    ]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\n{i}. Testing {config.plot_type.value.replace('_', ' ').title()} plot...")
        
        try:
            fig, ax = model.create_plot(config)
            print(f"   ✓ {config.plot_type.value} plot created successfully")
            
            # Clean up
            plt.close(fig)
            
        except Exception as e:
            print(f"   ✗ {config.plot_type.value} plot failed: {str(e)}")
    
    print("\n✓ All plot types test completed")

def test_plot_customization(model):
    """Test plot customization options."""
    print("\n" + "=" * 50)
    print("Testing Plot Customization...")
    print("=" * 50)
    
    # Test different styles
    styles = [PlotStyle.DEFAULT, PlotStyle.SEABORN, PlotStyle.CLASSIC, PlotStyle.GGPLOT]
    
    for i, style in enumerate(styles, 1):
        print(f"\n{i}. Testing {style.value} style...")
        
        config = PlotConfiguration(
            plot_type=PlotType.LINE,
            y_columns=['temperature'],
            title=f'Temperature Plot - {style.value} Style',
            style=style,
            grid=True
        )
        
        try:
            fig, ax = model.create_plot(config)
            print(f"   ✓ {style.value} style applied successfully")
            plt.close(fig)
        except Exception as e:
            print(f"   ✗ {style.value} style failed: {str(e)}")
    
    # Test color schemes
    print("\n5. Testing color schemes...")
    color_schemes = ['tab10', 'viridis', 'Set1', 'Pastel1']
    
    for scheme in color_schemes:
        config = PlotConfiguration(
            plot_type=PlotType.LINE,
            y_columns=['temperature', 'humidity', 'wind_speed'],
            title=f'Multi-line Plot - {scheme} Colors',
            color_scheme=scheme,
            legend=True
        )
        
        try:
            fig, ax = model.create_plot(config)
            print(f"   ✓ {scheme} color scheme applied successfully")
            plt.close(fig)
        except Exception as e:
            print(f"   ✗ {scheme} color scheme failed: {str(e)}")
    
    # Test advanced options
    print("\n6. Testing advanced options...")
    
    advanced_config = PlotConfiguration(
        plot_type=PlotType.SCATTER,
        x_column='temperature',
        y_columns=['humidity'],
        title='Advanced Scatter Plot',
        xlabel='Temperature (°C)',
        ylabel='Humidity (%)',
        figure_size=(10, 6),
        show_statistics=True,
        grid=True,
        alpha=0.7,
        marker_size=8.0
    )
    
    try:
        fig, ax = model.create_plot(advanced_config)
        print("   ✓ Advanced customization options applied successfully")
        plt.close(fig)
    except Exception as e:
        print(f"   ✗ Advanced customization failed: {str(e)}")
    
    print("\n✓ Plot customization test completed")

def test_error_handling(model):
    """Test error handling and edge cases."""
    print("\n" + "=" * 50)
    print("Testing Error Handling...")
    print("=" * 50)
    
    # Test with invalid column
    print("1. Testing invalid column...")
    config = PlotConfiguration(
        plot_type=PlotType.LINE,
        y_columns=['nonexistent_column'],
        title='Invalid Column Test'
    )
    
    try:
        fig, ax = model.create_plot(config)
        print("   ✗ Should have failed with invalid column")
        plt.close(fig)
    except Exception as e:
        print(f"   ✓ Correctly handled invalid column: {type(e).__name__}")
    
    # Test with empty data
    print("\n2. Testing empty data...")
    empty_model = DataModel()
    empty_model.df = pd.DataFrame()
    
    try:
        fig, ax = empty_model.create_plot(config)
        print("   ✗ Should have failed with empty data")
        plt.close(fig)
    except Exception as e:
        print(f"   ✓ Correctly handled empty data: {type(e).__name__}")
    
    # Test pie chart with multiple columns (should use only first)
    print("\n3. Testing pie chart with multiple columns...")
    pie_config = PlotConfiguration(
        plot_type=PlotType.PIE,
        y_columns=['quality_score'],
        title='Quality Score Distribution'
    )
    
    try:
        fig, ax = model.create_plot(pie_config)
        print("   ✓ Pie chart with single column handled correctly")
        plt.close(fig)
    except Exception as e:
        print(f"   ✗ Pie chart failed: {str(e)}")
    
    print("\n✓ Error handling test completed")

def test_performance(model):
    """Test performance with larger datasets."""
    print("\n" + "=" * 50)
    print("Testing Performance...")
    print("=" * 50)
    
    # Create larger dataset
    print("1. Creating large dataset (10,000 points)...")
    np.random.seed(42)
    large_data = {
        'x': np.linspace(0, 100, 10000),
        'y1': np.sin(np.linspace(0, 100, 10000)) + np.random.normal(0, 0.1, 10000),
        'y2': np.cos(np.linspace(0, 100, 10000)) + np.random.normal(0, 0.1, 10000),
        'y3': np.random.normal(0, 1, 10000).cumsum()
    }
    
    large_model = DataModel()
    large_model.df = pd.DataFrame(large_data)
    
    print(f"   Created dataset with shape: {large_model.df.shape}")
    
    # Test plotting performance
    import time
    
    config = PlotConfiguration(
        plot_type=PlotType.LINE,
        y_columns=['y1', 'y2', 'y3'],
        title='Performance Test - Large Dataset',
        legend=True,
        grid=True
    )
    
    print("\n2. Testing plot creation speed...")
    start_time = time.time()
    
    try:
        fig, ax = large_model.create_plot(config)
        end_time = time.time()
        
        print(f"   ✓ Large dataset plot created in {end_time - start_time:.3f} seconds")
        plt.close(fig)
        
    except Exception as e:
        print(f"   ✗ Large dataset plot failed: {str(e)}")
    
    print("\n✓ Performance test completed")

if __name__ == '__main__':
    print("Testing Advanced Plotting System")
    print("=" * 60)
    
    try:
        # Test basic functionality
        model = test_basic_plotting()
        
        # Test all plot types
        test_all_plot_types(model)
        
        # Test customization
        test_plot_customization(model)
        
        # Test error handling
        test_error_handling(model)
        
        # Test performance
        test_performance(model)
        
        print("\n" + "=" * 60)
        print("✓ All advanced plotting tests completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)