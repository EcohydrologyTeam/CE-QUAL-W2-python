import cequalw2 as w2
import os
import sys
import csv
import glob
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg

sys.path.append('.')


class MyTableWidget(qtw.QTableWidget):
    """
    Custom QTableWidget subclass that provides special key press handling.

    This class extends the QTableWidget class and overrides the keyPressEvent method
    to handle the Enter/Return key press event in a specific way. When the Enter/Return
    key is pressed, the current cell is moved to the next cell in a wrapping fashion,
    moving to the next row or wrapping to the top of the next column.
    """

    def __init__(self, parent):
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

        if event.key() == qtc.Qt.Key_Enter or event.key() == qtc.Qt.Key_Return:
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


class CeQualW2Viewer(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CE-QUAL-W2 Viewer')
        self.setGeometry(0, 0, 1500, 900)
        self.PLOT_TYPE = 'plot'

        self.file_path = ''
        self.data = None
        self.DEFAULT_YEAR = 2023
        self.year = self.DEFAULT_YEAR
        self.data_database_path = None
        self.stats_database_path = None
        self.table_name = 'data'
        self.default_fig_width = 12
        self.default_fig_height = 6

        # Create a menu bar
        menubar = self.menuBar()

        # Create an app toolbar
        self.app_toolbar = self.addToolBar('Toolbar')
        self.app_toolbar.setToolButtonStyle(qtc.Qt.ToolButtonTextUnderIcon)
        self.app_toolbar.setMovable(False)

        # Add an open button icon to the toolbar
        open_icon = qtg.QIcon('icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/folder-horizontal-open.png')
        # open_icon = qtg.QIcon(self.style().standardIcon(getattr(qtw.QStyle, 'SP_DialogOpenButton')))
        open_action = qtw.QAction(open_icon, 'Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.browse_file)
        self.app_toolbar.addAction(open_action)

        # Add a save button icon to the toolbar
        save_icon = qtg.QIcon('icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/disk-black.png')
        # save_icon = qtg.QIcon(self.style().standardIcon(getattr(qtw.QStyle, 'SP_DialogSaveButton')))
        save_action = qtw.QAction(save_icon, 'Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_data)
        self.app_toolbar.addAction(save_action)

        # Add a plot button icon to the toolbar
        plot_icon = qtg.QIcon('icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/map.png')
        # plot_icon = qtg.QIcon(self.style().standardIcon(getattr(qtw.QStyle, 'SP_ComputerIcon')))
        plot_action = qtw.QAction(plot_icon, 'Plot', self)
        plot_action.setShortcut('Ctrl+P')
        plot_action.triggered.connect(self.plot)
        self.app_toolbar.addAction(plot_action)

        # Add a multi-plot button icon to the toolbar
        multi_plot_icon = qtg.QIcon('icons/fugue-icons-3.5.6-src/bonus/icons-shadowless-24/map.png')
        multi_plot_action = qtw.QAction(plot_icon, 'Multi-Plot', self)
        multi_plot_action.setShortcut('Ctrl+P')
        multi_plot_action.triggered.connect(self.multi_plot)
        self.app_toolbar.addAction(multi_plot_action)

        # Add the toolbar to the main window
        self.addToolBar(self.app_toolbar)

        # Create Edit menu
        edit_menu = menubar.addMenu('Edit')

        # Create a scroll area to contain the plot
        self.plot_scroll_area = qtw.QScrollArea(self)
        self.plot_scroll_area.setWidgetResizable(False)

        # Create the start year label and text input field
        self.start_year_label = qtw.QLabel('Start Year:', self)
        self.start_year_label.setFixedWidth(75)
        self.start_year_input = qtw.QLineEdit(self)
        self.start_year_input.setAlignment(qtc.Qt.AlignCenter)
        self.start_year_input.setFixedWidth(55)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText(str(self.DEFAULT_YEAR))
        self.start_year_input.textChanged.connect(self.update_year)

        # Create the input filename label and text input field
        self.filename_label = qtw.QLabel('Filename:')
        self.filename_label.setFixedWidth(75)
        self.filename_input = qtw.QLineEdit(self)
        self.filename_input.setFixedWidth(400)
        self.filename_input.setReadOnly(True)
        self.filename_input.textChanged.connect(self.update_filename)

        # Create a layout for the start year and filename widgets
        self.start_year_and_filename_layout = qtw.QHBoxLayout()
        self.start_year_and_filename_layout.setAlignment(qtc.Qt.AlignLeft)
        self.start_year_and_filename_layout.addWidget(self.start_year_label)
        self.start_year_and_filename_layout.addWidget(self.start_year_input)
        self.start_year_and_filename_layout.addWidget(self.filename_label)
        self.start_year_and_filename_layout.addWidget(self.filename_input)

        # Create the statistics table
        self.stats_table = MyTableWidget(self)
        self.stats_table.setEditTriggers(qtw.QTableWidget.NoEditTriggers)
        self.stats_table.setMinimumHeight(200)

        # Create empty canvas and add a matplotlib navigation toolbar
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)

        # Create and customize the matplotlib navigation toolbar
        self.navigation_toolbar = NavigationToolbar(self.canvas, self)
        self.navigation_toolbar.setMaximumHeight(25)
        self.navigation_toolbar_background_color = '#eeffee'
        self.navigation_toolbar.setStyleSheet(f'background-color: {self.navigation_toolbar_background_color}; font-size: 14px; color: black;')

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

        # Create Copy action for the stats and data tables
        copy_action = qtw.QAction('Copy', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy_data)
        edit_menu.addAction(copy_action)

        # Create Paste action for the stats and data tables
        paste_action = qtw.QAction('Paste', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(self.paste_data)
        edit_menu.addAction(paste_action)

        # Fill the QTableWidget with data
        self.update_data_table()

        # Set tabs as central widget
        self.setCentralWidget(self.tab_widget)

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
            datetime_index = self.data.index.to_series().dt.strftime('%m/%d/%Y %H:%M')
            datetime_strings = datetime_index.tolist()

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
                        item.setTextAlignment(0x0082)
                    else:
                        value = array_data[row, column - 1]
                        value_text = f'{value:.4f}'
                        item = qtw.QTableWidgetItem(value_text)
                        item.setTextAlignment(0x0082)
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

    def update_filename(self, text):
        """
        Updates the filename attribute with the provided text.

        This method sets the filename attribute (`self.filename`) to the given text value.

        Args:
            text (str): The new filename.
        """
        self.filename = text

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
        file_dialog.setFileMode(qtw.QFileDialog.ExistingFile)
        file_dialog.setNameFilters(['All Files (*.*)', 'CSV Files (*.csv)', 'NPT Files (*.npt)', 'OPT Files (*.opt)'])
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            self.directory, self.filename = os.path.split(self.file_path)
            self.filename_input.setText(self.filename)
            basefilename, extension = os.path.splitext(self.filename)

            if extension.lower() in ['.npt', '.opt']:
                self.data_columns = w2.get_data_columns_fixed_width(self.file_path)
                FILE_TYPE = 'ASCII'
            elif extension.lower() == '.csv':
                self.data_columns = w2.get_data_columns_csv(self.file_path)
                FILE_TYPE = 'ASCII'
            elif extension.lower() == '.db':
                FILE_TYPE = 'SQLITE'
            else:
                file_dialog.close()
                self.show_warning_dialog('Only *.csv, *.npt, *.opt, and *.db files are supported.')
                return

            self.get_model_year()

            try:
                if FILE_TYPE == 'ASCII':
                    self.data = w2.read(self.file_path, self.year, self.data_columns)
                elif FILE_TYPE == 'SQLITE':
                    self.data = w2.read_sqlite(self.file_path)
            except IOError:
                self.show_warning_dialog(f'An error occurred while opening {self.filename}')
                file_dialog.close()

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

    def plot(self):
        # Check if data is available
        if self.data is None:
            return

        # Create the figure and canvas
        self.figure.clear()
        w2.plot(self.data, fig=self.figure, figsize=(self.default_fig_width, self.default_fig_height))
        self.resize_canvas(self.default_fig_width, self.default_fig_height)

        # Draw the canvas and create or update the statistics table
        self.canvas.draw() # self.canvas was updated to new_canvas in update_canvas() above
        self.update_stats_table()

    def multi_plot(self):
        # Check if data is available
        if self.data is None:
            return
        # Create the figure and canvas
        subplot_scale_factor = 2.0
        num_subplots = len(self.data.columns)
        multi_plot_fig_height = max(num_subplots * subplot_scale_factor, self.default_fig_height)
        self.figure.clear()
        w2.multi_plot(self.data, fig=self.figure, figsize=(self.default_fig_width, multi_plot_fig_height))
        self.resize_canvas(self.default_fig_width, multi_plot_fig_height)

        # Draw the canvas and create or update the statistics table
        self.canvas.draw() # self.canvas was updated to new_canvas in update_canvas() above
        self.update_stats_table()

    def show_warning_dialog(self, message):
        """
        Displays a warning dialog with the given message.

        This method creates and shows a warning dialog box with the provided `message`. The dialog box includes a critical icon,
        a title, and the message text.

        Args:
            message (str): The warning message to be displayed.
        """
        message_box = qtw.QMessageBox()
        message_box.setIcon(qtw.QMessageBox.Critical)
        message_box.setWindowTitle('Error')
        message_box.setText(message)
        message_box.exec_()

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
                print('ValueError:', row, col, value)
            except IndexError:
                print('IndexError:', row, col, value)

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

    def save_data(self):
        """
        Saves the data to a selected file as an SQLite database.

        This method allows the user to select a file path to save the data as an SQLite database.
        If a valid file path is selected and the `data` attribute is not `None`, the following steps are performed:
        1. The `data_database_path` attribute is set to the selected file path.
        2. The `save_to_sqlite` method is called to save the data to the SQLite database file.
        3. The statistics table is updated after saving the data.

        Note:
            - The `data` attribute must be set with the data before calling this method.
        """
        default_filename = self.file_path + '.db'
        options = qtw.QFileDialog.Options()
        # options |= qtw.QFileDialog.DontUseNativeDialog
        returned_path, _ = qtw.QFileDialog.getSaveFileName(self, "Save As", default_filename,
                                                           "SQLite Files (*.db);; All Files (*)", options=options)
        if not returned_path:
            return

        self.data_database_path = returned_path

        if self.data_database_path and self.data is not None:
            self.save_to_sqlite(self.data, self.data_database_path)
            self.update_stats_table()

    def save_stats(self):
        default_filename = self.file_path + '_stats.db'
        options = qtw.QFileDialog.Options()
        returned_path, _ = qtw.QFileDialog.getSaveFileName(self, "Save As", default_filename,
                                                           "SQLite Files (*.db);; All Files (*)", options=options)
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
    window = CeQualW2Viewer()
    window.show()
    sys.exit(app.exec_())
