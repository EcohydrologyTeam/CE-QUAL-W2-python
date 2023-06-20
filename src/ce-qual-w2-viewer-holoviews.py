# %% Import packages
import pandas as pd
import seaborn as sns
import holoviews as hv
import panel as pn
from collections import OrderedDict
from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter
from bokeh.models import HoverTool, DatetimeTickFormatter
import cequalw2 as w2

hv.extension('bokeh')

# Set the desired theme
hv.renderer('bokeh').theme = 'night_sky'

css = """
.bk-root .bk-tabs-header .bk-tab.bk-active {
  background-color: #00aedb;
  color: black;
  font-size: 14px;
  width: 100px;
  horizontal-align: center;
  padding: 5px, 5px, 5px, 5px;
  margin: 1px;
  border: 1px solid black;
}

.bk.bk-tab:not(bk-active) {
  background-color: gold;
  color: black;
  font-size: 14px;
  width: 100px;
  horizontal-align: center;
  padding: 5px, 5px, 5px, 5px;
  margin: 1px;
  border: 1px solid black;
}

"""

# q: What shade of green goes best with gold?
# a: https://www.color-hex.com/color-palette/700


pn.extension(raw_css=[css])

# %%
# Cycle through a list of colors
def color_cycle(colors, num_colors):
    """Cycle through a list of colors"""
    for i in range(num_colors):
        yield colors[i % len(colors)]

def hv_plot(df, width=1200, height=600, bgcolor='lightgray', line_color='blue',
    fontsize={'xlabel': 11, 'ylabel': 11, 'xticks': 10, 'yticks': 10}):

    # Create a HoloViews Curve element for each data column
    curves = OrderedDict()
    tooltips = OrderedDict()

    # Specify format for the date axis

    for column in df.columns:
        # Create a HoloViews Curve element for each data column
        curve = hv.Curve(df, 'Date', column).opts(
            width=width,
            height=height,
            # bgcolor='black',
            line_color='dodgerblue',
            fontsize=fontsize
        )

        date_axis_formatter = DatetimeTickFormatter(
            minutes=["%H:%M"],
            hours=["%H:%M"],
            days=["%d %b %Y"],
            months=["%d %b %Y"],
            years=["%d %b %Y"]
        )

        curve.opts(
            show_grid=True,
            show_legend=True,
            xformatter=date_axis_formatter
        )

        # Create a HoverTool to display tooltips. Show the values of the Date column and the selected column
        hover_tool = HoverTool(
            tooltips=[('Date', '@Date{%d %b %Y %H:%M}'), (column, '$y')], formatters={"@Date": "datetime"}
        )

        # Add the curve and hover tool to the dictionaries
        curves[column] = curve
        tooltips[column] = hover_tool

    return curves, tooltips


class CE_QUAL_W2_Viewer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

        # Compute summary statistics
        self.df_stats = self.df.describe()
        self.df_stats.index.name = 'Statistic'

        # Create dictionary of analysis and processing methods
        self.set_methods()

        # Create a processed dataframe as a placeholder
        self.df_processed = self.methods['Hourly Mean']
        # pn.bind(self.df_processed, self.update_processed_data_table)

        self.data_database_path = None
        self.stats_database_path = None
        self.table_name = 'data'

        # %% Formatting

        # Set theme
        pn.widgets.Tabulator.theme = 'default'

        # Specify special column formatting
        self.float_format = NumberFormatter(format='0.00', text_align='right')

        # %% Specify formatting

        # Specify column formatters
        self.float_cols = self.df.columns
        self.bokeh_formatters = {col: self.float_format for col in self.float_cols}

        # Text alignment. Note: alignments for currency and percentages were specified in bokeh_formatters
        text_align = {
            # 'Complete': 'center'
        }

        titles = {
            # 'abc def ghi': 'abc<br>def<br>ghi'
        }

        header_align = {col: 'center' for col in df.columns}

        # %% Create the app

        # Specify background color
        # self.background_color = '#f5fff5'
        self.background_color = '#fafafa'

        # Specify the app dimensions
        self.app_width = 1200
        self.app_height = 700

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

        # Create the processed data table using a Tabulator widget
        # For now, just compute the daily mean
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

        # Create a holoviews plot of the data. Don't use the cequalw2 module to do this. Use holoviews.
        self.curves, self.tooltips = hv_plot(self.df, width=self.app_width, height=self.app_height)

        # Create a dropdown widget for selecting data columns
        self.data_dropdown = pn.widgets.Select(options=list(self.curves.keys()), width=200)

        # Create a dropdown widget for selecting analysis and processing methods
        self.analysis_dropdown = pn.widgets.Select(options=list(self.methods.keys()), width=200)

        # Get the index of the df.columns list
        index = df.columns.tolist().index(self.data_dropdown.value)

        # Create a panel with the plot and the dropdown widget
        selected_column = self.data_dropdown.value
        self.plot = pn.pane.HoloViews(self.curves[selected_column])
        tip = self.tooltips[selected_column]
        self.plot.object.opts(tools=[tip])  # Add the HoverTool to the plot
        self.data_dropdown.param.watch(self.update_plot, 'value')
        self.analysis_dropdown.param.watch(self.update_processed_data_table, 'value')

        # Create the Data tab
        # self.data_tab_title = '''
        # <h1><font color="dodgerblue">ClearWater Insights: </font><font color="#7eab55">Data</font></h1>
        # <hr>
        # '''
        # self.data_tab_title_alert = pn.pane.Alert(self.data_tab_title, alert_type='light', align='center')

        self.data_tab = pn.Column(
            # self.data_tab_title_alert,
            self.data_table,
            background=self.background_color,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            padding=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
            width=self.app_width,
            height=self.app_height,
            # align='center',
        )

        # Create the Stats tab

        self.stats_tab = pn.Column(
            self.stats_table,
            background=self.background_color,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            padding=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
            width=self.app_width,
            height=200,
        )

        # Create a plot tab

        self.plot_tab = pn.Column(
            self.data_dropdown,
            self.plot,
            background=self.background_color,
            sizing_mode='stretch_both',
            margin=(25, 0, 0, 0),
            padding=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
            width=self.app_width,
            height=self.app_height,
            align='center'
        )

        self.processed_data_tab = pn.Column(
            self.analysis_dropdown,
            self.processed_data_table,
            background=self.background_color,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            padding=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
            width=self.app_width,
            height=self.app_height,
        )

        #------------------------------------------------------------------------------------

        # Alternative name: Prismatica

        sidebar_text = """
        <h2><font color="dodgerblue">AquaView</font></h2>
        <h3><font color="#7eab55">A Comprehensive Tool for Water Quality and Environmental Data Analysis</font></h3>
        <hr>

        AquaView is a tool for viewing and analyzing water quality and environmental time series data. Designed to work with model input and output data, sensor data, and laboratory measurements, AquaView seamlessly reads and writes multiple data formats, providing compatibility and flexibility with a variety of new and legacy models, sensors, analysis tools, and workflows.

        The user interface of AquaView is designed with simplicity and usability in mind. Its plotting component allows you to generate informative plots, enabling the identification of trends, patterns, and anomalies within your time series data. AquaView provides a tabular display, facilitating easy access and interpretation. AquaView's summary statistics provides a concise summary of your data. This feature allows you to evaluate key statistical measures, facilitating data-driven analysis and decision-making.

        AquaView streamlines data analysis and time series processing. Leveraging advanced algorithms and statistical techniques, this tool enables exploring data and calculating relevant metrics to derive valuable insights, such as identifying pollution sources, detecting changes in water quality over time, and deriving a deeper understanding of environmental data.

        The aim of AquaView is to streamline workflows and enhance productivity. By integrating data visualization, analysis, and statistical summaries, AquaView enables making informed decisions and effectively communicating findings.

        Upload a File:
        """

        self.file_input = pn.widgets.FileInput(sizing_mode='stretch_width')
        self.file_input.param.watch(self.browse_file, 'value')

        self.sidebar = pn.layout.WidgetBox(
            pn.pane.Markdown(
                sidebar_text,
                margin=(0, 10)
            ),
            self.file_input,
            max_width=350,
            height=1000,
            sizing_mode='stretch_width',
            scroll=True
        ).servable(area='sidebar')

        #------------------------------------------------------------------------------------

        # Create the app and add the tabs
        self.tabs = pn.Tabs(
            ('Data', self.data_tab), 
            ('Stats', self.stats_tab),
            ('Plot', self.plot_tab),
            ('Processed', self.processed_data_tab), 
            tabs_location='above',
            # background='blue',
            # sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
        ).servable(title='ClearWater Insights')

        self.main = pn.Row(self.sidebar, self.tabs)

        # Serve the app
        # self.tabs.show()
        self.main.show()

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
        print('update_processed_data_table() called')
        selected_analysis = self.analysis_dropdown.value
        self.df_processed = self.methods[selected_analysis]
        print(self.df_processed)
        # self.processed_data_table.object = methods[selected_analysis]
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

    def browse_file(self, event):
        self.file_path = self.file_input.value
        self.directory, self.filename = os.path.split(self.file_path)
        basefilename, extension = os.path.splitext(self.filename)

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
            file_dialog.close()
            # self.show_warning_dialog('Only *.csv, *.npt, *.opt, and *.db files are supported.')
            print('Only *.csv, *.npt, *.opt, and *.db files are supported.')
            return

        self.get_model_year()

        try:
            if FILE_TYPE == 'ASCII':
                self.df = w2.read(self.file_path, self.year, self.data_columns)
            elif FILE_TYPE == 'SQLITE':
                self.df = w2.read_sqlite(self.file_path)
            elif FILE_TYPE == 'EXCEL':
                self.df = w2.read_excel(self.file_path)
        except IOError:
            # self.show_warning_dialog(f'An error occurred while opening {self.filename}')
            print(f'An error occurred while opening {self.filename}')

    def set_methods(self):
        # Specify the analysis and processing methods
        self.methods = OrderedDict()
        # Compute hourly mean, interpolating to fill missing values
        self.methods['Hourly Mean'] = self.df.resample('H').mean().interpolate()
        self.methods['Hourly Max'] = self.df.resample('H').max().interpolate()
        self.methods['Hourly Min'] = self.df.resample('H').min().interpolate()
        self.methods['Daily Mean'] = self.df.resample('D').mean().interpolate()
        self.methods['Daily Max'] = self.df.resample('D').max().interpolate()
        self.methods['Daily Min'] = self.df.resample('D').min().interpolate()
        self.methods['Weekly Mean'] = self.df.resample('W').mean().interpolate()
        self.methods['Weekly Max'] = self.df.resample('W').max().interpolate()
        self.methods['Weekly Min'] = self.df.resample('W').min().interpolate()
        self.methods['Monthly Mean'] = self.df.resample('M').mean().interpolate()
        self.methods['Monthly Max'] = self.df.resample('M').max().interpolate()
        self.methods['Monthly Min'] = self.df.resample('M').min().interpolate()
        self.methods['Annual Mean'] = self.df.resample('Y').mean().interpolate()
        self.methods['Annual Max'] = self.df.resample('Y').max().interpolate()
        self.methods['Annual Min'] = self.df.resample('Y').min().interpolate()
        self.methods['Decadal Mean'] = self.df.resample('10Y').mean().interpolate()
        self.methods['Decadal Max'] = self.df.resample('10Y').max().interpolate()
        self.methods['Decadal Min'] = self.df.resample('10Y').min().interpolate()
        self.methods['Cumulative Sum'] = self.df.cumsum()
        self.methods['Cumulative Max'] = self.df.cummax()
        self.methods['Cumulative Min'] = self.df.cummin()
        # self.methods['Cumulative Mean'] = self.df.cummean()
        # self.methods['Cumulative Std'] = self.df.cumstd()
        # self.methods['Cumulative Skew'] = self.df.cumskew()
        # self.methods['Cumulative Kurtosis'] = self.df.cumkurt()
        # self.methods['Cumulative Product'] = self.df.cumprod()
        # self.methods['Cumulative Count'] = self.df.cumcount()
        # self.methods['Cumulative Quantile'] = self.df.cumquantile()
        # self.methods['Cumulative Rank'] = self.df.cumrank()
        # self.methods['Cumulative Mode'] = self.df.cummode()
        # self.methods['Cumulative Any'] = self.df.cumany()
        # self.methods['Cumulative All'] = self.df.cumall()
        # self.methods['Cumulative Nunique'] = self.df.cumnunique()
        # self.methods['Cumulative Sum of Squares'] = self.df.cumsum(axis=1)
        # self.methods['Cumulative Max of Squares'] = self.df.cummax(axis=1)
        # self.methods['Cumulative Min of Squares'] = self.df.cummin(axis=1)
        # self.methods['Cumulative Mean of Squares'] = self.df.cummean(axis=1)
        # self.methods['Cumulative Std of Squares'] = self.df.cumstd(axis=1)
        # self.methods['Cumulative Skew of Squares'] = self.df.cumskew(axis=1)
        # self.methods['Cumulative Kurtosis of Squares'] = self.df.cumkurt(axis=1)
        # self.methods['Cumulative Product of Squares'] = self.df.cumprod(axis=1)
        # self.methods['Cumulative Count of Squares'] = self.df.cumcount(axis=1)
        # self.methods['Cumulative Quantile of Squares'] = self.df.cumquantile(axis=1)
        # self.methods['Cumulative Rank of Squares'] = self.df.cumrank(axis=1)
        # self.methods['Cumulative Mode of Squares'] = self.df.cummode(axis=1)
        # self.methods['Cumulative Any of Squares'] = self.df.cumany(axis=1)
        # self.methods['Cumulative All of Squares'] = self.df.cumall(axis=1)
        # self.methods['Cumulative Nunique of Squares'] = self.df.cumnunique(axis=1)

# %%
# Test the app
if __name__ == '__main__':
    infile = '/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Spokane River/tsr_1_seg2.csv'
    header_rows = w2.get_data_columns_csv(infile)
    df = w2.read(infile, 2001, header_rows)
    CE_QUAL_W2_Viewer(df)