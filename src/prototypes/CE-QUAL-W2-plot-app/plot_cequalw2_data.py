import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QMessageBox, QDialog
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


sys.path.append('../../../src')
import cequalw2 as w2


class CSVPlotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CE-QUAL-W2 Plot")
        self.setGeometry(100, 100, 1024, 768)

        self.file_path = ""
        self.data = None
        self.year = 2023

        self.button_browse = QPushButton("Browse", self)
        self.button_browse.clicked.connect(self.browse_file)
        self.button_browse.setFixedWidth(100)

        self.button_plot = QPushButton("Plot", self)
        self.button_plot.clicked.connect(self.plot_data)
        self.button_plot.setFixedWidth(100)

        # Create a Matplotlib figure and canvas
        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)

        # Create a navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button_browse)
        button_layout.addWidget(self.button_plot)

        self.start_year_label = QLabel("Start Year:", self)
        self.start_year_label.setFixedWidth(75)
        self.start_year_input = QLineEdit(self)
        self.start_year_input.setFixedWidth(55)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText("2023")
        self.start_year_input.textChanged.connect(self.update_year)

        self.filename_label = QLabel("Filename:")
        self.filename_label.setFixedWidth(75)
        self.filename_input = QLineEdit(self)
        self.filename_input.setFixedWidth(820)
        self.filename_input.setReadOnly(True)
        self.filename_input.textChanged.connect(self.update_filename)

        start_year_and_filename_layout = QHBoxLayout()
        start_year_and_filename_layout.addWidget(self.start_year_label)
        start_year_and_filename_layout.addWidget(self.start_year_input)
        start_year_and_filename_layout.addWidget(self.filename_label)
        start_year_and_filename_layout.addWidget(self.filename_input)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addLayout(start_year_and_filename_layout)
        layout.addLayout(button_layout)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def update_year(self, text):
        self.year = int(text)

    def update_filename(self, text):
        self.filename = text

    def browse_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
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

    def show_warning_dialog(self):
        app = QApplication([])
        message_box = QMessageBox()
        message_box.setIcon(QMessageBox.Critical)
        message_box.setWindowTitle("Error")
        message_box.setText(f"An error occurred while opening {self.filename}")
        message_box.setStandardButtons(QMessageBox.Close)
        message_box.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CSVPlotApp()
    window.show()
    sys.exit(app.exec_())