import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import PyQt5.QtWidgets as qtw
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


sys.path.append('../../../src')
import cequalw2 as w2


class CSVPlotApp(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CE-QUAL-W2 Plot")
        self.setGeometry(100, 100, 1200, 900)

        self.file_path = ""
        self.data = None
        self.year = 2023

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
        toolbar_background_color = "#aaddaa"
        toolbar_foreground_color = "#333333"
        self.toolbar.setStyleSheet(f"background-color: {toolbar_background_color}; foreground-color: {toolbar_foreground_color}")

        button_layout = qtw.QHBoxLayout()
        button_layout.addWidget(self.button_browse)
        button_layout.addWidget(self.button_plot)

        self.start_year_label = qtw.QLabel("Start Year:", self)
        self.start_year_label.setFixedWidth(75)
        self.start_year_input = qtw.QLineEdit(self)
        self.start_year_input.setFixedWidth(55)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText("2023")
        self.start_year_input.textChanged.connect(self.update_year)

        self.filename_label = qtw.QLabel("Filename:")
        self.filename_label.setFixedWidth(75)
        self.filename_input = qtw.QLineEdit(self)
        self.filename_input.setFixedWidth(820)
        self.filename_input.setReadOnly(True)
        self.filename_input.textChanged.connect(self.update_filename)

        start_year_and_filename_layout = qtw.QHBoxLayout()
        start_year_and_filename_layout.addWidget(self.start_year_label)
        start_year_and_filename_layout.addWidget(self.start_year_input)
        start_year_and_filename_layout.addWidget(self.filename_label)
        start_year_and_filename_layout.addWidget(self.filename_input)

        self.stats_table = qtw.QTableWidget(self)
        self.stats_table.setEditTriggers(qtw.QTableWidget.NoEditTriggers)
        self.stats_table.setMinimumHeight(200)

        layout = qtw.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.stats_table)
        layout.addLayout(start_year_and_filename_layout)
        layout.addLayout(button_layout)

        central_widget = qtw.QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def update_year(self, text):
        self.year = int(text)

    def update_filename(self, text):
        self.filename = text

    def browse_file(self):
        file_dialog = qtw.QFileDialog(self)
        file_dialog.setFileMode(qtw.QFileDialog.ExistingFile)
        file_dialog.setNameFilter("CSV Files (*.csv)")
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            directory, filename = os.path.split(self.file_path)
            self.filename_input.setText(filename)
            data_columns = w2.get_data_columns(self.file_path)
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
            w2.plot(self.data, fig=self.figure, ax=ax)
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