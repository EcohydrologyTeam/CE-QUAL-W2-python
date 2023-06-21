# %% Import packages
import os
import glob
import csv
import pandas as pd
import seaborn as sns
import holoviews as hv
import panel as pn
from collections import OrderedDict
from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter
from tkinter import filedialog
import threading
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import cequalw2 as w2

# import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
# import PyQt5.QtGui as qtg

hv.extension('bokeh')

# Set the desired theme
hv.renderer('bokeh').theme = 'night_sky'

css = """
.bk.bk-tab.bk-active {
  background-color: #00aedb;
  color: black;
  font-size: 14px;
  width: 100px;
  text-align: center;
  padding: 5px;
  margin: 1px;
}

.bk.bk-tab:not(bk-active) {
  background-color: gold;
  color: black;
  font-size: 14px;
  width: 100px;
  text-align: center;
  padding: 5px;
  margin: 1px;
}

.hv-Tabulator {
    height: 600px; /* Set a fixed height for the table */
    overflow-y: auto; /* Enable vertical scrolling */
}
"""

pn.extension('tabulator', 'ipywidgets', raw_css=[css])

class ClearView:
    def __init__(self):
        self.data_database_path = None
        self.stats_database_path = None
        self.table_name = 'data'

        # Specify background color
        # self.background_color = '#f5fff5'
        self.background_color = '#fafafa'

        # Specify the app dimensions
        self.app_width = 1200
        self.app_height = 700

        # Set theme
        pn.widgets.Tabulator.theme = 'default'

        # Specify special column formatting
        self.float_format = NumberFormatter(format='0.00', text_align='right')

    def create_data_dropdown_widget(self):
        # Create a dropdown widget for selecting data columns
        self.data_dropdown = pn.widgets.Select(options=list(self.curves.keys()), width=200)

    def create_analysis_dropdown_widget(self):
        # Create a dropdown widget for selecting analysis and processing methods
        self.analysis_dropdown = pn.widgets.Select(options=list(self.time_series_methods.keys()), width=200)

    def create_plot(self):
        # Create a holoviews plot of the data. Don't use the cequalw2 module to do this. Use holoviews.
        self.curves, self.tooltips = w2.hv_plot(self.df, width=self.app_width, height=self.app_height)

    def create_plot_widget(self):
        # Create plot widget

        # Get the index of the df.columns list
        index = self.df.columns.tolist().index(self.data_dropdown.value)

        # Create a panel with the plot and the dropdown widget
        selected_column = self.data_dropdown.value
        self.plot = pn.pane.HoloViews(self.curves[selected_column])
        tip = self.tooltips[selected_column]
        self.plot.object.opts(tools=[tip])  # Add the HoverTool to the plot
        self.data_dropdown.param.watch(self.update_plot, 'value')
        self.analysis_dropdown.param.watch(self.update_processed_data_table, 'value')

    def update_data_tab(self):
        ''' Create the Data tab '''
        self.data_tab.clear()
        self.data_tab.append(self.data_table)

    def update_stats_tab(self):
        ''' Create the Stats tab '''
        self.stats_tab.clear()
        self.stats_tab.append(self.stats_table)

    def update_plot_tab(self):
        ''' Create the Plot tab '''
        self.plot_tab.clear()
        self.plot_tab.append(self.data_dropdown)
        self.plot_tab.append(self.plot)

    def update_methods_tab(self):
        ''' Create Methods tab '''
        self.methods_tab.clear()
        self.methods_tab.append(self.analysis_dropdown)
        self.methods_tab.append(self.processed_data_table)

    def create_data_table(self):
        ''' Create the data table using a Tabulator widget '''

        # Specify column formatters
        self.float_cols = self.df.columns
        self.bokeh_formatters = {col: self.float_format for col in self.float_cols}

        # Specify column formatters
        text_align = { }
        titles = { }
        header_align = {col: 'center' for col in self.df.columns}

        # Create the data table using a Tabulator widget
        self.data_table = pn.widgets.Tabulator(
            self.df,
            formatters=self.bokeh_formatters,
            text_align=text_align,
            frozen_columns=['Date'],
            show_index=True,
            titles=titles,
            header_align=header_align,
            width=self.app_width,
            height=self.app_height
        )

    def create_stats_table(self):
        ''' Create the stats table using a Tabulator widget '''

        # Compute summary statistics
        self.df_stats = self.df.describe()
        self.df_stats.index.name = 'Statistic'

        # Specify column formatters
        text_align = { }
        titles = { }
        header_align = {col: 'center' for col in self.df_stats.columns}

        # Create the stats table using a Tabulator widget
        self.stats_table = pn.widgets.Tabulator(
            self.df_stats,
            formatters=self.bokeh_formatters,
            text_align=text_align,
            frozen_columns=['Statistic'],
            show_index=True,
            titles=titles,
            header_align=header_align,
            width=self.app_width,
            height=250,
            background=self.background_color,
        )

    def create_processed_data_table(self):
        ''' Create the processed data table using a Tabulator widget '''

        # Set the default processed data table
        self.df_processed = self.time_series_methods['Hourly Mean'](self.df)

        # Specify column formatters
        text_align = { }
        titles = { }
        header_align = {col: 'center' for col in self.df_processed.columns}

        # Create the processed data table using a Tabulator widget
        self.processed_data_table = pn.widgets.Tabulator(
            self.df_processed,
            formatters=self.bokeh_formatters,
            text_align=text_align,
            frozen_columns=['Date'],
            show_index=True,
            titles=titles,
            header_align=header_align,
            width=self.app_width,
            height=self.app_height,
            background=self.background_color
        )

    # Define a callback function to update the plot when the data dropdown value changes
    def update_plot(self, event):
        print('update_plot() called')
        selected_column = self.data_dropdown.value
        index = self.df.columns.tolist().index(self.data_dropdown.value)
        curve = self.curves[selected_column]
        tip = self.tooltips[selected_column]
        curve.opts(tools=[tip])
        self.plot.object = curve

    # Define a callback function to update the processed data table when the analysis dropdown value changes
    def update_processed_data_table(self, event):
        selected_analysis = self.analysis_dropdown.value
        self.df_processed = self.time_series_methods[selected_analysis](self.df)
        self.processed_data_table.value = self.df_processed

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

        This method sets the filename attribute (`self.filename`) to the given text value.

        Args:
            text (str): The new filename.
        """
        self.filename = text

    def browse_file(self, event):
        # Open a PyQt5 file dialog
        file_dialog = qtw.QFileDialog(self.dialog_app.activeModalWidget())
        file_dialog.setFileMode(qtw.QFileDialog.ExistingFile)
        file_dialog.setNameFilters(['All Files (*.*)', 'CSV Files (*.csv)', 'NPT Files (*.npt)',
            'OPT Files (*.opt)', 'Excel Files (*.xlsx *.xls)', 'SQLite Files (*.db)'])
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
            self.directory, self.filename = os.path.split(self.file_path)
            basefilename, extension = os.path.splitext(self.filename)

            print('file_path = ', self.file_path)
            self.directory, self.filename = os.path.split(self.file_path)
            print('directory = ', self.directory)
            print('filename = ', self.filename)
            basefilename, extension = os.path.splitext(self.filename)
            print('basefilename = ', basefilename)
            print('extension = ', extension)

            if extension.lower() in ['.npt', '.opt']:
                self.data_columns = w2.get_data_columns_fixed_width(self.file_path)
                FILE_TYPE = 'ASCII'
            elif extension.lower() == '.csv':
                self.data_columns = w2.get_data_columns_csv(self.file_path)
                FILE_TYPE = 'ASCII'
            elif extension.lower() == '.db':
                FILE_TYPE = 'SQLITE'
            elif extension.lower() == '.xlsx' or extension.lower() == '.xls':
                FILE_TYPE = 'EXCEL'
            else:
                # self.show_warning_dialog('Only *.csv, *.npt, *.opt, and *.db files are supported.')
                print('Only *.csv, *.npt, *.opt, *.xlsx, and *.db files are supported.')
                return

            self.get_model_year()

            try:
                if FILE_TYPE == 'ASCII':
                    self.df = w2.read(self.file_path, self.year, self.data_columns)
                elif FILE_TYPE == 'SQLITE':
                    self.df = w2.read_sqlite(self.file_path)
                elif FILE_TYPE == 'EXCEL':
                    self.df = w2.read_excel(self.file_path)

                # Create plot (create this before the dropdown lists)
                self.create_plot()

                # Create time series methods
                self.set_time_series_methods()

                # Create dropdown lists (create these before creating the plot panel)
                self.create_data_dropdown_widget()
                self.create_analysis_dropdown_widget()

                # Create tables and plot panel
                self.create_plot_widget()
                self.create_data_table()
                self.create_stats_table()
                self.create_processed_data_table()

                # Create new tabs
                self.update_data_tab()
                self.update_stats_tab()
                self.update_plot_tab()
                self.update_methods_tab()

            except IOError:
                # self.show_warning_dialog(f'An error occurred while opening {self.filename}')
                print(f'An error occurred while opening {self.filename}')
                return

    def set_time_series_methods(self):
        # Specify the time series math and stats methods
        self.time_series_methods = OrderedDict()
        # Compute hourly mean, interpolating to fill missing values
        self.time_series_methods['Hourly Mean']    = lambda df: df.resample('H').mean().interpolate()
        self.time_series_methods['Hourly Max']     = lambda df: df.resample('H').max().interpolate()
        self.time_series_methods['Hourly Min']     = lambda df: df.resample('H').min().interpolate()
        self.time_series_methods['Daily Mean']     = lambda df: df.resample('D').mean().interpolate()
        self.time_series_methods['Daily Max']      = lambda df: df.resample('D').max().interpolate()
        self.time_series_methods['Daily Min']      = lambda df: df.resample('D').min().interpolate()
        self.time_series_methods['Weekly Mean']    = lambda df: df.resample('W').mean().interpolate()
        self.time_series_methods['Weekly Max']     = lambda df: df.resample('W').max().interpolate()
        self.time_series_methods['Weekly Min']     = lambda df: df.resample('W').min().interpolate()
        self.time_series_methods['Monthly Mean']   = lambda df: df.resample('M').mean().interpolate()
        self.time_series_methods['Monthly Max']    = lambda df: df.resample('M').max().interpolate()
        self.time_series_methods['Monthly Min']    = lambda df: df.resample('M').min().interpolate()
        self.time_series_methods['Annual Mean']    = lambda df: df.resample('Y').mean().interpolate()
        self.time_series_methods['Annual Max']     = lambda df: df.resample('Y').max().interpolate()
        self.time_series_methods['Annual Min']     = lambda df: df.resample('Y').min().interpolate()
        self.time_series_methods['Decadal Mean']   = lambda df: df.resample('10Y').mean().interpolate()
        self.time_series_methods['Decadal Max']    = lambda df: df.resample('10Y').max().interpolate()
        self.time_series_methods['Decadal Min']    = lambda df: df.resample('10Y').min().interpolate()
        self.time_series_methods['Cumulative Sum'] = lambda df: df.cumsum()
        self.time_series_methods['Cumulative Max'] = lambda df: df.cummax()
        self.time_series_methods['Cumulative Min'] = lambda df: df.cummin()
        # Compute moving averages
        # self.time_series_methods['7-Days Moving Average']  = lambda df: df.rolling(window=7).mean()
        # self.time_series_methods['24-Hour Moving Average'] = lambda df: df.rolling(window=24).mean()
        # Compute exponentially weighted moving averages
        # self.time_series_methods['24-hour EWMA'] = lambda df: df.ewm(span=24).mean()
        # self.time_series_methods['7-day EWMA']   = lambda df: df.ewm(span=7).mean()

        # # Compute exponential smoothing 
        # model = ExponentialSmoothing(df, trend='add', seasonal=None)
        # result = model.fit()
        # df['Exponential Smoothing'] = result.fittedvalues

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

        if self.data_database_path and self.df is not None:
            self.save_to_sqlite(self.data, self.data_database_path)

    def save_stats(self):
        """
        Saves statistics to an SQLite database file.

        Prompts the user to select a file path for saving the statistics and
        saves the statistics to the chosen file path.

        :return: None
        """

        default_filename = self.file_path + '_stats.db'
        options = qtw.QFileDialog.Options()
        returned_path, _ = qtw.QFileDialog.getSaveFileName(self, "Save As", default_filename,
                                                        "SQLite Files (*.db);; All Files (*)", options=options)
        if not returned_path:
            return

        self.stats_database_path = returned_path

        if self.stats_database_path and self.df_stats is not None:
            self.save_to_sqlite(self.stats, self.stats_database_path)

    def create_empty_tab(self):
        # empty_data = hv.Curve([])
        empty_data = ''
        tab = pn.Column(
            empty_data,
            background=self.background_color,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
            # height=self.app_height,
            scroll=True
        )
        return tab

    def create_empty_tabs(self):
        # Create empty tabs
        self.data_tab = self.create_empty_tab()
        self.stats_tab = self.create_empty_tab()
        self.plot_tab = self.create_empty_tab()
        self.methods_tab = self.create_empty_tab()

    def create_sidebar(self):
        # Alternative name: Prismatica

        sidebar_text = """
        <h2><font color="dodgerblue">ClearView</font></h2>
        <h3><font color="#7eab55">A Comprehensive Tool for Water Quality and Environmental Data Analysis</font></h3>
        <hr>

        ClearView is a tool for viewing and analyzing water quality and environmental time series data. Designed to work with model input and output data, sensor data, and laboratory measurements, ClearView seamlessly reads and writes multiple data formats, providing compatibility and flexibility with a variety of new and legacy models, sensors, analysis tools, and workflows.

        The user interface of ClearView is designed with simplicity and usability in mind. Its plotting component allows you to generate informative plots, enabling the identification of trends, patterns, and anomalies within your time series data. ClearView provides a tabular display, facilitating easy access and interpretation. ClearView's summary statistics provides a concise summary of your data. This feature allows you to evaluate key statistical measures, facilitating data-driven analysis and decision-making.

        ClearView streamlines data analysis and time series processing. Leveraging advanced algorithms and statistical techniques, this tool enables exploring data and calculating relevant metrics to derive valuable insights, such as identifying pollution sources, detecting changes in water quality over time, and deriving a deeper understanding of environmental data.

        The aim of ClearView is to streamline workflows and enhance productivity. By integrating data visualization, analysis, and statistical summaries, ClearView enables making informed decisions and effectively communicating findings.

        <hr>

        <h4>Open a File:</h4>
        """

        # create an html tag with dodgerblue color and bold text
        # pn.pane.HTML('<font color="dodgerblue"><b>Upload a File:</b></font>')

        # Create a button to trigger file selection
        self.file_button = pn.widgets.Button(name="Browse", button_type="primary")
        self.file_button.on_click(self.browse_file)

        # Create sidebar
        self.sidebar = pn.layout.WidgetBox(
            pn.pane.Markdown(
                sidebar_text,
                margin=(0, 10)
            ),
            self.file_button,
            max_width=350,
            height=1000,
            sizing_mode='stretch_width',
            scroll=True
        ).servable(area='sidebar')

    def create_app(self):
        # Create the app and add the tabs
        self.create_sidebar()
        self.create_empty_tabs()
        self.tabs = pn.Tabs(
            ('Data', self.data_tab),
            ('Stats', self.stats_tab),
            ('Plot', self.plot_tab),
            ('Methods', self.methods_tab),
            tabs_location='above',
            # background='blue',
            # sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
        ).servable(title='ClearWater Insights')

        # Create Main Layout
        self.main = pn.Row(self.sidebar, self.tabs)

        # Create a PyQt5 application
        self.dialog_app = qtw.QApplication([])

        # Serve the app
        self.main.show()


# Test the app
if __name__ == '__main__':
    clearview = ClearView()
    clearview.create_app()
