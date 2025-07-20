import pandas as pd
import numpy as np
import holoviews as hv
import panel as pn

hv.extension('bokeh')  # Load the HoloViews plotting extension for Bokeh

# Sample data

dates = pd.date_range(start='2023-07-01', end='2023-07-31', freq='H')

df = pd.DataFrame({
    'Time':                             dates,
    'Water Temperature':                np.random.uniform(10, 30, len(dates)),
    'Depth':                            np.random.uniform(1, 10,  len(dates)),
    'Flow':                             np.random.uniform(5, 50,  len(dates)),
    'Velocity':                         np.random.uniform(0.1, 2, len(dates)),
    'Vegetation_Biomass':               np.random.uniform(0, 100, len(dates)),
    'Net_Primary_Productivity (NPP)':   np.random.uniform(0, 100, len(dates)),
    'Gross_Primary_Productivity (GPP)': np.random.uniform(0, 100, len(dates)),
    'Leaf_Area_Index (LAI)':            np.random.uniform(0, 100, len(dates)),
    'Phenology':                        np.random.uniform(0, 100, len(dates)),
    'Leaf_Chlorophyll_Content':         np.random.uniform(0, 100, len(dates)),
    'Canopy_Height':                    np.random.uniform(0, 100, len(dates)),
    'Leaf_Nitrogen_Content':            np.random.uniform(0, 100, len(dates)),
    'Water_Use_Efficiency (WUE)':       np.random.uniform(0, 100, len(dates)),
    'Respiration_Rates':                np.random.uniform(0, 100, len(dates)),
    'Mortality_Rates':                  np.random.uniform(0, 100, len(dates)),
    'Recruitment_Rates':                np.random.uniform(0, 100, len(dates)),
    'Disturbance_Events':               np.random.uniform(0, 100, len(dates))
})

def create_time_series_plot(data, variables):
    curves = [hv.Curve(data, 'Time', v).opts(title=f'Time Series - {v}') for v in variables]
    plot = hv.Overlay(curves).opts(width=800, height=400, show_grid=True, tools=['hover'])
    return plot

# Create a list of available variables for selection
variables = list(df.columns)
y_variables = pn.widgets.MultiSelect(name='Variables', options=variables, value=['Water Temperature'])

# Update the plot when the selected variables change
@pn.depends(y_variables.param.value)
def update_plot(selected_variables):
    return create_time_series_plot(df, selected_variables)

# Create the app layout
app_layout = pn.Column(
    '# Water Data Explorer',
    '## Select variables to plot:',
    y_variables,
    pn.panel(update_plot, sizing_mode='stretch_width')
).servable(title='Water Data Explorer')

main = pn.Row(app_layout)
main.show()