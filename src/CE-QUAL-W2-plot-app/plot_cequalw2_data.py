import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import glob
import csv

sys.path.append('../../../src')
import cequalw2 as w2


class CSVPlotApp(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CE-QUAL-W2 Viewer')
        self.setGeometry(100, 100, 1200, 900)
        self.PLOT_TYPE = 'plot'

        self.file_path = ''
        self.data = None
        self.DEFAULT_YEAR = 2023
        self.year = self.DEFAULT_YEAR

        self.button_browse = qtw.QPushButton('Browse', self)
        self.button_browse.clicked.connect(self.browse_file)
        self.button_browse.setFixedWidth(100)

        self.button_plot = qtw.QPushButton('Plot', self)
        self.button_plot.clicked.connect(self.plot_data)
        self.button_plot.setFixedWidth(100)

        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setMaximumHeight(25)
        self.toolbar_background_color = '#eeffee'
        self.toolbar.setStyleSheet(f'background-color: {self.toolbar_background_color}; font-size: 14px; color: black;')

        self.button_layout = qtw.QHBoxLayout()
        self.button_layout.setAlignment(qtc.Qt.AlignLeft)
        self.button_layout.addWidget(self.button_browse)
        self.button_layout.addWidget(self.button_plot)

        self.start_year_label = qtw.QLabel('Start Year:', self)
        self.start_year_label.setFixedWidth(75)
        self.start_year_input = qtw.QLineEdit(self)
        self.start_year_input.setAlignment(qtc.Qt.AlignCenter)
        self.start_year_input.setFixedWidth(55)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText(str(self.DEFAULT_YEAR))
        self.start_year_input.textChanged.connect(self.update_year)

        self.filename_label = qtw.QLabel('Filename:')
        self.filename_label.setFixedWidth(75)
        self.filename_input = qtw.QLineEdit(self)
        self.filename_input.setFixedWidth(400)
        self.filename_input.setReadOnly(True)
        self.filename_input.textChanged.connect(self.update_filename)

        self.start_year_and_filename_layout = qtw.QHBoxLayout()
        self.start_year_and_filename_layout.setAlignment(qtc.Qt.AlignLeft)
        self.start_year_and_filename_layout.addWidget(self.start_year_label)
        self.start_year_and_filename_layout.addWidget(self.start_year_input)
        self.start_year_and_filename_layout.addWidget(self.filename_label)
        self.start_year_and_filename_layout.addWidget(self.filename_input)

        self.stats_table = qtw.QTableWidget(self)
        self.stats_table.setEditTriggers(qtw.QTableWidget.NoEditTriggers)
        self.stats_table.setMinimumHeight(200)

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
        self.data_table = qtw.QTableWidget(self.data_tab)
        self.tab_widget.addTab(self.data_tab, "Data")

        # Set layout for data_tab
        self.data_tab_layout = qtw.QVBoxLayout()
        self.data_tab_layout.addWidget(self.data_table)
        self.data_tab.setLayout(self.data_tab_layout)

        # Fill the QTableWidget with data
        self.update_data_table()

        # Set tabs as central widget
        self.setCentralWidget(self.tab_widget)


    def update_data_table(self):
        if self.data is not None:
            # Convert DataFrame to numpy array for efficiency
            array_data = self.data.values

            # Get the datetime index as an array
            # datetime_array = self.data.index.to_numpy()
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
        rows = []
        with open(w2_control_file_path, 'r') as f:
            csv_reader = csv.reader(f)
            for row in (csv_reader):
                rows.append(row)
        for i, row in enumerate(rows):
                if row[0].upper() == 'TMSTRT':
                    self.year = int(rows[i + 1][2])
                    self.start_year_input.setText(str(self.year))


    def parse_year_npt(self, w2_control_file_path):
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
        # Locate the CE-QUAL-W2 control file
        path1 = os.path.join(self.directory, 'w2_con.csv')
        path2 = os.path.join(self.directory, '../w2_con.csv')
        path3 = os.path.join(self.directory, 'w2_con.npt')
        path4 = os.path.join(self.directory, '../w2_con.npt')
        w2_control_file_path = None
        w2_file_type = None

        if glob.glob(path1):
            w2_control_file_path = path1
            w2_file_type = "CSV"
        elif glob.glob(path2):
            w2_control_file_path = path2
            w2_file_type = "CSV"
        elif glob.glob(path3):
            w2_control_file_path = path3
            w2_file_type = "NPT"
        elif glob.glob(path4):
            w2_control_file_path = path4
            w2_file_type = "NPT"
        else:
            print('No control file found!')

        print("w2_control_file_path = ", w2_control_file_path)

        if w2_file_type == "CSV":
            self.parse_year_csv(w2_control_file_path)
        elif w2_file_type == "NPT":
            self.parse_year_npt(w2_control_file_path)


    def update_year(self, text):
        try:
            self.year = int(text)
        except ValueError:
            self.year = self.DEFAULT_YEAR


    def update_filename(self, text):
        self.filename = text


    def browse_file(self):
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setFileMode(qtw.QFileDialog.ExistingFile)
        file_dialog.setNameFilters(['All Files (*.*)', 'CSV Files (*.csv)', 'NPT Files (*.npt)', 'OPT Files (*.opt)'])
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            self.directory, self.filename = os.path.split(self.file_path)
            self.filename_input.setText(self.filename)
            basefilename, extension = os.path.splitext(self.filename)

            # Get data columns
            if extension.lower() in ['.npt', '.opt']:
                data_columns = w2.get_data_columns_fixed_width(self.file_path)
            elif extension.lower() == '.csv':
                data_columns = w2.get_data_columns_csv(self.file_path)
            else:
                file_dialog.close()
                self.show_warning_dialog('Only *.csv, *.npt, and *.opt files are supported.')
                return

            # Get model year
            self.get_model_year()

            # Read the data
            try:
                self.data = w2.read(self.file_path, self.year, data_columns)
            except IOError:
                self.show_warning_dialog(f'An error occurred while opening {self.filename}')
                file_dialog.close()

        self.update_data_table()
        self.make_stats_table()


    def make_stats_table(self):
        if self.data is None:
            return

        # Compute statistics
        statistics = self.data.describe().reset_index()
        self.stats_table.setRowCount(len(statistics))
        self.stats_table.setColumnCount(len(self.data.columns) + 1)
        # Note: col = 0 is the index column, which lists the statistics names
        # Therefore, the total number of columns is len(data.columns) + 1
        header = ['']
        for col in self.data.columns:
            header.append(col)
        self.stats_table.setHorizontalHeaderLabels(header)
        for row in range(len(statistics)):
            for col in range(len(self.data.columns) + 1):
                # See note above about the number of columns
                value = statistics.iloc[row, col]
                try:
                    if col == 0:
                        value_text = str(value)
                    elif row == 0: 
                        value_text = f'{int(value):d}' # format the "count" statistic as an integer
                    else:
                        value_text = f'{value:.2f}' # format everything else as a float
                except ValueError:
                    value_text = str(value)
                item = qtw.QTableWidgetItem(value_text)
                item.setTextAlignment(0x0082)
                self.stats_table.setItem(row, col, item)


    def plot_data(self):
        if self.data is None:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        # self.data.plot(ax=ax)
        if self.PLOT_TYPE == 'plot':
            w2.plot(self.data, fig=self.figure, ax=ax)
        elif self.PLOT_TYPE == 'multiplot':
            w2.multi_plot(self.data, fig=self.figure, ax=ax)
        self.canvas.draw()


    def plot_option_changed(self):
        selected_option = self.plot_option_group.checkedButton().text()
        if selected_option == 'Single Plot':
            self.PLOT_TYPE = 'plot'
        elif selected_option == 'One Plot per Variable':
            self.PLOT_TYPE = 'multiplot'


    def show_warning_dialog(self, message):
        message_box = qtw.QMessageBox()
        message_box.setIcon(qtw.QMessageBox.Critical)
        message_box.setWindowTitle('Error')
        message_box.setText(message)
        # message_box.setStandardButtons(qtw.QMessageBox.Close)
        message_box.exec_()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    window = CSVPlotApp()
    window.show()
    sys.exit(app.exec_())