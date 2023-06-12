import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

sys.path.append('../../../src')
import cequalw2 as w2


class CSVPlotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Plot App")
        self.setGeometry(100, 100, 800, 600)

        self.file_path = ""
        self.data = None
        self.year = 2023

        self.button_browse = QPushButton("Browse", self)
        self.button_browse.clicked.connect(self.browse_file)
        self.button_browse.setFixedWidth(100)

        self.button_plot = QPushButton("Plot", self)
        self.button_plot.clicked.connect(self.plot_data)
        self.button_plot.setFixedWidth(100)

        self.figure = plt.Figure()
        self.canvas = FigureCanvas(self.figure)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button_browse)
        button_layout.addWidget(self.button_plot)

        self.filename_label = QLabel("Filename:")
        self.filename_input = QLineEdit(self)
        self.filename_input.setReadOnly(True)
        self.filename_input.textChanged.connect(self.update_filename)
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(self.filename_label)
        filename_layout.addWidget(self.filename_input)

        self.start_year_label = QLabel("Model Start Year:", self)
        self.start_year_input = QLineEdit(self)
        self.start_year_input.setReadOnly(False)
        self.start_year_input.setText("2023")
        self.start_year_input.textChanged.connect(self.update_year)

        start_year_layout = QHBoxLayout()
        start_year_layout.addWidget(self.start_year_label)
        start_year_layout.addWidget(self.start_year_input)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addLayout(button_layout)
        layout.addLayout(start_year_layout)
        layout.addLayout(filename_layout)

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
            self.filename_label = filename
            with open(self.file_path, 'r') as f:
                lines = f.readlines()
                header_vals = lines[2].strip().strip(',').strip().split(',')
                for i, val in enumerate(header_vals):
                    header_vals[i] = val.strip()
                data_columns = header_vals[1:]
            self.data = w2.read(self.file_path, self.year, data_columns)
            self.filename_input.setText(filename)

    def plot_data(self):
        if self.data is not None:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            # self.data.plot(ax=ax)
            w2.plot(self.data, fig=self.figure, ax=ax)
            self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CSVPlotApp()
    window.show()
    sys.exit(app.exec_())
