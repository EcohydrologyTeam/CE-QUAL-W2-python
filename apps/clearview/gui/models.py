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
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

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


class PlotType(Enum):
    """Enumeration of available plot types."""
    LINE = "line"
    SCATTER = "scatter"
    BAR = "bar"
    HISTOGRAM = "histogram"
    BOX = "box"
    VIOLIN = "violin"
    AREA = "area"
    STEP = "step"
    STEM = "stem"
    PIE = "pie"
    HEATMAP = "heatmap"
    CORRELATION = "correlation"


class PlotStyle(Enum):
    """Enumeration of plot styles."""
    DEFAULT = "default"
    SEABORN = "seaborn-v0_8"
    CLASSIC = "classic"
    GGPLOT = "ggplot"
    FIVETHIRTYEIGHT = "fivethirtyeight"
    BMHPLOT = "bmh"
    DARK_BACKGROUND = "dark_background"


@dataclass
class PlotConfiguration:
    """Configuration for plot customization."""
    plot_type: PlotType = PlotType.LINE
    columns: List[str] = None
    x_column: Optional[str] = None
    y_columns: List[str] = None
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    style: PlotStyle = PlotStyle.DEFAULT
    color_scheme: str = "tab10"
    figure_size: Tuple[int, int] = (12, 6)
    dpi: int = 100
    grid: bool = True
    legend: bool = True
    legend_position: str = "best"
    line_style: str = "-"
    line_width: float = 1.5
    marker_style: str = "o"
    marker_size: float = 6.0
    alpha: float = 1.0
    fill_alpha: float = 0.3
    subplot_layout: Tuple[int, int] = (1, 1)
    tight_layout: bool = True
    show_statistics: bool = False
    log_scale_x: bool = False
    log_scale_y: bool = False
    xlim: Optional[Tuple[float, float]] = None
    ylim: Optional[Tuple[float, float]] = None


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
    
    # Advanced Plotting Methods
    def create_plot(self, config: PlotConfiguration, figure=None, ax=None) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create a customized plot based on the configuration.
        
        Args:
            config: PlotConfiguration object with plot settings
            figure: Existing matplotlib figure (optional)
            ax: Existing matplotlib axes (optional)
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if self.df is None or self.df.empty:
            raise ValueError("No data available for plotting")
        
        # Set style
        if config.style != PlotStyle.DEFAULT:
            try:
                plt.style.use(config.style.value)
            except OSError:
                pass  # Fall back to default style
        
        # Create figure and axes if not provided
        if figure is None:
            figure = plt.figure(figsize=config.figure_size, dpi=config.dpi)
        
        if ax is None:
            if config.subplot_layout == (1, 1):
                ax = figure.add_subplot(111)
            else:
                # For multiple subplots, return the first one
                ax = figure.add_subplot(config.subplot_layout[0], config.subplot_layout[1], 1)
        
        # Clear existing content
        ax.clear()
        
        # Get color palette
        colors = self._get_color_palette(config.color_scheme, len(config.y_columns or []))
        
        # Create plot based on type
        if config.plot_type == PlotType.LINE:
            self._create_line_plot(ax, config, colors)
        elif config.plot_type == PlotType.SCATTER:
            self._create_scatter_plot(ax, config, colors)
        elif config.plot_type == PlotType.BAR:
            self._create_bar_plot(ax, config, colors)
        elif config.plot_type == PlotType.HISTOGRAM:
            self._create_histogram_plot(ax, config, colors)
        elif config.plot_type == PlotType.BOX:
            self._create_box_plot(ax, config, colors)
        elif config.plot_type == PlotType.VIOLIN:
            self._create_violin_plot(ax, config, colors)
        elif config.plot_type == PlotType.AREA:
            self._create_area_plot(ax, config, colors)
        elif config.plot_type == PlotType.STEP:
            self._create_step_plot(ax, config, colors)
        elif config.plot_type == PlotType.STEM:
            self._create_stem_plot(ax, config, colors)
        elif config.plot_type == PlotType.PIE:
            self._create_pie_plot(ax, config, colors)
        elif config.plot_type == PlotType.HEATMAP:
            self._create_heatmap_plot(ax, config)
        elif config.plot_type == PlotType.CORRELATION:
            self._create_correlation_plot(ax, config)
        
        # Apply customization
        self._apply_plot_customization(ax, config)
        
        if config.tight_layout:
            figure.tight_layout()
        
        return figure, ax
    
    def _get_color_palette(self, color_scheme: str, n_colors: int) -> List[str]:
        """Get a color palette for plotting."""
        try:
            if hasattr(plt.cm, color_scheme):
                cmap = plt.cm.get_cmap(color_scheme)
                return [cmap(i / max(1, n_colors - 1)) for i in range(n_colors)]
            else:
                # Use matplotlib color cycle
                prop_cycle = plt.rcParams['axes.prop_cycle']
                colors = prop_cycle.by_key()['color']
                return colors * (n_colors // len(colors) + 1)
        except Exception:
            # Fallback to default colors
            return ['C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']
    
    def _create_line_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a line plot."""
        x_data = self._get_x_data(config)
        
        for i, col in enumerate(config.y_columns or []):
            if col in self.df.columns:
                y_data = self.df[col].dropna()
                if len(y_data) > 0:
                    color = colors[i % len(colors)] if colors else None
                    ax.plot(x_data[:len(y_data)], y_data, 
                           label=col, color=color, 
                           linestyle=config.line_style,
                           linewidth=config.line_width,
                           marker=config.marker_style,
                           markersize=config.marker_size,
                           alpha=config.alpha)
    
    def _create_scatter_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a scatter plot."""
        if config.x_column and config.y_columns:
            x_data = self.df[config.x_column].dropna()
            for i, col in enumerate(config.y_columns):
                if col in self.df.columns:
                    y_data = self.df[col].dropna()
                    # Align data lengths
                    min_len = min(len(x_data), len(y_data))
                    color = colors[i % len(colors)] if colors else None
                    ax.scatter(x_data[:min_len], y_data[:min_len],
                              label=col, color=color,
                              s=config.marker_size**2,
                              alpha=config.alpha)
    
    def _create_bar_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a bar plot."""
        if config.y_columns:
            x_data = self._get_x_data(config)
            bar_width = 0.8 / len(config.y_columns)
            
            for i, col in enumerate(config.y_columns):
                if col in self.df.columns:
                    y_data = self.df[col].dropna()
                    x_offset = (i - len(config.y_columns)/2 + 0.5) * bar_width
                    color = colors[i % len(colors)] if colors else None
                    ax.bar(np.arange(len(y_data)) + x_offset, y_data,
                          width=bar_width, label=col, color=color,
                          alpha=config.alpha)
    
    def _create_histogram_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a histogram plot."""
        for i, col in enumerate(config.y_columns or []):
            if col in self.df.columns:
                data = self.df[col].dropna()
                if len(data) > 0:
                    color = colors[i % len(colors)] if colors else None
                    ax.hist(data, bins=30, alpha=config.alpha, 
                           label=col, color=color, edgecolor='black')
    
    def _create_box_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a box plot."""
        data_list = []
        labels = []
        
        for col in config.y_columns or []:
            if col in self.df.columns:
                data = self.df[col].dropna()
                if len(data) > 0:
                    data_list.append(data)
                    labels.append(col)
        
        if data_list:
            bp = ax.boxplot(data_list, labels=labels, patch_artist=True)
            for i, patch in enumerate(bp['boxes']):
                color = colors[i % len(colors)] if colors else 'lightblue'
                patch.set_facecolor(color)
                patch.set_alpha(config.alpha)
    
    def _create_violin_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a violin plot."""
        data_list = []
        labels = []
        
        for col in config.y_columns or []:
            if col in self.df.columns:
                data = self.df[col].dropna()
                if len(data) > 0:
                    data_list.append(data)
                    labels.append(col)
        
        if data_list:
            parts = ax.violinplot(data_list, showmeans=True, showmedians=True)
            for i, pc in enumerate(parts['bodies']):
                color = colors[i % len(colors)] if colors else 'lightblue'
                pc.set_facecolor(color)
                pc.set_alpha(config.alpha)
            
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels)
    
    def _create_area_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create an area plot."""
        x_data = self._get_x_data(config)
        
        for i, col in enumerate(config.y_columns or []):
            if col in self.df.columns:
                y_data = self.df[col].dropna()
                if len(y_data) > 0:
                    color = colors[i % len(colors)] if colors else None
                    ax.fill_between(x_data[:len(y_data)], y_data, 
                                   alpha=config.fill_alpha, label=col, color=color)
                    ax.plot(x_data[:len(y_data)], y_data, 
                           color=color, linewidth=config.line_width)
    
    def _create_step_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a step plot."""
        x_data = self._get_x_data(config)
        
        for i, col in enumerate(config.y_columns or []):
            if col in self.df.columns:
                y_data = self.df[col].dropna()
                if len(y_data) > 0:
                    color = colors[i % len(colors)] if colors else None
                    ax.step(x_data[:len(y_data)], y_data, 
                           where='mid', label=col, color=color,
                           linewidth=config.line_width, alpha=config.alpha)
    
    def _create_stem_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a stem plot."""
        x_data = self._get_x_data(config)
        
        for i, col in enumerate(config.y_columns or []):
            if col in self.df.columns:
                y_data = self.df[col].dropna()
                if len(y_data) > 0:
                    color = colors[i % len(colors)] if colors else None
                    markerline, stemlines, baseline = ax.stem(x_data[:len(y_data)], y_data,
                                                             label=col)
                    markerline.set_color(color)
                    stemlines.set_color(color)
                    markerline.set_alpha(config.alpha)
                    stemlines.set_alpha(config.alpha)
    
    def _create_pie_plot(self, ax: plt.Axes, config: PlotConfiguration, colors: List[str]):
        """Create a pie plot."""
        if config.y_columns and len(config.y_columns) == 1:
            col = config.y_columns[0]
            if col in self.df.columns:
                data = self.df[col].dropna()
                if len(data) > 0:
                    # Group small values together
                    data_sum = data.sum()
                    threshold = data_sum * 0.01  # 1% threshold
                    
                    labels = []
                    values = []
                    others = 0
                    
                    for idx, val in data.items():
                        if val >= threshold:
                            labels.append(f"Row {idx}")
                            values.append(val)
                        else:
                            others += val
                    
                    if others > 0:
                        labels.append("Others")
                        values.append(others)
                    
                    ax.pie(values, labels=labels, autopct='%1.1f%%',
                          colors=colors[:len(values)], alpha=config.alpha)
    
    def _create_heatmap_plot(self, ax: plt.Axes, config: PlotConfiguration):
        """Create a heatmap plot."""
        # Select numeric columns
        numeric_data = self.df.select_dtypes(include=[np.number])
        if not numeric_data.empty:
            # Create correlation matrix if more than one column
            if len(numeric_data.columns) > 1:
                corr_matrix = numeric_data.corr()
                im = ax.imshow(corr_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
                ax.set_xticks(range(len(corr_matrix.columns)))
                ax.set_yticks(range(len(corr_matrix.columns)))
                ax.set_xticklabels(corr_matrix.columns, rotation=45)
                ax.set_yticklabels(corr_matrix.columns)
                
                # Add colorbar
                plt.colorbar(im, ax=ax)
                
                # Add correlation values
                for i in range(len(corr_matrix.columns)):
                    for j in range(len(corr_matrix.columns)):
                        text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                     ha="center", va="center", color="black")
    
    def _create_correlation_plot(self, ax: plt.Axes, config: PlotConfiguration):
        """Create a correlation matrix plot."""
        numeric_data = self.df.select_dtypes(include=[np.number])
        if len(numeric_data.columns) > 1:
            corr_matrix = numeric_data.corr()
            
            # Create a mask for the upper triangle
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
            
            # Plot heatmap
            im = ax.imshow(corr_matrix.where(~mask), cmap='RdBu_r', 
                          aspect='auto', vmin=-1, vmax=1)
            
            ax.set_xticks(range(len(corr_matrix.columns)))
            ax.set_yticks(range(len(corr_matrix.columns)))
            ax.set_xticklabels(corr_matrix.columns, rotation=45)
            ax.set_yticklabels(corr_matrix.columns)
            
            plt.colorbar(im, ax=ax)
    
    def _get_x_data(self, config: PlotConfiguration):
        """Get x-axis data for plotting."""
        if config.x_column and config.x_column in self.df.columns:
            return self.df[config.x_column].dropna()
        else:
            # Use index as x-axis
            max_length = max(len(self.df[col].dropna()) for col in (config.y_columns or []) 
                           if col in self.df.columns) if config.y_columns else len(self.df)
            return np.arange(max_length)
    
    def _apply_plot_customization(self, ax: plt.Axes, config: PlotConfiguration):
        """Apply plot customization settings."""
        # Set title and labels
        if config.title:
            ax.set_title(config.title, fontsize=14, fontweight='bold')
        
        if config.xlabel:
            ax.set_xlabel(config.xlabel, fontsize=12)
        
        if config.ylabel:
            ax.set_ylabel(config.ylabel, fontsize=12)
        
        # Set grid
        if config.grid:
            ax.grid(True, alpha=0.3)
        
        # Set legend
        if config.legend and config.y_columns and len(config.y_columns) > 1:
            ax.legend(loc=config.legend_position)
        
        # Set scales
        if config.log_scale_x:
            ax.set_xscale('log')
        
        if config.log_scale_y:
            ax.set_yscale('log')
        
        # Set limits
        if config.xlim:
            ax.set_xlim(config.xlim)
        
        if config.ylim:
            ax.set_ylim(config.ylim)
        
        # Add statistics if requested
        if config.show_statistics and config.y_columns:
            self._add_statistics_text(ax, config)
    
    def _add_statistics_text(self, ax: plt.Axes, config: PlotConfiguration):
        """Add statistics text to the plot."""
        stats_text = []
        
        for col in config.y_columns or []:
            if col in self.df.columns:
                data = self.df[col].dropna()
                if len(data) > 0:
                    stats_text.append(f"{col}:")
                    stats_text.append(f"  Mean: {data.mean():.2f}")
                    stats_text.append(f"  Std: {data.std():.2f}")
                    stats_text.append(f"  Min: {data.min():.2f}")
                    stats_text.append(f"  Max: {data.max():.2f}")
                    stats_text.append("")
        
        if stats_text:
            ax.text(0.02, 0.98, '\n'.join(stats_text), transform=ax.transAxes,
                   verticalalignment='top', fontsize=8, 
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def get_plot_recommendations(self) -> Dict[str, List[str]]:
        """
        Get plot type recommendations based on data characteristics.
        
        Returns:
            Dict mapping plot types to recommended columns
        """
        if self.df is None or self.df.empty:
            return {}
        
        recommendations = {}
        numeric_cols = list(self.df.select_dtypes(include=[np.number]).columns)
        categorical_cols = list(self.df.select_dtypes(include=['object', 'category']).columns)
        datetime_cols = list(self.df.select_dtypes(include=['datetime64']).columns)
        
        # Line plots: good for time series and continuous data
        if len(numeric_cols) >= 1:
            recommendations['Line Plot'] = numeric_cols
        
        # Scatter plots: good for relationships between two numeric variables
        if len(numeric_cols) >= 2:
            recommendations['Scatter Plot'] = numeric_cols[:2]
        
        # Bar plots: good for categorical data
        if categorical_cols and numeric_cols:
            recommendations['Bar Plot'] = [categorical_cols[0], numeric_cols[0]]
        
        # Histograms: good for distribution analysis
        if numeric_cols:
            recommendations['Histogram'] = [numeric_cols[0]]
        
        # Box plots: good for comparing distributions
        if len(numeric_cols) >= 2:
            recommendations['Box Plot'] = numeric_cols
        
        # Heatmap/Correlation: good for correlation analysis
        if len(numeric_cols) >= 3:
            recommendations['Correlation Matrix'] = numeric_cols
        
        return recommendations