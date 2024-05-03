# wevote_functions/functions_time.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import pytz
import datetime
from datetime import timedelta
from wevote_functions.functions import positive_value_exists, convert_to_int, convert_to_str
from math import log10
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
    date = datetime.datetime.strptime(date_as_string, '%Y%m%d')
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
    date = datetime.datetime.strptime(date_as_string, '%Y-%m-%d')
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


#new date constants and functions
#new date format constants
DATE_FORMAT_YMD_HMS = "%Y-%m-%d %H:%M:%S"                   #2024-03-04 21:58:40
DATE_FORMAT_YMD_HM = "%Y-%m-%d %H:%M"                       #2024-03-04 21:58
DATE_FORMAT_YMD_HM_SLASH = "%Y/%m/%d %H:%M"                 #2024/03/04 21:58
DATE_FORMAT_YMD = "%Y-%m-%d"                                #2024-03-04
DATE_FORMAT_YMD_SLASH = "%Y/%m/%d"                          #2024/03/04
DATE_FORMAT_B_D_Y = "%b. %d, %Y"                            #Mar. 04, 2024
DATE_FORMAT_YMDTHMSZ = "%Y-%m-%dT%H:%M:%S%z"                #2024-03-04T21:58:40Z
DATE_FORMAT_A_D_B_Y_HMS_GMT = "%a, %d-%b-%Y %H:%M:%S GMT"   #Wed, 04-Mar-2024 21:58:40 GMT  
DATE_FORMAT_MDY_IMS_P_SLASH = "%m/%d/%Y %I:%M:%S %p"        #03/04/2024 09:58:40 PM
DATE_FORMAT_MDY_IMS_P = "%m/%d/%Y %H:%M"                    #03/04/2024 21:58
DATE_FORMAT_BD_Y_AT_HM ="%B %d, %Y at %H:%M"                #March 04, 2024 at 21:58
DATE_FORMAT_D = "%d"                                        #04


# convert current date to a date as integer. replaces all instances when searching for "pytz.timezone"
#     -import function into file
#     -replace all instances when searching "pytz.timezone" with "date_today_as_integer = get_current_date_as_integer("America/Los_Angeles")"
def get_current_date_as_integer(timezone_name="America/Los_Angeles"):
    """Retrieve the current date as an integer formatted as YYYYMMDD in the specified timezone."""
    timezone = pytz.timezone(timezone_name)
    datetime_now = timezone.localize(datetime.now())
    return convert_date_to_date_as_integer(datetime_now)



#adjust base date to another date
    #search for timedelta
    #usage:
        # Subtracting days to find a date 182 days ago
            # past_date = adjust_date(today, days=-182)

        # Adding days to find a date 50 days in the future
            # future_date = adjust_date(today, days=50)

def adjust_date(base_date, days=0, seconds=0, minutes=0, hours=0, weeks=0, months=0, years=0):
    delta = timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours, weeks=weeks, months=months, years=years)
    return base_date + delta