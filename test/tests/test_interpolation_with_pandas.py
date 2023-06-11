# %%
import pandas
from matplotlib import pyplot as plt
import datetime
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

# %%
# Make the graphs a bit prettier, and bigger
plt.style.use('seaborn')
plt.rcParams['figure.figsize'] = (15,9)
plt.rcParams['grid.color']='#AAAAAA'
plt.rcParams['lines.linewidth']=1
plt.rcParams['axes.facecolor']='#FBFBFB'
plt.rcParams["axes.edgecolor"] = '#222222'
plt.rcParams["axes.linewidth"]  = 0.5
plt.rcParams['xtick.color']='darkgreen' # tomato, seagreen
plt.rcParams['ytick.color']='darkgreen'
plt.rcParams['figure.subplot.hspace'] = 0.05 # Shrink the 
custom_colors = ['#3366CC', '#0099C6', '#109618', '#FCE030', '#FF9900', '#DC3912'] # (blue, teal, green, yellow, orange, red)

# Define string formatting constants
# This works in string format statements
DEG_C_ALT = u'\N{DEGREE SIGN}C' 
# These constants don't work in string format statements, but they are here for reference
DEGREE_SYMBOL = u'\u00b0'
SQUARED = u'\u00b2'
CUBED = u'\u00b3'.encode('utf-8')
DEG_C_UNICODE = u'\u2103' # Degrees Celsius symbol

# Define default line color
DEFAULT_COLOR = '#4488ee'


# %%
def read_w2_fixed_width_file(infile: str, ncols: int, names: list, skiprows: int = 3):
    '''
    Read fixed-width CE-QUAL-W2 data files

    infile : str
        Input filename
    ncols : int
        Number of columns, including day-of-year
    names : list
        List of column names to use for tables and plots

    Returns : pandas.DataFrame
    '''
    return pandas.read_fwf(infile, skiprows=skiprows, widths=[8]*ncols, 
        names=names, index_col=0)

def read_w2_csv_file(infile: str, names: list, skiprows: int = 3):
    '''
    Read CSV format CE-QUAL-W2 data files

    Note: These may have spaces between the commas

    infile : str
        Input filename
    ncols : int
        Number of columns, including day-of-year
    names : list
        List of column names to use for tables and plots

    Returns : pandas.DataFrame
    '''
    try:
        df = pandas.read_csv(infile, skiprows=skiprows, names=names, index_col=0)
    except:
        # Handle trailing comma, which adds an extra column
        new_names = names.copy()
        new_names.append('DROP_THIS')
        df = pandas.read_csv(infile, skiprows=skiprows, names=new_names, index_col=0)
        df = df.drop(axis=1,labels='DROP_THIS')
    return df


def round_time(dt: datetime.datetime=None, roundTo=60):
   '''
   Round a datetime object to any time in seconds

   dt : datetime.datetime object
   roundTo : Closest number of seconds to round to. Default = 1 minute.
   '''
   if dt == None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)

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
        dx = day1 + datetime.timedelta(days=(d-1))
        # Round the time
        dx = round_time(dt=dx, roundTo=60*60)
        datetimes.append(dx)
    return datetimes

def dataframe_to_date_format(year: int, data_frame: pandas.DataFrame):
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

# %%
'''
# CIN (constituent inflows), Berlin Model, 2006

Input files:
* BR1: 2006_DeerCrk_Cin.npt
* BR2: 2006_WillowCrk_Cin.npt
* BR3: 2006_IslandCrk_Cin.npt
* BR4: 2006_MillCrk_Cin.npt
'''

constituents = ['TDS','SO4','Cl','ISS','OP','NH4','Nox','Fe','LDOM','RDOM','LPOM','RPOM','BG','DIAT','OTH','DO']

# Inflow Concentrations
cin_br1 = read_w2_fixed_width_file('2006_DeerCrk_Cin.npt', 17, constituents)

# Convert day-of-year column of the data frames to date format
cin_br1 = dataframe_to_date_format(2006, cin_br1)

stations = [ '2006_DeerCrk_Cin.npt', ]

for station, cin in zip(stations, [cin_br1]):
    for constituent in constituents:
        fig, ax = plt.subplots()
        cin[constituent].plot(title=station, xlabel='Day of Year', ylabel='{c} (mg/L)'.format(c=constituent), style='.-', ax=ax)

# %%
import numpy as np
import pandas
df = cin_br1.copy()
pandas_datetimes = df.index.values
TDS = df['TDS']
# timestep = datetime.datetime(2006, 2, 2, 12, 0, 0)
timestep = datetime.datetime(2006, 4, 1, 0, 0, 0)
timestep = datetime.datetime(2006, 6, 1, 12, 0, 0)

# %%
# Convert datetimes from pandas (numpy.datetime64 format) to datetime objects
w2_datetimes = list(map(lambda x: datetime.datetime.utcfromtimestamp(x.astype('int')/1e9), pandas_datetimes))

# Convert datetime objects to UNIX time stamps (seconds elapsed since Jan 1, 1970)
w2_timestamps = list(map(lambda x: x.timestamp(), w2_datetimes))

# Convert current time step to UNIX time stamp
timestep_timestamp = timestep.timestamp()
# %%
# Interpolate TDS data to current time step
xi = np.interp(timestep_timestamp, w2_timestamps, TDS)
xi

# %%
from scipy.interpolate import interp1d
f = interp1d(w2_timestamps, TDS, kind='linear')
xi = f(timestep_timestamp)
print(pandas_datetimes)
print(TDS)
print(timestep)
print(xi)

# %%
from scipy.interpolate import interp1d
f = interp1d(w2_timestamps, TDS, kind='nearest')
xi = f(timestep_timestamp)
print(pandas_datetimes)
print(TDS)
print(timestep)
print(xi)
# %%
from scipy.interpolate import interp1d
f = interp1d(w2_timestamps, TDS, kind='previous')
xi = f(timestep_timestamp)
print(pandas_datetimes)
print(TDS)
print(timestep)
print(xi)

# %%
