# ClearView Documentation

Welcome to the ClearView documentation! ClearView is a comprehensive tool for water quality and environmental data analysis. This documentation will guide you through the features and functionality of ClearView, helping you effectively use the tool to analyze and visualize your data.

## Table of Contents

1. Introduction
2. Installation
3. Getting Started
   - Opening Data Files
   - Data Tab
   - Stats Tab
   - Plots Tab
   - Methods Tab
4. Supported Data Formats
5. Plotting Controls
6. Analysis Methods
7. Saving Data
8. Conclusion

## Overview

### ClearView: A Comprehensive Tool for Water Quality and Environmental Data Analysis

ClearView is a tool for viewing and analyzing water quality and environmental time series data. Designed to work with model input and output data, sensor data, and laboratory measurements, ClearView seamlessly reads and writes multiple data formats, providing compatibility and flexibility with a variety of new and legacy models, sensors, analysis tools, and workflows.

The user interface of ClearView is designed with simplicity and usability in mind. Its plotting component allows you to generate informative plots, enabling the identification of trends, patterns, and anomalies within your time series data. ClearView provides a tabular display, facilitating easy access and interpretation. ClearView's summary statistics provides a concise summary of your data. This feature allows you to evaluate key statistical measures, facilitating data-driven analysis and decision-making.

ClearView streamlines data analysis and time series processing. Leveraging advanced algorithms and statistical techniques, this tool enables exploring data and calculating relevant metrics to derive valuable insights, such as identifying pollution sources, detecting changes in water quality over time, and deriving a deeper understanding of environmental data.

The aim of ClearView is to streamline workflows and enhance productivity. By integrating data visualization, analysis, and statistical summaries, ClearView enables making informed decisions and effectively communicating findings.

## 1. Introduction

ClearView is a powerful tool designed for viewing and analyzing water quality and environmental time series data. It supports various data formats, including fixed-width and CSV ASCII files, Excel spreadsheets, and SQLite database files. ClearView integrates data visualization, statistical analysis, and summary statistics, enabling you to gain valuable insights and make informed decisions based on your data.

## 2. Installation

ClearView is developed as a holoviews panel app and utilizes pyqt5 for handling dialogs. To install ClearView, please follow these steps:

1. Clone the ClearView repository from GitHub: [https://github.com/EcohydrologyTeam/CE-QUAL-W2-python](https://github.com/EcohydrologyTeam/CE-QUAL-W2-python)
2. Install the required dependencies using the provided setup.py or requirements.txt file.
3. Run the ClearView application using the provided launch script or by executing the main application file.

Note: ClearView requires Python 3.9 or higher to run.

## 3. Getting Started

### Opening Data Files

To start using ClearView, follow these steps:

1. Launch the ClearView application.
2. In the sidebar, click on the "Browse" button.
3. A dialog will appear, allowing you to browse and select the input data file.
4. Choose the desired data file and click "Open."

### Data Tab

After opening a data file, ClearView will automatically read the data into a pandas dataframe and display it in the Data tab. This tab provides a tabular representation of the data, facilitating easy access and interpretation.

### Stats Tab

The Stats tab in ClearView provides a concise summary of your data. It calculates and displays key statistical measures, enabling data-driven analysis and decision-making. The summary statistics are automatically computed and updated when a new data file is opened.

### Plots Tab

The Plots tab in ClearView allows you to generate informative plots for your data. Follow these steps to create a plot:

1. Select the desired variable to plot from the drop-down list in the Plots tab.
2. ClearView will automatically generate the plot using the selected variable.
3. The plots are created using the bokeh library, which provides standard tools for panning, zooming, and more.
4. Zooming in on the data adjusts the x-axis granularity to display the date and time accurately.
5. A tooltip appears when hovering over each data point, displaying the date and value.

### Methods Tab

The Methods tab in ClearView enables you to apply various analysis methods to your data. To use the Methods tab:

1. Select the desired method from the dropdown list.
2. ClearView will apply the selected method to the data, automatically updating the data table in the Methods tab to show the processed data.
3. The following methods are currently supported in ClearView: Hourly Mean, Hourly Max, Hourly Min, Daily Mean, Daily Max, Daily Min, Weekly Mean, Weekly Max, Weekly Min, Monthly Mean, Monthly Max, Monthly Min, Annual Mean, Annual Max, Annual Min, Decadal Mean, Decadal Max, Decadal Min, Cumulative Sum, Cumulative Max, and Cumulative Min.
4. Supported Data Formats

ClearView supports the following data formats:

1. Fixed-width ASCII files (*.npt)
2. Fixed-width ASCII files (*.opt)
3. CSV files (*.csv)
4. Excel spreadsheets (*.xls, *.xlsx)
5. SQLite database files (*.db, *.sqlite)

ClearView seamlessly reads and writes these data formats, providing compatibility and flexibility with various models, sensors, analysis tools, and workflows.

## 5. Plotting Controls

ClearView utilizes the bokeh library for creating plots and provides several controls for interactive visualization:

- Panning: Click and drag the plot to pan in any direction.
- Zooming: Use the mouse wheel to zoom in and out of the plot.
- Reset Zoom: Click the reset zoom button to revert to the original zoom level.
- Zoom Box: Click and drag to create a zoom box around a specific area of the plot.
- Hover Tool: Hover over data points to display tooltips with date and value information.

These controls enhance your ability to explore and analyze the data visually.

## 6. Analysis Methods

ClearView offers a range of analysis methods that can be applied to your data. These methods allow you to derive valuable insights and perform data-driven analysis. The currently supported methods in ClearView are as follows:

- Hourly Mean
- Hourly Max
- Hourly Min
- Daily Mean
- Daily Max
- Daily Min
- Weekly Mean
- Weekly Max
- Weekly Min
- Monthly Mean
- Monthly Max
- Monthly Min
- Annual Mean
- Annual Max
- Annual Min
- Decadal Mean
- Decadal Max
- Decadal Min
- Cumulative Sum
- Cumulative Max
- Cumulative Min

By selecting a method from the dropdown list in the Methods tab, ClearView automatically applies the method and updates the data table to show the processed data.

## 7. Saving Data

ClearView allows you to save your data, processed data, and summary statistics to SQLite database files. To save the data:

1. Click on the "Save" button in the ClearView interface.
2. Choose the destination and file name for the SQLite database file.
3. Click "Save" to save the data.

You can also save the processed data and summary statistics to separate SQLite database files to keep track of your analysis results.

## 8. Conclusion

ClearView is a powerful tool for water quality and environmental data analysis. By providing an intuitive user interface, comprehensive plotting capabilities, statistical summaries, and various analysis methods, ClearView enables you to explore your data, derive valuable insights, and make informed decisions. We hope this documentation has provided you with a clear understanding of ClearView's features and how to effectively use the tool. Should you have any further questions or need assistance, please feel free to reach out to our support team. Happy analyzing!
