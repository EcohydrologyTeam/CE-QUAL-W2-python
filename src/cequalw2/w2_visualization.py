import warnings
import os
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import holoviews as hv
from holoviews import opts
import yaml
from typing import List
warnings.filterwarnings("ignore")


plt.style.use('seaborn')
plt.rcParams['figure.figsize'] = (15, 9)
plt.rcParams['grid.color'] = '#E0E0E0'
plt.rcParams['lines.linewidth'] = 1
plt.rcParams['axes.facecolor'] = '#FBFBFB'
plt.rcParams["axes.edgecolor"] = '#222222'
plt.rcParams["axes.linewidth"] = 0.5
plt.rcParams['xtick.color'] = 'black'
plt.rcParams['ytick.color'] = 'black'
plt.rcParams['figure.subplot.hspace'] = 0.05  # Shrink the horizontal space

# Custom curve colors
# Using mountain and lake names for new color palettes
rainbow = ['#3366CC', '#0099C6', '#109618', '#FCE030', '#FF9900',
           '#DC3912']  # (blue, teal, green, yellow, orange, red)
everest = ['#3366CC', '#DC4020', '#10AA18', '#0099C6', '#FCE030',
           '#FF9900', ]  # (blue, red, green, teal, yellow, orange)

k2 = (
    sns.color_palette('husl', desat=0.8)[4],  # blue
    sns.color_palette('tab10')[3],  # red
    sns.color_palette('deep')[2],  # green
    sns.color_palette('tab10', desat=0.8)[1],  # purple
    sns.color_palette('deep', desat=0.8)[4],  # purple
    sns.color_palette('colorblind')[2],  # sea green
    sns.color_palette('colorblind')[0],  # deep blue
    sns.color_palette('husl')[0],  # light red
)

# Define string formatting constants, which work in string format statements
DEG_C_ALT = '\N{DEGREE SIGN}C'

# Define default line color
DEFAULT_COLOR = '#4488ee'

def get_colors(df: pd.DataFrame, palette: str, min_colors: int = 6) -> List[str]:
    """
    Get a list of colors from Seaborn's color palette.

    :param df: The DataFrame used to determine the number of colors.
    :type df: pd.DataFrame
    :param palette: The name of the color palette to use.
    :type palette: str
    :param min_colors: The minimum number of colors to select. (Default: 6)
    :type min_colors: int, optional

    :return: A list of colors selected from the color palette.
    :rtype: List[str]
    """

    num_colors = min(len(df), min_colors)
    colors = sns.color_palette(palette, num_colors)
    return colors


def simple_plot(series: pd.Series, **kwargs) -> plt.Figure:
    """
    This function creates a simple plot using Matplotlib and Pandas.

    :param series: A Pandas Series object containing the data to be plotted.
    :param **kwargs: Additional keyword arguments to customize the plot.
    :type **kwargs: keyword arguments

    :Keyword Arguments:
       - `title` (str) -- The title of the plot.
       - `ylabel` (str) -- The label for the y-axis.
       - `colors` (List[str]) -- A list of colors for the plot.
       - `figsize` (tuple) -- The figure size as a tuple of width and height.
       - `style` (str) -- The line style for the plot.
       - `palette` (str) -- The color palette to use.

    :returns: A Matplotlib Figure object representing the plot.
    """

    title: str = kwargs.get('title', None)
    ylabel: str = kwargs.get('ylabel', None)
    colors: List[str] = kwargs.get('colors', None)
    figsize: tuple = kwargs.get('figsize', (15, 9))
    style: str = kwargs.get('style', '-')
    palette: str = kwargs.get('palette', 'colorblind')

    fig, axes = plt.subplots(figsize=figsize)

    if not colors:
        colors = sns.color_palette(palette, 6)
        axes.set_prop_cycle("color", colors)

    series.plot(ax=axes, title=title, ylabel=ylabel, style=style)
    axis = plt.gca()
    axis.set_ylabel(ylabel)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def plot(df: pd.DataFrame, **kwargs) -> plt.Figure:
    """
    This function creates a plot using Matplotlib and Pandas.

    :param df: A Pandas DataFrame object containing the data to be plotted.
    :param **kwargs: Additional keyword arguments to customize the plot.
    :type **kwargs: keyword arguments

    :Keyword Arguments:
        - `title` (str) -- The title of the plot.
        - `legend_values` (List[str]) -- The values for the legend.
        - `ylabel` (str) -- The label for the y-axis.
        - `fig_size` (tuple) -- The figure size as a tuple of width and height.
        - `line_style` (str) -- The line style for the plot.
        - `colors` (str or List[str]) -- The color(s) to use for the plot.

    :returns: A Matplotlib Figure object representing the plot.
    """

    title: str = kwargs.get('title', None)
    legend_values: List[str] = kwargs.get('legend_values', None)
    ylabel: str = kwargs.get('ylabel', None)
    figsize: tuple = kwargs.get('fig_size', (15, 9))
    line_style: str = kwargs.get('line_style', '-')
    colors = kwargs.get('colors', 'k')

    fig, axes = plt.subplots(figsize=figsize)

    axes.set_prop_cycle("color", colors)

    df.plot(ax=axes, title=title, ylabel=ylabel, style=line_style)

    if legend_values:
        axes.legend(legend_values)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def plot_dataframe(*args) -> hv.core.overlay.Overlay:
    """
    This function creates a plot using Holoviews and Pandas DataFrame.

    :param *args: Positional arguments required for the function.
                  The arguments must be provided in the following order:
        1. df (pd.DataFrame): The DataFrame containing the data to be plotted.
        2. title (str): The title of the plot.
        3. legend_values (list): The values for the legend.
        4. xlabel (str): The label for the x-axis.
        5. ylabel (str): The label for the y-axis.
        6. figsize (tuple): The figure size as a tuple of width and height.
        7. line_style (str): The line style for the plot.
        8. color_palette (str): The color palette to use.

    :type *args: variable arguments

    :raises ValueError: If the number of arguments is not equal to 8.

    :returns: A Holoviews Overlay object representing the plot.
    """

    # Assign positional arguments to variables
    if len(args) != 8:
        raise ValueError(
            "The following eight arguments are required: df, title, legend_values, xlabel, "
            "ylabel, figsize, line_style, color_palette")

    df: pd.DataFrame
    title: str
    legend_values: list
    xlabel: str
    ylabel: str
    figsize: tuple
    line_style: str
    color_palette: str

    df, title, legend_values, xlabel, ylabel, figsize, line_style, color_palette = args

    # Convert the dataframe to a Holoviews Dataset
    dataset = hv.Dataset(df, kdims=[xlabel], vdims=list(df.columns))

    # Define the style options
    style_opts = opts.Curve(line_width=2, line_style=line_style)

    # Generate the color palette
    color_palette = hv.plotting.util.process_cmap(color_palette, categorical=True)
    color_cycle = color_palette[0:len(df.columns)]

    # Create the plot
    myplot = dataset.to(hv.Curve, xlabel, list(df.columns), label=legend_values).opts(
        opts.Curve(color=color_cycle, **style_opts), opts.Overlay(legend_position='right'),
        opts.Curve(width=figsize[0], height=figsize[1]), title=title, xlabel=xlabel, ylabel=ylabel
    )

    return myplot


def multi_plot(df, title: str = None, legend_list: List[str] = None, xlabel: str = None,
               ylabels: List[str] = None, colors: List[str] = None, figsize=(15, 21),
               style: str = '-', palette: str = 'colorblind', **kwargs):
    """
    Plot multiple time series from a DataFrame on a single figure.

    :param df: DataFrame containing the time series data.
    :type df: pd.DataFrame
    :param title: Title of the plot. Defaults to None.
    :type title: str
    :param legend_list: List of labels for the legend. Defaults to None.
    :type legend_list: List[str]
    :param xlabel: Label for the x-axis. Defaults to None.
    :type xlabel: str
    :param ylabels: List of labels for the y-axes. Defaults to None.
    :type ylabels: List[str]
    :param colors: List of colors for each time series. Defaults to None.
    :type colors: List[str]
    :param figsize: Figure size in inches. Defaults to (15, 21).
    :type figsize: tuple
    :param style: Line style for the time series. Defaults to '-'.
    :type style: str
    :param palette: Color palette to use for the time series. Defaults to 'colorblind'.
    :type palette: str
    :param **kwargs: Additional keyword arguments to be passed to the plot function.

    :return: None
    """

    fig, axes = plt.subplots(figsize=figsize)
    plt.subplots_adjust(top=0.97)  # Save room for the plot title

    if not colors:
        colors = get_colors(df, palette, min_colors=6)

    axes.set_prop_cycle("color", colors)

    subplot_axes = df.plot(subplots=True, ax=axes, sharex=True, legend=False, title=title,
                           style=style, color=colors, **kwargs)

    if title:
        axes.set_title(title)

    if not ylabels:
        ylabels = df.columns

    # Label each sub-plot's y-axis
    for ax, ylabel in zip(subplot_axes, ylabels):
        ax.set_ylabel(ylabel)

    if legend_list:
        axes.legend(legend_list)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def plot_all_files(plot_control_yaml: str, model_path: str, year: int, filetype: str = 'png',
                   VERBOSE: bool = False):
    """
    Plot all files specified in the plot control YAML file.

    :param plot_control_yaml: Path to the plot control YAML file.
    :type plot_control_yaml: str
    :param model_path: Path to the model files directory.
    :type model_path: str
    :param year: Start year of the simulation.
    :type year: int
    :param filetype: Filetype for saving the plots (e.g., 'png', 'pdf', 'svg'). Defaults to 'png'.
    :type filetype: str
    :param VERBOSE: Flag indicating verbose output. Defaults to False.
    :type VERBOSE: bool
    """

    # Read the plot control file
    control_df = read_plot_control(plot_control_yaml)

    # Iterate over the data frame, plot each file, and save
    # an image file next to each data file in the model
    for row in control_df.iterrows():
        # Get the plotting parameters
        params = row[1]
        filename = params['Filename']
        columns = params['Columns']
        ylabels = params['Labels']
        plot_type = params['PlotType']

        # Open and read file
        inpath = os.path.join(model_path, filename)
        if VERBOSE:
            print(f'Reading {inpath}')
        df = read(inpath, year, columns)

        # Plot the data
        plots = []
        if plot_type == 'combined':
            ts_plot = plot(df, y_label=ylabels[0], colors=k2)
            ts_plot.plot_type = plot_type
            plots.append(ts_plot)
        elif plot_type == 'subplots':
            # ts_plot = multi_plot(df, ylabels=ylabels, colors=k2)
            ts_plot = multi_plot(df, ylabels=ylabels, palette='tab10')
            ts_plot.plot_type = plot_type
            plots.append(ts_plot)
        elif plot_type == 'separate':
            for i, col in enumerate(df.columns):
                ts_plot = simple_plot(df[col], ylabel=ylabels[i], colors=k2)
                ts_plot.plot_type = plot_type
                ts_plot.variable_name = col
                plots.append(ts_plot)
        else:
            print(f'Plot type not specified for {filename}')

        # Save the figure
        for ts_plot in plots:
            if isinstance(filetype, list):
                for ft in filetype:
                    if ts_plot.plot_type == 'separate':
                        outpath = f'{inpath}_{ts_plot.variable_name}.{ft}'
                        ts_plot.get_figure().savefig(outpath)
                    else:
                        outpath = f'{inpath}.{ft}'
                        ts_plot.get_figure().savefig(outpath)
            if isinstance(filetype, str):
                if ts_plot.plot_type == 'separate':
                    outpath = f'{inpath}_{ts_plot.variable_name}.{filetype}'
                    ts_plot.get_figure().savefig(outpath)
                else:
                    outpath = f'{inpath}_{ts_plot.variable_name}.{filetype}'
                    ts_plot.get_figure().savefig(outpath)