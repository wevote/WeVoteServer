# wevote_functions/functions_date.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import pytz
from datetime import datetime
from wevote_functions.functions import positive_value_exists, convert_to_int, convert_to_str
# from math import log10
from django.utils.timezone import localtime, now
from nameparser.config import CONSTANTS

CONSTANTS.string_format = "{title} {first} {middle} \"{nickname}\" {last} {suffix}"


def generate_date_as_integer():
    # We want to store the day as an integer for extremely quick database indexing and lookup
    datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
    day_as_string = "{:d}{:02d}{:02d}".format(
        datetime_now.year,
        datetime_now.month,
        datetime_now.day,
    )
    return convert_to_int(day_as_string)


def convert_date_to_date_as_integer(date):
    day_as_string = "{:d}{:02d}{:02d}".format(
        date.year,
        date.month,
        date.day,
    )
    return convert_to_int(day_as_string)


def convert_date_as_integer_to_date(date_as_integer):
    date_as_string = convert_to_str(date_as_integer)
    date = datetime.strptime(date_as_string, '%Y%m%d')
    return date


def convert_date_to_we_vote_date_string(date):
    day_as_string = "{:d}-{:02d}-{:02d}".format(
        date.year,
        date.month,
        date.day,
    )
    return day_as_string


def convert_we_vote_date_string_to_date(we_vote_date_string):
    date_as_string = convert_to_str(we_vote_date_string)
    date = datetime.strptime(date_as_string, '%Y-%m-%d')
    return date


def convert_we_vote_date_string_to_date_as_integer(we_vote_date_string):
    if positive_value_exists(we_vote_date_string):
        try:
            date_as_string = convert_to_str(we_vote_date_string)
            date_as_string = date_as_string.replace("-", "")
            date_as_integer = convert_to_int(date_as_string)
            return date_as_integer
        except Exception as e:
            return 0
    else:
        return 0


# new date constants and functions
# new date format constants
DATE_FORMAT_YMD_HMS = "%Y-%m-%d %H:%M:%S"                   # 2024-03-04 21:58:40
# DATE_FORMAT_YMD_HM = "%Y-%m-%d %H:%M"                       # 2024-03-04 21:58
# DATE_FORMAT_YMD_HM_SLASH = "%Y/%m/%d %H:%M"                 # 2024/03/04 21:58
DATE_FORMAT_YMD = "%Y-%m-%d"                                # 2024-03-04
# DATE_FORMAT_YMD_SLASH = "%Y/%m/%d"                          # 2024/03/04
# DATE_FORMAT_B_D_Y = "%b. %d, %Y"                            # Mar. 04, 2024
DATE_FORMAT_YMD_T_HMS_Z = "%Y-%m-%dT%H:%M:%S%z"                # 2024-03-04T21:58:40Z
DATE_FORMAT_A_DBY_HMS_GMT = "%a, %d-%b-%Y %H:%M:%S GMT"   # Wed, 04-Mar-2024 21:58:40 GMT  
# DATE_FORMAT_MDY_IMS_P_SLASH = "%m/%d/%Y %I:%M:%S %p"        # 03/04/2024 09:58:40 PM
DATE_FORMAT_MDY_HM = "%m/%d/%Y %H:%M"                    # 03/04/2024 21:58
DATE_FORMAT_B_D_Y_AT_HM = "%B %d, %Y at %H:%M"                # March 04, 2024 at 21:58
DATE_FORMAT_DAY_OF_WEEK_TWO_DIGIT = "%d"                      # 04


# parse string into localized date time object
def parse_date_string(date_string, date_format, timezone_name="America/Los_Angeles"):
    timezone = pytz.timezone(timezone_name)
    date_time = datetime.strptime(date_string, date_format)
    return timezone.localize(date_time)


# retrieve the current datetime and timezone in the specified timezone
def get_timezone_and_datetime_now(timezone_name="America/Los_Angeles", datetime_obj=None, datetime_format=None):
    timezone = pytz.timezone(timezone_name)
    if datetime_obj is None:
        datetime_obj = datetime.now()
    elif isinstance(datetime_obj, str) and datetime_format:
        localized_datetime = parse_date_string(datetime_obj, datetime_format, timezone_name)
        return timezone, localized_datetime

    localized_datetime = timezone.localize(datetime_obj)
    return timezone, localized_datetime


# convert current date to a date as integer. replaces all instances when searching for "pytz.timezone"
#     -import function into file
#     -replace all instances when searching "pytz.timezone" with "date_today_as_integer = get_current_date_as_integer()"
def get_current_date_as_integer(timezone_name="America/Los_Angeles"):
    _, datetime_now = get_timezone_and_datetime_now(timezone_name)
    return convert_date_to_date_as_integer(datetime_now)


def get_current_year_as_integer():
    try:
        datetime_now = localtime(now()).date()  # WeVote uses Pacific Time for TIME_ZONE
        current_year = convert_to_int(datetime_now.year)
    except Exception as e:
        current_year = 2024
    return current_year
