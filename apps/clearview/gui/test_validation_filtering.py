#!/usr/bin/env python3
"""
Test script for data validation and filtering functionality.
"""

import sys
import os
import pandas as pd
import numpy as np

# Add path for cequalw2 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Import models
from models import DataModel, ValidationResult, FilterOperator, DataFilter

def test_validation_features():
    """Test data validation functionality."""
    
    print("Testing Data Validation Features...")
    print("=" * 50)
    
    # Create test data with various issues
    test_data = {
        'id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'name': ['Alice', 'Bob', 'Charlie', None, 'Eve', 'Alice', 'Grace', '', 'Ivan', 'Jane'],
        'age': [25, 30, np.nan, 35, 40, 25, 45, 50, 1000, 22],  # Has missing value and outlier
        'score': [85.5, 92.0, 78.5, np.nan, 95.0, 85.5, 88.0, 91.5, 87.0, 90.0],
        'date_str': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                     '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10'],
        'constant': [100] * 10,  # Column with single value
        'all_null': [None] * 10   # Column with all null values
    }
    
    df = pd.DataFrame(test_data)
    
    # Add duplicate row
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    
    model = DataModel()
    model.df = df
    
    # Test validation
    print("1. Testing data validation...")
    validation_result = model.validate_data()
    
    print(f"   Valid: {validation_result.is_valid}")
    print(f"   Rows: {validation_result.row_count}")
    print(f"   Columns: {validation_result.column_count}")
    print(f"   Missing values: {validation_result.missing_data_count}")
    print(f"   Duplicate rows: {validation_result.duplicate_count}")
    print(f"   Issues: {len(validation_result.issues)}")
    print(f"   Warnings: {len(validation_result.warnings)}")
    
    if validation_result.issues:
        print("   Issues found:")
        for issue in validation_result.issues:
            print(f"     - {issue}")
    
    if validation_result.warnings:
        print("   Warnings found:")
        for warning in validation_result.warnings:
            print(f"     - {warning}")
    
    print("✓ Data validation test completed")
    
    # Test column information
    print("\n2. Testing column information...")
    column_info = model.get_column_info()
    
    for col_name, info in column_info.items():
        print(f"   {col_name}: {info['data_type']}, {info['non_null_count']} non-null, "
              f"{info['unique_count']} unique")
    
    print("✓ Column information test completed")
    
    return model

def test_filtering_features(model):
    """Test data filtering functionality."""
    print("\n" + "=" * 50)
    print("Testing Data Filtering Features...")
    print("=" * 50)
    
    if model.df is None:
        print("No data available for filtering tests")
        return
    
    print(f"Original data shape: {model.df.shape}")
    
    # Test 1: Simple equality filter
    print("\n1. Testing equality filter (age = 25)...")
    filters = [DataFilter(column='age', operator=FilterOperator.EQUALS, value=25)]
    filtered_df = model.apply_filters(filters)
    print(f"   Filtered shape: {filtered_df.shape}")
    print(f"   Filtered ages: {list(filtered_df['age'].unique())}")
    
    # Test 2: Greater than filter
    print("\n2. Testing greater than filter (age > 30)...")
    filters = [DataFilter(column='age', operator=FilterOperator.GREATER_THAN, value=30)]
    filtered_df = model.apply_filters(filters)
    print(f"   Filtered shape: {filtered_df.shape}")
    print(f"   Filtered ages: {sorted(filtered_df['age'].dropna().tolist())}")
    
    # Test 3: Between filter
    print("\n3. Testing between filter (age between 25 and 40)...")
    filters = [DataFilter(column='age', operator=FilterOperator.BETWEEN, value=25, value2=40)]
    filtered_df = model.apply_filters(filters)
    print(f"   Filtered shape: {filtered_df.shape}")
    print(f"   Filtered ages: {sorted(filtered_df['age'].dropna().tolist())}")
    
    # Test 4: String contains filter
    print("\n4. Testing contains filter (name contains 'a')...")
    filters = [DataFilter(column='name', operator=FilterOperator.CONTAINS, value='a', case_sensitive=False)]
    filtered_df = model.apply_filters(filters)
    print(f"   Filtered shape: {filtered_df.shape}")
    print(f"   Filtered names: {list(filtered_df['name'].dropna().unique())}")
    
    # Test 5: Null filter
    print("\n5. Testing null filter (age is null)...")
    filters = [DataFilter(column='age', operator=FilterOperator.IS_NULL)]
    filtered_df = model.apply_filters(filters)
    print(f"   Filtered shape: {filtered_df.shape}")
    
    # Test 6: Multiple filters (AND operation)
    print("\n6. Testing multiple filters (age > 25 AND score >= 85)...")
    filters = [
        DataFilter(column='age', operator=FilterOperator.GREATER_THAN, value=25),
        DataFilter(column='score', operator=FilterOperator.GREATER_EQUAL, value=85)
    ]
    filtered_df = model.apply_filters(filters)
    print(f"   Filtered shape: {filtered_df.shape}")
    
    print("✓ Data filtering tests completed")

def test_data_cleaning_features(model):
    """Test data cleaning functionality."""
    print("\n" + "=" * 50)
    print("Testing Data Cleaning Features...")
    print("=" * 50)
    
    if model.df is None:
        print("No data available for cleaning tests")
        return
    
    # Test duplicate removal
    print("1. Testing duplicate removal...")
    initial_shape = model.df.shape
    print(f"   Initial shape: {initial_shape}")
    
    success = model.remove_duplicates()
    final_shape = model.df.shape
    print(f"   Final shape: {final_shape}")
    print(f"   Duplicates removed: {success}")
    
    # Test missing data handling - fill method
    print("\n2. Testing missing data handling (fill method)...")
    initial_missing = model.df.isnull().sum().sum()
    print(f"   Initial missing values: {initial_missing}")
    
    # Make a copy to test different methods
    original_df = model.df.copy()
    
    success = model.handle_missing_data(method='fill')
    final_missing = model.df.isnull().sum().sum()
    print(f"   Final missing values: {final_missing}")
    print(f"   Missing data handled: {success}")
    
    # Restore original data and test interpolation
    model.df = original_df.copy()
    print("\n3. Testing missing data handling (interpolate method)...")
    initial_missing = model.df.isnull().sum().sum()
    print(f"   Initial missing values: {initial_missing}")
    
    success = model.handle_missing_data(method='interpolate')
    final_missing = model.df.isnull().sum().sum()
    print(f"   Final missing values: {final_missing}")
    print(f"   Missing data handled: {success}")
    
    print("✓ Data cleaning tests completed")

if __name__ == '__main__':
    print("Testing Data Validation and Filtering System")
    print("=" * 60)
    
    try:
        # Test validation features
        model = test_validation_features()
        
        # Test filtering features
        test_filtering_features(model)
        
        # Test data cleaning features
        test_data_cleaning_features(model)
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)