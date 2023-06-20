import pandas as pd
import holoviews as hv
from bokeh.models import HoverTool
import panel as pn

hv.extension('bokeh')  # Load the HoloViews plotting extension

def hv_plot(df):
    # Create a HoloViews Curve element for each data column
    curves = {}
    for column in df.columns[1:]:
        curve = hv.Curve(df, 'Date', column).opts(width=800, height=400)
        curves[column] = curve

    # Create a HoverTool to display tooltips. Show the values of the Date column and the selected column
    hover_tool = HoverTool(
        tooltips=[('Date', '@Date{%Y-%m-%d}'), ('Value', '$y')], formatters={"@Date": "datetime"}
    )

    # HoverTool(tooltips=[('date', '@DateTime{%F}')], formatters={'@DateTime': 'datetime'})
    tooltips = [hover_tool]

    return curves, tooltips

# Define a callback function to update the plot when the dropdown value changes
def update_plot(event):
    selected_column = dropdown.value
    plot_object.object = curves[selected_column]

# Create plot widget
def create_and_show_plot_widget(df):
    curves, tooltips = hv_plot(df)

    # Create a dropdown widget for selecting data columns
    dropdown = pn.widgets.Select(options=list(curves.keys()))

    # Create a panel with the plot and the dropdown widget
    plot_object = pn.pane.HoloViews(curves[dropdown.value])
    plot_object.object.opts(tools=tooltips)  # Add the HoverTool to the plot
    dropdown.param.watch(update_plot, 'value')
    panel = pn.Column(plot_object, dropdown)

    # Show the panel
    panel.show()

if __name__ == '__main__':
    # Create a sample dataframe with water quality time series data
    data = {
        'Date': pd.date_range(start='2023-01-01', periods=100),
        'Temperature': [25, 26, 26, 25, 24, 24, 23, 22, 23, 24] * 10,
        'pH': [7.0, 7.1, 7.2, 7.3, 7.2, 7.1, 7.0, 7.2, 7.3, 7.4] * 10,
        'Turbidity': [1.2, 1.5, 1.4, 1.6, 1.3, 1.7, 1.9, 1.8, 1.6, 1.5] * 10
    }
    df = pd.DataFrame(data)

    create_and_show_plot_widget(df)