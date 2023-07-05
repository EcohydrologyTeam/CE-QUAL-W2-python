import os
from typing import List
from enum import Enum
import pandas as pd
import h5py
import sqlite3
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


def get_header_row_number(file_path):
    """Get the row number of the header in a file.

    This function determines the row number of the header in a file based on the file name.
    If the file name starts with 'tsr' (case insensitive), the header row number is 0.
    Otherwise, the header row number is 2.

    Args:
        file_path (str): The path of the file.

    Returns:
        int: The row number of the header in the file.

    """
    _, filename = os.path.split(file_path)
    if filename.lower().startswith('tsr'):
        header_row_number = 0
    else:
        header_row_number = 2
    return header_row_number


def get_data_columns_csv(file_path):
    """
    Extracts data columns from a file.

    Parameters:
        file_path (str): The path to the file.

    Returns:
        list: A list of data columns extracted from the file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
    """

    with open(file_path, 'r') as f:
        # Get the header line
        lines = f.readlines()
        header_row_number = get_header_row_number(file_path)
        header_vals = lines[header_row_number].strip().strip(',').strip().split(',')
        # Get the data columns
        for i, val in enumerate(header_vals):
            header_vals[i] = val.strip()
        data_columns = header_vals[1:]
        return data_columns


def get_data_columns_fixed_width(file_path):
    """
    Retrieves the data columns from a fixed-width file.

    Args:
        file_path (str): The path to the fixed-width file.

    Returns:
        list: A list containing the data columns extracted from the file.

    Example:
        >>> file_path = 'data.txt'
        >>> data_columns = get_data_columns_fixed_width(file_path)
        >>> print(data_columns)
        ['Column1', 'Column2', 'Column3', 'Column4']
    """

    with open(file_path, 'r') as f:
        # Get the header line
        header_row_number = get_header_row_number(file_path)
        header = f.readlines()[header_row_number]
        header_vals = split_fixed_width_line(header, 8)

        for i, val in enumerate(header_vals):
            header_vals[i] = val.strip()
        data_columns = header_vals[1:]
        if data_columns[-1] == "":
            data_columns = data_columns[:-1]

        return data_columns


def split_fixed_width_line(line, field_width):
    """
    Split a line into segments of fixed width.

    Args:
        line (str): The line to be split.
        field_width (int): The width of each segment.

    Returns:
        list: A list of segments of fixed width.

    Examples:
        >>> line = "This is a sample line that we want to split."
        >>> segments = split_fixed_width_line(line, 8)
        >>> segments
        ['This is ', 'a sample', ' line th', 'at we wa', 'nt to sp', 'lit.']
    """

    return [line[i:i + field_width] for i in range(0, len(line), field_width)]


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


def read_sqlite(file_path: str) -> pd.DataFrame:
    """
    Read an SQLite database file and return the contents of the first table as a Pandas DataFrame.

    Args:
        file_path (str): The path to the SQLite database file.

    Returns:
        pd.DataFrame: The contents of the first table in the SQLite database.

    Raises:
        sqlite3.OperationalError: If there is an error executing SQL queries.
    """

    # Establish a connection to the SQLite database file
    connection = sqlite3.connect(file_path)

    # Create a cursor object to execute SQL queries
    cursor = connection.cursor()

    # Execute the SQL query to fetch table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")

    # Fetch all table names from the cursor as a list of tuples
    tables = cursor.fetchall()

    # Fetch the name of the first (and only) table in the list
    table_name = tables[0][0]

    # Execute the SQL query to fetch all records from the table
    cursor.execute(f"SELECT * FROM {table_name}")

    # Fetch all records from the cursor as a list of tuples
    records = cursor.fetchall()

    # Get the column names from the cursor description
    column_names = [description[0] for description in cursor.description]

    # Create a Pandas DataFrame from the records and column names
    df = pd.DataFrame(records, columns=column_names)

    # Convert the first column to Pandas date-time objects
    df[column_names[0]] = pd.to_datetime(df[column_names[0]])
    
    # Set the index to the date-time column
    df.set_index(column_names[0], inplace=True)

    # Close the cursor and connection
    cursor.close()
    connection.close()

    # Return the DataFrame
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

    print('file_type:', file_type)

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


def read_excel(file_path: str, **kwargs):
    """
    Read CE-QUAL-W2 time series from an Excel file.

    :param file_path: The path to the Excel file.
    :type file_path: str
    :return: Dataframe of the time series in the input file.
    :rtype: pd.DataFrame
    """
    # Get keyword arguments
    skiprows = kwargs.get('skiprows', 3)

    df = pd.read_excel(file_path, skiprows=skiprows)
    first_column_name = df.columns[0]
    df.rename(columns={f'{first_column_name}': 'Date'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y %H:%M')
    df.set_index('Date', inplace=True)
    return df


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
