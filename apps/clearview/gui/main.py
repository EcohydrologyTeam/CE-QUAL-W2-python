"""
ClearView - CE-QUAL-W2 Data Visualization and Analysis Application

A comprehensive PyQt6-based GUI for loading, analyzing, and visualizing CE-QUAL-W2
water quality model output data. This application provides an intuitive interface
for working with complex time series datasets containing 100+ water quality parameters.

Features:
- Smart Plot system with intelligent column selection
- Multi-format data loading (CSV, NPT, OPT, Excel, HDF5, NetCDF, SQLite)  
- Interactive plotting with pan/zoom navigation
- Professional matplotlib toolbar integration
- TSR (Time Series Results) file support for particle tracking
- Data validation and quality checking
- Export capabilities for data and visualizations

Key Classes:
- ClearView: Main application window and primary interface
- ColumnPickerDialog: Smart column selection dialog for plotting
- MyTableWidget: Custom table widget with enhanced navigation

Architecture:
The application uses a tabbed interface design with dedicated sections for plotting,
statistics, data viewing, advanced analysis, validation, and filtering. The Smart Plot
system replaces overwhelming multi-plot displays with intelligent parameter selection.

This module represents the monolithic version of the ClearView application. An MVC
version is also available with separated concerns across multiple files.

Usage:
    python main.py

Author: CE-QUAL-W2 Python Development Team
License: MIT
"""

import os
import sys
import csv
import glob
import sqlite3
import numpy as np
import pandas as pd

# Set Qt API before importing matplotlib to use PyQt6
os.environ['QT_API'] = 'pyqt6'

# Import PyQt6 first
import PyQt6.QtCore as qtc
import PyQt6.QtWidgets as qtw
import PyQt6.QtGui as qtg

# Now import matplotlib with proper backend
import matplotlib
matplotlib.use('qtagg')  # Use the generic Qt Agg backend
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
# Add src to path for importing cequalw2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
import cequalw2 as w2


class MyTableWidget(qtw.QTableWidget):
    """
    Custom QTableWidget subclass that provides special key press handling.

    This class extends the QTableWidget class and overrides the keyPressEvent method
    to handle the Enter/Return key press event in a specific way. When the Enter/Return
    key is pressed, the current cell is moved to the next cell in a wrapping fashion,
    moving to the next row or wrapping to the top of the next column.
    """

    def __init__(self, parent):
        # import sys, os
        # print('Current working directory', os.path.abspath(os.getcwd()))
        super().__init__(parent)

    def keyPressEvent(self, event):
        """
        Override the key press event handling.

        If the Enter/Return key is pressed, move the current cell to the next cell
        in a wrapping fashion, moving to the next row or wrapping to the top of
        the next column. Otherwise, pass the event to the base class for default
        key press handling.

        :param event: The key press event.
        :type event: QKeyEvent
        """

        if event.key() == qtc.Qt.Key.Key_Enter or event.key() == qtc.Qt.Key.Key_Return:
            current_row = self.currentRow()
            current_column = self.currentColumn()

            if current_row == self.rowCount() - 1 and current_column == self.columnCount() - 1:
                # Wrap around to the top of the next column
                self.setCurrentCell(0, 0)
            elif current_row < self.rowCount() - 1:
                # Move to the next cell down
                self.setCurrentCell(current_row + 1, current_column)
            else:
                # Move to the top of the next column
                self.setCurrentCell(0, current_column + 1)
        else:
            super().keyPressEvent(event)


class ColumnPickerDialog(qtw.QDialog):
    """
    Interactive dialog for intelligent column selection in time series plotting.
    
    This dialog provides a user-friendly interface for selecting which columns to plot
    from large CE-QUAL-W2 datasets that may contain 100+ parameters. It features smart
    suggestions based on common water quality parameter names and interactive filtering.
    
    Key Features:
    - Smart column suggestions based on water quality parameter priorities
    - Real-time search/filtering of available columns
    - Multi-selection with Select All/None convenience buttons
    - Live preview showing estimated plot dimensions
    - Plot options for customizing visualization appearance
    
    The dialog automatically prioritizes common water quality parameters like temperature,
    pH, dissolved oxygen, turbidity, flow rates, and nutrient concentrations to help
    users quickly identify the most relevant data for analysis.
    
    Args:
        dataframe (pd.DataFrame): The source DataFrame containing time series data
        parent (QWidget, optional): Parent widget for the dialog
        
    Attributes:
        dataframe (pd.DataFrame): Reference to the source data
        selected_columns (list): Currently selected column names
        column_list (QListWidget): UI widget for column selection
        search_box (QLineEdit): Search/filter input field
        preview_label (QLabel): Shows selection summary and plot preview info
    """
    
    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.selected_columns = []
        self.setup_ui()
        self.suggest_default_columns()
    
    def setup_ui(self):
        """
        Create and configure the dialog's user interface components.
        
        Sets up a comprehensive column selection interface including:
        - Title label and search functionality
        - Multi-selection list widget for columns
        - Action buttons (Select All/None/Suggested Selection)
        - Plot options checkboxes (auto-scale, grid, shared X-axis)
        - Live preview label showing selection summary
        - OK/Cancel dialog buttons
        
        The layout uses vertical stacking with grouped sections for intuitive
        navigation and a professional appearance.
        """
        self.setWindowTitle("Select Columns to Plot")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = qtw.QVBoxLayout(self)
        
        # Title
        title_label = qtw.QLabel("Select time series for plotting:")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Search box
        search_layout = qtw.QHBoxLayout()
        search_label = qtw.QLabel("Search:")
        self.search_box = qtw.QLineEdit()
        self.search_box.setPlaceholderText("Type to filter columns...")
        self.search_box.textChanged.connect(self.filter_columns)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Column list
        self.column_list = qtw.QListWidget()
        self.column_list.setSelectionMode(qtw.QAbstractItemView.SelectionMode.MultiSelection)
        self.populate_column_list()
        layout.addWidget(self.column_list)
        
        # Selection buttons
        button_layout = qtw.QHBoxLayout()
        self.select_all_btn = qtw.QPushButton("Select All")
        self.select_none_btn = qtw.QPushButton("Select None")
        self.suggest_btn = qtw.QPushButton("Suggested Selection")
        
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_none_btn.clicked.connect(self.select_none)
        self.suggest_btn.clicked.connect(self.suggest_default_columns)
        
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.select_none_btn)
        button_layout.addWidget(self.suggest_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Options
        options_group = qtw.QGroupBox("Plot Options")
        options_layout = qtw.QGridLayout(options_group)
        
        self.auto_scale_cb = qtw.QCheckBox("Auto-scale Y axes")
        self.auto_scale_cb.setChecked(True)
        self.show_grid_cb = qtw.QCheckBox("Show grid")
        self.show_grid_cb.setChecked(True)
        self.shared_x_cb = qtw.QCheckBox("Shared X-axis")
        self.shared_x_cb.setChecked(True)
        
        options_layout.addWidget(self.auto_scale_cb, 0, 0)
        options_layout.addWidget(self.show_grid_cb, 0, 1)
        options_layout.addWidget(self.shared_x_cb, 1, 0)
        
        layout.addWidget(options_group)
        
        # Preview label
        self.preview_label = qtw.QLabel()
        self.preview_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.preview_label)
        
        # Dialog buttons
        button_box = qtw.QDialogButtonBox(
            qtw.QDialogButtonBox.StandardButton.Ok | qtw.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect selection change to update preview
        self.column_list.itemSelectionChanged.connect(self.update_preview)
    
    def populate_column_list(self):
        """
        Populate the column selection list with numeric columns from the DataFrame.
        
        Filters the source DataFrame to include only numeric columns suitable for
        plotting, excluding non-numeric data like text identifiers or categorical
        variables. Each column is added as a selectable list item with the column
        name as both display text and stored data.
        
        Only numeric columns are included because:
        - Time series plotting requires numeric Y-axis values
        - Text/categorical columns would cause plotting errors
        - Provides cleaner user interface without invalid options
        
        Side Effects:
            Clears and repopulates the column_list widget with numeric columns only.
        """
        self.column_list.clear()
        
        # Get numeric columns only
        numeric_columns = self.dataframe.select_dtypes(include=['number']).columns.tolist()
        
        for col in numeric_columns:
            item = qtw.QListWidgetItem(col)
            item.setData(qtc.Qt.ItemDataRole.UserRole, col)
            self.column_list.addItem(item)
    
    def filter_columns(self, text):
        """Filter columns based on search text."""
        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            visible = text.lower() in item.text().lower()
            item.setHidden(not visible)
    
    def select_all(self):
        """Select all visible columns."""
        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            if not item.isHidden():
                item.setSelected(True)
        self.update_preview()
    
    def select_none(self):
        """Deselect all columns."""
        self.column_list.clearSelection()
        self.update_preview()
    
    def suggest_default_columns(self):
        """
        Intelligently suggest default columns based on common water quality parameters.
        
        Implements a two-pass selection algorithm to identify the most relevant columns
        for water quality analysis from potentially large datasets (100+ parameters):
        
        Pass 1: Priority-based selection
        - Searches for columns containing water quality keywords (temp, ph, do, etc.)
        - Prioritizes essential parameters like temperature, dissolved oxygen, pH
        - Limits selection to 4 columns maximum for optimal plot readability
        
        Pass 2: Fallback selection
        - If insufficient priority matches found (< 3 columns)
        - Selects first available numeric columns to ensure meaningful visualization
        - Maintains minimum of 3 columns for comparative analysis
        
        Priority Keywords (in order of importance):
        - Temperature: 'temp', 'temperature'
        - Dissolved Oxygen: 'do', 'dissolved', 'oxygen'
        - pH and Water Chemistry: 'ph', 'turbidity'
        - Physical Parameters: 'flow', 'depth'
        - Nutrients: 'nitrate', 'phosphate'
        
        This approach ensures users get relevant water quality data by default while
        maintaining the flexibility to modify selections as needed.
        
        Side Effects:
            - Updates column selection state in the UI
            - Triggers preview text update
            - May modify existing user selections
        """
        self.select_none()
        
        # Common water quality parameter names to prioritize
        priority_terms = ['temp', 'temperature', 'ph', 'do', 'dissolved', 'oxygen', 
                         'turbidity', 'flow', 'depth', 'nitrate', 'phosphate']
        
        suggested_count = 0
        max_suggestions = 4
        
        # First pass: exact matches
        for i in range(self.column_list.count()):
            if suggested_count >= max_suggestions:
                break
            item = self.column_list.item(i)
            col_name = item.text().lower()
            
            for term in priority_terms:
                if term in col_name:
                    item.setSelected(True)
                    suggested_count += 1
                    break
        
        # If we don't have enough suggestions, add first few numeric columns
        if suggested_count < 3:
            for i in range(min(3, self.column_list.count())):
                item = self.column_list.item(i)
                if not item.isSelected():
                    item.setSelected(True)
                    suggested_count += 1
                    if suggested_count >= max_suggestions:
                        break
        
        self.update_preview()
    
    def update_preview(self):
        """Update the preview text."""
        selected_count = len(self.column_list.selectedItems())
        if selected_count == 0:
            self.preview_label.setText("No columns selected")
        else:
            estimated_height = max(selected_count * 2.5, 6)
            self.preview_label.setText(
                f"Preview: {selected_count} subplot{'s' if selected_count != 1 else ''}, "
                f"estimated height: {estimated_height:.1f} inches"
            )
    
    def get_selected_columns(self):
        """Return list of selected column names."""
        return [item.text() for item in self.column_list.selectedItems()]


class ClearView(qtw.QMainWindow):
    """
    Main application window for ClearView - CE-QUAL-W2 Data Visualization and Analysis Tool.
    
    ClearView is a comprehensive PyQt6-based GUI application designed for loading, analyzing,
    and visualizing CE-QUAL-W2 water quality model output data. It provides an intuitive
    interface for working with complex time series datasets typically containing 100+
    water quality parameters.
    
    Key Capabilities:
    - **Multi-format Data Loading**: Supports CSV, NPT, OPT, Excel, HDF5, NetCDF, and SQLite
    - **Intelligent Plotting**: Smart column selection with water quality parameter suggestions
    - **Interactive Analysis**: Pan, zoom, and explore time series data with professional tools
    - **Data Validation**: Built-in quality checking and error handling for model outputs
    - **Export Functions**: Save data tables, statistics, and plots in multiple formats
    - **TSR File Support**: Specialized handling for Time Series Results from particle tracking
    
    Architecture:
    The application follows a tabbed interface design with dedicated sections for:
    - **Plot Tab**: Primary visualization with Smart Plot functionality
    - **Statistics Tab**: Descriptive statistics and data summaries  
    - **Data Tab**: Editable table view of loaded dataset
    - **Advanced Plotting Tab**: Full-featured plotting with 12+ chart types
    - **Validation Tab**: Data quality assessment tools
    - **Filtering Tab**: Advanced data filtering and transformation
    
    Smart Plot System:
    The centerpiece feature replaces traditional overwhelming multi-plot displays with
    an intelligent column picker that suggests relevant water quality parameters based
    on common CE-QUAL-W2 output patterns. This solves the "100+ parameter problem" by
    providing curated, readable visualizations.
    
    PyQt6 Compatibility:
    Fully migrated from PyQt5 to PyQt6 with custom solutions for compatibility issues
    including matplotlib toolbar integration and proper enum handling.
    
    Typical Workflow:
    1. Load CE-QUAL-W2 output file (various formats supported)
    2. Use Smart Plot to select relevant water quality parameters
    3. Analyze time series data with interactive navigation tools
    4. Export results for reporting or further analysis
    
    Class Constants:
        DEFAULT_WINDOW_WIDTH (int): Initial window width in pixels (1500)
        DEFAULT_WINDOW_HEIGHT (int): Initial window height in pixels (900)
        DEFAULT_YEAR (int): Default model year for CE-QUAL-W2 data (2023)
        TOOLBAR_HEIGHT (int): Standard toolbar height in pixels
        ICON_SIZE (int): Standard icon dimensions for UI elements
        PLOT_SCALE_FACTOR (float): Scaling factor for plot dimensions
        
    Attributes:
        data (pd.DataFrame): Currently loaded time series dataset
        stats (pd.DataFrame): Statistical summary of loaded data
        year (int): Model year extracted from CE-QUAL-W2 control files
        file_path (str): Path to currently loaded data file
        canvas (FigureCanvas): Matplotlib canvas for plot display
        mpl_toolbar (NavigationToolbar): Hidden matplotlib toolbar for functionality
        navigation_toolbar (QToolBar): Custom visual toolbar with emoji icons
        
    Example:
        >>> app = qtw.QApplication([])
        >>> window = ClearView()
        >>> window.show()
        >>> app.exec()
    """
    
    # Class constants for configuration
    DEFAULT_WINDOW_WIDTH = 1500
    DEFAULT_WINDOW_HEIGHT = 900
    DEFAULT_YEAR = 2023
    DEFAULT_FIG_WIDTH = 12
    DEFAULT_FIG_HEIGHT = 4
    ICON_SIZE = 24
    TOOLBAR_HEIGHT = 25
    STATS_TABLE_MIN_HEIGHT = 200
    PLOT_SCALE_FACTOR = 1.5
    SUBPLOT_SCALE_FACTOR = 2.0
    
    # UI element dimensions
    LABEL_WIDTH = 75
    YEAR_INPUT_WIDTH = 55
    FILENAME_INPUT_WIDTH = 400

    def __init__(self):
        super().__init__()
        self.setWindowTitle('ClearView - CE-QUAL-W2 Data Viewer')
        
        # Center window on screen with proper sizing
        self.resize(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
        self.center_on_screen()
        
        # Initialize data attributes
        self.file_path = ''
        self.data = None
        self.stats = None
        self.year = self.DEFAULT_YEAR
        self.data_database_path = None
        self.stats_database_path = None
        self.table_name = 'data'
        self.default_fig_width = self.DEFAULT_FIG_WIDTH
        self.default_fig_height = self.DEFAULT_FIG_HEIGHT
        
        # Set up assets directory path
        self.assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
        
        # Initialize UI
        self.setup_ui()

    def center_on_screen(self):
        """Center the window on the screen."""
        # PyQt6 compatible way to get screen geometry
        screen = qtw.QApplication.primaryScreen().geometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def load_icon(self, icon_path, fallback_style=None):
        """
        Safely load an icon from the assets directory with fallback.
        
        Args:
            icon_path (str): Relative path to icon from assets directory
            fallback_style: QStyle standard icon to use if file not found
            
        Returns:
            QIcon: The loaded icon or fallback
        """
        full_path = os.path.join(self.assets_dir, icon_path)
        if os.path.exists(full_path):
            return qtg.QIcon(full_path)
        elif fallback_style:
            return qtg.QIcon(self.style().standardIcon(fallback_style))
        else:
            # Use a generic file icon as ultimate fallback
            return qtg.QIcon(self.style().standardIcon(qtw.QStyle.StandardPixmap.SP_FileIcon))

    def setup_ui(self):
        """Set up the user interface components."""
        # Create a menu bar
        menubar = self.menuBar()

        # Create menus
        file_menu = menubar.addMenu('File')
        edit_menu = menubar.addMenu('Edit')
        save_menu = menubar.addMenu('Save')
        plot_menu = menubar.addMenu('Plot')

        # Create an app toolbar
        self.app_toolbar = self.addToolBar('Toolbar')
        self.app_toolbar.setToolButtonStyle(qtc.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.app_toolbar.setMovable(False)
        self.app_toolbar.setIconSize(qtc.QSize(self.ICON_SIZE, self.ICON_SIZE))

        # Create app toolbar icons using safe loading
        open_icon = self.load_icon(
            'icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/folder-horizontal-open.png',
            qtw.QStyle.StandardPixmap.SP_DialogOpenButton
        )
        save_data_icon = self.load_icon(
            'icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/disk-black.png',
            qtw.QStyle.StandardPixmap.SP_DialogSaveButton
        )
        save_stats_icon = self.load_icon(
            'icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/disk.png',
            qtw.QStyle.StandardPixmap.SP_DialogSaveButton
        )
        copy_icon = self.load_icon(
            'icons/fugue-icons-3.5.6-src/bonus/icons-24/document-text-image.png',
            qtw.QStyle.StandardPixmap.SP_DialogCancelButton
        )
        paste_icon = self.load_icon(
            'icons/fugue-icons-3.5.6-src/bonus/icons-24/photo-album.png',
            qtw.QStyle.StandardPixmap.SP_DialogApplyButton
        )
        plot_icon = self.load_icon(
            'icons/w2_veiwer_multi_plot_icon.png',
            qtw.QStyle.StandardPixmap.SP_ComputerIcon
        )

        # Set open_icon alignment to top
        # open_icon.addPixmap(open_icon.pixmap(24, 24, qtg.QIcon.Active, qtg.QIcon.On))

        # Create Open action
        open_action = qtg.QAction(open_icon, 'Open File', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.browse_file)

        # Create Copy action for the stats and data tables
        copy_action = qtg.QAction(copy_icon, 'Copy Data', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy_data)

        # Create Paste action for the stats and data tables
        paste_action = qtg.QAction(paste_icon, 'Paste Data', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(self.paste_data)

        # Add a save data button icon to the toolbar
        save_data_action = qtg.QAction(save_data_icon, 'Save Data', self)
        save_data_action.setShortcut('Ctrl+S')
        save_data_action.triggered.connect(self.save_data)

        # Add a save stats button icon to the toolbar
        save_stats_action = qtg.QAction(save_stats_icon, 'Save Stats', self)
        save_stats_action.setShortcut('Ctrl+Shift+S')
        save_stats_action.triggered.connect(self.save_stats)

        # Add a plot button icon to the toolbar
        plot_action = qtg.QAction(plot_icon, 'Plot', self)
        plot_action.setShortcut('Ctrl+P')
        plot_action.triggered.connect(self.multi_plot)

        # Add the toolbar to the main window
        self.addToolBar(self.app_toolbar)

        # Create a scroll area to contain the plot
        self.plot_scroll_area = qtw.QScrollArea(self)
        self.plot_scroll_area.setWidgetResizable(False)
        self.plot_scroll_area.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        # Create the start year label and text input field
        self.start_year_label = qtw.QLabel('Start Year:', self)
        self.start_year_label.setFixedWidth(self.LABEL_WIDTH)
        self.start_year_input = qtw.QLineEdit(self)
        self.start_year_input.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self.start_year_input.setFixedWidth(self.YEAR_INPUT_WIDTH)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText(str(self.DEFAULT_YEAR))
        self.start_year_input.textChanged.connect(self.update_year)

        # Create the input filename label and text input field
        self.filename_label = qtw.QLabel('Filename:')
        self.filename_label.setFixedWidth(self.LABEL_WIDTH)
        self.filename_input = qtw.QLineEdit(self)
        self.filename_input.setFixedWidth(self.FILENAME_INPUT_WIDTH)
        self.filename_input.setReadOnly(True)
        self.filename_input.textChanged.connect(self.update_filename)

        # Create a layout for the start year and filename widgets
        self.start_year_and_filename_layout = qtw.QHBoxLayout()
        self.start_year_and_filename_layout.setAlignment(qtc.Qt.AlignmentFlag.AlignLeft)
        self.start_year_and_filename_layout.addWidget(self.start_year_label)
        self.start_year_and_filename_layout.addWidget(self.start_year_input)
        self.start_year_and_filename_layout.addWidget(self.filename_label)
        self.start_year_and_filename_layout.addWidget(self.filename_input)

        # Create the statistics table
        self.stats_table = MyTableWidget(self)
        self.stats_table.setEditTriggers(qtw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_table.setMinimumHeight(self.STATS_TABLE_MIN_HEIGHT)

        # Create empty canvas and add a matplotlib navigation toolbar
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)

        # Create hidden matplotlib navigation toolbar for functionality
        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        self.mpl_toolbar.hide()  # Hide the original toolbar but keep functionality
        
        # Create custom visual toolbar for PyQt6 compatibility
        self.navigation_toolbar = qtw.QToolBar()
        self.navigation_toolbar.setMaximumHeight(self.TOOLBAR_HEIGHT)
        self.navigation_toolbar_background_color = '#eeffee'
        self.navigation_toolbar.setStyleSheet(f'background-color: {self.navigation_toolbar_background_color}; font-size: 14px; color: black;')
        
        # Add navigation actions with text labels (PyQt6 compatible)
        home_action = qtg.QAction("🏠 Home", self.navigation_toolbar)
        home_action.setToolTip("Reset view to fit all data")
        home_action.triggered.connect(self.reset_plot_view)
        self.navigation_toolbar.addAction(home_action)
        
        self.navigation_toolbar.addSeparator()
        
        pan_action = qtg.QAction("✋ Pan", self.navigation_toolbar)
        pan_action.setToolTip("Pan the plot")
        pan_action.setCheckable(True)
        pan_action.triggered.connect(self.toggle_pan)
        self.navigation_toolbar.addAction(pan_action)
        
        zoom_action = qtg.QAction("🔍 Zoom", self.navigation_toolbar)
        zoom_action.setToolTip("Zoom to rectangle")
        zoom_action.setCheckable(True)
        zoom_action.triggered.connect(self.toggle_zoom)
        self.navigation_toolbar.addAction(zoom_action)
        
        self.navigation_toolbar.addSeparator()
        
        save_action = qtg.QAction("💾 Save", self.navigation_toolbar)
        save_action.setToolTip("Save the figure")
        save_action.triggered.connect(self.save_figure)
        self.navigation_toolbar.addAction(save_action)
        
        # Store action references for toggling
        self.pan_action = pan_action
        self.zoom_action = zoom_action

        # Create tabs
        self.tab_widget = qtw.QTabWidget()
        self.plot_tab = qtw.QWidget()
        self.statistics_tab = qtw.QWidget()
        self.tab_widget.addTab(self.plot_tab, "Plot")
        self.tab_widget.addTab(self.statistics_tab, "Statistics")

        # Set layout for the Plot Tab
        self.plot_tab_layout = qtw.QVBoxLayout()
        self.plot_tab_layout.addWidget(self.navigation_toolbar)
        self.plot_tab_layout.addWidget(self.plot_scroll_area)
        self.plot_scroll_area.setWidget(self.canvas)
        self.plot_tab_layout.addLayout(self.start_year_and_filename_layout)
        self.plot_tab.setLayout(self.plot_tab_layout)

        # Set layout for the Statistics Tab
        self.statistics_tab_layout = qtw.QVBoxLayout()
        self.statistics_tab_layout.addWidget(self.stats_table)
        self.statistics_tab.setLayout(self.statistics_tab_layout)

        # Create the Data Tab
        self.data_tab = qtw.QWidget()
        self.data_table = MyTableWidget(self.data_tab)
        self.data_table.itemChanged.connect(self.table_cell_changed)
        self.tab_widget.addTab(self.data_tab, "Data")

        # Set layout for the Data Tab
        self.data_tab_layout = qtw.QVBoxLayout()
        self.data_tab_layout.addWidget(self.data_table)
        self.data_tab.setLayout(self.data_tab_layout)

        # Add actions to the menus
        file_menu.addAction(open_action)
        file_menu.addAction(save_data_action)
        file_menu.addAction(save_stats_action)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        plot_menu.addAction(plot_action)

        # Add actions to the app toolbar
        self.app_toolbar.addAction(open_action)
        self.app_toolbar.addAction(save_data_action)
        self.app_toolbar.addAction(save_stats_action)
        self.app_toolbar.addAction(copy_action)
        self.app_toolbar.addAction(paste_action)
        self.app_toolbar.addAction(plot_action)

        # Add a system tray icon
        self.tray_icon = qtw.QSystemTrayIcon(self)
        tray_icon = self.load_icon(
            'icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/map.png',
            qtw.QStyle.StandardPixmap.SP_ComputerIcon
        )
        self.tray_icon.setIcon(tray_icon)
        self.tray_icon.setToolTip('ClearView')
        self.tray_icon.setVisible(True)
        self.tray_icon.show()

        # Fill the QTableWidget with data
        self.update_data_table()

        # Set tabs as central widget
        self.setCentralWidget(self.tab_widget)

        # Add a recent files list to the file menu
        self.recent_files_menu = file_menu.addMenu('Recent Files')
        self.recent_files_menu.aboutToShow.connect(self.update_recent_files_menu)
        
    def update_recent_files_menu(self):
        """
        Updates the recent files menu with the most recent files.

        This method updates the recent files menu with the most recent files.
        """
        self.recent_files_menu.clear()
        self.recent_files_menu.addAction('Clear Menu', self.clear_recent_files_menu)
        self.recent_files_menu.addSeparator()
        recent_files = self.get_recent_files()
        for file in recent_files:
            self.recent_files_menu.addAction(file, lambda checked, file=file: self.open_recent_file(file))

    def clear_recent_files_menu(self):
        """
        Clears the recent files menu.

        This method clears the recent files menu.
        """
        self.set_recent_files([])
        self.update_recent_files_menu()

    def get_recent_files(self):
        """
        Retrieves the recent files from the settings.

        This method retrieves the recent files from the settings.

        Returns:
            A list of recent files.
        """
        settings = qtc.QSettings()
        recent_files = settings.value('recent_files', [])
        return recent_files

    def set_recent_files(self, recent_files):
        """
        Sets the recent files in the settings.

        This method sets the recent files in the settings.

        Args:
            recent_files (list): A list of recent files.
        """
        settings = qtc.QSettings()
        settings.setValue('recent_files', recent_files)

    def update_stats_table(self):
        """
        Updates the statistics table based on the available data.

        This method computes descriptive statistics for the data stored in the `data` attribute and populates the statistics table (`self.stats_table`) with the results.
        If the `data` attribute is `None`, the method returns without performing any calculations.

        The statistics table is set up with the appropriate number of rows and columns based on the number of statistics and data columns.
        The header labels are set to display the column names, and the table cells are populated with the computed statistics.
        The formatting of the statistics values depends on their type:
        - The "count" statistic is displayed as an integer.
        - Other statistics are displayed as floating-point numbers with two decimal places.
        - If a value cannot be converted to a number, it is displayed as a string.

        Note:
            - The number of columns in the statistics table is equal to the number of data columns plus one, accounting for the index column that lists the statistics names.
            - The `data` attribute must be set with the data before calling this method.
        """
        if self.data is None:
            return

        self.stats = self.data.describe().reset_index()
        self.stats_table.setRowCount(len(self.stats))
        self.stats_table.setColumnCount(len(self.data.columns) + 1)

        header = ['']
        for col in self.data.columns:
            header.append(col)
        self.stats_table.setHorizontalHeaderLabels(header)

        for row in range(len(self.stats)):
            for col in range(len(self.data.columns) + 1):
                value = self.stats.iloc[row, col]
                try:
                    if col == 0:
                        value_text = str(value)
                    elif row == 0:
                        value_text = f'{int(value):d}'
                    else:
                        value_text = f'{value:.2f}'
                except ValueError:
                    value_text = str(value)
                item = qtw.QTableWidgetItem(value_text)
                item.setTextAlignment(0x0082)
                self.stats_table.setItem(row, col, item)

        # Autofit the column widths
        self.stats_table.resizeColumnsToContents()

    def update_data_table(self):
        """
        Updates the data table with the current data.

        This method takes the current data stored in the `data` attribute and updates the `data_table` widget accordingly.

        If the `data` attribute is not `None`, the method performs the following steps:
        1. Converts the DataFrame to a numpy array for efficiency.
        2. Converts the datetime index to a formatted string representation.
        3. Sets the table headers with the formatted datetime index and column names.
        4. Populates the table with the values from the numpy array, aligned and formatted.

        Note:
            This method assumes that the `data_table` widget has been properly initialized.
        """
        if self.data is not None:
            array_data = self.data.values
            
            # Handle different index types safely
            try:
                # Try to format as datetime if possible
                datetime_index = self.data.index.to_series().dt.strftime('%m/%d/%Y %H:%M')
                datetime_strings = datetime_index.tolist()
            except AttributeError:
                # Fall back to string representation for non-datetime indexes
                datetime_strings = [str(idx) for idx in self.data.index]

            header = ['Date']
            for col in self.data.columns:
                header.append(col)

            number_rows, number_columns = array_data.shape
            self.data_table.setRowCount(number_rows)
            self.data_table.setColumnCount(number_columns + 1)
            self.data_table.setHorizontalHeaderLabels(header)

            for row in range(number_rows):
                for column in range(number_columns + 1):
                    if column == 0:
                        item = qtw.QTableWidgetItem(datetime_strings[row])
                        item.setTextAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
                    else:
                        value = array_data[row, column - 1]
                        
                        # Safe formatting for different data types
                        try:
                            # Try to format as float first
                            if pd.isna(value):
                                value_text = 'NaN'
                            elif isinstance(value, (int, float)):
                                value_text = f'{float(value):.4f}'
                            else:
                                # For strings or other types, convert to string
                                value_text = str(value)
                        except (ValueError, TypeError):
                            # Fallback to string representation
                            value_text = str(value)
                        
                        item = qtw.QTableWidgetItem(value_text)
                        item.setTextAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
                    self.data_table.setItem(row, column, item)
        # Autofit the column widths
        self.data_table.resizeColumnsToContents()

    def parse_year_csv(self, w2_control_file_path):
        """
        Parses the year from a CSV file and sets it as the year attribute.

        This method reads a CSV file specified by `w2_control_file_path` and searches for a row where the first column (index 0)
        contains the value 'TMSTRT'. The year value is extracted from the subsequent row in the third column (index 2) and set
        as the year attribute of the class. Additionally, the extracted year is displayed in a QLineEdit widget with the object name
        'start_year_input'.

        Args:
            w2_control_file_path (str): The file path to the CSV file.
        """
        rows = []
        with open(w2_control_file_path, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                rows.append(row)
        for i, row in enumerate(rows):
            if row[0].upper() == 'TMSTRT':
                self.year = int(rows[i + 1][2])
                self.start_year_input.setText(str(self.year))

    def parse_year_npt(self, w2_control_file_path):
        """
        Parses the year from an NPT file and sets it as the year attribute.

        This method reads an NPT file specified by `w2_control_file_path` and searches for a line that starts with 'TMSTR' or 'TIME'.
        The subsequent line is then extracted, and the year value is obtained by removing the first 24 characters from the line
        and stripping any leading or trailing whitespace. The extracted year is then converted to an integer and set as the year
        attribute of the class. Additionally, the extracted year is displayed in a QLineEdit widget with the object name
        'start_year_input'.

        Args:
            w2_control_file_path (str): The file path to the NPT file.
        """
        with open(w2_control_file_path, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            line = line.strip().upper()
            if line.startswith('TMSTR') or line.startswith('TIME'):
                data_line = lines[i + 1]
                year_str = data_line[24:].strip()
                self.year = int(year_str)
                self.start_year_input.setText(str(self.year))

    def get_model_year(self):
        """
        Retrieves the model year from the CE-QUAL-W2 control file.

        This method locates the CE-QUAL-W2 control file in the specified directory by searching for specific filenames:
        - 'w2_con.csv'
        - '../w2_con.csv'
        - 'w2_con.npt'
        - '../w2_con.npt'

        Once the control file is found, its path and file type are stored in variables. The method then determines the file type
        (either CSV or NPT) and calls the appropriate parsing method (`parse_year_csv` or `parse_year_npt`) to extract the model year.
        The extracted year is then set as the year attribute of the class.

        Note:
            If no control file is found, a message is printed to indicate the absence of the file.
        """
        control_file_paths = [
            os.path.join(self.directory, 'w2_con.csv'),
            os.path.join(self.directory, '../w2_con.csv'),
            os.path.join(self.directory, 'w2_con.npt'),
            os.path.join(self.directory, '../w2_con.npt')
        ]

        w2_control_file_path = None
        w2_file_type = None

        for path in control_file_paths:
            if glob.glob(path):
                w2_control_file_path = path
                _, extension = os.path.splitext(path)
                w2_file_type = extension[1:].upper()
                break

        if w2_control_file_path is None:
            print('No control file found!')
            return

        print("w2_control_file_path =", w2_control_file_path)

        if w2_file_type == "CSV":
            self.parse_year_csv(w2_control_file_path)
        elif w2_file_type == "NPT":
            self.parse_year_npt(w2_control_file_path)

    def update_year(self, text):
        """
        Updates the year attribute based on the provided text.

        This method attempts to convert the `text` parameter to an integer and assigns it to the year attribute (`self.year`).
        If the conversion fails due to a `ValueError`, the year attribute is set to the default year value (`self.DEFAULT_YEAR`).

        Args:
            text (str): The text representing the new year value.
        """
        try:
            self.year = int(text)
        except ValueError:
            self.year = self.DEFAULT_YEAR

    def update_filename(self, text):
        """
        Updates the filename attribute with the provided text.

        This method updates the filename attribute (`self.filename`) with the given text value. The filename attribute represents
        the name of a file associated with the class or object.

        Args:
            text (str): The new filename text.
        """
        self.filename = text

    def load_excel_file(self, file_path):
        """
        Load data from Excel file with sheet selection support.
        
        Args:
            file_path (str): Path to Excel file
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            # Try to read the first sheet first
            xl_file = pd.ExcelFile(file_path)
            
            if len(xl_file.sheet_names) == 1:
                # Single sheet, load directly
                return pd.read_excel(file_path, index_col=0, parse_dates=True)
            else:
                # Multiple sheets, let user choose (for now, use first sheet)
                # TODO: Add sheet selection dialog
                sheet_name = xl_file.sheet_names[0]
                return pd.read_excel(file_path, sheet_name=sheet_name, index_col=0, parse_dates=True)
                
        except Exception as e:
            raise Exception(f"Error loading Excel file: {str(e)}")

    def load_hdf5_file(self, file_path):
        """
        Load data from HDF5 file.
        
        Args:
            file_path (str): Path to HDF5 file
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            # Try common HDF5 key names
            with pd.HDFStore(file_path, 'r') as store:
                keys = store.keys()
                if not keys:
                    raise ValueError("No datasets found in HDF5 file")
                
                # Use first key for now
                # TODO: Add key selection dialog for multiple datasets
                key = keys[0]
                return store[key]
                
        except Exception as e:
            raise Exception(f"Error loading HDF5 file: {str(e)}")

    def load_netcdf_file(self, file_path):
        """
        Load data from NetCDF file.
        
        Args:
            file_path (str): Path to NetCDF file
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            import xarray as xr
            
            # Load with xarray and convert to pandas
            ds = xr.open_dataset(file_path)
            
            # Convert to DataFrame (this may need customization based on data structure)
            df = ds.to_dataframe()
            
            # Reset index to make time a column if it's in the index
            if df.index.names and 'time' in df.index.names:
                df = df.reset_index()
                df = df.set_index('time')
            
            return df
            
        except ImportError:
            raise Exception("xarray library required for NetCDF support. Install with: pip install xarray")
        except Exception as e:
            raise Exception(f"Error loading NetCDF file: {str(e)}")

    def browse_file(self):
        """
        Browse and process a selected file.

        This method opens a file dialog to allow the user to browse and select a file. Once a file is selected, the method performs
        the following steps:
        1. Extracts the file path, directory, and filename.
        2. Sets the filename in a QLineEdit widget (`self.filename_input`).
        3. Determines the file extension and calls the appropriate methods to retrieve the data columns.
        4. Retrieves the model year using the `get_model_year` method.
        5. Attempts to read the data from the selected file using the extracted file path, year, and data columns.
        6. Displays a warning dialog if an error occurs while opening the file.
        7. Updates the data table and statistics table.

        Note:
            - Supported file extensions are '.csv', '.npt', and '.opt'.
            - The `update_data_table` and `update_stats_table` methods are called after processing the file.
        """
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setFileMode(qtw.QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilters([
            'All Files (*.*)', 
            'CSV Files (*.csv)', 
            'NPT Files (*.npt)',
            'OPT Files (*.opt)', 
            'Excel Files (*.xlsx *.xls)', 
            'SQLite Files (*.db *.sqlite)',
            'HDF5 Files (*.h5 *.hdf5)',
            'NetCDF Files (*.nc)'
        ])
        if file_dialog.exec():
            self.file_path = file_dialog.selectedFiles()[0]
            self.directory, self.filename = os.path.split(self.file_path)
            self.filename_input.setText(self.filename)
            basefilename, extension = os.path.splitext(self.filename)

            # Determine file type and setup
            if extension.lower() in ['.npt', '.opt']:
                self.data_columns = w2.get_data_columns_fixed_width(self.file_path)
                FILE_TYPE = 'ASCII'
            elif extension.lower() == '.csv':
                self.data_columns = w2.get_data_columns_csv(self.file_path)
                FILE_TYPE = 'ASCII'
            elif extension.lower() in ['.db', '.sqlite']:
                FILE_TYPE = 'SQLITE'
            elif extension.lower() in ['.xlsx', '.xls']:
                FILE_TYPE = 'EXCEL'
            elif extension.lower() in ['.h5', '.hdf5']:
                FILE_TYPE = 'HDF5'
            elif extension.lower() == '.nc':
                FILE_TYPE = 'NETCDF'
            else:
                self.show_warning_dialog(
                    f'Unsupported file format: {extension}\n'
                    'Supported formats: .csv, .npt, .opt, .db, .sqlite, .xlsx, .xls, .h5, .hdf5, .nc'
                )
                return

            self.get_model_year()

            try:
                if FILE_TYPE == 'ASCII':
                    # Add debugging information for CSV files
                    if extension.lower() == '.csv':
                        print(f"Attempting to read CSV file: {self.filename}")
                        print(f"Expected data columns: {self.data_columns}")
                        print(f"Number of expected columns: {len(self.data_columns)}")
                        
                        # Try to preview the file structure
                        try:
                            with open(self.file_path, 'r') as f:
                                first_few_lines = [f.readline().strip() for _ in range(3)]
                            print("First 3 lines of file:")
                            for i, line in enumerate(first_few_lines):
                                print(f"  Line {i}: {line}")
                                if line:
                                    print(f"    Columns in line: {len(line.split(','))}")
                        except Exception as preview_e:
                            print(f"Could not preview file: {preview_e}")
                    
                    self.data = w2.read(self.file_path, self.year, self.data_columns)
                elif FILE_TYPE == 'SQLITE':
                    self.data = w2.read_sqlite(self.file_path)
                elif FILE_TYPE == 'EXCEL':
                    self.data = self.load_excel_file(self.file_path)
                elif FILE_TYPE == 'HDF5':
                    self.data = self.load_hdf5_file(self.file_path)
                elif FILE_TYPE == 'NETCDF':
                    self.data = self.load_netcdf_file(self.file_path)
                else:
                    raise ValueError(f"Unsupported file type: {FILE_TYPE}")
                    
                # Validate that data was loaded successfully
                if self.data is None or self.data.empty:
                    self.show_warning_dialog(f'No data found in {self.filename}')
                    return
                    
            except FileNotFoundError:
                self.show_warning_dialog(f'File not found: {self.filename}')
                return
            except PermissionError:
                self.show_warning_dialog(f'Permission denied accessing: {self.filename}')
                return
            except pd.errors.EmptyDataError:
                self.show_warning_dialog(f'The file {self.filename} appears to be empty')
                return
            except pd.errors.ParserError as e:
                error_msg = f'Error parsing {self.filename}: {str(e)}'
                if extension.lower() == '.csv':
                    error_msg += '\n\nThis may be due to column structure mismatch. '
                    error_msg += 'The CSV file might have a different format than expected by CE-QUAL-W2.'
                self.show_warning_dialog(error_msg)
                return
            except OSError as e:
                if 'Error reading' in str(e) and extension.lower() == '.csv':
                    print(f"Primary CSV loader failed, trying fallback loader...")
                    fallback_data = self.load_csv_fallback(self.file_path)
                    
                    if fallback_data is not None:
                        self.data = fallback_data
                        print(f"✓ Fallback CSV loader succeeded!")
                        # Continue with normal processing
                    else:
                        error_msg = f'Error reading CSV file {self.filename}.\n\n'
                        error_msg += 'This may be due to:\n'
                        error_msg += '• Column structure mismatch\n'
                        error_msg += '• Missing or extra columns\n'
                        error_msg += '• Invalid header format\n\n'
                        error_msg += f'Technical error: {str(e)}'
                        self.show_warning_dialog(error_msg)
                        return
                else:
                    self.show_warning_dialog(f'Error reading file {self.filename}: {str(e)}')
                    return
            except Exception as e:
                self.show_warning_dialog(f'An unexpected error occurred while opening {self.filename}: {str(e)}')
                return

        self.update_data_table()
        self.update_stats_table()

    def resize_canvas(self, fig_width, fig_height):
        """
        Resize canvas, converting figure width and height in inches to pixels.

        :param fig_width: Width of the figure in inches.
        :type fig_width: float

        :param fig_height: Height of the figure in inches.
        :type fig_height: float

        :return: None
        :rtype: None
        """
        default_dpi = mpl.rcParams['figure.dpi']
        canvas_width = int(default_dpi * fig_width)
        canvas_height = int(default_dpi * fig_height)
        self.canvas.resize(canvas_width, canvas_height)

    def clear_figure_and_canvas(self):
        self.canvas.figure.clear()
        self.canvas.figure.clf()

    def show_column_picker_dialog(self):
        """Show column picker dialog and return selected columns."""
        if self.data is None:
            return None
            
        dialog = ColumnPickerDialog(self.data, self)
        if dialog.exec() == qtw.QDialog.DialogCode.Accepted:
            return dialog.get_selected_columns()
        return None

    def multi_plot(self):
        """
        Create intelligent multi-subplot visualizations with interactive column selection.
        
        This method implements the core "Smart Plot" functionality that replaces the old
        overwhelming multi-plot system. Instead of plotting all available columns (which
        could be 100+ parameters), it provides an intelligent interface for selecting
        specific time series data to visualize.
        
        Workflow:
        1. **Column Selection**: Opens ColumnPickerDialog with smart suggestions
        2. **Data Filtering**: Extracts only selected columns while preserving index
        3. **Layout Optimization**: Calculates optimal subplot dimensions and spacing
        4. **Plot Creation**: Uses cequalw2.multi_plot() with fallback matplotlib plotting
        5. **Canvas Update**: Refreshes display and updates statistics table
        
        Key Features:
        - Interactive column picker with water quality parameter suggestions
        - Automatic subplot height optimization based on selection count
        - Fallback plotting if cequalw2.multi_plot() encounters issues
        - Proper error handling with user-friendly warnings
        - Canvas resizing to accommodate different plot sizes
        
        The method intelligently handles various scenarios:
        - Large datasets (100+ columns) → Selective plotting prevents overwhelming UI
        - Small datasets (< 10 columns) → Still provides organized selection interface
        - Mixed data types → Filters to numeric columns only
        - Empty selections → Graceful cancellation without errors
        
        Height Calculation Algorithm:
        - Individual subplot height: 2.0-3.5 inches (adaptive based on count)
        - Maximum total height: 12 inches (prevents oversized plots)
        - Ensures readability while fitting in available screen space
        
        Returns:
            None: Method handles UI updates directly
            
        Side Effects:
            - May open ColumnPickerDialog (modal)
            - Updates matplotlib canvas and figure
            - Refreshes statistics table
            - May display warning dialogs for invalid data
            - Modifies canvas size to fit plot dimensions
            
        Note:
            This method is connected to the main "Plot" toolbar button and represents
            the primary plotting interface for the application. It replaces both the
            old "Single Plot" and "Multi-Plot" functionality with a unified, intelligent
            approach to data visualization.
        """
        # Check if data is available
        if self.data is None:
            return

        # Show column picker dialog
        selected_columns = self.show_column_picker_dialog()
        if not selected_columns:
            return  # User cancelled or no columns selected
        
        # Filter data to selected columns only - preserve index
        filtered_data = self.data[selected_columns].copy()
        
        # Ensure we have data to plot
        if filtered_data.empty:
            self.show_warning_dialog("No data to plot in selected columns.")
            return

        # Create the figure and canvas
        self.clear_figure_and_canvas()
        num_subplots = len(selected_columns)
        
        # Better subplot height calculation with reasonable maximum
        subplot_height = max(2.0, min(3.5, 10.0 / num_subplots))
        calculated_height = num_subplots * subplot_height
        
        # Cap the maximum height to prevent oversized plots
        max_reasonable_height = 12.0  # Maximum 12 inches
        multi_plot_fig_height = min(calculated_height, max_reasonable_height)
        
        # Create plots with filtered data
        try:
            w2.multi_plot(filtered_data, fig=self.canvas.figure, figsize=(self.default_fig_width, multi_plot_fig_height))
        except Exception as e:
            # If w2.multi_plot fails, try a simple matplotlib approach
            import matplotlib.pyplot as plt
            
            self.canvas.figure.clear()
            
            for i, col in enumerate(selected_columns):
                ax = self.canvas.figure.add_subplot(num_subplots, 1, i+1)
                ax.plot(filtered_data.index, filtered_data[col], label=col)
                ax.set_ylabel(col)
                ax.grid(True)
                if i == len(selected_columns) - 1:  # Last subplot
                    ax.set_xlabel('Index')
            
            self.canvas.figure.tight_layout()
        self.resize_canvas(self.default_fig_width, multi_plot_fig_height)

        # Draw the canvas and create or update the statistics table
        self.canvas.draw()
        self.update_stats_table()

    def reset_plot_view(self):
        """
        Reset plot view to display all data with auto-scaled axes (Home function).
        
        This method implements the "Home" button functionality in the matplotlib toolbar,
        restoring the plot to its initial state where all data points are visible with
        appropriately scaled axes. It's equivalent to the standard matplotlib home button
        but integrated with the custom PyQt6-compatible toolbar.
        
        Actions Performed:
        1. Delegates to matplotlib's native home() functionality via hidden toolbar
        2. Resets all plot axes to show complete data range
        3. Clears any active pan/zoom modes
        4. Updates toolbar button states to reflect neutral navigation state
        
        This is particularly useful after users have zoomed or panned the plot and want
        to return to the full overview of their time series data.
        
        Side Effects:
            - Redraws the matplotlib canvas
            - Unchecks pan and zoom toolbar buttons
            - Resets any stored navigation state in matplotlib
            - May trigger canvas refresh events
        """
        try:
            # Use matplotlib's home functionality
            self.mpl_toolbar.home()
            
            # Reset toolbar button states
            self.pan_action.setChecked(False)
            self.zoom_action.setChecked(False)
            
        except Exception as e:
            print(f"Warning: Could not reset plot view: {e}")
    
    def toggle_pan(self, checked):
        """
        Toggle pan mode for interactive plot navigation (drag to move view).
        
        Enables or disables matplotlib's pan functionality, allowing users to click and
        drag on the plot to move the visible area around. This is useful for exploring
        different sections of large time series datasets without changing the zoom level.
        
        The method ensures mutual exclusivity with zoom mode - activating pan will
        automatically deactivate zoom and vice versa, following standard matplotlib
        toolbar behavior patterns.
        
        Pan Mode Behavior:
        - **Activated**: Mouse cursor changes to hand icon, click-drag moves plot view
        - **Deactivated**: Returns to normal cursor, click-drag has no effect
        - **Auto-deactivates**: Zoom mode if it was previously active
        
        Args:
            checked (bool): True to activate pan mode, False to deactivate
            
        Technical Implementation:
        Uses the hidden NavigationToolbar2QT (self.mpl_toolbar) to access matplotlib's
        native pan functionality while maintaining the custom visual toolbar appearance.
        The pan() method acts as a toggle - calling it once activates, calling again
        deactivates.
        
        Side Effects:
            - Changes mouse cursor behavior on plot canvas
            - Updates zoom button state (unchecks if pan is activated)
            - May trigger matplotlib mode change events
        """
        try:
            if checked:
                # Uncheck zoom and activate pan
                self.zoom_action.setChecked(False)
                # Use matplotlib's pan functionality
                self.mpl_toolbar.pan()
            else:
                # Deactivate pan mode (toggle off)
                self.mpl_toolbar.pan()
                    
        except Exception as e:
            print(f"Warning: Pan functionality error: {e}")
    
    def toggle_zoom(self, checked):
        """
        Toggle zoom mode for interactive plot magnification (drag to select zoom area).
        
        Enables or disables matplotlib's zoom-to-rectangle functionality, allowing users
        to draw a rectangle around the area they want to examine in detail. This is
        essential for analyzing specific time periods or parameter ranges in detailed
        water quality datasets.
        
        The method ensures mutual exclusivity with pan mode - activating zoom will
        automatically deactivate pan mode, following standard matplotlib toolbar
        behavior patterns.
        
        Zoom Mode Behavior:
        - **Activated**: Mouse cursor changes to crosshair, click-drag creates zoom rectangle
        - **Rectangle Selection**: Releasing mouse button zooms to selected area
        - **Deactivated**: Returns to normal cursor behavior
        - **Auto-deactivates**: Pan mode if it was previously active
        
        Args:
            checked (bool): True to activate zoom mode, False to deactivate
            
        Technical Implementation:
        Uses the hidden NavigationToolbar2QT (self.mpl_toolbar) to access matplotlib's
        native zoom functionality while maintaining the custom visual toolbar appearance.
        The zoom() method acts as a toggle - calling it once activates, calling again
        deactivates.
        
        Usage Tips:
        - After zooming, use Home button (🏠) to return to full data view
        - Multiple zoom operations can be applied sequentially
        - Works on both X and Y axes simultaneously
        
        Side Effects:
            - Changes mouse cursor behavior on plot canvas
            - Updates pan button state (unchecks if zoom is activated)
            - May trigger matplotlib mode change events
            - Canvas redraws when zoom rectangle is applied
        """
        try:
            if checked:
                # Uncheck pan and activate zoom
                self.pan_action.setChecked(False)
                # Use matplotlib's zoom functionality
                self.mpl_toolbar.zoom()
            else:
                # Deactivate zoom mode (toggle off)
                self.mpl_toolbar.zoom()
                    
        except Exception as e:
            print(f"Warning: Zoom functionality error: {e}")

    def save_figure(self):
        """Save the current figure to a file."""
        try:
            file_path, _ = qtw.QFileDialog.getSaveFileName(
                self, 
                "Save Figure", 
                "", 
                "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
            )
            if file_path:
                self.canvas.figure.savefig(file_path, dpi=150, bbox_inches='tight')
        except Exception as e:
            self.show_warning_dialog(f"Error saving figure: {e}")

    def show_warning_dialog(self, message):
        """
        Displays a warning dialog with the given message.

        This method creates and shows a warning dialog box with the provided `message`. The dialog box includes a critical icon,
        a title, and the message text.

        Args:
            message (str): The warning message to be displayed.
        """
        message_box = qtw.QMessageBox()
        message_box.setIcon(qtw.QMessageBox.Icon.Critical)
        message_box.setWindowTitle('Error')
        message_box.setText(message)
        message_box.exec()

    def table_cell_changed(self, item):
        """
        Handles the change in a table cell value.

        This method is triggered when a cell value in the table widget (`self.data_table`) is changed.
        If the `data` attribute is not `None`, the method retrieves the row, column, and new value of the changed cell.
        If the column index is 0, it attempts to convert the value to a datetime object using the specified format.
        Otherwise, it attempts to convert the value to a float and updates the corresponding value in the `data` DataFrame.

        Note:
            - The table widget (`self.data_table`) must be properly set up and connected to this method.
            - The `data` attribute must be set with the data before calling this method.
        """
        if self.data is not None:
            row = item.row()
            col = item.column()
            value = item.text()

            try:
                if col == 0:
                    datetime_index = pd.to_datetime(value, format='%m/%d/%Y %H:%M')
                else:
                    self.data.iloc[row, col - 1] = float(value)
            except ValueError:
                # Silently ignore conversion errors - not all cells contain numeric data
                pass
            except IndexError:
                # Silently ignore index errors - table structure may be changing
                pass

    def save_to_sqlite(self, df: pd.DataFrame, database_path: str):
        """
        Saves the data to an SQLite database.

        This method saves the data stored in the `data` attribute to an SQLite database file specified by the `data_database_path` attribute.
        The table name is set as the `filename` attribute.
        If the database file already exists, the table with the same name is replaced.
        The data is saved with the index included as a column.

        Note:
            - The `data` attribute must be set with the data before calling this method.
            - The `data_database_path` attribute must be properly set with the path to the SQLite database file.
        """
        self.table_name, _ = os.path.splitext(self.filename)
        con = sqlite3.connect(database_path)
        df.to_sql(self.table_name, con, if_exists="replace", index=True)
        con.close()

    def save_to_hdf5(self, df, file_path):
        """Save dataframe to HDF5 format."""
        key = self.table_name if hasattr(self, 'table_name') else 'data'
        df.to_hdf(file_path, key=key, mode='w', complevel=9, complib='zlib')

    def save_to_excel(self, df, file_path):
        """Save dataframe to Excel format."""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Data', index=True)

    def save_to_csv(self, df, file_path):
        """Save dataframe to CSV format."""
        df.to_csv(file_path, index=True)

    def show_info_dialog(self, message):
        """Display an information dialog."""
        msg_box = qtw.QMessageBox()
        msg_box.setIcon(qtw.QMessageBox.Icon.Information)
        msg_box.setWindowTitle('Information')
        msg_box.setText(message)
        msg_box.exec()

    def save_data(self):
        """
        Saves the data to a selected file in multiple formats.

        This method allows the user to select a file path and format to save the data.
        Supported formats: SQLite, HDF5, Excel, CSV.
        """
        if self.data is None:
            self.show_warning_dialog("No data to save!")
            return
            
        default_filename = os.path.splitext(self.file_path)[0] if self.file_path else "data"
        file_filters = [
            "SQLite Files (*.db)",
            "HDF5 Files (*.h5)",
            "Excel Files (*.xlsx)",
            "CSV Files (*.csv)",
            "All Files (*)"
        ]
        
        returned_path, selected_filter = qtw.QFileDialog.getSaveFileName(
            self, "Save Data As", default_filename, ";;".join(file_filters)
        )
        
        if not returned_path:
            return

        try:
            # Determine format from file extension or filter
            _, ext = os.path.splitext(returned_path)
            
            if ext.lower() == '.db' or 'SQLite' in selected_filter:
                self.save_to_sqlite(self.data, returned_path)
            elif ext.lower() == '.h5' or 'HDF5' in selected_filter:
                self.save_to_hdf5(self.data, returned_path)
            elif ext.lower() == '.xlsx' or 'Excel' in selected_filter:
                self.save_to_excel(self.data, returned_path)
            elif ext.lower() == '.csv' or 'CSV' in selected_filter:
                self.save_to_csv(self.data, returned_path)
            else:
                # Default to SQLite
                if not ext:
                    returned_path += '.db'
                self.save_to_sqlite(self.data, returned_path)
            
            self.data_database_path = returned_path
            self.show_info_dialog(f"Data saved successfully to {returned_path}")
            self.update_stats_table()
            
        except Exception as e:
            self.show_warning_dialog(f"Error saving data: {str(e)}")

    def save_stats(self):
        """
        Saves statistics to an SQLite database file.

        Prompts the user to select a file path for saving the statistics and
        saves the statistics to the chosen file path.

        :return: None
        """

        default_filename = self.file_path + '_stats.db'
        returned_path, _ = qtw.QFileDialog.getSaveFileName(self, "Save As", default_filename,
                                                        "SQLite Files (*.db);; All Files (*)")
        if not returned_path:
            return

        self.stats_database_path = returned_path

        if self.stats_database_path and self.stats is not None:
            self.save_to_sqlite(self.stats, self.stats_database_path)
            self.update_stats_table()

    def parse_2x2_array(self, string):
        """
        Parse a 2x2 array from a string.

        The string should represent a 2x2 array with values separated by tabs
        for columns and newlines for rows. This method splits the string into rows
        and columns, and returns a NumPy array representing the 2x2 array.

        :param string: The string representation of the 2x2 array.
        :type string: str
        :return: The NumPy array representing the 2x2 array.
        :rtype: numpy.ndarray
        """
        rows = string.split('\n')
        array = [row.split('\t') for row in rows]
        return np.array(array)

    def load_csv_fallback(self, file_path):
        """
        Fallback CSV loader that can handle files with flexible column structures.
        
        This method tries to load CSV files without strict column expectations,
        which can help with TSR files or other CE-QUAL-W2 CSV outputs that might
        have different formats.
        """
        try:
            # First, try to load without any assumptions about columns
            df = pd.read_csv(file_path)
            print(f"Fallback loader: Successfully loaded CSV with shape {df.shape}")
            print(f"Columns found: {list(df.columns)}")
            
            # Convert numeric columns properly (handles scientific notation)
            for col in df.columns:
                if col != df.columns[0]:  # Skip the first column for now
                    try:
                        df[col] = pd.to_numeric(df[col], errors='ignore')
                    except Exception:
                        pass  # Keep as string if conversion fails
            
            # Try to set the first column as index if it looks like a time/date column
            if len(df.columns) > 1:
                first_col = df.columns[0]
                if any(keyword in first_col.lower() for keyword in ['time', 'date', 'jday', 'day']):
                    # Convert first column to numeric if possible
                    try:
                        df[first_col] = pd.to_numeric(df[first_col], errors='ignore')
                    except Exception:
                        pass
                    df = df.set_index(first_col)
                    print(f"Set '{first_col}' as index")
            
            print(f"Data types after processing: {df.dtypes.value_counts()}")
            return df
            
        except Exception as e:
            print(f"Fallback CSV loader also failed: {e}")
            return None

    def copy_data(self):
        """
        Copy the selected data from the current tab's table widget to the clipboard.

        This method checks the current index of the tab widget and determines the
        corresponding table widget to work with. It then copies the selected cells
        from the table widget and sets the resulting string as the text content of
        the clipboard.
        """
        if self.tab_widget.currentIndex() == 1:
            table_widget = self.stats_table
        elif self.tab_widget.currentIndex() == 2:
            table_widget = self.data_table
        else:
            return

        selected = table_widget.selectedRanges()
        if selected:
            s = ''
            for row in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                for col in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                    s += str(table_widget.item(row, col).text()) + '\t'
                s = s.strip() + '\n'
            s = s.strip()
            qtw.QApplication.clipboard().setText(s)

    def paste_data(self):
        """
        Paste data from the clipboard into the selected cells of the current tab's table widget.

        This method checks the current index of the tab widget and determines the
        corresponding table widget to work with. It retrieves the data from the clipboard,
        parses it into a NumPy array using the parse_2x2_array() method, and then inserts
        the values into the selected cells of the table widget.
        """
        if self.tab_widget.currentIndex() == 1:
            table_widget = self.stats_table
        elif self.tab_widget.currentIndex() == 2:
            table_widget = self.data_table
        else:
            return

        selected = table_widget.selectedRanges()
        if selected:
            s = qtw.QApplication.clipboard().text()
            values = self.parse_2x2_array(s)
            nrows, ncols = values.shape
            maxcol = table_widget.columnCount()
            maxrow = table_widget.rowCount()
            # print(maxcol, maxrow, type(maxcol), type(maxrow))

            top_row = selected[0].topRow()
            left_col = selected[0].leftColumn()

            for i, row in enumerate(range(nrows)):
                row = top_row + i
                for j, col in enumerate(range(ncols)):
                    col = left_col + j
                    if row < maxrow and col < maxcol:
                        table_widget.setItem(row, col, qtw.QTableWidgetItem(values[i][j]))


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    window = ClearView()
    window.show()
    sys.exit(app.exec())
