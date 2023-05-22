import datetime
from typing import List
import warnings
import os
import sqlite3
from enum import Enum
import seaborn as sns
from matplotlib import pyplot as plt
import pandas as pd
import holoviews as hv
from holoviews import opts
import h5py
import yaml
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
rainbow = ['#3366CC', '#0099C6', '#109618', '#FCE030', '#FF9900', '#DC3912']  # (blue, teal, green, yellow, orange, red)
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
DEG_C_ALT = u'\N{DEGREE SIGN}C'

# Define default line color
DEFAULT_COLOR = '#4488ee'


class FileType(Enum(int)):
    """
    File type enumeration

    Args:
        Enum (int): Enumeration
    """
    UNKNOWN = 0
    FIXED_WIDTH = 1
    CSV = 2


def round_time(dt: datetime.datetime = None, round_to=60) -> datetime.datetime:
    """
    Round a datetime object to any time in seconds

    Args:
        dt (datetime.datetime, optional): Input datetime. Defaults to None.
        round_to (int, optional): Closest number of seconds to round to. Defaults to 60 seconds.

    Returns:
        datetime.datetime: Rounded datetime
    """
    if dt is None:
        dt = datetime.datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds+round_to/2) // round_to * round_to
    return dt + datetime.timedelta(0, rounding-seconds, -dt.microsecond)


def day_of_year_to_datetime(year: int, day_of_year_list: list) -> List(datetime.datetime):
    """
    Convert a list of day-of-year values to datetime objects

    Args:
        year (int): Start year of the data
        day_of_year_list (list): List of day-of-year values (e.g., from CE-QUAL-W2)

    Returns:
        List(datetime.datetime): List of datetime objects
    """
    day1 = datetime.datetime(year, 1, 1, 0, 0, 0)
    datetimes = []
    for d in day_of_year_list:
        # Compute the difference, subtracting 1 from the day_of_year
        try:
            d = float(d)
            dx = day1 + datetime.timedelta(days=(d-1))
        except TypeError:
            print(f'Type Error! d = {d}, type(d) = {type(d)}')
        # Round the time
        dx = round_time(dt=dx, round_to=60*60)
        datetimes.append(dx)
    return datetimes


def convert_to_datetime(year: int, days: List[int]) -> List[datetime]:
    """
    Convert a list of days of the year to datetime objects for a specific year

    Args:
        year (int): The year for which to create the datetime objects.
        days (List[int]): A list of days of the year (1-365 or 1-366 for leap years).

    Returns:
        List[datetime]: A list of `datetime` objects corresponding to the specified days and year.
    """
    # TODO: Note, this was written with ChatGPT to replace the above function. It needs testing.
    start_date = datetime.datetime(year, 1, 1)
    datetime_objects = [start_date + datetime.timedelta(days=day - 1) for day in days]
    return datetime_objects


def dataframe_to_date_format(year: int, data_frame: pd.DataFrame):
    """
    Convert the day-of-year column in a CE-QUAL-W2 data frame to datetime objects

    Args:
        year (int): Start year of the data
        data_frame (pd.DataFrame): Data frame to convert

    Returns:
        pd.DataFrame: Dataframe of datetime objects
    """
    datetimes = day_of_year_to_datetime(year, data_frame.index)
    data_frame.index = datetimes
    data_frame.index.name = 'Date'
    return data_frame


def read_npt_opt(infile: str, data_columns: List[str], skiprows: int = 3) -> pd.DataFrame:
    """
    Read CE-QUAL-W2 time series (fixed-width format, *.npt files)

    Args:
        infile (str): Time series file (*.npt or *.opt)
        year (int): Start year of the simulation
        data_columns (List[str]): Names of the data columns
        skiprows (int, optional): Number of header rows to skip. Defaults to 3.

    Returns:
        pd.DataFrame: Dataframe of time series data read from the input file
    """

    # This function cannot trust that the file is actually in fixed-width format.
    # Check if the first line after the header contains commas.
    # If it is a CSV file, then call read_csv() instead.
    # TODO: Add support for tabs and other delimiters. (LOW PRIORITY)
    with open(infile, 'r', encoding='utf-8') as f:
        for i in range(skiprows + 1):
            line = f.readline()
        if ',' in line:
            return read_csv(infile, data_columns=data_columns, skiprows=skiprows)

    # Parse the fixed-width file
    ncols_to_read = len(data_columns) + 1  # number of columns to read, including the date/day column
    columns_to_read = ['DoY', *data_columns]
    try:
        df = pd.read_fwf(infile, skiprows=skiprows, widths=ncols_to_read*[8], names=columns_to_read, index_col=0)
    except:
        print('Error reading ' + infile)
        raise
    return df


def read_csv(infile: str, data_columns: List[str], skiprows: int = 3) -> pd.DataFrame:
    """
    Read CE-QUAL-W2 time series in CSV format

    Args:
        infile (str): Time series file (*.npt or *.opt)
        data_columns (List[str]): Names of the data columns
        skiprows (int, optional): Number of header rows to skip. Defaults to 3.

    Returns:
        pd.DataFrame: Dataframe of time series data read from the input file
    """

    try:
        df = pd.read_csv(infile, skiprows=skiprows, names=data_columns, index_col=0)
    except IndexError:
        # Handle trailing comma, which adds an extra (empty) column
        try:
            df = pd.read_csv(infile, skiprows=skiprows, names=[*data_columns, 'JUNK'], index_col=0)
            df = df.drop(axis=1, labels='JUNK')
        except IndexError:
            print('Error reading ' + infile)
            print('Trying again with an additional column')
            df = pd.read_csv(infile, skiprows=skiprows, names=[*data_columns, 'JUNK1', 'JUNK2'], index_col=0)
            df = df.drop(axis=1, labels=['JUNK1', 'JUNK2'])
    except:
        print('Error reading ' + infile)
        raise
    return df


def read(infile: str, year: int, data_columns: List[str], skiprows: int = 3, file_type: FileType = None):
    """
    Read CE-QUAL-W2 time series data (npt/opt and csv formats) and convert the Day of Year (Julian Day) to date-time format.
    This function automatically detects the file type, if the file is named with *.npt, *.opt, or *.csv extensions. 

    Args:
        infile (str): Input time series file
        year (int): Start year of the simulation
        data_columns (List[str]): List of names of the data columns
        skiprows (int, optional): Number of header rows to skip. Defaults to 3.
        file_type (FileType, optional): File type (csv, npt, or opt). Defaults to None.

    Raises:
        Exception: File type was not specified
        Exception: File type was not defined correctly

    Returns:
        pd.DataFrame: Pandas Dataframe
    """

    # If not defined, set the file type using the input filename
    if not file_type:
        if infile.lower().endswith('.csv'):
            file_type = FileType.CSV
        elif infile.lower().endswith('.npt') or infile.lower().endswith('.opt'):
            file_type = FileType.FIXED_WIDTH
        else:
            raise Exception('The file type was not specified, and it could not be determined from the filename.')

    # Read the data
    if file_type == FileType.FIXED_WIDTH:
        df = read_npt_opt(infile, data_columns, skiprows=skiprows)
    elif file_type == FileType.CSV:
        df = read_csv(infile, data_columns, skiprows=skiprows)
    else:
        raise Exception('Error: file_type is not defined correctly.')

    # Convert day-of-year column of the data frames to date format
    df = dataframe_to_date_format(year, df)

    return df


def read_met(infile: str, year: int, data_columns: List[str] = None, skiprows: int = 3):
    """
    Read meteorology time series

    Args:
        infile (str): Time series file
        year (int): Start year of the simualtion
        data_columns (List[str], optional): Names of the data columns. Defaults to None.
        skiprows (int, optional): Number of header rows to skip. Defaults to 3.

    Returns:
        pd.DataFrame: Dataframe of the time series in the input file
    """
    if not data_columns:
        data_columns = [
            'Air Temperature ($^oC$)',
            'Dew Point Temperature ($^oC$)',
            'Wind Speed (m/s)',
            'Wind Direction (radians)',
            'Cloudiness (fraction)',
            'Solar Radiation ($W/m^2$)'
        ]

    return read(infile, year, data_columns, skiprows=skiprows)


def get_colors(df: pd.DataFrame, palette: str, min_colors: int = 6) -> List[str]:
    """
    Get a list of colors from Seaborn's color palette.

    Args:
        df (pd.DataFrame): The DataFrame used to determine the number of colors.
        palette (str): The name of the color palette to use.
        min_colors (int, optional): The minimum number of colors to select. Defaults to 6.

    Returns:
        List[str]: A list of colors selected from the color palette.
    """
    num_colors = min(len(df), min_colors)
    colors = sns.color_palette(palette, num_colors)
    return colors


def simple_plot(series: pd.Series, title: str = None, xlabel: str = None, ylabel: str = None, 
    colors: List[str] = None, figsize=(15, 9), style: str = '-', palette: str = 'colorblind', **kwargs) -> plt.Figure:
    """
    Plot one time series

    Args:
        series (pd.Series): Time series.
        title (str, optional): Plot title. Defaults to None.
        xlabel (str, optional): x-axis label. Defaults to None.
        ylabel (str, optional): y-axis label. Defaults to None.
        colors (List[str], optional): List of colors. Defaults to None.
        figsize (tuple, optional): Figure size. Defaults to (15, 9).
        style (str, optional): Line style. Defaults to '-'.
        palette (str, optional): Color palette. Defaults to 'colorblind'.

    Returns:
        plt.Figure: Figure handle of the generated plot.
    """

    fig, axes = plt.subplots(figsize=figsize)

    if not colors:
        colors = sns.color_palette(palette, 6)
        axes.set_prop_cycle("color", colors)

    series.plot(ax=axes, title=title, ylabel=ylabel, style=style)
    axis = plt.gca()
    axis.set_ylabel(ylabel)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def plot(df: pd.DataFrame, title: str = None, legend_values: List[str] = None,
         x_label: str = None, y_label: str = None, colors: List[str] = None,
         fig_size=(15, 9), line_style: str = '-', palette: str = 'colorblind', **kwargs) -> plt.Figure:
    """
    Plot entire data frame in on one axis

    Args:
        df (pd.DataFrame): The dataframe to plot.
        title (str): The title of the plot.
        legend_values (list): List of legend values corresponding to each column in the dataframe.
        x_label (str): Label for the x-axis.
        y_label (str): Label for the y-axis.
        colors (list): List of colors for each column in the dataframe.
        fig_size (tuple): Figure size (width, height) in inches.
        line_style (str): Line style for the plot.
        color_palette (str): Color palette name for generating colors.

    Returns:
        plt.Figure: Figure handle
    """

    fig, axes = plt.subplots(figsize=fig_size)

    if not colors:
        colors = get_colors(df, palette, min_colors=6)

    axes.set_prop_cycle("color", colors)

    df.plot(ax=axes, title=title, ylabel=y_label, style=line_style)

    if legend_values:
        axes.legend(legend_values)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def plot_dataframe(df: pd.DataFrame, title: str, legend_values: list, x_label: str, y_label: str,
                   colors: list, fig_size: tuple, line_style: str, color_palette: str) -> hv.core.overlay.Overlay:
    """
    Plot an entire dataframe using Holoviews. (Written using ChatGPT. Needs testing.)

    Args:
        df (pd.DataFrame): The dataframe to plot.
        title (str): The title of the plot.
        legend_values (list): List of legend values corresponding to each column in the dataframe.
        x_label (str): Label for the x-axis.
        y_label (str): Label for the y-axis.
        colors (list): List of colors for each column in the dataframe.
        fig_size (tuple): Figure size (width, height) in inches.
        line_style (str): Line style for the plot.
        color_palette (str): Color palette name for generating colors.

    Returns:
        hv.core.overlay.Overlay: The Holoviews overlay object representing the plot.
    """
    # Convert the dataframe to a Holoviews Dataset
    dataset = hv.Dataset(df, kdims=[x_label], vdims=list(df.columns))

    # Define the style options
    style_opts = opts.Curve(line_width=2, line_style=line_style)

    # Generate the color palette
    color_palette = hv.plotting.util.process_cmap(color_palette, categorical=True)
    color_cycle = color_palette[0:len(df.columns)]

    # Create the plot
    plot = dataset.to(hv.Curve, x_label, list(df.columns), label=legend_values).opts(
        opts.Curve(color=color_cycle, **style_opts), opts.Overlay(legend_position='right'),
        opts.Curve(width=fig_size[0], height=fig_size[1]), title=title, xlabel=x_label, ylabel=y_label
    )

    return plot


def multi_plot(df, title: str = None, legend_list: List[str] = None, xlabel: str = None,
              ylabels: List[str] = None, colors: List[str] = None, figsize=(15, 21),
              style: str = '-', palette: str = 'colorblind', **kwargs):
    """
    Plot each column as a separate subplot

    Args:
        df (_type_): _description_
        title (str, optional): _description_. Defaults to None.
        legend_list (List[str], optional): _description_. Defaults to None.
        xlabel (str, optional): _description_. Defaults to None.
        ylabels (List[str], optional): _description_. Defaults to None.
        colors (List[str], optional): _description_. Defaults to None.
        figsize (tuple, optional): _description_. Defaults to (15, 21).
        style (str, optional): _description_. Defaults to '-'.
        palette (str, optional): _description_. Defaults to 'colorblind'.

    Returns:
        _type_: _description_
    """

    fig, axes = plt.subplots(figsize=figsize)
    plt.subplots_adjust(top=0.97)  # Save room for the plot title

    if not colors:
        colors = get_colors(df, palette, min_colors=6)

    axes.set_prop_cycle("color", colors)

    subplot_axes = df.plot(subplots=True, ax=axes, sharex=True, legend=False, title=title, style=style, color=colors)

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


def write_hdf(df: pd.DataFrame, group: str, outfile: str, overwrite=True):
    """
    Write CE-QUAL-W2 timeseries dataframe to HDF5

    The index column must be a datetime array. This columns will be written to HDF5 as a string array. 
    Each data column will be written using its data type.

    Args:
        df (pd.DataFrame): _description_
        group (str): _description_
        outfile (str): _description_
        overwrite (bool, optional): _description_. Defaults to True.
    """
    with h5py.File(outfile, 'a') as f:
        index = df.index.astype('str')
        string_dt = h5py.special_dtype(vlen=str)
        date_path = group + '/' + df.index.name
        if overwrite and (date_path in f):
            del f[date_path]
        f.create_dataset(date_path, data=index, dtype=string_dt)

        for col in df.columns:
            ts_path = group + '/' + col
            if overwrite and (ts_path in f):
                del f[ts_path]
            f.create_dataset(ts_path, data=df[col])


def read_hdf(group: str, infile: str, variables: List[str]):
    '''
    Read CE-QUAL-W2 timeseries from HDF5 and create a dataframe

    This function assumes that a string-based datetime array named Date is present. This will be read and 
    assiened as the index column of the output pandas dataframe will be a datetime array. 
    '''

    with h5py.File(infile, 'r') as f:
        # Read dates
        date_path = group + '/' + 'Date'
        dates_str = f.get(date_path)

        # Read time series data
        ts = {}
        for v in variables:
            ts_path = group + '/' + v
            ts[v] = f.get(ts_path)

        dates = []
        for dstr in dates_str:
            dstr = dstr.decode('utf-8')
            d = pd.to_datetime(dstr)
            dates.append(d)

        df = pd.DataFrame(ts, index=dates)
        return df


def read_plot_control(yaml_infile: str, index_name='item') -> pd.DataFrame:
    '''Read CE-QUAL-W2 plot control file (YAML format)'''
    with open(yaml_infile) as yaml_file:
        yaml_contents = yaml.load(yaml_file, Loader=yaml.SafeLoader)
        control_df = pd.json_normalize(yaml_contents)
        control_df.set_index(control_df[index_name], inplace=True)
        control_df.drop(columns=[index_name], inplace=True)
    return control_df


def write_plot_control(control_df: pd.DataFrame, yaml_outfile: str, index_name: str = 'item'):
    '''Write CE-QUAL-W2 plot control file (YAML format)'''
    text = yaml.dump(control_df.reset_index().to_dict(orient='records'),
                     sort_keys=False, width=200, indent=4, default_flow_style=None)
    with open(yaml_outfile, 'w') as f:
        f.write(text)


def plot_all_files(plot_control_yaml: str, model_path: str, year: int, filetype='png', VERBOSE=False):
    '''Plot all files in a model using the plot configuration file (YAML format)'''
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
            ts_plot = plot(df, ylabel=ylabels[0], colors=k2)
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


def generate_plots_report(control_df: pd.DataFrame, model_path: str, outfile: str, title: str = None, subtitle: str = None, file_type: str = 'png', yaml: str = None, pdf_report = False):
    '''
    Generate a report of all the plots in the specified plot control dataframe

    If outfile is not an absolute path, the file will be written to the
    model folder.

    This function uses the "item" key for the plot captions. The form of the 
    key in the plot control YAML file should be the inflow/outflow variable name
    and the location, separated by an underscore, e.g., QIN_BR1 and TTR_TR5.
    An exception to the is the QGT file, which doesn't have separate location
    indicators (WB, TR, or BR).
    '''
    files = control_df['Filename']
    keys = control_df.index

    if not os.path.abspath(outfile):
        outfile = os.path.join(model_path, outfile)

    with open(outfile, 'w') as f:
        if yaml:
            f.write(yaml + '\n')
        if title:
            f.write(f'# {title}\n\n')
        else:
            f.write('# Summary of Model Plots\n\n')
        if subtitle:
            f.write(f'## {subtitle}\n\n')

        for i, (key, model_file) in enumerate(zip(control_df.index, control_df['Filename'])):
            # Full path to the CE-QUAL-W2 ASCII input/output file
            ascii_path = os.path.join(model_path, model_file)
            # Full path to the image file
            image_path = f'{ascii_path}.{file_type}'
            # Create the figure caption
            if '_' in key:
                variable, location = key.split('_')
                caption = f'Figure {i + 1}. Time series of {variable}, {location}, in file {model_file}'
            else:
                caption = f'Figure {i + 1}. Time series of {key}, in file {model_file}'
            # Write the image within a table
            f.write(f'| ![]({image_path}) |\n')
            f.write('|:-:|\n')
            f.write(f'| {caption} |\n\n\n')

    basefile = os.path.splitext(outfile)[0]

    if pdf_report:
        os.system(f'pandoc {basefile}.md -o {basefile}.pdf --from markdown --template todd.latex --top-level-division="chapter"')


def sql_query(database_name: str, query: str):
    '''Read time series data from a SQLite database using an SQL query'''
    with sqlite3.connect('w2_data.db') as db:
        df = pd.read_sql(query, db)
        df.index = df['Date']
        df.index = pd.to_datetime(df.index)
        df.drop(columns=['Date'], inplace=True)
        return df


def read_sql(database: str, table: str, index_is_datetime = True):
    '''Read a table in a SQLite database'''
    connection = sqlite3.connect(database)
    df = pd.read_sql_query(f'select * from {table}', connection)
    connection.close()
    df.index = pd.to_datetime(df.index)
    return df


def write_csv(df: pd.DataFrame, outfile: str, year: int, header: str = None, float_format='%.3f'):
    ''' Write data frame to CE-QUAL-W2 CSV format'''
    # Convert date to Julian days (day of year)
    diff = df.index - datetime.datetime(year,1,1) + datetime.timedelta(days=1)
    jday = diff.days + diff.seconds / 3600.0 / 24.0
    columns = ['JDAY'] + df.columns.to_list() # This needs to be done before assigning jday
    df['JDAY'] = jday
    df = df[columns]

    if not header:
        header = '$\n\n'
    with open(outfile, 'w') as f:
        f.write(header)
        df.to_csv(f, header=True, index=False, float_format=float_format)