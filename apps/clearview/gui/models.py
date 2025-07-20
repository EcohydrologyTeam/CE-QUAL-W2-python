"""
Data models for ClearView application.
Handles data loading, processing, and state management.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add src to path for importing cequalw2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
import cequalw2 as w2


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