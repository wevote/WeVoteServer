# wevote_functions/functions_date.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import datetime
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


