# %% Import packages
import pandas as pd
import seaborn as sns
import holoviews as hv
import panel as pn
from collections import OrderedDict
from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter
from bokeh.models import HoverTool
import cequalw2 as w2

hv.extension('bokeh')

css = """
.bk-root .bk-tabs-header .bk-tab.bk-active {
  background-color: #00aedb;
  color: black;
  font-size: 18px;
  width: 100px;
  horizontal-align: center;
  padding: 5px, 5px, 5px, 5px;
  margin: 1px;
  border: 1px solid black;
}

.bk.bk-tab:not(bk-active) {
  background-color: gold;
  color: black;
  font-size: 18px;
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

def hv_plot(df):
    # Create a HoloViews Curve element for each data column
    curves = OrderedDict()
    tooltips = OrderedDict()

    for column in df.columns:
        # Create a HoloViews Curve element for each data column
        curve = hv.Curve(df, 'Date', column).opts(width=1400, height=600)

        # Add the grid style to the curve
        curve.opts(show_grid=True, show_legend=True)

        # Create a HoverTool to display tooltips. Show the values of the Date column and the selected column
        hover_tool = HoverTool(
            # tooltips=[('Date', '@Date{%Y-%m-%d}'), ('Value', '$y')], formatters={"@Date": "datetime"}
            tooltips=[('Date', '@Date{%Y-%m-%d}'), (column, '$y')], formatters={"@Date": "datetime"}
        )

        # Add the curve and hover tool to the dictionaries
        curves[column] = curve
        tooltips[column] = hover_tool

    return curves, tooltips


class CE_QUAL_W2_Viewer:
    def __init__(self, df):
        self.df = df

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
        self.app_width = 1400
        self.app_height = 600

        # Create the data table using a Tabulator widget
        self.data_table = pn.widgets.Tabulator(
            self.df,
            formatters=self.bokeh_formatters,
            text_align=text_align,
            frozen_columns=['Item'],
            show_index=True,
            titles=titles,
            header_align=header_align,
            width=self.app_width,
            height=self.app_height
        )

        # Create the stats table using a Tabulator widget
        self.stats_table = pn.widgets.Tabulator(
            self.df.describe(),
            formatters=self.bokeh_formatters,
            text_align=text_align,
            frozen_columns=['Item'],
            show_index=True,
            titles=titles,
            header_align=header_align,
            width=self.app_width,
            height=300
        )

        # Create the processed data table using a Tabulator widget
        # For now, just compute the daily mean
        self.processed_data_table = pn.widgets.Tabulator(
            self.df.resample('D').mean(),
            formatters=self.bokeh_formatters,
            text_align=text_align,
            frozen_columns=['Item'],
            show_index=True,
            titles=titles,
            header_align=header_align,
            width=self.app_width,
            height=300
        )

        # Create a holoviews plot of the data. Don't use the cequalw2 module to do this. Use holoviews.
        self.curves, self.tooltips = hv_plot(self.df)

        # Create a dropdown widget for selecting data columns
        self.data_dropdown = pn.widgets.Select(options=list(self.curves.keys()), width=200)

        # Create a dropdown widget for selecting analysis and processing methods
        self.analysis_dropdown = pn.widgets.Select(options=['Daily Mean', 'Daily Max', 'Daily Min'], width=200)


        # Get the index of the df.columns list
        index = df.columns.tolist().index(self.data_dropdown.value)

        # Create a panel with the plot and the dropdown widget
        selected_column = self.data_dropdown.value
        self.plot = pn.pane.HoloViews(self.curves[selected_column])
        tip = self.tooltips[selected_column]
        self.plot.object.opts(tools=[tip])  # Add the HoverTool to the plot
        self.data_dropdown.param.watch(self.update_plot, 'value')

        # Create the Data tab
        self.data_tab_title = '''
        <h1><font color="dodgerblue">ClearWater Insights: </font><font color="#7eab55">Data</font></h1>
        <hr>
        '''

        self.data_tab_title_alert = pn.pane.Alert(self.data_tab_title, alert_type='light', align='center')

        self.data_tab = pn.Column(
            self.data_tab_title_alert,
            self.data_table,
            background=self.background_color,
            sizing_mode='stretch_both',
            margin=(0, 0, 0, 0),
            padding=(0, 0, 0, 0),
            css_classes=['panel-widget-box'],
            width=self.app_width,
            height=self.app_height,
            align='center',
        )

        # Create the Stats tab
        self.stats_tab_title = '''
        <h1><font color="dodgerblue">ClearWater Insights: </font><font color="#7eab55">Statistics</font></h1>
        <hr>
        '''

        self.stats_tab_title_alert = pn.pane.Alert(self.stats_tab_title, alert_type='light', align='center')

        self.stats_tab = pn.Column(
            self.stats_tab_title_alert,
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
        self.plot_tab_title = '''
        <h1><font color="dodgerblue">ClearWater Insights: </font><font color="#7eab55">Plots</font></h1>
        <hr>
        '''

        self.plot_tab_title_alert = pn.pane.Alert(self.plot_tab_title, alert_type='light', align='center')

        self.plot_tab = pn.Column(
            self.plot_tab_title_alert,
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

        # Create the Processed Data tab
        self.processed_data_tab_title = '''
        <h1><font color="dodgerblue">ClearWater Insights: </font><font color="#7eab55">Processed Data</font></h1>
        <hr>
        '''

        self.processed_data_tab_title_alert = pn.pane.Alert(self.processed_data_tab_title, alert_type='light', align='center')

        self.processed_data_tab = pn.Column(
            self.processed_data_tab_title_alert,
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
        )

        # Serve the app
        self.tabs.show()

    # Define a callback function to update the plot when the data dropdown value changes
    def update_plot(self, event):
        selected_column = self.data_dropdown.value
        index = self.df.columns.tolist().index(self.data_dropdown.value)
        curve = self.curves[selected_column]
        tip = self.tooltips[selected_column]
        curve.opts(tools=[tip])
        self.plot.object = curve

    # Define a callback function to update the processed data table when the analysis dropdown value changes
    def update_processed_data_table(self, event):
        selected_analysis = self.analysis_dropdown.value
        if selected_analysis == 'Daily Mean':
            self.processed_data_table.object = self.df.resample('D').mean()
        elif selected_analysis == 'Daily Max':
            self.processed_data_table.object = self.df.resample('D').max()
        elif selected_analysis == 'Daily Min':
            self.processed_data_table.object = self.df.resample('D').min()
        if selected_analysis == 'Hourly Mean':
            self.processed_data_table.object = self.df.resample('H').mean()
        elif selected_analysis == 'Hourly Max':
            self.processed_data_table.object = self.df.resample('H').max()
        elif selected_analysis == 'Hourly Min':
            self.processed_data_table.object = self.df.resample('H').min()

# %%
# Test the app
if __name__ == '__main__':
    infile = '/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Spokane River/tsr_1_seg2.csv'
    header_rows = w2.get_data_columns_csv(infile)
    df = w2.read(infile, 2001, header_rows)
    CE_QUAL_W2_Viewer(df)