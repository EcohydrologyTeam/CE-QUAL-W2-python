import pandas as pd
from typing import List
from enum import Enum
import h5py
from . import w2_datetime


class FileType(Enum):
    """
    File type enumeration

    Args:
        Enum (int): Enumeration
    """

    UNKNOWN = 0
    FIXED_WIDTH = 1
    CSV = 2


def dataframe_to_date_format(year: int, data_frame: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the day-of-year column in a CE-QUAL-W2 data frame to datetime objects.

    :param year: The start year of the data.
    :type year: int
    :param data_frame: The data frame to convert.
    :type data_frame: pd.DataFrame
    :return: The data frame with the day-of-year column converted to datetime objects.
    :rtype: pd.DataFrame
    """

    datetimes = w2_datetime.day_of_year_to_datetime(year, data_frame.index)
    data_frame.index = datetimes
    data_frame.index.name = 'Date'
    return data_frame


def read_npt_opt(infile: str, data_columns: List[str], skiprows: int = 3) -> pd.DataFrame:
    """
    Read CE-QUAL-W2 time series (fixed-width format, *.npt files).

    :param infile: The path to the time series file (*.npt or *.opt).
    :type infile: str
    :param data_columns: The names of the data columns.
    :type data_columns: List[str]
    :param skiprows: The number of header rows to skip. Defaults to 3.
    :type skiprows: int, optional
    :return: A DataFrame of the time series data read from the input file.
    :rtype: pd.DataFrame
    """

    # This function cannot trust that the file is actually in fixed-width format.
    # Check if the first line after the header contains commas.
    # If it is a CSV file, then call read_csv() instead.

    # TODO: Add support for tabs and other delimiters. (LOW PRIORITY)

    with open(infile, 'r', encoding='utf-8') as f:
        for _ in range(skiprows + 1):
            line = f.readline()
        if ',' in line:
            return read_csv(infile, data_columns=data_columns, skiprows=skiprows)

    # Parse the fixed-width file

    # Number of columns to read, including the date/day column
    ncols_to_read = len(data_columns) + 1

    columns_to_read = ['DoY', *data_columns]
    try:
        df = pd.read_fwf(infile, skiprows=skiprows, widths=ncols_to_read*[8],
                         names=columns_to_read, index_col=0)
    except:
        raise IOError(f'Error reading {infile}')

    df.attrs['Filename'] = infile

    return df


def read_csv(infile: str, data_columns: List[str], skiprows: int = 3) -> pd.DataFrame:
    """
    Read CE-QUAL-W2 time series in CSV format.

    :param infile: The path to the time series file (*.npt or *.opt).
    :type infile: str
    :param data_columns: The names of the data columns.
    :type data_columns: List[str]
    :param skiprows: The number of header rows to skip. Defaults to 3.
    :type skiprows: int, optional
    :return: A DataFrame of the time series data read from the input file.
    :rtype: pd.DataFrame
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
            df = pd.read_csv(infile, skiprows=skiprows, names=[*data_columns, 'JUNK1', 'JUNK2'],
                             index_col=0)
            df = df.drop(axis=1, labels=['JUNK1', 'JUNK2'])
    except:
        raise IOError(f'Error reading {infile}')

    df.attrs['Filename'] = infile

    return df


def read(*args, **kwargs):
    """
    Read CE-QUAL-W2 time series data in various formats and convert the Day of Year to date-time
    format.

    This function supports reading data from CSV (Comma Separated Values) files and fixed-width
    format (npt/opt) files.  The file type can be explicitly specified using the `file_type`
    keyword argument, or it can be inferred from the file extension. By default, the function
    assumes a skiprows value of 3 for header rows.

    :param args: Any number of positional arguments. The first argument should be the path to the
                 input time series file. The second argument should be the start year of the
                 simulation. The third argument (optional) should be the list of names of the data
                 columns.
    :param kwargs: Any number of keyword arguments.
                   - skiprows: The number of header rows to skip. Defaults to 3.
                   - file_type: The file type (CSV, npt, or opt). If not specified, it is
                                determined from the file extension.
    :raises ValueError: If the file type was not specified and could not be determined from the
                        filename.
    :raises ValueError: If an unrecognized file type is encountered. Valid file types are CSV, npt,
                        and opt.
    :return: A Pandas DataFrame containing the time series data with the Day of Year converted to
             date format.
    :rtype: pd.DataFrame
    """

    # Assign positional and keyword arguments to variables
    if len(args) != 3:
        raise ValueError("Exactly three arguments are required.")

    infile, year, data_columns = args

    # Assign keywords to variables
    skiprows = kwargs.get('skiprows', 3)
    file_type = kwargs.get('file_type', None)

    # If not defined, set the file type using the input filename
    if not file_type:
        if infile.lower().endswith('.csv'):
            file_type = FileType.CSV
        elif infile.lower().endswith('.npt') or infile.lower().endswith('.opt'):
            file_type = FileType.FIXED_WIDTH
        else:
            raise ValueError(
                'The file type was not specified, and it could not be determined from the filename.')

    # Read the data
    if file_type == FileType.FIXED_WIDTH:
        df = read_npt_opt(infile, data_columns, skiprows=skiprows)
    elif file_type == FileType.CSV:
        df = read_csv(infile, data_columns, skiprows=skiprows)
    else:
        raise ValueError('Unrecognized file type. Valid file types are CSV, npt, and opt.')

    # Convert day-of-year column of the data frames to date format
    df = dataframe_to_date_format(year, df)
    df.attrs['Filename'] = infile

    return df


def read_met(*args, **kwargs) -> pd.DataFrame:
    """
    Read meteorology time series.

    :param args: Any number of positional arguments. The first argument should be the path to the
                 input time series file.
                 The second argument should be the start year of the simulation.
    :param kwargs: Any number of keyword arguments.
                   - skiprows: The number of header rows to skip. Defaults to 3.
                   - file_type: The file type (CSV, npt, or opt). If not specified, it is
                                determined from the file extension.
    :return: Dataframe of the time series in the input file.
    :rtype: pd.DataFrame
    """

    # Assign positional and keyword arguments to variables
    if len(args) != 2:
        raise ValueError("Exactly two arguments are required.")

    infile, year = args

    if not kwargs.get('data_columns'):
        kwargs['data_columns'] = [
            'Air Temperature ($^oC$)',
            'Dew Point Temperature ($^oC$)',
            'Wind Speed (m/s)',
            'Wind Direction (radians)',
            'Cloudiness (fraction)',
            'Solar Radiation ($W/m^2$)'
        ]
    data_columns = kwargs.get('data_columns')

    return read(infile, year, data_columns, **kwargs)



def write_hdf(df: pd.DataFrame, group: str, outfile: str, overwrite=True):
    """
    Write CE-QUAL-W2 timeseries dataframe to HDF5

    The index column must be a datetime array.
    This column will be written to HDF5 as a string array.
    Each data column will be written using its data type.

    :param df: The DataFrame containing the timeseries data.
    :type df: pd.DataFrame
    :param group: The HDF5 group where the data will be stored.
    :type group: str
    :param outfile: The output HDF5 file path.
    :type outfile: str
    :param overwrite: Whether to overwrite existing data in HDF5. Defaults to True.
    :type overwrite: bool, optional
    """

    with h5py.File(outfile, 'a') as f:
        index = df.index.astype('str')
        string_dt = h5py.special_dtype(vlen=str)
        date_path = f'{group}/{df.index.name}'
        if overwrite and (date_path in f):
            del f[date_path]
        f.create_dataset(date_path, data=index, dtype=string_dt)

        for col in df.columns:
            ts_path = f'{group}/{col}'
            if overwrite and (ts_path in f):
                del f[ts_path]
            f.create_dataset(ts_path, data=df[col])


def read_hdf(group: str, infile: str, variables: List[str]) -> pd.DataFrame:
    """
    Read CE-QUAL-W2 timeseries from HDF5 and create a dataframe.

    This function assumes that a string-based datetime array named Date is present.
    This will be read and assigned as the index column of the output pandas dataframe,
    which will be a datetime array.

    :param group: The group within the HDF5 file containing the time series data.
    :type group: str
    :param infile: The path to the HDF5 file.
    :type infile: str
    :param variables: A list of variable names to read from the HDF5 file.
    :type variables: List[str]

    :return: Dataframe containing the time series data.
    :rtype: pd.DataFrame
    """

    with h5py.File(infile, 'r') as f:
        # Read dates
        date_path = f'{group}/Date'
        dates_str = f.get(date_path)

        # Read time series data
        ts = {}
        for variable in variables:
            ts_path = f'{group}/{variable}'
            ts[variable] = f.get(ts_path)

        dates = []
        for dstr in dates_str:
            dstr = dstr.decode('utf-8')
            dt = pd.to_datetime(dstr)
            dates.append(dt)

        df = pd.DataFrame(ts, index=dates)
        df.attrs['Filename'] = infile

        return df


def read_plot_control(yaml_infile: str, index_name: str = 'item') -> pd.DataFrame:
    """
    Read CE-QUAL-W2 plot control file in YAML format.

    :param yaml_infile: Path to the YAML file.
    :type yaml_infile: str
    :param index_name: Name of the column to be set as the index in the resulting DataFrame.
                       Defaults to 'item'.
    :type index_name: str

    :return: DataFrame containing the contents of the plot control file.
    :rtype: pd.DataFrame
    """
    with open(yaml_infile, encoding='utf-8') as yaml_file:
        yaml_contents = yaml.load(yaml_file, Loader=yaml.SafeLoader)
        control_df = pd.json_normalize(yaml_contents)
        control_df.set_index(control_df[index_name], inplace=True)
        control_df.drop(columns=[index_name], inplace=True)
    return control_df


def write_plot_control(control_df: pd.DataFrame, yaml_outfile: str):
    """
    Write CE-QUAL-W2 plot control file in YAML format.

    :param control_df: DataFrame containing the plot control data.
    :type control_df: pd.DataFrame
    :param yaml_outfile: Path to the output YAML file.
    :type yaml_outfile: str
    """
    text = yaml.dump(control_df.reset_index().to_dict(orient='records'),
                     sort_keys=False, width=200, indent=4, default_flow_style=None)
    with open(yaml_outfile, 'w', encoding='utf-8') as f:
        f.write(text)