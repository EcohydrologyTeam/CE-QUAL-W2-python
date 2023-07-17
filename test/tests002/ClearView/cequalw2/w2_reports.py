import os
import pandas as pd
import datetime
import sqlite3


def generate_plots_report(*args, **kwargs) -> None:
    """
    Generate a report of all the plots in the specified plot control dataframe.

    If `outfile` is not an absolute path, the file will be written to the model folder.

    This function uses the "item" key for the plot captions. The form of the key in the plot
    control YAML file should be the inflow/outflow variable name
    and the location, separated by an underscore, e.g., QIN_BR1 and TTR_TR5.
    An exception to this is the QGT file, which doesn't have separate location indicators
    (WB, TR, or BR).

    :param args: Any number of positional arguments. The following three arguments must be
                 specified:
                 - `control_df` (pd.DataFrame): The plot control dataframe.
                 - `model_path` (str): The path to the model.
                 - `outfile` (str): The output file path for the report.
    :param kwargs: Any number of keyword arguments.
                   - `title` (str, optional): The title for the report.
                   - `subtitle` (str, optional): The subtitle for the report.
                   - `file_type` (str, optional): The file type for the plots. Defaults to 'png'.
                   - `yaml` (str, optional): Additional YAML content to be included in the report.
                   - `pdf_report` (bool, optional): Whether to generate a PDF report using Pandoc.
                                                    Defaults to False.
    :raises ValueError: If the number of positional arguments is not equal to 3.
    """

    # Assign the positional and keyword arguments to variables
    if len(args) != 3:
        raise ValueError("The following three arguments must be specified: control_df, "
                         "model_path, and outfile")

    control_df: pd.DataFrame
    model_path: str
    outfile: str
    control_df, model_path, outfile = args

    title: str = kwargs.get('title', None)
    subtitle: str = kwargs.get('subtitle', None)
    file_type: str = kwargs.get('file_type', 'png')
    yaml: str = kwargs.get('yaml', None)
    yaml: bool = kwargs.get('pdf_report', False)

    files = control_df['Filename']
    keys = control_df.index

    if not os.path.abspath(outfile):
        outfile = os.path.join(model_path, outfile)

    with open(outfile, 'w', encoding='utf-8') as f:
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
                caption = f'Figure {i + 1}. Time series of {variable}, {location}, ' + \
                    f'in file {model_file}'
            else:
                caption = f'Figure {i + 1}. Time series of {key}, in file {model_file}'
            # Write the image within a table
            f.write(f'| ![]({image_path}) |\n')
            f.write('|:-:|\n')
            f.write(f'| {caption} |\n\n\n')

    basefile = os.path.splitext(outfile)[0]

    if pdf_report:
        os.system(
            f'pandoc {basefile}.md -o {basefile}.pdf '
            '--from markdown --template todd.latex '
            '--top-level-division="chapter"')


def sql_query(database_name: str, query: str):
    """
    Read time series data from a SQLite database using an SQL query.

    :param database_name: The name of the SQLite database file.
    :type database_name: str
    :param query: The SQL query to execute for retrieving the data.
    :type query: str
    :return: A Pandas DataFrame containing the queried time series data.
    :rtype: pandas.DataFrame
    """

    with sqlite3.connect(database_name) as db:
        df = pd.read_sql(query, db)
        df.index = df['Date']
        df.index = pd.to_datetime(df.index)
        df.drop(columns=['Date'], inplace=True)
        return df


def read_sql(database: str, table: str, index_is_datetime=True):
    """
    Read data from a SQLite database using an SQL query.

    :param database: The name of the SQLite database.
    :type database: str
    :param table: The name of the table from which to retrieve the data.
    :type table: str
    :param index_is_datetime: Flag indicating whether to convert the index to datetime.
                              Defaults to True.
    :type index_is_datetime: bool
    :return: A Pandas DataFrame containing the queried data.
    :rtype: pandas.DataFrame
    """

    connection = sqlite3.connect(database)
    df = pd.read_sql_query(f'select * from {table}', connection)
    connection.close()
    df.index = pd.to_datetime(df.index)
    return df


def write_csv(df: pd.DataFrame, outfile: str, year: int, header: str = None, float_format='%.3f'):
    """
    Write a Pandas DataFrame to a CSV file with additional formatting options.

    :param df: The DataFrame to be written to the CSV file.
    :type df: pandas.DataFrame
    :param outfile: The path to the output CSV file.
    :type outfile: str
    :param year: The year used for calculating Julian days.
    :type year: int
    :param header: Optional header string to be written at the beginning of the CSV file.
                   Defaults to None.
    :type header: str, optional
    :param float_format: Format specifier for floating-point values in the CSV file.
                         Defaults to '%.3f'.
    :type float_format: str
    """

    # Convert date to Julian days (day of year)
    diff = df.index - datetime.datetime(year, 1, 1) + datetime.timedelta(days=1)
    jday = diff.days + diff.seconds / 3600.0 / 24.0
    columns = ['JDAY'] + df.columns.to_list()  # This needs to be done before assigning jday
    df['JDAY'] = jday
    df = df[columns]

    if not header:
        header = '$\n\n'
    with open(outfile, 'w', encoding="utf-8") as f:
        f.write(header)
        df.to_csv(f, header=True, index=False, float_format=float_format)