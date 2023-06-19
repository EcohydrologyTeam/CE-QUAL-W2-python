# %% Import packages
import pandas as pd
import seaborn as sns
import holoviews as hv
import panel as pn
from collections import OrderedDict
from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter
from bokeh.models import HoverTool
import cequalw2 as w2

pn.extension()

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
        curve = hv.Curve(df, 'Date', column).opts(width=1400, height=600)
        curves[column] = curve

        # Create a HoverTool to display tooltips. Show the values of the Date column and the selected column
        hover_tool = HoverTool(
            # tooltips=[('Date', '@Date{%Y-%m-%d}'), ('Value', '$y')], formatters={"@Date": "datetime"}
            tooltips=[('Date', '@Date{%Y-%m-%d}'), (column, '$y')], formatters={"@Date": "datetime"}
        )

        tooltips[column] = hover_tool

    return curves, tooltips


# %% Load the budget spreadsheet (a copy of the original spreadsheet)
# df = w2.read_excel('/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Spokane River/_aaa.xlsx')

infile = '/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Spokane River/tsr_1_seg2.csv'
header_rows = w2.get_data_columns_csv(infile)
df = w2.read(infile, 2001, header_rows)

# %% Formatting

# Set theme
pn.widgets.Tabulator.theme = 'default'

# Specify special column formatting
float_format = NumberFormatter(format='0.00', text_align='right')

# %% Specify formatting

# Specify column formatters
float_cols = df.columns
bokeh_formatters = {col: float_format for col in float_cols}

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
background_color = '#f5fff5'

# Specify the app dimensions
app_width = 1400
app_height = 600

# Create the data table using a Tabulator widget
data_table = pn.widgets.Tabulator(
    df,
    formatters=bokeh_formatters,
    text_align=text_align,
    frozen_columns=['Item'],
    show_index=True,
    titles=titles,
    header_align=header_align,
    width=app_width,
    height=app_height
)

# Create a holoviews plot of the data. Don't use the cequalw2 module to do this. Use holoviews.
curves, tooltips = hv_plot(df)

# Create a dropdown widget for selecting data columns
dropdown = pn.widgets.Select(options=list(curves.keys()), width=200)

# Define a callback function to update the plot when the dropdown value changes
def update_plot(event):
    selected_column = dropdown.value
    index = df.columns.tolist().index(dropdown.value)
    curve = curves[selected_column]
    tip = tooltips[selected_column]
    curve.opts(tools=[tip])
    plot.object = curve
    # plot.object.opts(tools=[tip])  # Add the HoverTool to the plot
    print('plot.object = ', plot.object)
    print('tip = ', tip)
    print()


    print('selected_column = ', selected_column)
    print('index = ', index)
    print(df.columns.tolist()[index])

# Get the index of the df.columns list using dropdown.value
index = df.columns.tolist().index(dropdown.value)

# Create a panel with the plot and the dropdown widget
selected_column = dropdown.value
print('selected_column = ', selected_column)
plot = pn.pane.HoloViews(curves[selected_column])
tip = tooltips[selected_column]
plot.object.opts(tools=[tip])  # Add the HoverTool to the plot
dropdown.param.watch(update_plot, 'value')

# %%
# Create the Data tab
data_tab = pn.Column(
    '## CE-QUAL-W2 Viewer',
    data_table,
    background=background_color,
    sizing_mode='stretch_both',
    margin=(25, 0, 0, 0),
    padding=(0, 0, 0, 0),
    css_classes=['panel-widget-box'],
    width=app_width,
    height=app_height,
    align='center',
)

# Create a plot tab
plot_tab = pn.Column(
    '## Plot',
    dropdown,
    plot,
    background=background_color,
    sizing_mode='stretch_both',
    margin=(25, 0, 0, 0),
    padding=(0, 0, 0, 0),
    css_classes=['panel-widget-box'],
    width=app_width,
    height=app_height,
    align='center',
)

# Create the app and add the tabs
tabs = pn.Tabs(
    ('Data', data_tab), 
    ('Plot', plot_tab)
)

# Serve the app
tabs.show()

# %%
