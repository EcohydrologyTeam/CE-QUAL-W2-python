import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
import pandas as pd
import datetime
import h5py
import warnings
from enum import Enum
import yaml
import os
import glob
import sqlite3
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


class FileType(Enum):
    unknown = 0
    fixed_width = 1
    csv = 2


def round_time(dt: datetime.datetime = None, roundTo=60):
    '''
    Round a datetime object to any time in seconds

    dt : datetime.datetime object
    roundTo : Closest number of seconds to round to. Default = 1 minute.
    '''
    if dt == None:
        dt = datetime.datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds+roundTo/2) // roundTo * roundTo
    return dt + datetime.timedelta(0, rounding-seconds, -dt.microsecond)


def day_of_year_to_datetime(year: int, day_of_year_list: list):
    '''
    Convert a list of day-of-year values to datetime objects

    year : int
        Start year of the data
    day_of_list : list
        List of day-of-year values, e.g., from CE-QUAL-W2
    '''
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
        dx = round_time(dt=dx, roundTo=60*60)
        datetimes.append(dx)
    return datetimes


def dataframe_to_date_format(year: int, data_frame: pd.DataFrame):
    '''
    Convert the day-of-year column in a CE-QUAL-W2 data frame
    to datetime objects

    year : int
        Start year of the data
    data_frame : pandas.DataFrame object
        Data frame to convert
    '''
    datetimes = day_of_year_to_datetime(year, data_frame.index)
    data_frame.index = datetimes
    data_frame.index.name = 'Date'
    return data_frame


def read_npt_opt(infile: str, year: int, data_columns: List[str], skiprows: int = 3):
    '''
    Read CE-QUAL-W2 time series (fixed-width format, *.npt files)
    '''

    # This function cannot trust that the file is actually in fixed-width format.
    # Check if the first line after the header contains commas.
    # If it is a CSV file, then call read_csv() instead.
    # TODO: Add support for tabs and other delimiters. (LOW PRIORITY)
    with open(infile, 'r') as f:
        for i in range(skiprows + 1):
            line = f.readline()
        if ',' in line:
            return read_csv(infile, year, data_columns=data_columns, skiprows=skiprows)

    # Parse the fixed-width file
    ncols_to_read = len(data_columns) + 1  # number of columns to read, including the date/day column
    columns_to_read = ['DoY', *data_columns]
    try:
        df = pd.read_fwf(infile, skiprows=skiprows, widths=ncols_to_read*[8], names=columns_to_read, index_col=0)
    except:
        print('Error reading ' + infile)
        raise
    return df


def read_csv(infile: str, year: int, data_columns: List[str], skiprows: int = 3):
    '''Read CE-QUAL-W2 time series (CSV format)'''

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
    '''
    Read CE-QUAL-W2 time series data (npt/opt and csv formats) and convert the Day of Year (Julian Day) to date-time format

    This function automatically detects the file type, if the file is named with *.npt, *.opt, or *.csv extensions. 
    '''

    # If not defined, set the file type using the input filename
    if not file_type:
        if infile.lower().endswith('.csv'):
            file_type = FileType.csv
        elif infile.lower().endswith('.npt') or infile.lower().endswith('.opt'):
            file_type = FileType.fixed_width
        else:
            raise Exception('The file type was not specified, and it could not be determined from the filename.')

    # Read the data
    if file_type == FileType.fixed_width:
        df = read_npt_opt(infile, year, data_columns, skiprows=skiprows)
    elif file_type == FileType.csv:
        df = read_csv(infile, year, data_columns, skiprows=skiprows)
    else:
        raise Exception('Error: file_type is not defined correctly.')

    # Convert day-of-year column of the data frames to date format
    df = dataframe_to_date_format(year, df)

    return df


def read_met(infile: str, year: int, data_columns: List[str] = None, skiprows: int = 3):
    '''Read meteorology time series'''
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


def get_colors(df: pd.DataFrame, palette: str, min_colors=6):
    '''Get list of colors from the specified Seaborn color palette'''

    colors = sns.color_palette(palette, min(min_colors, len(df.columns)))
    return colors


def simple_plot(series: pd.Series, title: str = None, xlabel: str = None, ylabel: str = None, 
    colors: List[str] = None, figsize=(15, 9), style: str = '-', palette: str = 'colorblind', **kwargs):
    '''Plot one time series'''

    fig, axes = plt.subplots(figsize=figsize)

    if not colors:
        colors = sns.color_palette(palette, 6)
        axes.set_prop_cycle("color", colors)

    series.plot(ax=axes, title=title, ylabel=ylabel, style=style)
    axis = plt.gca()
    axis.set_ylabel(ylabel)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def plot(df: pd.DataFrame, title: str = None, legend_list: List[str] = None,
         xlabel: str = None, ylabel: str = None, colors: List[str] = None,
         figsize=(15, 9), style: str = '-', palette: str = 'colorblind', **kwargs):
    '''Plot entire data frame in on one axis'''

    fig, axes = plt.subplots(figsize=figsize)

    if not colors:
        colors = get_colors(df, palette, min_colors=6)

    axes.set_prop_cycle("color", colors)

    df.plot(ax=axes, title=title, ylabel=ylabel, style=style)

    if legend_list:
        axes.legend(legend_list)

    fig.tight_layout()  # This resolves a lot of layout issues
    return fig


def multi_plot(df, title: str = None, legend_list: List[str] = None, xlabel: str = None,
              ylabels: List[str] = None, colors: List[str] = None, figsize=(15, 21),
              style: str = '-', palette: str = 'colorblind', **kwargs):
    '''Plot each column as a separate subplot'''

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
    '''
    Write CE-QUAL-W2 timeseries dataframe to HDF5

    The index column must be a datetime array. This columns will be written to HDF5 as a string array. 
    Each data column will be written using its data type.
    '''

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
    Read CE-QUAL-W2 timeseries dataframe to HDF5

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