"""
View components for ClearView application.
Handles UI elements, layouts, and user interactions.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
from typing import Optional, Dict, Any


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
        """Create the plot tab with matplotlib canvas."""
        plot_widget = qtw.QWidget()
        plot_layout = qtw.QVBoxLayout(plot_widget)
        
        # Create matplotlib figure and canvas
        self.fig = plt.figure(figsize=(self.default_fig_width, self.default_fig_height))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, plot_widget)
        
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        self.tab_widget.addTab(plot_widget, 'Plot')
    
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