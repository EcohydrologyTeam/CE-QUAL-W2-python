"""
View components for ClearView application.
Handles UI elements, layouts, and user interactions.
"""

import os
import pandas as pd
import numpy as np

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
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from typing import Optional, Dict, Any, List
from models import FilterOperator, DataFilter, ValidationResult, PlotType, PlotStyle, PlotConfiguration


class MyTableWidget(qtw.QTableWidget):
    """Custom QTableWidget with enhanced navigation."""
    
    def __init__(self, parent):
        super().__init__(parent)
    
    def keyPressEvent(self, event):
        """Handle Enter/Return key to move to next cell."""
        if event.key() == qtc.Qt.Key_Enter or event.key() == qtc.Qt.Key_Return:
            current_row = self.currentRow()
            current_column = self.currentColumn()
            total_rows = self.rowCount()
            total_columns = self.columnCount()
            
            if current_row < total_rows - 1:
                self.setCurrentCell(current_row + 1, current_column)
            elif current_column < total_columns - 1:
                self.setCurrentCell(0, current_column + 1)
            else:
                self.setCurrentCell(0, 0)
        else:
            super().keyPressEvent(event)


class ClearViewMainWindow(qtw.QMainWindow):
    """Main window view for ClearView application."""
    
    # UI Constants
    DEFAULT_WINDOW_WIDTH = 1500
    DEFAULT_WINDOW_HEIGHT = 900
    DEFAULT_FIG_WIDTH = 12
    DEFAULT_FIG_HEIGHT = 6
    ICON_SIZE = 24
    
    # Signals
    file_opened = qtc.pyqtSignal(str)
    cell_changed = qtc.pyqtSignal(int, int, str)
    year_changed = qtc.pyqtSignal(str)
    filename_changed = qtc.pyqtSignal(str)
    plot_requested = qtc.pyqtSignal()
    multi_plot_requested = qtc.pyqtSignal()
    save_data_requested = qtc.pyqtSignal()
    save_stats_requested = qtc.pyqtSignal()
    copy_requested = qtc.pyqtSignal()
    paste_requested = qtc.pyqtSignal()
    validation_requested = qtc.pyqtSignal()
    filter_applied = qtc.pyqtSignal(list)  # List of DataFilter objects
    duplicates_removal_requested = qtc.pyqtSignal()
    missing_data_handling_requested = qtc.pyqtSignal(str)  # method name
    custom_plot_requested = qtc.pyqtSignal(object)  # PlotConfiguration object
    plot_export_requested = qtc.pyqtSignal(str)  # export format
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle('ClearView')
        self.setGeometry(0, 0, self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
        self.center_on_screen()
        
        # Initialize figure dimensions
        self.default_fig_width = self.DEFAULT_FIG_WIDTH
        self.default_fig_height = self.DEFAULT_FIG_HEIGHT
        
        # Set up assets directory path
        self.assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets')
        
        # Initialize UI components
        self._setup_ui()
        
        # Create system tray if available
        if qtw.QSystemTrayIcon.isSystemTrayAvailable():
            self._create_tray_icon()
    
    def center_on_screen(self):
        """Center the window on the screen."""
        screen = qtw.QApplication.desktop().screenGeometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)
    
    def load_icon(self, icon_path, fallback_style=None):
        """Safely load an icon with fallback."""
        full_path = os.path.join(self.assets_dir, icon_path)
        if os.path.exists(full_path):
            return qtg.QIcon(full_path)
        elif fallback_style:
            return qtg.QIcon(self.style().standardIcon(fallback_style))
        else:
            return qtg.QIcon(self.style().standardIcon(qtw.QStyle.SP_FileIcon))
    
    def _setup_ui(self):
        """Set up the user interface components."""
        self._create_menus()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()
    
    def _create_menus(self):
        """Create the menu bar and menus."""
        menubar = self.menuBar()
        
        # File menu
        self.file_menu = menubar.addMenu('File')
        self.recent_files_menu = self.file_menu.addMenu('Recent Files')
        
        # Edit menu
        self.edit_menu = menubar.addMenu('Edit')
        
        # Save menu
        self.save_menu = menubar.addMenu('Save')
        
        # Plot menu
        self.plot_menu = menubar.addMenu('Plot')
        
        self._create_menu_actions()
    
    def _create_menu_actions(self):
        """Create menu actions."""
        # File actions
        open_action = qtw.QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._on_open_file)
        self.file_menu.addAction(open_action)
        
        clear_recent_action = qtw.QAction('Clear Recent Files', self)
        clear_recent_action.triggered.connect(self._on_clear_recent_files)
        self.recent_files_menu.addAction(clear_recent_action)
        
        # Edit actions
        copy_action = qtw.QAction('Copy', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(lambda: self.copy_requested.emit())
        self.edit_menu.addAction(copy_action)
        
        paste_action = qtw.QAction('Paste', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(lambda: self.paste_requested.emit())
        self.edit_menu.addAction(paste_action)
        
        # Save actions
        save_data_action = qtw.QAction('Save Data', self)
        save_data_action.triggered.connect(lambda: self.save_data_requested.emit())
        self.save_menu.addAction(save_data_action)
        
        save_stats_action = qtw.QAction('Save Statistics', self)
        save_stats_action.triggered.connect(lambda: self.save_stats_requested.emit())
        self.save_menu.addAction(save_stats_action)
        
        # Plot actions
        plot_action = qtw.QAction('Plot', self)
        plot_action.triggered.connect(lambda: self.plot_requested.emit())
        self.plot_menu.addAction(plot_action)
        
        multi_plot_action = qtw.QAction('Multi Plot', self)
        multi_plot_action.triggered.connect(lambda: self.multi_plot_requested.emit())
        self.plot_menu.addAction(multi_plot_action)
    
    def _create_toolbar(self):
        """Create the toolbar."""
        self.app_toolbar = self.addToolBar('Toolbar')
        self.app_toolbar.setToolButtonStyle(qtc.Qt.ToolButtonTextUnderIcon)
        
        # Open file action
        open_icon = self.load_icon('folder-open-24.png', qtw.QStyle.SP_DirOpenIcon)
        open_action = qtw.QAction(open_icon, 'Open', self)
        open_action.triggered.connect(self._on_open_file)
        self.app_toolbar.addAction(open_action)
        
        self.app_toolbar.addSeparator()
        
        # Plot action
        plot_icon = self.load_icon('bar-chart-2-24.png', qtw.QStyle.SP_ComputerIcon)
        plot_action = qtw.QAction(plot_icon, 'Plot', self)
        plot_action.triggered.connect(lambda: self.plot_requested.emit())
        self.app_toolbar.addAction(plot_action)
        
        # Multi plot action
        multi_plot_icon = self.load_icon('grid-24.png', qtw.QStyle.SP_ComputerIcon)
        multi_plot_action = qtw.QAction(multi_plot_icon, 'Multi Plot', self)
        multi_plot_action.triggered.connect(lambda: self.multi_plot_requested.emit())
        self.app_toolbar.addAction(multi_plot_action)
        
        self.app_toolbar.addSeparator()
        
        # Save actions
        save_icon = self.load_icon('save-24.png', qtw.QStyle.SP_DialogSaveButton)
        save_action = qtw.QAction(save_icon, 'Save', self)
        save_action.triggered.connect(lambda: self.save_data_requested.emit())
        self.app_toolbar.addAction(save_action)
    
    def _create_central_widget(self):
        """Create the central widget with tabs and tables."""
        central_widget = qtw.QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = qtw.QVBoxLayout(central_widget)
        
        # Create input controls
        self._create_input_controls(main_layout)
        
        # Create tab widget
        self.tab_widget = qtw.QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Data tab
        self._create_data_tab()
        
        # Statistics tab
        self._create_stats_tab()
        
        # Plot tab
        self._create_plot_tab()
        
        # Validation tab
        self._create_validation_tab()
        
        # Filtering tab
        self._create_filtering_tab()
    
    def _create_input_controls(self, layout):
        """Create input controls for year and filename."""
        controls_layout = qtw.QHBoxLayout()
        
        # Year input
        controls_layout.addWidget(qtw.QLabel('Year:'))
        self.year_edit = qtw.QLineEdit()
        self.year_edit.setMaximumWidth(100)
        self.year_edit.textChanged.connect(lambda text: self.year_changed.emit(text))
        controls_layout.addWidget(self.year_edit)
        
        controls_layout.addSpacing(20)
        
        # Filename input
        controls_layout.addWidget(qtw.QLabel('Filename:'))
        self.filename_edit = qtw.QLineEdit()
        self.filename_edit.textChanged.connect(lambda text: self.filename_changed.emit(text))
        controls_layout.addWidget(self.filename_edit)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
    
    def _create_data_tab(self):
        """Create the data tab with table."""
        self.data_table = MyTableWidget(self)
        self.data_table.itemChanged.connect(self._on_table_item_changed)
        self.tab_widget.addTab(self.data_table, 'Data')
    
    def _create_stats_tab(self):
        """Create the statistics tab with table."""
        self.stats_table = qtw.QTableWidget()
        self.stats_table.setColumnCount(6)
        self.stats_table.setHorizontalHeaderLabels(['Variable', 'Count', 'Mean', 'Std', 'Min', 'Max'])
        self.tab_widget.addTab(self.stats_table, 'Statistics')
    
    def _create_plot_tab(self):
        """Create the enhanced plot tab with customization controls."""
        plot_widget = qtw.QWidget()
        plot_layout = qtw.QHBoxLayout(plot_widget)
        
        # Left panel: Plot controls
        controls_panel = qtw.QWidget()
        controls_panel.setMaximumWidth(350)
        controls_layout = qtw.QVBoxLayout(controls_panel)
        
        # Plot type selection
        plot_type_group = qtw.QGroupBox("Plot Type")
        plot_type_layout = qtw.QVBoxLayout(plot_type_group)
        
        self.plot_type_combo = qtw.QComboBox()
        self.plot_type_combo.addItems([
            "Line Plot", "Scatter Plot", "Bar Plot", "Histogram", 
            "Box Plot", "Violin Plot", "Area Plot", "Step Plot",
            "Stem Plot", "Pie Chart", "Heatmap", "Correlation Matrix"
        ])
        plot_type_layout.addWidget(self.plot_type_combo)
        controls_layout.addWidget(plot_type_group)
        
        # Column selection
        columns_group = qtw.QGroupBox("Data Columns")
        columns_layout = qtw.QFormLayout(columns_group)
        
        self.x_column_combo = qtw.QComboBox()
        self.x_column_combo.addItem("Index (default)")
        columns_layout.addRow("X-axis:", self.x_column_combo)
        
        self.y_columns_list = qtw.QListWidget()
        self.y_columns_list.setMaximumHeight(120)
        self.y_columns_list.setSelectionMode(qtw.QAbstractItemView.MultiSelection)
        columns_layout.addRow("Y-axis:", self.y_columns_list)
        
        controls_layout.addWidget(columns_group)
        
        # Plot styling
        styling_group = qtw.QGroupBox("Styling")
        styling_layout = qtw.QFormLayout(styling_group)
        
        self.plot_style_combo = qtw.QComboBox()
        self.plot_style_combo.addItems([
            "Default", "Seaborn", "Classic", "GGPlot", 
            "FiveThirtyEight", "BMH", "Dark Background"
        ])
        styling_layout.addRow("Style:", self.plot_style_combo)
        
        self.color_scheme_combo = qtw.QComboBox()
        self.color_scheme_combo.addItems([
            "tab10", "viridis", "plasma", "inferno", "magma",
            "Set1", "Set2", "Set3", "Pastel1", "Pastel2"
        ])
        styling_layout.addRow("Colors:", self.color_scheme_combo)
        
        controls_layout.addWidget(styling_group)
        
        # Plot customization
        customization_group = qtw.QGroupBox("Customization")
        customization_layout = qtw.QFormLayout(customization_group)
        
        self.title_edit = qtw.QLineEdit()
        self.title_edit.setPlaceholderText("Plot Title")
        customization_layout.addRow("Title:", self.title_edit)
        
        self.xlabel_edit = qtw.QLineEdit()
        self.xlabel_edit.setPlaceholderText("X-axis Label")
        customization_layout.addRow("X Label:", self.xlabel_edit)
        
        self.ylabel_edit = qtw.QLineEdit()
        self.ylabel_edit.setPlaceholderText("Y-axis Label")
        customization_layout.addRow("Y Label:", self.ylabel_edit)
        
        # Figure size
        size_layout = qtw.QHBoxLayout()
        self.width_spin = qtw.QSpinBox()
        self.width_spin.setRange(4, 20)
        self.width_spin.setValue(12)
        self.height_spin = qtw.QSpinBox()
        self.height_spin.setRange(3, 15)
        self.height_spin.setValue(6)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(qtw.QLabel("x"))
        size_layout.addWidget(self.height_spin)
        customization_layout.addRow("Size (in):", size_layout)
        
        controls_layout.addWidget(customization_group)
        
        # Plot options
        options_group = qtw.QGroupBox("Options")
        options_layout = qtw.QVBoxLayout(options_group)
        
        self.grid_cb = qtw.QCheckBox("Show Grid")
        self.grid_cb.setChecked(True)
        options_layout.addWidget(self.grid_cb)
        
        self.legend_cb = qtw.QCheckBox("Show Legend")
        self.legend_cb.setChecked(True)
        options_layout.addWidget(self.legend_cb)
        
        self.statistics_cb = qtw.QCheckBox("Show Statistics")
        options_layout.addWidget(self.statistics_cb)
        
        self.log_x_cb = qtw.QCheckBox("Log Scale X")
        options_layout.addWidget(self.log_x_cb)
        
        self.log_y_cb = qtw.QCheckBox("Log Scale Y")
        options_layout.addWidget(self.log_y_cb)
        
        controls_layout.addWidget(options_group)
        
        # Buttons
        buttons_layout = qtw.QVBoxLayout()
        
        create_plot_btn = qtw.QPushButton("Create Plot")
        create_plot_btn.clicked.connect(self._create_custom_plot)
        buttons_layout.addWidget(create_plot_btn)
        
        export_plot_btn = qtw.QPushButton("Export Plot")
        export_plot_btn.clicked.connect(self._export_plot)
        buttons_layout.addWidget(export_plot_btn)
        
        # Quick plot buttons
        quick_group = qtw.QGroupBox("Quick Plots")
        quick_layout = qtw.QVBoxLayout(quick_group)
        
        quick_line_btn = qtw.QPushButton("Quick Line Plot")
        quick_line_btn.clicked.connect(lambda: self._quick_plot("line"))
        quick_layout.addWidget(quick_line_btn)
        
        quick_scatter_btn = qtw.QPushButton("Quick Scatter")
        quick_scatter_btn.clicked.connect(lambda: self._quick_plot("scatter"))
        quick_layout.addWidget(quick_scatter_btn)
        
        quick_hist_btn = qtw.QPushButton("Quick Histogram")
        quick_hist_btn.clicked.connect(lambda: self._quick_plot("histogram"))
        quick_layout.addWidget(quick_hist_btn)
        
        buttons_layout.addWidget(quick_group)
        
        controls_layout.addLayout(buttons_layout)
        controls_layout.addStretch()
        
        # Right panel: Plot canvas
        canvas_panel = qtw.QWidget()
        canvas_layout = qtw.QVBoxLayout(canvas_panel)
        
        # Create matplotlib figure and canvas
        self.fig = plt.figure(figsize=(self.default_fig_width, self.default_fig_height))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, canvas_panel)
        
        canvas_layout.addWidget(self.toolbar)
        canvas_layout.addWidget(self.canvas)
        
        # Add panels to main layout
        plot_layout.addWidget(controls_panel)
        plot_layout.addWidget(canvas_panel, stretch=1)
        
        self.tab_widget.addTab(plot_widget, 'Advanced Plotting')
    
    def _create_validation_tab(self):
        """Create the validation tab with validation controls and results."""
        validation_widget = qtw.QWidget()
        validation_layout = qtw.QVBoxLayout(validation_widget)
        
        # Validation controls
        controls_group = qtw.QGroupBox("Data Validation")
        controls_layout = qtw.QHBoxLayout(controls_group)
        
        validate_btn = qtw.QPushButton("Validate Data")
        validate_btn.clicked.connect(lambda: self.validation_requested.emit())
        controls_layout.addWidget(validate_btn)
        
        remove_duplicates_btn = qtw.QPushButton("Remove Duplicates")
        remove_duplicates_btn.clicked.connect(lambda: self.duplicates_removal_requested.emit())
        controls_layout.addWidget(remove_duplicates_btn)
        
        # Missing data handling
        missing_data_combo = qtw.QComboBox()
        missing_data_combo.addItems(["Drop Missing", "Fill Missing", "Interpolate"])
        missing_data_combo.currentTextChanged.connect(
            lambda text: self.missing_data_handling_requested.emit(text.lower().replace(" ", "_"))
        )
        controls_layout.addWidget(qtw.QLabel("Missing Data:"))
        controls_layout.addWidget(missing_data_combo)
        
        controls_layout.addStretch()
        validation_layout.addWidget(controls_group)
        
        # Validation results area
        results_group = qtw.QGroupBox("Validation Results")
        results_layout = qtw.QVBoxLayout(results_group)
        
        self.validation_results = qtw.QTextEdit()
        self.validation_results.setReadOnly(True)
        self.validation_results.setMaximumHeight(150)
        results_layout.addWidget(self.validation_results)
        
        validation_layout.addWidget(results_group)
        
        # Column information table
        column_info_group = qtw.QGroupBox("Column Information")
        column_info_layout = qtw.QVBoxLayout(column_info_group)
        
        self.column_info_table = qtw.QTableWidget()
        self.column_info_table.setColumnCount(7)
        self.column_info_table.setHorizontalHeaderLabels([
            'Column', 'Type', 'Non-Null', 'Null', 'Unique', 'Sample Values', 'Notes'
        ])
        column_info_layout.addWidget(self.column_info_table)
        
        validation_layout.addWidget(column_info_group)
        
        self.tab_widget.addTab(validation_widget, 'Validation')
    
    def _create_filtering_tab(self):
        """Create the filtering tab with filter controls."""
        filtering_widget = qtw.QWidget()
        filtering_layout = qtw.QVBoxLayout(filtering_widget)
        
        # Filter controls
        controls_group = qtw.QGroupBox("Data Filters")
        controls_layout = qtw.QVBoxLayout(controls_group)
        
        # Filter creation area
        filter_creation_layout = qtw.QGridLayout()
        
        filter_creation_layout.addWidget(qtw.QLabel("Column:"), 0, 0)
        self.filter_column_combo = qtw.QComboBox()
        filter_creation_layout.addWidget(self.filter_column_combo, 0, 1)
        
        filter_creation_layout.addWidget(qtw.QLabel("Operator:"), 0, 2)
        self.filter_operator_combo = qtw.QComboBox()
        self.filter_operator_combo.addItems([
            "equals", "not_equals", "greater_than", "greater_equal",
            "less_than", "less_equal", "contains", "starts_with",
            "ends_with", "is_null", "not_null", "between"
        ])
        filter_creation_layout.addWidget(self.filter_operator_combo, 0, 3)
        
        filter_creation_layout.addWidget(qtw.QLabel("Value:"), 1, 0)
        self.filter_value_edit = qtw.QLineEdit()
        filter_creation_layout.addWidget(self.filter_value_edit, 1, 1)
        
        filter_creation_layout.addWidget(qtw.QLabel("Value 2:"), 1, 2)
        self.filter_value2_edit = qtw.QLineEdit()
        self.filter_value2_edit.setPlaceholderText("For 'between' operator")
        filter_creation_layout.addWidget(self.filter_value2_edit, 1, 3)
        
        # Case sensitive checkbox
        self.case_sensitive_cb = qtw.QCheckBox("Case Sensitive")
        self.case_sensitive_cb.setChecked(True)
        filter_creation_layout.addWidget(self.case_sensitive_cb, 2, 0)
        
        # Add and clear filter buttons
        filter_buttons_layout = qtw.QHBoxLayout()
        add_filter_btn = qtw.QPushButton("Add Filter")
        add_filter_btn.clicked.connect(self._add_filter)
        filter_buttons_layout.addWidget(add_filter_btn)
        
        clear_filters_btn = qtw.QPushButton("Clear All")
        clear_filters_btn.clicked.connect(self._clear_filters)
        filter_buttons_layout.addWidget(clear_filters_btn)
        
        apply_filters_btn = qtw.QPushButton("Apply Filters")
        apply_filters_btn.clicked.connect(self._apply_filters)
        filter_buttons_layout.addWidget(apply_filters_btn)
        
        filter_buttons_layout.addStretch()
        filter_creation_layout.addLayout(filter_buttons_layout, 2, 1, 1, 3)
        
        controls_layout.addLayout(filter_creation_layout)
        filtering_layout.addWidget(controls_group)
        
        # Active filters list
        active_filters_group = qtw.QGroupBox("Active Filters")
        active_filters_layout = qtw.QVBoxLayout(active_filters_group)
        
        self.active_filters_list = qtw.QListWidget()
        active_filters_layout.addWidget(self.active_filters_list)
        
        filtering_layout.addWidget(active_filters_group)
        
        # Filtered data preview
        preview_group = qtw.QGroupBox("Filtered Data Preview")
        preview_layout = qtw.QVBoxLayout(preview_group)
        
        self.filtered_data_table = qtw.QTableWidget()
        preview_layout.addWidget(self.filtered_data_table)
        
        filtering_layout.addWidget(preview_group)
        
        # Store active filters
        self.active_filters = []
        
        self.tab_widget.addTab(filtering_widget, 'Filtering')
    
    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready')
    
    def _create_tray_icon(self):
        """Create system tray icon."""
        self.tray_icon = qtw.QSystemTrayIcon(self)
        tray_icon_image = self.load_icon('ClearView24.png', qtw.QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(tray_icon_image)
        
        # Create tray menu
        tray_menu = qtw.QMenu()
        show_action = qtw.QAction('Show', self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = qtw.QAction('Quit', self)
        quit_action.triggered.connect(qtw.QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    # Event handlers
    def _on_open_file(self):
        """Handle open file action."""
        file_path, _ = qtw.QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "All Supported (*.csv *.npt *.opt *.xls *.xlsx *.h5 *.hdf5 *.nc);;"
            "CSV Files (*.csv);;"
            "NPT Files (*.npt);;"
            "OPT Files (*.opt);;"
            "Excel Files (*.xls *.xlsx);;"
            "HDF5 Files (*.h5 *.hdf5);;"
            "NetCDF Files (*.nc)"
        )
        
        if file_path:
            self.file_opened.emit(file_path)
    
    def _on_table_item_changed(self, item):
        """Handle table item changes."""
        row = item.row()
        col = item.column()
        value = item.text()
        self.cell_changed.emit(row, col, value)
    
    def _on_clear_recent_files(self):
        """Handle clear recent files action."""
        self.recent_files_menu.clear()
        clear_action = qtw.QAction('Clear Recent Files', self)
        clear_action.triggered.connect(self._on_clear_recent_files)
        self.recent_files_menu.addAction(clear_action)
    
    # Public methods for updating UI
    def update_data_table(self, df: pd.DataFrame):
        """Update the data table with new dataframe."""
        if df is None or df.empty:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
        
        # Set table dimensions
        self.data_table.setRowCount(len(df))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(df.columns.astype(str))
        
        # Populate table
        for i, row in df.iterrows():
            for j, value in enumerate(row):
                if pd.isna(value):
                    item = qtw.QTableWidgetItem("")
                else:
                    item = qtw.QTableWidgetItem(str(value))
                self.data_table.setItem(i, j, item)
    
    def update_stats_table(self, stats: Dict[str, Any]):
        """Update the statistics table."""
        self.stats_table.setRowCount(len(stats))
        
        for i, (var_name, var_stats) in enumerate(stats.items()):
            self.stats_table.setItem(i, 0, qtw.QTableWidgetItem(var_name))
            self.stats_table.setItem(i, 1, qtw.QTableWidgetItem(str(var_stats.get('count', ''))))
            self.stats_table.setItem(i, 2, qtw.QTableWidgetItem(f"{var_stats.get('mean', 0):.2f}"))
            self.stats_table.setItem(i, 3, qtw.QTableWidgetItem(f"{var_stats.get('std', 0):.2f}"))
            self.stats_table.setItem(i, 4, qtw.QTableWidgetItem(f"{var_stats.get('min', 0):.2f}"))
            self.stats_table.setItem(i, 5, qtw.QTableWidgetItem(f"{var_stats.get('max', 0):.2f}"))
    
    def update_recent_files_menu(self, recent_files):
        """Update the recent files menu."""
        self.recent_files_menu.clear()
        
        for file_path in recent_files[:10]:  # Show only 10 recent files
            if os.path.exists(file_path):
                action = qtw.QAction(os.path.basename(file_path), self)
                action.triggered.connect(lambda checked, path=file_path: self.file_opened.emit(path))
                self.recent_files_menu.addAction(action)
        
        if recent_files:
            self.recent_files_menu.addSeparator()
        
        clear_action = qtw.QAction('Clear Recent Files', self)
        clear_action.triggered.connect(self._on_clear_recent_files)
        self.recent_files_menu.addAction(clear_action)
    
    def set_year(self, year: Optional[int]):
        """Set the year in the input field."""
        if year is not None:
            self.year_edit.setText(str(year))
        else:
            self.year_edit.clear()
    
    def set_filename(self, filename: str):
        """Set the filename in the input field."""
        self.filename_edit.setText(filename)
    
    # Filtering helper methods
    def _add_filter(self):
        """Add a new filter to the active filters list."""
        column = self.filter_column_combo.currentText()
        operator_text = self.filter_operator_combo.currentText()
        value = self.filter_value_edit.text()
        value2 = self.filter_value2_edit.text()
        case_sensitive = self.case_sensitive_cb.isChecked()
        
        if not column or not value:
            return
        
        # Map operator text to enum
        operator_map = {
            "equals": FilterOperator.EQUALS,
            "not_equals": FilterOperator.NOT_EQUALS,
            "greater_than": FilterOperator.GREATER_THAN,
            "greater_equal": FilterOperator.GREATER_EQUAL,
            "less_than": FilterOperator.LESS_THAN,
            "less_equal": FilterOperator.LESS_EQUAL,
            "contains": FilterOperator.CONTAINS,
            "starts_with": FilterOperator.STARTS_WITH,
            "ends_with": FilterOperator.ENDS_WITH,
            "is_null": FilterOperator.IS_NULL,
            "not_null": FilterOperator.NOT_NULL,
            "between": FilterOperator.BETWEEN
        }
        
        operator = operator_map.get(operator_text, FilterOperator.EQUALS)
        
        # Create filter object
        data_filter = DataFilter(
            column=column,
            operator=operator,
            value=value,
            value2=value2 if value2 else None,
            case_sensitive=case_sensitive
        )
        
        self.active_filters.append(data_filter)
        
        # Update UI
        self._update_active_filters_list()
        
        # Clear input fields
        self.filter_value_edit.clear()
        self.filter_value2_edit.clear()
    
    def _clear_filters(self):
        """Clear all active filters."""
        self.active_filters.clear()
        self._update_active_filters_list()
        self.filtered_data_table.setRowCount(0)
        self.filtered_data_table.setColumnCount(0)
    
    def _apply_filters(self):
        """Apply active filters and emit signal."""
        if self.active_filters:
            self.filter_applied.emit(self.active_filters)
    
    def _update_active_filters_list(self):
        """Update the active filters list widget."""
        self.active_filters_list.clear()
        
        for i, filter_obj in enumerate(self.active_filters):
            filter_text = f"{filter_obj.column} {filter_obj.operator.value}"
            if filter_obj.value is not None:
                filter_text += f" {filter_obj.value}"
            if filter_obj.value2 is not None:
                filter_text += f" AND {filter_obj.value2}"
            
            item = qtw.QListWidgetItem(filter_text)
            item.setData(qtc.Qt.UserRole, i)  # Store filter index
            self.active_filters_list.addItem(item)
    
    def update_filter_columns(self, columns: List[str]):
        """Update the column options in the filter dropdown."""
        self.filter_column_combo.clear()
        self.filter_column_combo.addItems(columns)
    
    def update_validation_results(self, validation_result: ValidationResult):
        """Update the validation results display."""
        # Update text area
        result_text = f"Data Validation Results:\n"
        result_text += f"{'=' * 30}\n"
        result_text += f"Status: {'VALID' if validation_result.is_valid else 'INVALID'}\n"
        result_text += f"Rows: {validation_result.row_count}\n"
        result_text += f"Columns: {validation_result.column_count}\n"
        result_text += f"Missing Values: {validation_result.missing_data_count}\n"
        result_text += f"Duplicate Rows: {validation_result.duplicate_count}\n\n"
        
        if validation_result.issues:
            result_text += "ISSUES:\n"
            for issue in validation_result.issues:
                result_text += f"  • {issue}\n"
            result_text += "\n"
        
        if validation_result.warnings:
            result_text += "WARNINGS:\n"
            for warning in validation_result.warnings:
                result_text += f"  • {warning}\n"
        
        self.validation_results.setPlainText(result_text)
    
    def update_column_info_table(self, column_info: Dict[str, Dict[str, Any]]):
        """Update the column information table."""
        self.column_info_table.setRowCount(len(column_info))
        
        for row, (col_name, info) in enumerate(column_info.items()):
            # Column name
            self.column_info_table.setItem(row, 0, qtw.QTableWidgetItem(col_name))
            
            # Data type
            self.column_info_table.setItem(row, 1, qtw.QTableWidgetItem(info.get('data_type', '')))
            
            # Non-null count
            self.column_info_table.setItem(row, 2, qtw.QTableWidgetItem(str(info.get('non_null_count', ''))))
            
            # Null count
            self.column_info_table.setItem(row, 3, qtw.QTableWidgetItem(str(info.get('null_count', ''))))
            
            # Unique count
            self.column_info_table.setItem(row, 4, qtw.QTableWidgetItem(str(info.get('unique_count', ''))))
            
            # Sample values
            sample_values = info.get('sample_values', [])
            sample_text = ', '.join(str(v) for v in sample_values[:5])  # Show first 5
            if len(sample_values) > 5:
                sample_text += '...'
            self.column_info_table.setItem(row, 5, qtw.QTableWidgetItem(sample_text))
            
            # Notes (for numeric columns, show min/max)
            notes = ""
            if 'min_value' in info and 'max_value' in info:
                notes = f"Range: {info['min_value']:.2f} - {info['max_value']:.2f}"
            elif 'max_length' in info:
                notes = f"Max length: {info['max_length']}"
            
            self.column_info_table.setItem(row, 6, qtw.QTableWidgetItem(notes))
        
        # Resize columns to content
        self.column_info_table.resizeColumnsToContents()
    
    def update_filtered_data_preview(self, filtered_df: pd.DataFrame):
        """Update the filtered data preview table."""
        if filtered_df.empty:
            self.filtered_data_table.setRowCount(0)
            self.filtered_data_table.setColumnCount(0)
            return
        
        # Show only first 100 rows for performance
        preview_df = filtered_df.head(100)
        
        # Set table dimensions
        self.filtered_data_table.setRowCount(len(preview_df))
        self.filtered_data_table.setColumnCount(len(preview_df.columns))
        self.filtered_data_table.setHorizontalHeaderLabels(preview_df.columns.astype(str))
        
        # Populate table
        for i, row in preview_df.iterrows():
            for j, value in enumerate(row):
                if pd.isna(value):
                    item = qtw.QTableWidgetItem("")
                else:
                    item = qtw.QTableWidgetItem(str(value))
                self.filtered_data_table.setItem(i, j, item)
        
        # Add info about truncation if needed
        if len(filtered_df) > 100:
            info_item = qtw.QTableWidgetItem(f"Showing first 100 of {len(filtered_df)} rows")
            info_item.setBackground(qtg.QColor(255, 255, 200))  # Light yellow background
            self.filtered_data_table.setItem(0, 0, info_item)
    
    def get_figure(self):
        """Get the matplotlib figure for plotting."""
        return self.fig
    
    def get_canvas(self):
        """Get the matplotlib canvas."""
        return self.canvas
    
    def clear_figure(self):
        """Clear the matplotlib figure."""
        self.fig.clear()
        self.canvas.draw()
    
    def show_message(self, message: str, message_type: str = 'info'):
        """Show a message dialog."""
        if message_type == 'warning':
            qtw.QMessageBox.warning(self, 'Warning', message)
        elif message_type == 'error':
            qtw.QMessageBox.critical(self, 'Error', message)
        else:
            qtw.QMessageBox.information(self, 'Information', message)
    
    def show_status_message(self, message: str, timeout: int = 0):
        """Show a message in the status bar."""
        self.status_bar.showMessage(message, timeout)
    
    # Advanced Plotting helper methods
    def _create_custom_plot(self):
        """Create a custom plot based on user configuration."""
        config = self._get_plot_configuration()
        if config:
            self.custom_plot_requested.emit(config)
    
    def _quick_plot(self, plot_type: str):
        """Create a quick plot with default settings."""
        # Get selected columns for Y-axis
        selected_items = self.y_columns_list.selectedItems()
        if not selected_items:
            self.show_message("Please select at least one column for plotting", "warning")
            return
        
        y_columns = [item.text() for item in selected_items]
        
        # Create basic configuration
        plot_type_map = {
            "line": PlotType.LINE,
            "scatter": PlotType.SCATTER,
            "histogram": PlotType.HISTOGRAM
        }
        
        config = PlotConfiguration(
            plot_type=plot_type_map.get(plot_type, PlotType.LINE),
            y_columns=y_columns,
            title=f"{plot_type.title()} Plot",
            grid=True,
            legend=len(y_columns) > 1
        )
        
        self.custom_plot_requested.emit(config)
    
    def _export_plot(self):
        """Export the current plot."""
        file_path, selected_filter = qtw.QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            "plot",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;EPS (*.eps)"
        )
        
        if file_path:
            # Determine format from filter or extension
            if 'PNG' in selected_filter:
                format_type = 'png'
            elif 'PDF' in selected_filter:
                format_type = 'pdf'
            elif 'SVG' in selected_filter:
                format_type = 'svg'
            elif 'EPS' in selected_filter:
                format_type = 'eps'
            else:
                # Determine from extension
                ext = os.path.splitext(file_path)[1].lower()
                format_map = {'.png': 'png', '.pdf': 'pdf', '.svg': 'svg', '.eps': 'eps'}
                format_type = format_map.get(ext, 'png')
            
            try:
                self.fig.savefig(file_path, format=format_type, dpi=300, bbox_inches='tight')
                self.show_message(f"Plot exported to {os.path.basename(file_path)}")
            except Exception as e:
                self.show_message(f"Error exporting plot: {str(e)}", 'error')
    
    def _get_plot_configuration(self) -> Optional[PlotConfiguration]:
        """Get plot configuration from UI controls."""
        # Get selected Y columns
        selected_items = self.y_columns_list.selectedItems()
        if not selected_items:
            self.show_message("Please select at least one column for Y-axis", "warning")
            return None
        
        y_columns = [item.text() for item in selected_items]
        
        # Get X column
        x_column = None
        if self.x_column_combo.currentText() != "Index (default)":
            x_column = self.x_column_combo.currentText()
        
        # Map plot type
        plot_type_map = {
            "Line Plot": PlotType.LINE,
            "Scatter Plot": PlotType.SCATTER,
            "Bar Plot": PlotType.BAR,
            "Histogram": PlotType.HISTOGRAM,
            "Box Plot": PlotType.BOX,
            "Violin Plot": PlotType.VIOLIN,
            "Area Plot": PlotType.AREA,
            "Step Plot": PlotType.STEP,
            "Stem Plot": PlotType.STEM,
            "Pie Chart": PlotType.PIE,
            "Heatmap": PlotType.HEATMAP,
            "Correlation Matrix": PlotType.CORRELATION
        }
        
        plot_type = plot_type_map.get(self.plot_type_combo.currentText(), PlotType.LINE)
        
        # Map plot style
        style_map = {
            "Default": PlotStyle.DEFAULT,
            "Seaborn": PlotStyle.SEABORN,
            "Classic": PlotStyle.CLASSIC,
            "GGPlot": PlotStyle.GGPLOT,
            "FiveThirtyEight": PlotStyle.FIVETHIRTYEIGHT,
            "BMH": PlotStyle.BMHPLOT,
            "Dark Background": PlotStyle.DARK_BACKGROUND
        }
        
        style = style_map.get(self.plot_style_combo.currentText(), PlotStyle.DEFAULT)
        
        # Create configuration
        config = PlotConfiguration(
            plot_type=plot_type,
            x_column=x_column,
            y_columns=y_columns,
            title=self.title_edit.text(),
            xlabel=self.xlabel_edit.text(),
            ylabel=self.ylabel_edit.text(),
            style=style,
            color_scheme=self.color_scheme_combo.currentText(),
            figure_size=(self.width_spin.value(), self.height_spin.value()),
            grid=self.grid_cb.isChecked(),
            legend=self.legend_cb.isChecked(),
            show_statistics=self.statistics_cb.isChecked(),
            log_scale_x=self.log_x_cb.isChecked(),
            log_scale_y=self.log_y_cb.isChecked()
        )
        
        return config
    
    def update_plot_columns(self, columns: List[str]):
        """Update the column options in the plot dropdowns."""
        # Update X column combo
        current_x = self.x_column_combo.currentText()
        self.x_column_combo.clear()
        self.x_column_combo.addItem("Index (default)")
        self.x_column_combo.addItems(columns)
        
        # Restore selection if possible
        index = self.x_column_combo.findText(current_x)
        if index >= 0:
            self.x_column_combo.setCurrentIndex(index)
        
        # Update Y columns list
        self.y_columns_list.clear()
        for col in columns:
            item = qtw.QListWidgetItem(col)
            self.y_columns_list.addItem(item)
    
    def set_plot_recommendations(self, recommendations: Dict[str, List[str]]):
        """Set plot recommendations based on data characteristics."""
        # This could be used to highlight recommended plot types
        # For now, we'll just update the status with recommendations
        if recommendations:
            rec_text = "Recommended plots: " + ", ".join(recommendations.keys())
            self.show_status_message(rec_text, 5000)