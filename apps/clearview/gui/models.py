"""
Data models for ClearView application.
Handles data loading, processing, and state management.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Add src to path for importing cequalw2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
import cequalw2 as w2


class FilterOperator(Enum):
    """Enumeration of filter operators."""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    NOT_NULL = "not_null"
    BETWEEN = "between"


@dataclass
class DataFilter:
    """Data structure for filter conditions."""
    column: str
    operator: FilterOperator
    value: Any = None
    value2: Any = None  # For BETWEEN operator
    case_sensitive: bool = True


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    row_count: int
    column_count: int
    missing_data_count: int
    duplicate_count: int


class DataModel:
    """Model class for managing CE-QUAL-W2 data."""
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.filename: str = ""
        self.model_year: Optional[int] = None
        self.recent_files: List[str] = []
        self._observers: List = []
    
    def add_observer(self, observer):
        """Add observer for data changes."""
        self._observers.append(observer)
    
    def notify_observers(self, event_type: str, **kwargs):
        """Notify all observers of data changes."""
        for observer in self._observers:
            if hasattr(observer, 'on_data_changed'):
                observer.on_data_changed(event_type, **kwargs)
    
    def load_file(self, file_path: str) -> bool:
        """
        Load data from various file formats.
        
        Args:
            file_path: Path to the data file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.csv':
                self.df = pd.read_csv(file_path)
            elif file_extension in ['.npt', '.opt']:
                self.df = w2.read(file_path)
            elif file_extension in ['.xls', '.xlsx']:
                self.df = self._load_excel_file(file_path)
            elif file_extension in ['.h5', '.hdf5']:
                self.df = self._load_hdf5_file(file_path)
            elif file_extension == '.nc':
                self.df = self._load_netcdf_file(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            self.filename = os.path.basename(file_path)
            self._extract_model_year()
            self._add_to_recent_files(file_path)
            
            self.notify_observers('data_loaded', file_path=file_path)
            return True
            
        except Exception as e:
            self.notify_observers('load_error', error=str(e), file_path=file_path)
            return False
    
    def _load_excel_file(self, file_path: str) -> pd.DataFrame:
        """Load data from Excel file with sheet selection support."""
        excel_file = pd.ExcelFile(file_path)
        
        if len(excel_file.sheet_names) == 1:
            return pd.read_excel(file_path, sheet_name=0)
        else:
            # For multiple sheets, load the first one by default
            # In a full implementation, we'd show a sheet selection dialog
            return pd.read_excel(file_path, sheet_name=0)
    
    def _load_hdf5_file(self, file_path: str) -> pd.DataFrame:
        """Load data from HDF5 file."""
        return pd.read_hdf(file_path, key='data')
    
    def _load_netcdf_file(self, file_path: str) -> pd.DataFrame:
        """Load data from NetCDF file."""
        import xarray as xr
        ds = xr.open_dataset(file_path)
        return ds.to_dataframe().reset_index()
    
    def _extract_model_year(self):
        """Extract model year from filename or data."""
        if self.filename:
            # Try to extract year from CSV filename
            parts = self.filename.split('_')
            for part in parts:
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                    if 1900 <= year <= 2100:
                        self.model_year = year
                        break
            
            # Try to extract from NPT filename
            if not self.model_year and 'npt' in self.filename.lower():
                for part in parts:
                    if part.isdigit() and len(part) == 4:
                        self.model_year = int(part)
                        break
    
    def _add_to_recent_files(self, file_path: str):
        """Add file to recent files list."""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]  # Keep only 10 recent files
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate and return data statistics."""
        if self.df is None or self.df.empty:
            return {}
        
        numeric_columns = self.df.select_dtypes(include=[np.number]).columns
        stats = {}
        
        for col in numeric_columns:
            if not self.df[col].isna().all():
                stats[col] = {
                    'count': self.df[col].count(),
                    'mean': self.df[col].mean(),
                    'std': self.df[col].std(),
                    'min': self.df[col].min(),
                    'max': self.df[col].max()
                }
        
        return stats
    
    def save_to_format(self, file_path: str, format_type: str) -> bool:
        """
        Save data to specified format.
        
        Args:
            file_path: Output file path
            format_type: Format type ('sqlite', 'hdf5', 'excel', 'csv')
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.df is None or self.df.empty:
            return False
        
        try:
            if format_type == 'sqlite':
                self._save_to_sqlite(file_path)
            elif format_type == 'hdf5':
                self._save_to_hdf5(file_path)
            elif format_type == 'excel':
                self._save_to_excel(file_path)
            elif format_type == 'csv':
                self._save_to_csv(file_path)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            self.notify_observers('data_saved', file_path=file_path, format=format_type)
            return True
            
        except Exception as e:
            self.notify_observers('save_error', error=str(e), file_path=file_path)
            return False
    
    def _save_to_sqlite(self, file_path: str):
        """Save dataframe to SQLite database."""
        with sqlite3.connect(file_path) as conn:
            self.df.to_sql('data', conn, if_exists='replace', index=False)
    
    def _save_to_hdf5(self, file_path: str):
        """Save dataframe to HDF5 format."""
        self.df.to_hdf(file_path, key='data', mode='w', complevel=9, complib='zlib')
    
    def _save_to_excel(self, file_path: str):
        """Save dataframe to Excel format."""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            self.df.to_excel(writer, sheet_name='Data', index=False)
    
    def _save_to_csv(self, file_path: str):
        """Save dataframe to CSV format."""
        self.df.to_csv(file_path, index=False)
    
    def update_cell_value(self, row: int, col: int, value: Any):
        """Update a specific cell value in the dataframe."""
        if self.df is not None and 0 <= row < len(self.df) and 0 <= col < len(self.df.columns):
            self.df.iloc[row, col] = value
            self.notify_observers('cell_updated', row=row, col=col, value=value)
    
    def set_year(self, year: int):
        """Set the model year."""
        self.model_year = year
        self.notify_observers('year_updated', year=year)
    
    def set_filename(self, filename: str):
        """Set the filename."""
        self.filename = filename
        self.notify_observers('filename_updated', filename=filename)
    
    # Data Validation Methods
    def validate_data(self) -> ValidationResult:
        """
        Comprehensive data validation.
        
        Returns:
            ValidationResult: Validation results with issues and warnings
        """
        if self.df is None or self.df.empty:
            return ValidationResult(
                is_valid=False,
                issues=["No data loaded"],
                warnings=[],
                row_count=0,
                column_count=0,
                missing_data_count=0,
                duplicate_count=0
            )
        
        issues = []
        warnings = []
        
        # Basic data checks
        row_count = len(self.df)
        column_count = len(self.df.columns)
        missing_data_count = self.df.isnull().sum().sum()
        duplicate_count = self.df.duplicated().sum()
        
        # Check for empty dataframe
        if row_count == 0:
            issues.append("Dataframe is empty (no rows)")
        
        if column_count == 0:
            issues.append("Dataframe has no columns")
        
        # Check for missing data
        if missing_data_count > 0:
            missing_percentage = (missing_data_count / (row_count * column_count)) * 100
            if missing_percentage > 50:
                issues.append(f"Excessive missing data: {missing_percentage:.1f}% of all values")
            elif missing_percentage > 10:
                warnings.append(f"Significant missing data: {missing_percentage:.1f}% of all values")
            else:
                warnings.append(f"Missing data detected: {missing_data_count} values ({missing_percentage:.1f}%)")
        
        # Check for duplicate rows
        if duplicate_count > 0:
            duplicate_percentage = (duplicate_count / row_count) * 100
            if duplicate_percentage > 25:
                issues.append(f"Excessive duplicate rows: {duplicate_count} ({duplicate_percentage:.1f}%)")
            else:
                warnings.append(f"Duplicate rows detected: {duplicate_count} ({duplicate_percentage:.1f}%)")
        
        # Check column data types and values
        for col in self.df.columns:
            col_data = self.df[col]
            
            # Check for columns with all null values
            if col_data.isnull().all():
                warnings.append(f"Column '{col}' contains only null values")
            
            # Check for columns with single unique value
            elif col_data.nunique() == 1 and not col_data.isnull().all():
                warnings.append(f"Column '{col}' has only one unique value")
            
            # Check numeric columns for outliers
            if pd.api.types.is_numeric_dtype(col_data):
                self._check_numeric_outliers(col, col_data, warnings)
        
        # Check for potential datetime columns
        self._check_datetime_columns(warnings)
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            row_count=row_count,
            column_count=column_count,
            missing_data_count=missing_data_count,
            duplicate_count=duplicate_count
        )
    
    def _check_numeric_outliers(self, col_name: str, col_data: pd.Series, warnings: List[str]):
        """Check for outliers in numeric columns using IQR method."""
        try:
            clean_data = col_data.dropna()
            if len(clean_data) < 10:  # Need sufficient data for outlier detection
                return
            
            Q1 = clean_data.quantile(0.25)
            Q3 = clean_data.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = clean_data[(clean_data < lower_bound) | (clean_data > upper_bound)]
            
            if len(outliers) > 0:
                outlier_percentage = (len(outliers) / len(clean_data)) * 100
                if outlier_percentage > 10:
                    warnings.append(f"Column '{col_name}' has {len(outliers)} outliers ({outlier_percentage:.1f}%)")
        except Exception:
            pass  # Skip outlier detection if it fails
    
    def _check_datetime_columns(self, warnings: List[str]):
        """Check for columns that might be datetime but aren't properly typed."""
        for col in self.df.columns:
            if not pd.api.types.is_datetime64_any_dtype(self.df[col]):
                # Check if column looks like it could be datetime
                sample_values = self.df[col].dropna().astype(str).head(10)
                datetime_like_count = 0
                
                for value in sample_values:
                    if self._looks_like_datetime(value):
                        datetime_like_count += 1
                
                if datetime_like_count >= 5:  # If at least half look like datetime
                    warnings.append(f"Column '{col}' may contain datetime data but is not datetime type")
    
    def _looks_like_datetime(self, value: str) -> bool:
        """Check if a string value looks like a datetime."""
        try:
            pd.to_datetime(value)
            return True
        except (ValueError, TypeError):
            return False
    
    # Data Filtering Methods
    def apply_filters(self, filters: List[DataFilter]) -> pd.DataFrame:
        """
        Apply multiple filters to the data.
        
        Args:
            filters: List of DataFilter objects
            
        Returns:
            pd.DataFrame: Filtered dataframe
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        
        filtered_df = self.df.copy()
        
        for filter_obj in filters:
            filtered_df = self._apply_single_filter(filtered_df, filter_obj)
        
        return filtered_df
    
    def _apply_single_filter(self, df: pd.DataFrame, filter_obj: DataFilter) -> pd.DataFrame:
        """Apply a single filter to the dataframe."""
        if filter_obj.column not in df.columns:
            return df
        
        col_data = df[filter_obj.column]
        
        try:
            if filter_obj.operator == FilterOperator.EQUALS:
                mask = col_data == filter_obj.value
            elif filter_obj.operator == FilterOperator.NOT_EQUALS:
                mask = col_data != filter_obj.value
            elif filter_obj.operator == FilterOperator.GREATER_THAN:
                mask = col_data > filter_obj.value
            elif filter_obj.operator == FilterOperator.GREATER_EQUAL:
                mask = col_data >= filter_obj.value
            elif filter_obj.operator == FilterOperator.LESS_THAN:
                mask = col_data < filter_obj.value
            elif filter_obj.operator == FilterOperator.LESS_EQUAL:
                mask = col_data <= filter_obj.value
            elif filter_obj.operator == FilterOperator.CONTAINS:
                if filter_obj.case_sensitive:
                    mask = col_data.astype(str).str.contains(str(filter_obj.value), na=False)
                else:
                    mask = col_data.astype(str).str.contains(str(filter_obj.value), case=False, na=False)
            elif filter_obj.operator == FilterOperator.STARTS_WITH:
                if filter_obj.case_sensitive:
                    mask = col_data.astype(str).str.startswith(str(filter_obj.value), na=False)
                else:
                    mask = col_data.astype(str).str.lower().str.startswith(str(filter_obj.value).lower(), na=False)
            elif filter_obj.operator == FilterOperator.ENDS_WITH:
                if filter_obj.case_sensitive:
                    mask = col_data.astype(str).str.endswith(str(filter_obj.value), na=False)
                else:
                    mask = col_data.astype(str).str.lower().str.endswith(str(filter_obj.value).lower(), na=False)
            elif filter_obj.operator == FilterOperator.IS_NULL:
                mask = col_data.isnull()
            elif filter_obj.operator == FilterOperator.NOT_NULL:
                mask = col_data.notnull()
            elif filter_obj.operator == FilterOperator.BETWEEN:
                mask = (col_data >= filter_obj.value) & (col_data <= filter_obj.value2)
            else:
                return df  # Unknown operator, return unchanged
            
            return df[mask]
            
        except Exception:
            return df  # If filter fails, return unchanged data
    
    def get_column_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about each column.
        
        Returns:
            Dict: Column information including data types, unique values, etc.
        """
        if self.df is None or self.df.empty:
            return {}
        
        column_info = {}
        
        for col in self.df.columns:
            col_data = self.df[col]
            
            info = {
                'data_type': str(col_data.dtype),
                'non_null_count': col_data.count(),
                'null_count': col_data.isnull().sum(),
                'unique_count': col_data.nunique(),
                'memory_usage': col_data.memory_usage(deep=True)
            }
            
            # Add type-specific information
            if pd.api.types.is_numeric_dtype(col_data):
                clean_data = col_data.dropna()
                if len(clean_data) > 0:
                    info.update({
                        'min_value': clean_data.min(),
                        'max_value': clean_data.max(),
                        'mean_value': clean_data.mean(),
                        'std_value': clean_data.std(),
                        'median_value': clean_data.median()
                    })
            elif pd.api.types.is_string_dtype(col_data) or col_data.dtype == 'object':
                clean_data = col_data.dropna().astype(str)
                if len(clean_data) > 0:
                    info.update({
                        'max_length': clean_data.str.len().max(),
                        'min_length': clean_data.str.len().min(),
                        'avg_length': clean_data.str.len().mean()
                    })
            
            # Sample of unique values (up to 10)
            unique_values = col_data.dropna().unique()
            if len(unique_values) <= 10:
                info['sample_values'] = list(unique_values)
            else:
                info['sample_values'] = list(unique_values[:10])
            
            column_info[col] = info
        
        return column_info
    
    def remove_duplicates(self, subset: Optional[List[str]] = None, keep: str = 'first') -> bool:
        """
        Remove duplicate rows from the dataframe.
        
        Args:
            subset: Columns to consider for duplicate detection
            keep: Which duplicates to keep ('first', 'last', False)
            
        Returns:
            bool: True if duplicates were removed
        """
        if self.df is None or self.df.empty:
            return False
        
        initial_count = len(self.df)
        self.df = self.df.drop_duplicates(subset=subset, keep=keep)
        final_count = len(self.df)
        
        if final_count < initial_count:
            removed_count = initial_count - final_count
            self.notify_observers('duplicates_removed', count=removed_count)
            return True
        
        return False
    
    def handle_missing_data(self, method: str = 'drop', columns: Optional[List[str]] = None, 
                           fill_value: Any = None) -> bool:
        """
        Handle missing data in the dataframe.
        
        Args:
            method: Method to handle missing data ('drop', 'fill', 'interpolate')
            columns: Specific columns to process (None for all)
            fill_value: Value to use for filling (for 'fill' method)
            
        Returns:
            bool: True if data was modified
        """
        if self.df is None or self.df.empty:
            return False
        
        initial_missing = self.df.isnull().sum().sum()
        if initial_missing == 0:
            return False
        
        if columns is None:
            target_df = self.df
        else:
            target_df = self.df[columns]
        
        try:
            if method == 'drop':
                self.df = self.df.dropna(subset=columns)
            elif method == 'fill':
                if fill_value is not None:
                    if columns is None:
                        self.df = self.df.fillna(fill_value)
                    else:
                        self.df[columns] = self.df[columns].fillna(fill_value)
                else:
                    # Use column-specific defaults
                    for col in (columns or self.df.columns):
                        if pd.api.types.is_numeric_dtype(self.df[col]):
                            self.df[col] = self.df[col].fillna(self.df[col].median())
                        else:
                            self.df[col] = self.df[col].fillna('Unknown')
            elif method == 'interpolate':
                if columns is None:
                    numeric_cols = self.df.select_dtypes(include=[np.number]).columns
                    self.df[numeric_cols] = self.df[numeric_cols].interpolate()
                else:
                    for col in columns:
                        if pd.api.types.is_numeric_dtype(self.df[col]):
                            self.df[col] = self.df[col].interpolate()
            
            final_missing = self.df.isnull().sum().sum()
            if final_missing != initial_missing:
                handled_count = initial_missing - final_missing
                self.notify_observers('missing_data_handled', 
                                    method=method, count=handled_count)
                return True
                
        except Exception as e:
            self.notify_observers('error', message=f"Error handling missing data: {str(e)}")
        
        return False