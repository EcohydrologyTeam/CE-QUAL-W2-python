# %% Import packages
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import datetime as dt
import panel as pn
from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter
pn.extension()
import cequalw2 as w2

# %% Load the budget spreadsheet (a copy of the original spreadsheet)
# df = w2.read_excel('/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Spokane River/_aaa.xlsx')

infile = '/Users/todd/GitHub/ecohydrology/CE-QUAL-W2/examples_precomputed/Spokane River/tsr_1_seg2.csv'
header_rows = w2.get_data_columns_csv(infile)
df = w2.read(infile, 2001, header_rows)
print(df.columns)

# # Remove the Date column
# df.index = df['Date']
# df = df.drop(columns=['Date'])
float_cols = df.columns


# %% Formatting

# Set theme
pn.widgets.Tabulator.theme = 'default'

# Specify special column formatting
float_format = NumberFormatter(format='0.00', text_align='right')

# %% Specify formatting

# Specify column formatters
bokeh_formatters = {col: float_format for col in float_cols}

# Text alignment. Note: alignments for currency and percentages were specified in bokeh_formatters
text_align = {
    # 'Complete': 'center',
    # 'Progress': 'left',
}

# For the headers that are too long, create titles with wrapped lines
titles = {
    # 'abc def ghi': 'abc<br>def<br>ghi',
    # 'def ghi jkl': 'def<br>ghi<br>jkl'
}

header_align = {col: 'center' for col in df.columns}

# %% Create the app

# Specify background color
background_color = '#f5fff5'

# Specify the app dimensions
app_width = 1800
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
    background=background_color,
    sizing_mode='stretch_both',
    margin=(25, 0, 0, 0),
    padding=(0, 0, 0, 0),
    css_classes=['panel-widget-box'],
    width=app_width,
    height=app_height,
    align='center',
)

# Create a holoviews plot of the data. Don't use the cequalw2 module to do this. Use holoviews.
plot = w2.hv_plot_time_series(df, colors=len(df.columns*['blue']))


# Add the plot to the plot tab
plot_tab.append(
    pn.pane.HoloViews(
        plot,
        sizing_mode='stretch_both',
        align='center',
        width=app_width,
        height=app_height,
    )
)

# Create the app and add tabs
tabs = pn.Tabs(
    ('Data', data_tab)
)

# Serve the app
tabs.show()
# %%
