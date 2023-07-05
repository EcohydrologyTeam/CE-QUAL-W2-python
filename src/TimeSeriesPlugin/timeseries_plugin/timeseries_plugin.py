import os
from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
import pandas as pd
import matplotlib.pyplot as plt

def classFactory(iface):
    from .timeseries_plugin import TimeSeriesPlugin
    return TimeSeriesPlugin(iface)

class TimeSeriesPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.toolbar = None
        self.browse_action = None
        self.plot_action = None
        self.file_path = None
        self.data = None

    def initGui(self):
        self.toolbar = self.iface.addToolBar("Time Series Plugin")
        
        # Add Browse button
        self.browse_action = QAction(QIcon(""), "Browse", self.iface.mainWindow())
        self.browse_action.triggered.connect(self.browse_file)
        self.toolbar.addAction(self.browse_action)
        
        # Add Plot button
        self.plot_action = QAction(QIcon(""), "Plot", self.iface.mainWindow())
        self.plot_action.triggered.connect(self.plot_data)
        self.toolbar.addAction(self.plot_action)
        
    def unload(self):
        self.iface.removeToolBarIcon(self.browse_action)
        self.iface.removeToolBarIcon(self.plot_action)
        del self.toolbar
    
    def browse_file(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Excel Files (*.xls *.xlsx)")
        
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            self.read_data()
    
    def read_data(self):
        try:
            self.data = pd.read_excel(self.file_path)
            QMessageBox.information(self.iface.mainWindow(), "Success", "Data read successfully from file.")
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "Error", f"Failed to read data: {str(e)}")
    
    def plot_data(self):
        if self.data is not None:
            self.data.plot(x='Date', y='PO4', legend=False)
            plt.xlabel('Time')
            plt.ylabel('Value')
            plt.title('Time Series Data')
            plt.show()
        else:
            QMessageBox.warning(self.iface.mainWindow(), "Warning", "No data available. Please browse a file first.")

