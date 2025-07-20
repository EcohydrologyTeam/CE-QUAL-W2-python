import datetime
from typing import List


def round_time(date_time: datetime.datetime = None, round_to: int = 60) -> datetime.datetime:
    """
    Round a datetime object to the nearest specified time interval.

    :param date_time: The input datetime object. Defaults to the current datetime if not provided.
    :type date_time: datetime.datetime, optional
    :param round_to: The closest number of seconds to round to. Defaults to 60 seconds.
    :type round_to: int, optional

    :return: The rounded datetime object.
    :rtype: datetime.datetime
    """

    if date_time is None:
        date_time = datetime.datetime.now()

    seconds = (date_time.replace(tzinfo=None) - date_time.min).seconds
    rounding = (seconds + round_to / 2) // round_to * round_to

    return date_time + datetime.timedelta(0, rounding - seconds)


def day_of_year_to_datetime(year: int, day_of_year_list: List[int]) -> List[datetime.datetime]:
    """
    Convert a list of day-of-year values to datetime objects.

    :param year: The start year of the data.
    :type year: int
    :param day_of_year_list: A list of day-of-year values (e.g., from CE-QUAL-W2).
    :type day_of_year_list: list
    :return: A list of datetime objects corresponding to the day-of-year values.
    :rtype: List[datetime.datetime]
    """

    day1 = datetime.datetime(year, 1, 1, 0, 0, 0)
    datetimes = []
    for d in day_of_year_list:
        try:
            d = float(d)
            time_diff = day1 + datetime.timedelta(days=d - 1)
        except TypeError:
            print(f'Type Error! d = {d}, type(d) = {type(d)}')

        time_diff = round_time(date_time=time_diff, round_to=60 * 60)
        datetimes.append(time_diff)
    return datetimes


def convert_to_datetime(year: int, days: List[int]) -> List[datetime.datetime]:
    """
    Convert a list of days of the year to datetime objects for a specific year.

    :param year: The year for which to create the datetime objects.
    :type year: int
    :param days: A list of days of the year (1-365 or 1-366 for leap years).
    :type days: List[int]
    :return: A list of datetime objects corresponding to the specified days and year.
    :rtype: List[datetime.datetime]
    """

    start_date = datetime.datetime(year, 1, 1)
    datetime_objects = [start_date + datetime.timedelta(days=day - 1) for day in days]
    return datetime_objects