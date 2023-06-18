import warnings
import os
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import matplotlib as mpl
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
    sns.color_palette('husl', desat=0.8)[4],    # blue
    sns.color_palette('tab10')[3],              # red
    sns.color_palette('deep')[2],               # green
    sns.color_palette('tab10', desat=0.8)[1],   # purple
    sns.color_palette('deep', desat=0.8)[4],    # purple
    sns.color_palette('colorblind')[2],         # sea green
    sns.color_palette('colorblind')[0],         # deep blue
    sns.color_palette('husl')[0]                # light red
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
    Plot a DataFrame using matplotlib.

    Args:
        df (pd.DataFrame): The DataFrame to be plotted.
        **kwargs: Additional keyword arguments for customizing the plot.

    Keyword Args:
        fig (plt.Figure): The figure object to use for the plot. If not provided, a new figure will be created.
        ax (plt.Axes): The axes object to use for the plot. If not provided, a new axes will be created.
        legend_values (List[str]): The legend labels for the plot.
        fig_size (tuple): The size of the figure in inches (width, height). Default is (15, 9).
        style (str): The line style of the plot. Default is '-'.
        colors: The colors to use for plotting.

    Returns:
        plt.Figure: The figure object containing the plot.

    """
    fig = kwargs.get('fig', None)
    ax = kwargs.get('ax', None)
    legend_values: List[str] = kwargs.get('legend_values', None)
    figsize: tuple = kwargs.get('fig_size', (15, 9))
    style: str = kwargs.get('style', '-')
    colors = kwargs.get('colors', k2)
    ylabel = kwargs.get('ylabel', None)

    if fig is None and ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        ax = fig.add_subplot(111)

    ax.set_prop_cycle("color", colors)

    if ylabel is None:
        ylabel = df.columns[0]

    kwargs['fig'] = fig
    kwargs['ax'] = ax
    kwargs['style'] = style
    kwargs['ylabel'] = ylabel
    if 'colors' in kwargs.keys():
        kwargs.pop('colors')

    df.plot(**kwargs)

    if legend_values:
        ax.legend(legend_values)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig

def multi_plot(df: pd.DataFrame, **kwargs) -> plt.Figure:
    """
    Plot a DataFrame using matplotlib separating the variables into multiple subplots.

    This function creates a subplot for each column of the provided DataFrame and plots the data using matplotlib.
    It supports various customization options such as specifying the figure and axes objects, figure size, title,
    x-label, y-labels, colors, line style, and color palette.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to be plotted.

    Keyword Args:
        fig (plt.Figure, optional): The figure object to use for the plot. If not provided, a new figure will be created.
        ax (plt.Axes, optional): The axes object to use for the plot. If not provided, a new axes will be created.
        figsize (tuple, optional): The size of the figure in inches (width, height). Default is (15, 30).
        title (str, optional): The title of the plot.
        xlabel (str, optional): The label for the x-axis.
        ylabels (Union[str, List[str]], optional): The labels for the y-axes. If not provided, column names will be used.
        colors (Union[str, List[str]], optional): The colors to use for plotting. If not provided, a color palette will be used.
        style (str, optional): The line style of the plot. Default is '-'.
        palette (str, optional): The color palette to use. Default is 'colorblind'.

    Returns:
        plt.Figure: The figure object containing the subplots.

    Raises:
        None

    Example:
        # Create a DataFrame
        df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6], 'z': [7, 8, 9]})

        # Plot the DataFrame
        multi_plot(df, title='Multiple Columns Plot', ylabels=['Y1', 'Y2', 'Y3'])

    """
    # Set defaults
    subplots = True
    sharex = True

    # Parse keyword arguments
    fig = kwargs.get('fig', None)
    ax = kwargs.get('ax', None)
    figsize = kwargs.get('figsize', (15, 30))
    title = kwargs.get('title', None)
    xlabel = kwargs.get('xlabel', None)
    ylabels = kwargs.get('ylabels', None)
    colors = kwargs.get('colors', None)
    style = kwargs.get('style', '-')
    palette = kwargs.get('palette', 'colorblind')

    if fig is None and ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        ax = fig.add_subplot(111)

    # Save room for the plot title
    plt.subplots_adjust(top=0.99)

    if not colors:
        colors = get_colors(df, palette, min_colors=6)

    ax.set_prop_cycle("color", colors)

    # Calculate the number subplots
    num_subplots = len(df.columns)

    # Plot the data
    kwargs['fig'] = fig
    kwargs['ax'] = ax
    kwargs['subplots'] = subplots
    kwargs['sharex'] = sharex
    kwargs['xlabel'] = xlabel
    kwargs['figsize'] = figsize
    kwargs['style'] = style
    kwargs['legend'] = False
    # axes = df.plot(fig=fig, ax=ax, subplots=subplots, sharex=sharex, xlabel=xlabel, figsize=figsize, style=style, legend=False)
    axes = df.plot(**kwargs)

    # Set the title
    if title:
        ax.set_title(title)

    # Label the y-axes
    if not ylabels:
        ylabels = df.columns

    # Label each sub-plot's y-axis
    for subplot_axis, ylabel in zip(axes, ylabels):
        subplot_axis.set_ylabel(ylabel)

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

                    
@mpl.rc_context({'axes.labelsize': 3})
def tiny_plot(df, **kwargs):
    """
    Create a tiny plot for generating app icons.

    This function creates a tiny plot using the specified DataFrame and additional keyword arguments.
    The plot is customized to have a small size of 3x3 inches and a font size of 3 points.
    It utilizes the 'w2.plot' function for the actual plotting.

    Parameters:
        df (pandas.DataFrame): The DataFrame containing the data to be plotted.
        **kwargs: Additional keyword arguments to be passed to the 'w2.plot' function.

    Returns:
        None

    Example:
        >>> df = pd.DataFrame(...)
        >>> tiny_plot(df, title='My App Icon')
    """
    kwargs['figsize'] = (3, 3)
    kwargs['fontsize'] = 3
    fig = plot(df, **kwargs)
    return fig

@mpl.rc_context({'axes.labelsize': 3})
def tiny_multi_plot(df, **kwargs):
    """
    Create a tiny multi-plot for generating app icons.

    This function creates a tiny multi-plot using the specified DataFrame and additional keyword arguments.
    The plot is customized to have a small size of 3x3 inches and a font size of 3 points.
    It utilizes the 'w2.multi_plot' function for the actual plotting.

    Parameters:
        df (pandas.DataFrame): The DataFrame containing the data to be plotted.
        **kwargs: Additional keyword arguments to be passed to the 'w2.multi_plot' function.

    Returns:
        None

    Example:
        >>> df = pd.DataFrame(...)
        >>> tiny_multi_plot(df, title='My App Icon')
    """
    kwargs['figsize'] = (3, 3)
    kwargs['fontsize'] = 3
    fig = multi_plot(df, **kwargs)
    return fig

