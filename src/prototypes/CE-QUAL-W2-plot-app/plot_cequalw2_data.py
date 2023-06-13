import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
# from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


sys.path.append('../../../src')
import cequalw2 as w2


class CSVPlotApp(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CE-QUAL-W2 Plot")
        self.setGeometry(100, 100, 1200, 900)
        self.PLOT_TYPE = "plot"

        self.file_path = ""
        self.data = None
        self.DEFAULT_YEAR = 2023
        self.year = self.DEFAULT_YEAR

        self.button_browse = qtw.QPushButton("Browse", self)
        self.button_browse.clicked.connect(self.browse_file)
        self.button_browse.setFixedWidth(100)

        self.button_plot = qtw.QPushButton("Plot", self)
        self.button_plot.clicked.connect(self.plot_data)
        self.button_plot.setFixedWidth(100)

        # Create a Matplotlib figure and canvas
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)

        # Create a navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setMaximumHeight(25)
        self.toolbar_background_color = "#aaddaa"
        self.toolbar.setStyleSheet(f"background-color: {self.toolbar_background_color}")

        self.button_layout = qtw.QHBoxLayout()
        self.button_layout.setAlignment(qtc.Qt.AlignLeft)
        self.button_layout.addWidget(self.button_browse)
        self.button_layout.addWidget(self.button_plot)

        self.start_year_label = qtw.QLabel("Start Year:", self)
        self.start_year_label.setFixedWidth(75)
        self.start_year_input = qtw.QLineEdit(self)
        self.start_year_input.setAlignment(qtc.Qt.AlignCenter)
        self.start_year_input.setFixedWidth(55)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText(str(self.DEFAULT_YEAR))
        self.start_year_input.textChanged.connect(self.update_year)

        self.filename_label = qtw.QLabel("Filename:")
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
        self.radio_plot = qtw.QRadioButton("Single Plot")
        self.radio_multiplot = qtw.QRadioButton("One Plot per Variable")
        self.plot_option_group.addButton(self.radio_plot)
        self.plot_option_group.addButton(self.radio_multiplot)
        self.radio_plot.setChecked(True)  # Set default selection to Plot
        self.plot_option_group.buttonClicked.connect(self.plot_option_changed)
        self.radio_layout = qtw.QHBoxLayout()
        self.radio_layout.setAlignment(qtc.Qt.AlignLeft)
        self.radio_layout.addWidget(self.radio_plot)
        self.radio_layout.addWidget(self.radio_multiplot)

        self.layout = qtw.QVBoxLayout()
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.stats_table)
        self.layout.addLayout(self.start_year_and_filename_layout)
        self.layout.addLayout(self.radio_layout)
        self.layout.addLayout(self.button_layout)

        self.central_widget = qtw.QWidget(self)
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

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
        file_dialog.setNameFilter("CSV Files (*.csv)")
        file_dialog.setNameFilters(["CSV Files (*.csv)", "NPT Files (*.npt)", "OPT Files (*.opt)"])
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            directory, filename = os.path.split(self.file_path)
            self.filename_input.setText(filename)
            basefilename, extension = os.path.splitext(filename)

            if extension.lower() in [".npt", ".opt"]:
                data_columns = w2.get_data_columns_fixed_width(self.file_path)
            elif extension.lower() == ".csv":
                data_columns = w2.get_data_columns_csv(self.file_path)
            else:
                raise ValueError("Only *.csv, *.npt, and *.opt files are supported.")

            try:
                self.data = w2.read(self.file_path, self.year, data_columns)
            except IOError:
                self.show_warning_dialog()
                file_dialog.close()

    def plot_data(self):
        if self.data is not None:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            # self.data.plot(ax=ax)
            if self.PLOT_TYPE == "plot":
                w2.plot(self.data, fig=self.figure, ax=ax)
            elif self.PLOT_TYPE == "multiplot":
                w2.multi_plot(self.data, fig=self.figure, ax=ax)
            self.canvas.draw()

            # Compute statistics
            statistics = self.data.describe().reset_index()
            self.stats_table.setRowCount(len(statistics))
            self.stats_table.setColumnCount(len(self.data.columns))
            header = ['']
            for col in self.data.columns:
                header.append(col)
            self.stats_table.setHorizontalHeaderLabels(header)
            for row in range(len(statistics)):
                for col in range(len(self.data.columns)):
                    value = statistics.iloc[row, col]
                    try:
                        if row != 0: # if it is not the "count" statistic, which is an integer
                            value_text = f"{value:.2f}"
                        else:
                            value_text = f"{int(value):d}"
                    except ValueError:
                        value_text = str(value)
                    item = qtw.QTableWidgetItem(value_text)
                    item.setTextAlignment(0x0082)
                    self.stats_table.setItem(row, col, item)

    def plot_option_changed(self):
        selected_option = self.plot_option_group.checkedButton().text()
        if selected_option == "Single Plot":
            self.PLOT_TYPE = "plot"
        elif selected_option == "One Plot per Variable":
            self.PLOT_TYPE = "multiplot"

    def show_warning_dialog(self):
        app = qtw.QApplication([])
        message_box = qtw.QMessageBox()
        message_box.setIcon(qtw.QMessageBox.Critical)
        message_box.setWindowTitle("Error")
        message_box.setText(f"An error occurred while opening {self.filename}")
        message_box.setStandardButtons(qtw.QMessageBox.Close)
        message_box.exec_()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    window = CSVPlotApp()
    window.show()
    sys.exit(app.exec_())