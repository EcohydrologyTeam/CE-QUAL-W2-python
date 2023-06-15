import cequalw2 as w2
import os
import sys
import csv
import glob
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw

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
        self.setGeometry(100, 100, 1200, 900)
        self.PLOT_TYPE = 'plot'

        self.file_path = ''
        self.data = None
        self.DEFAULT_YEAR = 2023
        self.year = self.DEFAULT_YEAR
        self.database_path = None
        self.table_name = 'data'

        # Create a menu bar
        menubar = self.menuBar()

        # Create Edit menu
        edit_menu = menubar.addMenu('Edit')

        # Create Browse button
        self.button_browse = qtw.QPushButton('Browse', self)
        self.button_browse.clicked.connect(self.browse_file)
        self.button_browse.setFixedWidth(100)

        # Create Plot button
        self.button_plot = qtw.QPushButton('Plot', self)
        self.button_plot.clicked.connect(self.plot_data)
        self.button_plot.setFixedWidth(100)

        # Create the figure and canvas
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)

        # Create and customize the matplotlib navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setMaximumHeight(25)
        self.toolbar_background_color = '#eeffee'
        self.toolbar.setStyleSheet(f'background-color: {self.toolbar_background_color}; font-size: 14px; color: black;')

        # Create a button layout for the Browse and Plot buttons
        self.button_layout = qtw.QHBoxLayout()
        self.button_layout.setAlignment(qtc.Qt.AlignLeft)
        self.button_layout.addWidget(self.button_browse)
        self.button_layout.addWidget(self.button_plot)

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

        # Create the radio button items, group, and layout
        self.plot_option_group = qtw.QButtonGroup(self)
        self.radio_plot = qtw.QRadioButton('Single Plot')
        self.radio_multiplot = qtw.QRadioButton('One Plot per Variable')
        self.plot_option_group.addButton(self.radio_plot)
        self.plot_option_group.addButton(self.radio_multiplot)
        self.radio_plot.setChecked(True)
        self.plot_option_group.buttonClicked.connect(self.plot_option_changed)
        self.radio_layout = qtw.QHBoxLayout()
        self.radio_layout.setAlignment(qtc.Qt.AlignLeft)
        self.radio_layout.addWidget(self.radio_plot)
        self.radio_layout.addWidget(self.radio_multiplot)

        # Create tabs
        self.tab_widget = qtw.QTabWidget()
        self.plot_tab = qtw.QWidget()
        self.statistics_tab = qtw.QWidget()
        self.tab_widget.addTab(self.plot_tab, "Plot")
        self.tab_widget.addTab(self.statistics_tab, "Statistics")

        # Set layout for plot_tab
        self.plot_tab_layout = qtw.QVBoxLayout()
        self.plot_tab_layout.addWidget(self.toolbar)
        self.plot_tab_layout.addWidget(self.canvas)
        self.plot_tab_layout.addLayout(self.start_year_and_filename_layout)
        self.plot_tab_layout.addLayout(self.radio_layout)
        self.plot_tab_layout.addLayout(self.button_layout)
        self.plot_tab.setLayout(self.plot_tab_layout)

        # Set layout for statistics_tab
        self.statistics_tab_layout = qtw.QVBoxLayout()
        self.statistics_tab_layout.addWidget(self.stats_table)
        self.statistics_tab.setLayout(self.statistics_tab_layout)

        # Create a new tab and a QTableWidget
        self.data_tab = qtw.QWidget()
        self.data_table = MyTableWidget(self.data_tab)
        self.data_table.itemChanged.connect(self.table_cell_changed)
        self.tab_widget.addTab(self.data_tab, "Data")

        # Set layout for the Data tab
        self.data_tab_layout = qtw.QVBoxLayout()
        self.data_tab_layout.addWidget(self.data_table)
        self.data_tab.setLayout(self.data_tab_layout)

        # Create save buttons and layout for the data table
        self.button_data_save = qtw.QPushButton('Save', self)
        self.button_data_save.clicked.connect(self.save_data)
        self.button_data_save.setFixedWidth(100)
        self.save_button_layout = qtw.QHBoxLayout()
        self.save_button_layout.setAlignment(qtc.Qt.AlignLeft)
        self.save_button_layout.addWidget(self.button_data_save)

        # Create Copy action for the data table
        copy_data_table_action = qtw.QAction('Copy', self)
        copy_data_table_action.setShortcut('Ctrl+C')
        copy_data_table_action.triggered.connect(self.copy_data_table)
        edit_menu.addAction(copy_data_table_action)

        # Create Copy action for the stats table
        copy_stats_table_action = qtw.QAction('Copy', self)
        copy_stats_table_action.setShortcut('Ctrl+C')
        copy_stats_table_action.triggered.connect(self.copy_stats_table)

        # Create Paste action for the data table
        paste_data_table_action = qtw.QAction('Paste', self)
        paste_data_table_action.setShortcut('Ctrl+V')
        paste_data_table_action.triggered.connect(self.paste_data_table)
        edit_menu.addAction(paste_data_table_action)

        # Create Paste action for the stats table
        paste_stats_table_action = qtw.QAction('Paste', self)
        paste_stats_table_action.setShortcut('Ctrl+V')
        paste_stats_table_action.triggered.connect(self.paste_data_table)

        self.data_tab_layout.addLayout(self.save_button_layout)

        # Fill the QTableWidget with data
        self.update_data_table()

        # Set tabs as central widget
        self.setCentralWidget(self.tab_widget)

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
                data_columns = w2.get_data_columns_fixed_width(self.file_path)
            elif extension.lower() == '.csv':
                data_columns = w2.get_data_columns_csv(self.file_path)
            else:
                file_dialog.close()
                self.show_warning_dialog('Only *.csv, *.npt, and *.opt files are supported.')
                return

            self.get_model_year()

            try:
                self.data = w2.read(self.file_path, self.year, data_columns)
            except IOError:
                self.show_warning_dialog(f'An error occurred while opening {self.filename}')
                file_dialog.close()

        self.update_data_table()
        self.update_stats_table()

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

        statistics = self.data.describe().reset_index()
        self.stats_table.setRowCount(len(statistics))
        self.stats_table.setColumnCount(len(self.data.columns) + 1)

        header = ['']
        for col in self.data.columns:
            header.append(col)
        self.stats_table.setHorizontalHeaderLabels(header)

        for row in range(len(statistics)):
            for col in range(len(self.data.columns) + 1):
                value = statistics.iloc[row, col]
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

    def plot_data(self):
        """
        Plots the data using the selected plot type.

        This method clears the existing figure, creates a subplot, and plots the data based on the selected plot type (`self.PLOT_TYPE`).
        If the `data` attribute is `None`, the method returns without performing any plotting.

        The plot is rendered on the canvas (`self.canvas`) associated with the figure.
        Additionally, the statistics table is updated after plotting the data.

        Note:
            - The figure and canvas must be properly initialized before calling this method.
            - The `data` attribute must be set with the data before calling this method.
            - The plot type is determined by the value of `self.PLOT_TYPE`.
        """
        if self.data is None:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if self.PLOT_TYPE == 'plot':
            w2.plot(self.data, fig=self.figure, ax=ax)
        elif self.PLOT_TYPE == 'multiplot':
            w2.multi_plot(self.data, fig=self.figure, ax=ax)

        self.canvas.draw()
        self.update_stats_table()

    def plot_option_changed(self):
        """
        Handles the change in the selected plot option.

        This method retrieves the text of the currently selected plot option from the checked radio button in the plot option group.
        Based on the selected option, the `PLOT_TYPE` attribute is updated to either 'plot' (for single plot) or 'multiplot' (for one plot per variable).

        Note:
            - The plot option group and radio buttons must be properly set up and connected to this method.
            - The `PLOT_TYPE` attribute controls the type of plot to be generated in the `plot_data` method.
        """
        selected_option = self.plot_option_group.checkedButton().text()

        if selected_option == 'Single Plot':
            self.PLOT_TYPE = 'plot'
        elif selected_option == 'One Plot per Variable':
            self.PLOT_TYPE = 'multiplot'

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

    def save_to_sqlite(self):
        """
        Saves the data to an SQLite database.

        This method saves the data stored in the `data` attribute to an SQLite database file specified by the `database_path` attribute.
        The table name is set as the `filename` attribute.
        If the database file already exists, the table with the same name is replaced.
        The data is saved with the index included as a column.

        Note:
            - The `data` attribute must be set with the data before calling this method.
            - The `database_path` attribute must be properly set with the path to the SQLite database file.
        """
        self.table_name = self.filename
        con = sqlite3.connect(self.database_path)
        self.data.to_sql(self.table_name, con, if_exists="replace", index=True)
        con.close()

    def save_data(self):
        """
        Saves the data to a selected file as an SQLite database.

        This method allows the user to select a file path to save the data as an SQLite database.
        If a valid file path is selected and the `data` attribute is not `None`, the following steps are performed:
        1. The `database_path` attribute is set to the selected file path.
        2. The `save_to_sqlite` method is called to save the data to the SQLite database file.
        3. The statistics table is updated after saving the data.

        Note:
            - The `data` attribute must be set with the data before calling this method.
        """
        default_filename = self.file_path + '.db'
        options = qtw.QFileDialog.Options()
        # options |= qtw.QFileDialog.DontUseNativeDialog
        returned_path, _ = qtw.QFileDialog.getSaveFileName(self, "Save As", default_filename,
                                                           "All Files (*);;Text Files (*.txt)", options=options)
        if not returned_path:
            return

        self.database_path = returned_path

        if self.database_path and self.data is not None:
            self.save_to_sqlite()
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

    def copy(self, table_widget: MyTableWidget):
        """
        Copy the selected cells of the table to the clipboard.

        The selected cells are concatenated into a string with tab-separated
        values for columns and newline-separated values for rows. The resulting
        string is then set as the text content of the clipboard.

        :param table_widget: The table widget from which to copy the cells.
        :type table_widget: MyTableWidget
        """
        selected = table_widget.selectedRanges()
        if selected:
            s = ''
            for row in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                for col in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                    s += str(table_widget.item(row, col).text()) + '\t'
                s = s.strip() + '\n'
            s = s.strip()
            qtw.QApplication.clipboard().setText(s)

    def paste(self, table_widget: MyTableWidget):
        """
        Paste the contents of the clipboard into the selected cells of the table.

        The contents of the clipboard are expected to be in the same format as
        produced by the copy() method (tab-separated values for columns, newline-separated
        values for rows). The values are parsed into a NumPy array using the parse_2x2_array()
        method and then inserted into the selected cells of the table.

        :param table_widget: The table widget to paste the contents into.
        :type table_widget: MyTableWidget
        """
        selected = table_widget.selectedRanges()
        if selected:
            s = qtw.QApplication.clipboard().text()
            values = self.parse_2x2_array(s)
            nrows, ncols = values.shape

            top_row = selected[0].topRow()
            left_col = selected[0].leftColumn()

            for i, row in enumerate(range(nrows)):
                row = top_row + i
                for j, col in enumerate(range(ncols)):
                    col = left_col + j
                    table_widget.setItem(row, col, qtw.QTableWidgetItem(values[i][j]))

    def copy_data_table(self):
        self.copy(self.data_table)

    def copy_stats_table(self):
        self.copy(self.stats_table)

    def paste_data_table(self):
        self.paste(self.data_table)

    def paste_stats_table(self):
        self.paste(self.stats_table)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    window = CeQualW2Viewer()
    window.show()
    sys.exit(app.exec_())
