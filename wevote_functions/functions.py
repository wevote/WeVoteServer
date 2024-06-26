# wevote_functions/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import datetime
import json
import random
import re
import string
from math import log10
import django.utils.html
import requests
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from nameparser import HumanName
from nameparser.config import CONSTANTS
import wevote_functions.admin
CONSTANTS.string_format = "{title} {first} {middle} \"{nickname}\" {last} {suffix}"

# We don't want to include the actual constants from organization/models.py, since that can cause include conflicts
CORPORATION = 'C'
GROUP = 'G'  # Group of people (not an individual), but org status unknown
INDIVIDUAL = 'I'  # One person
NONPROFIT = 'NP'
NONPROFIT_501C3 = 'C3'
NONPROFIT_501C4 = 'C4'
NEWS_ORGANIZATION = 'NW'
ORGANIZATION = 'O'  # Deprecated
ORGANIZATION_WORD = 'ORGANIZATION'
POLITICAL_ACTION_COMMITTEE = 'P'
PUBLIC_FIGURE = 'PF'
TRADE_ASSOCIATION = 'TA'
UNKNOWN = 'U'
VOTER = 'V'

logger = wevote_functions.admin.get_logger(__name__)


STATE_CODE_MAP = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    # 'AS': 'American Samoa',
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DC': 'District of Columbia',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'GU': 'Guam',
    'HI': 'Hawaii',
    'IA': 'Iowa',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'MA': 'Massachusetts',
    'MD': 'Maryland',
    'ME': 'Maine',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MO': 'Missouri',
    # 'MP': 'Northern Mariana Islands',
    'MS': 'Mississippi',
    'MT': 'Montana',
    'NA': 'National',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'NE': 'Nebraska',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NV': 'Nevada',
    'NY': 'New York',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    # 'PR': 'Puerto Rico',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VA': 'Virginia',
    'VI': 'Virgin Islands',
    'VT': 'Vermont',
    'WA': 'Washington',
    'WI': 'Wisconsin',
    'WV': 'West Virginia',
    'WY': 'Wyoming',
}

UTC_OFFSET_MAP = {
    'AK': -32400,
    'AL': -18000,
    'AR': -21600,
    'AS': -39600,
    'AZ': -25200,
    'CA': -28800,
    'CO': -25200,
    'CT': -18000,
    'DC': -18000,
    'DE': -18000,
    'FL': -18000,
    'GA': -18000,
    'GU':  36000,
    'HI': -36000,
    'IA': -21600,
    'ID': -25200,
    'IL': -21600,
    'IN': -18000,
    'KS': -21600,
    'KY': -18000,
    'LA': -21600,
    'MA': -18000,
    'MD': -18000,
    'ME': -18000,
    'MI': -18000,
    'MN': -21600,
    'MO': -21600,
    'MP':  36000,
    'MS': -21600,
    'MT': -25200,
    'NC': -18000,
    'ND': -21600,
    'NE': -21600,
    'NH': -18000,
    'NJ': -18000,
    'NM': -25200,
    'NV': -25200,
    'NY': -18000,
    'OH': -18000,
    'OK': -21600,
    'OR': -25200,
    'PA': -18000,
    'PR': -14400,
    'RI': -18000,
    'SC': -18000,
    'SD': -21600,
    'TN': -18000,
    'TX': -21600,
    'UT': -25200,
    'VA': -18000,
    'VI': -14400,
    'VT': -18000,
    'WA': -28800,
    'WI': -21600,
    'WV': -18000,
    'WY': -25200,
}


# When the map is displayed in the app and DevTools is open to the DOM Elements, you can scroll and zoom the map
# and the geo_center_lat, geo_center_lng, and geo_center_zoom will update and display the numbers you want in this table
STATE_GEOGRAPHIC_CENTER = {
    'AK': [63.051125222381906, -147.268434375, 4],
    'AL': [32.7794, -86.8287, 7],  # Latitude, Longitude, Google Maps initial zoom level
    'AR': [34.79620542848227, -92.343326875, 7],
    'AS': [-14.303992186338759, -170.14381713867186, 10],
    'AZ': [34.0107102, -113.2422312, 6],
    'CA': [37.55082113640302, -120.54626015624999, 6],
    'CO': [38.9972, -105.5478, 7],
    'CT': [41.5138025, -72.4898248, 9],
    'DC': [38.9373675, -76.9924978, 11],
    'DE': [39.215925835306194, -75.19996166093752, 8],
    'FL': [28.6305, -82.4497, 6],
    'GA': [32.6415, -83.4426, 7],
    'GU': [13.448318943161425, 144.76966677246094, 11],
    'HI': [20.406007330518783, -157.18668828125, 7],
    'IA': [42.0751, -93.4960, 7],
    'ID': [45.45583577952023, -116.83223828125001, 6],
    'IL': [39.76357653687774, -89.03170507812501, 6],
    'IN': [39.8942, -86.2816, 7],
    'KS': [38.4937, -98.3804, 7],
    'KY': [37.5347, -85.3021, 7],
    'LA': [31.0689, -91.9968, 7],
    'MA': [42.007034063166614, -71.5006828125, 8],
    'MD': [38.867061211976086, -76.977667578125, 8],
    'ME': [45.3695, -69.2428, 7],
    'MI': [44.3467, -85.4102, 6],
    'MN': [46.25031983812459, -93.1187765625, 6],
    'MO': [38.3566, -92.4580, 7],
    'MP': [9, 168, 8],
    'MS': [32.7364, -89.6678, 7],
    'MT': [47.0527, -109.6333, 6],
    'NC': [35.5557, -79.3877, 7],
    'ND': [47.4501, -100.4659, 7],
    'NE': [41.5378, -99.7951, 7],
    'NH': [43.972177, -71.474005, 7],
    'NJ': [40.1907, -74.6728, 8],
    'NM': [34.49769285849705, -106.04668203125, 7],
    'NV': [38.80003220160127, -117.97153203125, 6],
    'NY': [42.9538, -75.5268, 7],
    'OH': [40.2862, -82.7937, 7],
    'OK': [35.5889, -97.4943, 7],
    'OR': [44.22561389089467, -120.942821484375, 7],
    'PA': [40.8781, -77.7996, 7],
    'PR': [18.179492511673608, -66.14993485656514, 9],
    'RI': [41.493850403715435, -71.41863571875001, 9],
    'SC': [33.9169, -80.8964, 7],
    'SD': [44.4443, -100.2263, 7],
    'TN': [35.8580, -86.3505, 7],
    'TX': [31.4757, -99.3312, 6],
    'UT': [39.534650281529416, -111.835094921875, 7],
    'VA': [37.8345270239665, -78.073670703125, 7],
    'VI': [18.093611, -64.830278, 9],
    'VT': [43.93198591201998, -72.86032128385402, 8],
    'WA': [47.3453926933735, -121.644709765625, 7],
    'WI': [44.834835759965294, -89.939168359375, 7],
    'WV': [38.6409, -80.0129587890625, 7],
    'WY': [42.9957, -107.5512, 7],
}

POSITIVE_TWITTER_HANDLE_SEARCH_KEYWORDS = [
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "congress",
    "for",
    "rep",
    "sen",
    "vote",
]

NEGATIVE_TWITTER_HANDLE_SEARCH_KEYWORDS = [
    "coach",
    "nfl",
]

POSITIVE_SEARCH_KEYWORDS = [
    "affiliate",
    "america",
    "candidate",
    "chair",
    "city",
    "civic",
    "congress",
    "conservative",
    "council",
    "country",
    "county",
    "democrat",
    "district",
    "elect",
    "endorse",
    "government",
    "leader",
    "liberal",
    "local",
    "municipal",
    "office",
    "official",
    "paid for",
    "party",
    "politic",
    "public",
    "represent",
    "republican",
    "running",
    "senate",
    "state",
    "taxes",
    "transparency",
]

NEGATIVE_SEARCH_KEYWORDS = [
    "album",
    "amateur",
    "author",
    "available to serve your needs",
    "books",
    "brexit",
    "call us today",
    "coach",
    "cricket",
    "complete satisfaction",
    "dean",
    "fake",
    "folk",
    "for our customers",
    "inc.",
    "is a city",
    "listen",
    "musician",
    "nightlife",
    "our quality work",
    "parody",
    "photographer",
    "preorder",
    "pre-order",
    "produced by",
    "promoter",
    "quarterback",
    "singer",
    "soul",
    "view the profiles of people named",
    "we guarantee",
    "writer",
]

ALLIANCE = 'ALLIANCE'
AMERICAN_INDEPENDENT = 'AMERICAN_INDEPENDENT'
CONSTITUTION = 'CONSTITUTION'
DEMOCRAT = 'DEMOCRAT'
D_R = 'D_R'
ECONOMIC_GROWTH = 'ECONOMIC_GROWTH'
GREEN = 'GREEN'
INDEPENDENT = 'INDEPENDENT'
INDEPENDENT_GREEN = 'INDEPENDENT_GREEN'
LIBERTARIAN = 'LIBERTARIAN'
NO_PARTY_PREFERENCE = 'NO_PARTY_PREFERENCE'
NON_PARTISAN = 'NON_PARTISAN'
PEACE_AND_FREEDOM = 'PEACE_AND_FREEDOM'
REFORM = 'REFORM'
REPUBLICAN = 'REPUBLICAN'
WORKING_FAMILIES = 'WORKING_FAMILIES'

LANGUAGE_CODE_ENGLISH = 'en'
LANGUAGE_CODE_SPANISH = 'es'

# U.S. House California District 33
# UNITED STATES REPRESENTATIVE, 33rd District

# We also check generate state specific phrases like "of california"
MEASURE_TITLE_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES = [
]

MEASURE_TITLE_SYNONYMS = []  # This is a list of synonym lists

MAXIMUM_SUPPORTED_MEASURE_NUMBER = 100
current_number = MAXIMUM_SUPPORTED_MEASURE_NUMBER
while current_number > 0:
    # This is a fresh list of synonyms based on proposition number, or letter
    one_list_of_synonyms = []
    one_synonym = "amendment " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "amend. no. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "amendment no. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

    # This is a fresh list of synonyms based on proposition number, or letter
    one_list_of_synonyms = []
    one_synonym = "measure " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "measure no. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

    # This is a fresh list of synonyms based on proposition number, or letter
    one_list_of_synonyms = []
    one_synonym = "proposition " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "proposition no. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "proposition number " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop - " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop. no. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

    # This is a fresh list of synonyms based on proposition number, or letter
    one_list_of_synonyms = []
    one_synonym = "question " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "question no. " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "question number " + str(current_number)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

    current_number -= 1

LETTER_IDENTIFIERS = [
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1", "i1", "j1", "k1", "l1", "m1",
    "n1", "o1", "p1", "q1", "r1", "s1", "t1", "u1", "v1", "w1", "x1", "y1", "z1",
    "aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh", "ii", "jj", "kk", "ll", "mm",
    "nn", "oo", "pp", "qq", "rr", "ss", "tt", "uu", "vv", "ww", "xx", "yy", "zz",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
for letter_identifier in LETTER_IDENTIFIERS:
    one_list_of_synonyms = []
    one_synonym = "amendment " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "amendment no. " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

    # Start over on another list
    one_list_of_synonyms = []
    one_synonym = "measure " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

    # Start over on another list
    one_list_of_synonyms = []
    one_synonym = "proposition " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop - " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    one_synonym = "prop. " + str(letter_identifier)
    one_list_of_synonyms.append(one_synonym)
    MEASURE_TITLE_SYNONYMS.append(one_list_of_synonyms)

OFFICE_NAME_EQUIVALENT_PHRASE_PAIRS = {
    'commissioner of insurance': 'insurance commissioner',
    'house of delegates': 'state representative',
    'member state board of equalization': 'state board of equalization',
    'member of the state assembly': 'state assembly',
    'superintendent of public instruction': 'state superintendent of public instruction',
    'supervisor': 'board of supervisors',
    'united states representative': 'u.s. house',
    'united states senator': 'u.s. senate',
}

DISTRICT_PAIR_PATTERNS_XND = [
    ['district {district_number}', '{district_number}nd district'],
    ['{district_number}nd congressional district', 'district {district_number}'],
]
DISTRICT_PAIR_PATTERNS_XRD = [
    ['district {district_number}', '{district_number}rd district'],
    ['{district_number}rd congressional district', 'district {district_number}'],
]
DISTRICT_PAIR_PATTERNS_XST = [
    ['district {district_number}', '{district_number}st district'],
    ['{district_number}st congressional district', 'district {district_number}'],
]
DISTRICT_PAIR_PATTERNS_XTH = [
    ['district {district_number}', '{district_number}th district'],
    ['{district_number}th congressional district', 'district {district_number}'],
]

MIDDLE_INITIAL_SUBSTRINGS = []
LETTER_LIST = string.ascii_uppercase
for letter in LETTER_LIST:
    letter_substring = " {letter} ".format(letter=letter)
    MIDDLE_INITIAL_SUBSTRINGS.append(letter_substring)
    letter_substring = " {letter}. ".format(letter=letter)
    MIDDLE_INITIAL_SUBSTRINGS.append(letter_substring)


def add_to_list_if_positive_value_exists(value=None, incoming_list=[]):
    if not incoming_list or not positive_value_exists(incoming_list):
        updated_list = []
    else:
        updated_list = incoming_list
    if positive_value_exists(value):
        if value not in updated_list:
            updated_list.append(value)
    return updated_list


def is_ordinal_number(incoming_integer):
    if incoming_integer in range(1, 4):  # Numbers equal 1, 2, or 3
        return True
    if incoming_integer < 10:
        return False
    tens_digits = incoming_integer % 100
    if tens_digits in range(1, 4):
        return True
    if tens_digits in range(21, 99):
        last_digit = tens_digits % 10
        if last_digit in range(1, 4):
            return True
    return False


def generate_office_equivalent_district_phrase_pairs():
    district_numbers_in_chosen_order = []
    district_number = 200
    while district_number < 300:
        district_numbers_in_chosen_order.append(district_number)
        district_number += 1
    district_number = 100
    while district_number < 200:
        district_numbers_in_chosen_order.append(district_number)
        district_number += 1
    district_number = 10
    while district_number < 100:
        district_numbers_in_chosen_order.append(district_number)
        district_number += 1
    district_number = 1
    while district_number < 10:
        district_numbers_in_chosen_order.append(district_number)
        district_number += 1
    office_equivalent_district_phrase_pairs = []
    for district_number in district_numbers_in_chosen_order:
        if is_ordinal_number(district_number):
            last_digit = district_number % 10
            if last_digit == 1:
                patterns_to_use = DISTRICT_PAIR_PATTERNS_XST
            elif last_digit == 2:
                patterns_to_use = DISTRICT_PAIR_PATTERNS_XND
            elif last_digit == 3:
                patterns_to_use = DISTRICT_PAIR_PATTERNS_XRD
            else:
                patterns_to_use = DISTRICT_PAIR_PATTERNS_XTH
        else:
            patterns_to_use = DISTRICT_PAIR_PATTERNS_XTH
        for left_template, right_template in patterns_to_use:
            new_pair = [
                left_template.format(district_number=district_number),
                right_template.format(district_number=district_number)
            ]
            office_equivalent_district_phrase_pairs.append(new_pair)
    return office_equivalent_district_phrase_pairs


# We also check generate state specific phrases like "of california"
OFFICE_NAME_COMMON_PHRASES_TO_REMOVE_FROM_SEARCHES = [
    "long beach",
    "orange county",
    "san diego",
    "san francisco",
    # "santa clara county",
    # "of santa clara county",
    "(voter nominated)",
]


class LocalSwitch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


# See also 'convert_to_political_party_constant'
def candidate_party_display(raw_party_incoming):
    if not positive_value_exists(raw_party_incoming):
        return ""
    raw_party = raw_party_incoming.strip()
    raw_party = raw_party.lower()
    raw_party = raw_party.replace("party preference: ", "")

    if raw_party is None:
        return ''
    if raw_party == '':
        return ''
    if raw_party == 'Alliance'.lower():
        return 'Alliance'
    if raw_party == ALLIANCE.lower():
        return 'Alliance'
    if raw_party == AMERICAN_INDEPENDENT.lower():
        return 'American Independent'
    if raw_party == 'Amer. Ind.'.lower():
        return 'American Independent'
    if raw_party == 'Constitution'.lower():
        return 'Constitution'
    if raw_party == CONSTITUTION.lower():
        return 'Constitution'
    if raw_party == 'DEM'.lower():
        return 'Democrat'
    if raw_party == DEMOCRAT.lower():
        return 'Democrat'
    if raw_party == 'DEM'.lower():
        return 'Democrat'
    if raw_party == 'Democratic'.lower():
        return 'Democrat'
    if raw_party == 'Democratic Party'.lower():
        return 'Democrat'
    if raw_party == D_R.lower():
        return 'D-R Party'
    if raw_party == ECONOMIC_GROWTH.lower():
        return 'Economic Growth'
    if raw_party == 'Party Preference: Democratic'.lower():
        return 'Democrat'
    if raw_party == GREEN.lower():
        return 'Green'
    if raw_party == 'GRN'.lower():
        return 'Green'
    if raw_party == INDEPENDENT.lower():
        return 'Independent'
    if raw_party == 'Independent'.lower():
        return 'Independent'
    if raw_party == LIBERTARIAN.lower():
        return 'Libertarian'
    if raw_party == 'Libertarian'.lower():
        return 'Libertarian'
    if raw_party == 'LIB'.lower():
        return 'Libertarian'
    if raw_party == NO_PARTY_PREFERENCE.lower():
        return 'No Party Preference'
    if raw_party == 'NPP'.lower():
        return 'No Party Preference'
    if raw_party == 'Party Preference: None'.lower():
        return 'No Party Preference'
    if raw_party == NON_PARTISAN.lower():
        return 'Nonpartisan'
    if raw_party == 'Nonpartisan'.lower():
        return 'Nonpartisan'
    if raw_party == PEACE_AND_FREEDOM.lower():
        return 'Peace and Freedom'
    if raw_party == 'PF'.lower():
        return 'Peace and Freedom'
    if raw_party == REFORM.lower():
        return 'Reform'
    if raw_party == REPUBLICAN.lower():
        return 'Republican'
    if raw_party == 'Republican'.lower():
        return 'Republican'
    if raw_party == 'Republican Party'.lower():
        return 'Republican'
    if raw_party == 'REP'.lower():
        return 'Republican'
    if raw_party == 'Party Preference: Republican'.lower():
        return 'Republican'
    if raw_party == 'Unknown National Party'.lower():
        return 'Party Unknown'
    if raw_party == 'none':
        return ''
    if raw_party == WORKING_FAMILIES.lower():
        return 'Working Families'
    if raw_party == 'working families':
        return 'Working Families'
    else:
        return raw_party_incoming


def convert_pennies_integer_to_dollars_string(pennies_integer):
    cents_to_dollars_format_string = '{:,.2f}'
    dollars_string = cents_to_dollars_format_string.format(pennies_integer / 100)
    return dollars_string


# This is how we make sure a variable is a boolean
def convert_to_bool(value):
    if value is True:
        return True
    elif value == 1:
        return True
    elif value > 0:
        return True
    elif value is False:
        return False
    elif value == 0:
        return True
    elif value is None:
        return False

    value = value.lower()
    if value in ['true', '1']:
        return True
    elif value in ['false', '0']:
        return False
    return False


# This is how we make sure a variable is float
def convert_to_float(value):
    # Catch the cases where the incoming value is None
    if value is None:
        return 0.0
    try:
        new_value = float(value)
    except ValueError:
        new_value = 0.0
    return new_value


# This is how we make sure a variable is an integer
def convert_to_int(value):
    # Catch the cases where the incoming value is None
    if value is None:
        return 0
    try:
        new_value = int(value)
    except ValueError:
        new_value = 0
    return new_value


# This is how we make sure a variable is a string
def convert_to_str(value):
    # Catch the cases where the incoming value is None
    if value is None:
        return ""
    try:
        new_value = str(value)
    except ValueError:
        new_value = ''
    return new_value


# See also 'candidate_party_display'
def convert_to_political_party_constant(raw_party_incoming):
    if not positive_value_exists(raw_party_incoming):
        return ""

    raw_party = raw_party_incoming.strip()
    raw_party = raw_party.lower()
    raw_party = raw_party.replace("party preference: ", "")

    if raw_party == 'alliance':
        return ALLIANCE
    if raw_party == 'amer. ind.':
        return AMERICAN_INDEPENDENT
    if raw_party == 'american independent':
        return AMERICAN_INDEPENDENT
    if raw_party == 'constitution':
        return CONSTITUTION
    if raw_party == 'dem':
        return DEMOCRAT
    if raw_party == 'democrat':
        return DEMOCRAT
    if raw_party == 'democratic':
        return DEMOCRAT
    if raw_party == 'democratic party':
        return DEMOCRAT
    if raw_party == 'd-r party':
        return D_R
    if raw_party == 'economic growth':
        return ECONOMIC_GROWTH
    if raw_party == 'grn':
        return GREEN
    if raw_party == 'green':
        return GREEN
    if raw_party == 'green party':
        return GREEN
    if raw_party == 'g-p':
        return GREEN
    if raw_party == 'independent':
        return INDEPENDENT
    if raw_party == 'independent green':
        return INDEPENDENT_GREEN
    if raw_party == 'lib':
        return LIBERTARIAN
    if raw_party == 'libertarian':
        return LIBERTARIAN
    if raw_party == 'libertarian party':
        return LIBERTARIAN
    if raw_party == 'npp':
        return NO_PARTY_PREFERENCE
    if raw_party == 'no party preference':
        return NO_PARTY_PREFERENCE
    if raw_party == 'non-partisan':
        return NON_PARTISAN
    if raw_party == 'nonpartisan':
        return NON_PARTISAN
    if raw_party == 'pf':
        return PEACE_AND_FREEDOM
    if raw_party == 'p-f':
        return PEACE_AND_FREEDOM
    if raw_party == 'peace and freedom':
        return PEACE_AND_FREEDOM
    if raw_party == 'peace and freedom party':
        return PEACE_AND_FREEDOM
    if raw_party == 'reform':
        return REFORM
    if raw_party == 'reform party':
        return REFORM
    if raw_party == 'rep':
        return REPUBLICAN
    if raw_party == 'republican':
        return REPUBLICAN
    if raw_party == 'republican party':
        return REPUBLICAN
    if raw_party == 'working families':
        return WORKING_FAMILIES
    else:
        return raw_party_incoming


def digit_count(number):
    if number > 1 and round(log10(number)) >= log10(number) and number % 10 != 0:
        return round(log10(number))
    elif number > 1 and round(log10(number)) < log10(number) and number % 10 != 0:
        return round(log10(number)) + 1
    elif number % 10 == 0 and number != 0:
        return int(log10(number) + 1)
    elif number == 1 or number == 0:
        return 1


def extract_state_from_ocd_division_id(ocd_division_id):
    # Pull this from ocdDivisionId
    pieces = [piece.split(':', 1) for piece in ocd_division_id.split('/')]
    fields = {}

    # if it included the ocd-division bit, pop it off
    if pieces[0] == ['ocd-division']:
        pieces.pop(0)

    if pieces[0][0] != 'country':
        # raise ValueError('OCD id must start with country')
        return ''
    fields['country'] = pieces[0][1]

    if len(pieces) < 2:
        return ''

    if pieces[1][0] == 'district' and pieces[1][1] == 'dc':
        # Special case for District of Columbia. No Taxation without Representation!
        return 'dc'

    if pieces[1][0] != 'state':
        # raise ValueError('Expecting state from OCD, and state not found')
        return ''

    fields['state'] = pieces[1][1]

    return fields['state']


def extract_state_code_from_address_string(text_for_map_search):
    text_for_map_search_lower = text_for_map_search.lower()
    text_for_map_search_substring_list = re.split(r'[;,\s]\s*', text_for_map_search_lower)
    for state_code, state_name in STATE_CODE_MAP.items():
        if state_code.lower() in text_for_map_search_substring_list:
            return state_code.lower()
        elif state_name.lower() in text_for_map_search_substring_list:
            return state_code.lower()

    return ""


def extract_district_id_label_when_district_id_exists_from_ocd_id(ocd_division_id):
    if not positive_value_exists(ocd_division_id):
        return ''

    # Pull this from ocdDivisionId
    pieces = [piece.split(':', 1) for piece in ocd_division_id.split('/')]
    fields = {}

    # if it included the ocd-division bit, pop it off
    if pieces[0] == ['ocd-division']:
        pieces.pop(0)

    if pieces[0][0] != 'country':
        # raise ValueError('OCD id must start with country')
        return ''
    fields['country'] = pieces[0][1]

    if len(pieces) < 2:
        return ''

    if pieces[1][0] != 'state':
        # raise ValueError('Expecting state from OCD, and state not found')
        return ''

    fields['state'] = pieces[1][1]

    try:
        if pieces[2][0] in ['place']:
            # These do not have district numbers
            pass
        else:
            return pieces[2][0]
    except Exception as e:
        pass

    return None


def extract_district_id_from_ocd_division_id(ocd_division_id):
    if not positive_value_exists(ocd_division_id):
        return ''

    # Pull this from ocdDivisionId
    pieces = [piece.split(':', 1) for piece in ocd_division_id.split('/')]
    fields = {}

    try:
        last_piece = pieces[-1]
        string_at_end = last_piece[1]
        integer_at_end = convert_to_int(string_at_end)
        if integer_at_end > 0:
            return integer_at_end
    except Exception as e:
        pass

    return None


def extract_zip5_from_zip9(zip9):
    if zip9:
        zip9 = zip9.strip()
    zip5_text = zip9[0:5]
    if len(zip5_text) == 5:
        return zip5_text
    elif len(zip5_text) == 4:
        return '0' + zip5_text
    elif len(zip5_text) == 3:
        return '00' + zip5_text
    return zip5_text


def extract_zip4_from_zip9(zip9):
    if zip9:
        zip9 = zip9.strip()
    if len(zip9) <= 5:
        return ''
    elif len(zip9) == 9:
        # Return characters 6-9
        return zip9[5:9]
    return ''


def extract_zip_formatted_from_zip9(zip9):
    formatted_zip_text = extract_zip5_from_zip9(zip9)
    if len(extract_zip4_from_zip9(zip9)) == 4:
        formatted_zip_text += '-' + extract_zip4_from_zip9(zip9)

    return formatted_zip_text


# precompile when this "functions" app is loaded
pattern_quotes = re.compile(r'"([A-Z]+)\s?""([A-Z]+)""\s?([A-Z]+)"')
pattern_nick_in_middle = re.compile(r'(.*?)(?:[`\'])([A-Z.]+)(?:[`\'])(.*?)$')
pattern_nick_in_middle_paren = re.compile(r'(.*?)(?:\()([A-Z]+)(?:\) )(.*?)$')
pattern_nick_in_middle_quotes = re.compile(r'(.*?)(?:[`\"])([A-Z.]+)(?:[`\"])(.*?)$')
pattern_nick_at_end = re.compile(r'(.*?)\s+(.*?)\s+\((.*?)\)$')


def display_city_with_correct_capitalization(original_city):
    if original_city is not None and not callable(original_city):
        city = str(original_city)
        city.strip()

        city_array = city.split()
        modified_city_string = ''
        for word in city_array:
            modified_city_string += word.capitalize() + ' '

        city = modified_city_string.strip()

        if " Del " in city:
            city = city.replace(' Del ', ' del ')

        city = city.replace("  ", " ")

        return city
    return original_city


def display_full_name_with_correct_capitalization(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        try:
            # Special case for nicknames from Google civic ... "MARY ""MELL"" FLYNN"
            nick = pattern_quotes.search(full_name)
            if nick and len(nick.groups()) == 3:
                return_string = nick.group(1).title() + ' "' + nick.group(2).title() + '" ' + nick.group(3).title()
                return return_string.replace("  ", " ")
            # Special case for nicknames from Google civic ...
            # BEATRICE `BEA` E. GUNN PHILLIPS  ...  CARLOS 'CHUCK' TAYLOR   ...  CAROL 'C.J.' KEAVNEY
            nick2 = pattern_nick_in_middle.search(full_name)
            if nick2 and len(nick2.groups()) == 3:
                return_string = nick2.group(1).title() + ' "' + nick2.group(2).title() + '" ' + nick2.group(3).title()
                return return_string.replace("  ", " ")
            # Special case for nicknames from Google civic ...  LORRAINE (LORI) GEITTMANN
            nick3 = pattern_nick_in_middle_paren.search(full_name)
            if nick3 and len(nick3.groups()) == 3:
                return_string = nick3.group(1).title() + ' "' + nick3.group(2).title() + '" ' + nick3.group(3).title()
                return return_string.replace("  ", " ")
            # Special case for nicknames with correct nickname quotes ...  LORRAINE "LORI" GEITTMANN
            nick3 = pattern_nick_in_middle_quotes.search(full_name)
            if nick3 and len(nick3.groups()) == 3:
                return_string = nick3.group(1).title() + ' "' + nick3.group(2).title() + '" ' + nick3.group(3).title()
                return return_string.replace("  ", " ")

            # Special case for nicknames from Google civic ...  ISRAEL RODRIGUEZ (IROD)
            # This will not work for someone with a middle name, wouldn't know where to put the nickname
            nick4 = pattern_nick_at_end.search(full_name)
            if nick4 and len(nick4.groups()) == 3 and nick4.group(3) != "WITHDRAWN":
                return_string = nick4.group(1).title() + ' "' + nick4.group(3).title() + '" ' + nick4.group(2).title()
                return return_string.replace("  ", " ")
        except Exception as e:
            logger.error('Parsing/regex error in display_full_name_with_correct_capitalization: ', e)
        pattern = r'^([A-Z]\.[A-Z]\.).*?'
        cap = re.search(pattern, full_name)
        full_name_parsed = HumanName(full_name)
        full_name_parsed.capitalize()
        full_name_str = str(full_name_parsed)
        if cap is not None:             # Handle "A.J. BRADY" so it is not "A.j. Brady"
            full_name_str = full_name_str.replace(full_name_str[0:4], cap.group(), 1)

        if " del " in full_name_str:  # Handle "EVE FRANCES DEL CASTELLO" so it is not " => "Eve Frances del Castello"
            full_name_str = full_name_str.replace(' del ', ' Del ')

        full_name_str = full_name_str.replace("  ", " ")

        return full_name_str
    return ""


def convert_district_scope_to_ballotpedia_race_office_level(district_scope):
    federal_scope_list = ['congressional', 'national']
    local_scope_list = [
        'cityCouncil', 'citywide', 'cityWide', 'countyCouncil', 'countywide', 'countyWide', 'schoolBoard', 'special',
        'city', 'county', 'county-council',
    ]  # ids on second line from CTCL and not in specification
    state_scope_list = [
        'judicial', 'stateLower', 'stateUpper', 'statewide', 'stateWide', 'township', 'ward',
        'state', 'state-house',
    ]  # ids on second line from CTCL and not in specification
    if district_scope in federal_scope_list:
        return 'Federal'
    elif district_scope in local_scope_list:
        return 'Local'
    elif district_scope in state_scope_list:
        return 'State'
    else:
        return ''


def convert_level_to_race_office_level(level):
    federal_level_list = ['country']
    local_level_list = ['administrativeArea2']
    state_level_list = ['administrativeArea1']
    #   deputyHeadOfGovernment -
    #   executiveCouncil -
    #   governmentOfficer -
    #   headOfGovernment -
    #   headOfState -
    #   highestCourtJudge -
    #   judge -
    #   legislatorLowerBody -
    #   legislatorUpperBody -
    #   schoolBoard -
    #   specialPurposeOfficer -
    # federal_role_list = ['headOfGovernment', 'headOfState', 'legislatorUpperBody', 'legislatorLowerBody']
    # local_role_list = []
    # state_role_list = []
    if level in federal_level_list:
        return 'Federal'
    elif level in local_level_list:
        return 'Local'
    elif level in state_level_list:
        return 'State'
    # elif role in federal_role_list:
    #     return 'Federal'
    # elif role in local_role_list:
    #     return 'Local'
    # elif role in state_role_list:
    #     return 'State'
    else:
        return ''


def extract_email_addresses_from_string(incoming_string):
    """
    Thanks to https://gist.github.com/dideler/5219706
    :param incoming_string:
    :return:
    """
    string_lower_case = incoming_string.lower()
    regex = re.compile((r"([a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`"
                        r"{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                        r"\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

    collection_of_emails = (email[0] for email in re.findall(regex, string_lower_case) if not email[0].startswith('//'))

    list_of_emails = []
    for email in collection_of_emails:
        list_of_emails.append(email)

    return list_of_emails


def extract_title_from_full_name(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        title = full_name_parsed.title
        return title
    return ""


def extract_first_name_from_full_name(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        first_name = full_name_parsed.first
        return first_name
    return ""


def extract_middle_name_from_full_name(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        middle_name = full_name_parsed.middle
        return middle_name
    return ""


def extract_last_name_from_full_name(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        last_name = full_name_parsed.last
        return last_name
    return ""


def extract_suffix_from_full_name(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        suffix = full_name_parsed.suffix
        return suffix
    return ""


def extract_nickname_from_full_name(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        nickname = full_name_parsed.nickname
        return nickname
    return ""


def extract_vote_usa_measure_id(raw_vote_usa_measure_id):
    return extract_vote_usa_office_id(raw_vote_usa_measure_id)


def extract_vote_usa_office_id(raw_vote_usa_office_id):
    if positive_value_exists(raw_vote_usa_office_id):
        if '|' in raw_vote_usa_office_id:
            parts = raw_vote_usa_office_id.split("|")
            vote_usa_office_id = parts[1]
        else:
            vote_usa_office_id = raw_vote_usa_office_id
        return vote_usa_office_id
    else:
        return ''


def extract_website_from_url(url_string):
    """

    :param url_string:
    :return:
    """
    if not url_string:
        return ""
    if not positive_value_exists(url_string):
        return ""
    url_string = str(url_string)
    url_string.strip()
    url_string = url_string.replace("https://www.", "")
    url_string = url_string.replace("http://www.", "")
    url_string = url_string.replace("https://", "")
    url_string = url_string.replace("http://", "")
    url_string = url_string.replace("www://", "")
    if 'actblue' not in url_string \
            and 'bit.ly' not in url_string \
            and 'facebook' not in url_string \
            and 'instagram' not in url_string \
            and 'linkedin' not in url_string \
            and 'nationbuilder' not in url_string \
            and 'tinyurl' not in url_string \
            and 'twitter' not in url_string \
            and 'wikipedia' not in url_string \
            and 'winred' not in url_string \
            and 'youtube' not in url_string:
        # We don't filter out 'wixsite' because there are valid URLs are like 'https://electcestrada50.wixsite.com'
        url_string = url_string.split("/")[0]
    return url_string


def extract_facebook_username_from_text_string(facebook_text_string):
    """

    :param facebook_text_string:
    :return:
    """
    if not facebook_text_string:
        return ""
    if not positive_value_exists(facebook_text_string):
        return ""
    facebook_text_string = str(facebook_text_string)
    facebook_text_string.strip()
    facebook_text_string = facebook_text_string.lower()
    facebook_text_string = facebook_text_string.replace("http://facebook.com", "")
    facebook_text_string = facebook_text_string.replace("http://www.facebook.com", "")
    facebook_text_string = facebook_text_string.replace("http://m.facebook.com", "")
    facebook_text_string = facebook_text_string.replace("https://facebook.com", "")
    facebook_text_string = facebook_text_string.replace("https://www.facebook.com", "")
    facebook_text_string = facebook_text_string.replace("https://m.facebook.com", "")
    facebook_text_string = facebook_text_string.replace("/www.facebook.com", "")
    facebook_text_string = facebook_text_string.replace("www.facebook.com", "")
    facebook_text_string = facebook_text_string.replace("/facebook.com", "")
    facebook_text_string = facebook_text_string.replace("facebook.com", "")
    facebook_text_string = facebook_text_string.replace("@", "")
    while facebook_text_string.find('/') == 0 or \
            facebook_text_string.find('#') == 0 or \
            facebook_text_string.find('!') == 0:
        facebook_text_string = facebook_text_string[1:]
    if facebook_text_string.find('/') > 0:
        facebook_text_string = facebook_text_string.split("/", 1)[0]  # Remove all after first "/" (including "/")
    facebook_text_string = facebook_text_string.split("?", 1)[0]  # Remove everything after first "?" (including "?")
    return facebook_text_string


def extract_and_replace_facebook_page_id(facebook_full_graph_url):
    # Find the page name from the facebook_full_graph_url
    list_of_integers = [int(x) for x in re.findall(r'\d+', facebook_full_graph_url)]
    # Pop off the last integer

    if len(list_of_integers) > 0:
        # Take the last number
        possible_page_id = list_of_integers.pop()
        if digit_count(possible_page_id) > 8:
            reassembled_url = str('')
            facebook_page_id = possible_page_id
            parts = facebook_full_graph_url.split('/')
            for one_part in parts:
                if str(facebook_page_id) in one_part:
                    reassembled_url += str(facebook_page_id) + '/'
                else:
                    reassembled_url += str(one_part) + '/'
        else:
            reassembled_url = facebook_full_graph_url
    else:
        reassembled_url = facebook_full_graph_url

    if reassembled_url.endswith("//"):
        reassembled_url = reassembled_url[:-1]
    if reassembled_url.endswith("//"):
        reassembled_url = reassembled_url[:-1]
    return reassembled_url


def extract_instagram_handle_from_text_string(instagram_text_string):
    """

    :param instagram_text_string:
    :return:
    """
    if not instagram_text_string:
        return ""
    if not positive_value_exists(instagram_text_string):
        return ""
    instagram_text_string = str(instagram_text_string)
    instagram_text_string.strip()
    instagram_text_string = instagram_text_string.lower()
    instagram_text_string = instagram_text_string.replace("http://instagram.com", "")
    instagram_text_string = instagram_text_string.replace("http://www.instagram.com", "")
    instagram_text_string = instagram_text_string.replace("http://m.instagram.com", "")
    instagram_text_string = instagram_text_string.replace("https://instagram.com", "")
    instagram_text_string = instagram_text_string.replace("https://www.instagram.com", "")
    instagram_text_string = instagram_text_string.replace("https://m.instagram.com", "")
    instagram_text_string = instagram_text_string.replace("/www.instagram.com", "")
    instagram_text_string = instagram_text_string.replace("www.instagram.com", "")
    instagram_text_string = instagram_text_string.replace("/instagram.com", "")
    instagram_text_string = instagram_text_string.replace("instagram.com", "")
    instagram_text_string = instagram_text_string.replace("@", "")
    while instagram_text_string.find('/') == 0 or \
            instagram_text_string.find('#') == 0 or \
            instagram_text_string.find('!') == 0:
        instagram_text_string = instagram_text_string[1:]
    if instagram_text_string.find('/') > 0:
        instagram_text_string = instagram_text_string.split("/", 1)[0]  # Remove all after first "/" (including "/")
    instagram_text_string = instagram_text_string.split("?", 1)[0]  # Remove everything after first "?" (including "?")
    return instagram_text_string


def extract_twitter_handle_from_text_string(twitter_text_string):
    """

    :param twitter_text_string:
    :return:
    """
    if not twitter_text_string:
        return ""
    if not positive_value_exists(twitter_text_string):
        return ""
    twitter_text_string = str(twitter_text_string)
    twitter_text_string.strip()
    strings_to_be_removed_from_url = [
        "http://twitter.com", "http://www.twitter.com", "http://m.twitter.com", "https://twitter.com",
        "https://m.twitter.com", "https://www.twitter.com", "/www.twitter.com", "www.twitter.com",
        "twitter.com", "@",
    ]
    for string_to_be_removed in strings_to_be_removed_from_url:
        twitter_text_string = re.compile(re.escape(string_to_be_removed), re.IGNORECASE).sub("", twitter_text_string)
    twitter_text_string = str(twitter_text_string)
    while twitter_text_string.find('/') == 0 or \
            twitter_text_string.find('#') == 0 or \
            twitter_text_string.find('!') == 0:
        twitter_text_string = twitter_text_string[1:]
    if twitter_text_string.find('/') > 0:
        twitter_text_string = twitter_text_string.split("/", 1)[0]  # Remove everything after first "/" (including "/")
    twitter_text_string = twitter_text_string.split("?", 1)[0]  # Remove everything after first "?" (including "?")

    return twitter_text_string


def is_candidate_we_vote_id(candidate_we_vote_id):
    if not positive_value_exists(candidate_we_vote_id):
        return False
    pattern = re.compile(r'^(wv[\w]{2}cand\d+)$')

    # match variable stores either a match object or None
    match = pattern.match(candidate_we_vote_id)

    # If a match is found, we additionally check if the string ends with the pattern.
    # This ensures that the match covers the entire string from start to finish.
    if match and match.end() == len(candidate_we_vote_id):
        return True
    else:
        return False


def is_politician_we_vote_id(politician_we_vote_id):
    if not positive_value_exists(politician_we_vote_id):
        return False
    pattern = re.compile(r'^(wv[\w]{2}pol\d+)$')
    match = pattern.match(politician_we_vote_id)
    if match and match.end() == len(politician_we_vote_id):
        return True
    else:
        return False


def is_url_valid(url_to_test):
    if not url_to_test:
        return False
    try:
        validate = URLValidator(
            schemes="https"
        )
        result = validate(url_to_test)
    except ValidationError as e:
        return False
    return True


def is_valid_state_code(possible_state_code):
    if positive_value_exists(possible_state_code):
        possible_state_code_lower = possible_state_code.lower()
        for state_code, state_name in STATE_CODE_MAP.items():
            if state_code.lower() == possible_state_code_lower:
                return True
    return False


def get_ip_from_headers(request):
    x_forwarded_for = request.META.get('X-Forwarded-For')
    http_x_forwarded_for = request.headers.get('x-forwarded-for')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[-1].strip()
    elif http_x_forwarded_for:
        return http_x_forwarded_for.split(',')[0].strip()
    else:
        return request.META.get('REMOTE_ADDR')


def get_maximum_number_to_retrieve_from_request(request):
    if 'maximum_number_to_retrieve' in request.GET:
        maximum_number_to_retrieve = request.GET['maximum_number_to_retrieve']
    else:
        maximum_number_to_retrieve = 0
    if maximum_number_to_retrieve == "":
        maximum_number_to_retrieve = 0
    else:
        maximum_number_to_retrieve = convert_to_int(maximum_number_to_retrieve)

    return maximum_number_to_retrieve


# http://stackoverflow.com/questions/1622793/django-cookies-how-can-i-set-them
def set_cookie(response, cookie_name, cookie_value, days_expire=None):
    if days_expire is None:
        max_age = 10 * 365 * 24 * 60 * 60  # ten years
    else:
        max_age = days_expire * 24 * 60 * 60
    expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age),
                                         "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie(cookie_name, cookie_value, max_age=max_age, expires=expires, path="/")


def delete_cookie(response, cookie_name):
    response.delete_cookie(cookie_name, path="/")


def get_voter_api_device_id(request, generate_if_no_cookie=False):
    """
    This function retrieves the voter_api_device_id from the cookies on API server
    :param request:
    :param generate_if_no_cookie:
    :return:
    """
    voter_api_device_id = ''
    # First check the headers
    voter_device_id = request.headers.get('x-header-deviceid', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # Then check for incoming GET value
    voter_device_id = request.GET.get('voter_device_id', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # Then check for incoming POST value
    voter_device_id = request.POST.get('voter_device_id', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # We switch from voter_device_id to voter_api_device_id here
    if 'voter_api_device_id' in request.COOKIES:
        voter_api_device_id = request.COOKIES['voter_api_device_id']
        # logger.debug("from cookie, voter_api_device_id: {voter_api_device_id}".format(
        #     voter_api_device_id=voter_api_device_id
        # ))
    if voter_api_device_id == '' and generate_if_no_cookie:
        voter_api_device_id = generate_voter_device_id()  # Stored in cookie below
        # logger.debug("generate_voter_device_id, voter_api_device_id: {voter_api_device_id}".format(
        #     voter_api_device_id=voter_api_device_id
        # ))
    return voter_api_device_id


def get_voter_device_id(request, generate_if_no_value=False):
    """
    This function retrieves the voter_device_id from the GET values coming from a client
    :param request:
    :param generate_if_no_value:
    :return:
    """
    # First check the headers
    voter_device_id = request.headers.get('x-header-deviceid', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # Then check for incoming GET value
    voter_device_id = request.GET.get('voter_device_id', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # Then check for incoming POST value
    voter_device_id = request.POST.get('voter_device_id', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # Then check for a cookie (in Native)
    if 'voter_device_id' in request.COOKIES:
        return request.COOKIES['voter_device_id']

    if generate_if_no_value:
        voter_device_id = generate_voter_device_id()
        logger.debug("generate_voter_device_id, voter_device_id: {voter_device_id}".format(
            voter_device_id=voter_device_id
        ))
        return voter_device_id
    else:
        return ''


def is_link_to_video(link_url):
    if link_url is None:
        return False
    if "youtube.com" in link_url:
        return True
    return False


def is_speaker_type_individual(speaker_type):
    if speaker_type in (INDIVIDUAL, VOTER):
        return True
    return False


def is_speaker_type_organization(speaker_type):
    if speaker_type in (CORPORATION, GROUP, NEWS_ORGANIZATION, NONPROFIT, NONPROFIT_501C3,
                        NONPROFIT_501C4, ORGANIZATION, ORGANIZATION_WORD, POLITICAL_ACTION_COMMITTEE, "ORGANIZATION",
                        TRADE_ASSOCIATION):
        return True
    return False


def is_speaker_type_public_figure(speaker_type):
    if speaker_type in (PUBLIC_FIGURE, "PUBLIC_FIGURE"):
        return True
    return False


def is_voter_device_id_valid(voter_device_id):
    if not voter_device_id \
            or len(voter_device_id) <= 70 \
            or len(voter_device_id) >= 90:
        success = False
        status = "VALID_VOTER_DEVICE_ID_MISSING "
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
        }
    else:
        success = True
        status = "VALID_VOTER_DEVICE_ID_FOUND "
        json_data = {
            'status': status,
            'success': True,
            'voter_device_id': voter_device_id,
        }

    results = {
        'status': status,
        'success': success,
        'json_data': json_data,
    }
    return results


# TODO: To be deprecated since we don't want to set voter_device_id locally to the API server
def set_voter_device_id(request, response, voter_device_id):
    if 'voter_device_id' not in request.COOKIES:
        set_cookie(response, 'voter_device_id', voter_device_id)


def set_voter_api_device_id(request, response, voter_api_device_id):
    overwrite_cookie = False
    if 'voter_api_device_id' in request.COOKIES:
        overwrite_cookie = request.COOKIES['voter_api_device_id'] != voter_api_device_id
    if 'voter_api_device_id' not in request.COOKIES or overwrite_cookie:
        set_cookie(response, 'voter_api_device_id', voter_api_device_id)


def delete_voter_api_device_id_cookie(response):
    delete_cookie(response, 'voter_api_device_id')


def generate_random_string(
        string_length=88,
        chars=string.ascii_lowercase + string.ascii_uppercase + string.digits,
        remove_confusing_digits=False):
    """
    Generate a random string.
    :param string_length:
    :param chars:
    :param remove_confusing_digits: do not offer these often confused letter/number
    :return:
    """
    if remove_confusing_digits:
        chars = chars.replace("0", "")
        chars = chars.replace("o", "")
        chars = chars.replace("O", "")
        chars = chars.replace("1", "")
        chars = chars.replace("l", "")
    return ''.join(random.SystemRandom().choice(chars) for _ in range(string_length))


def generate_voter_device_id():
    """

    :return:
    :test: WeVoteAPIsV1TestsDeviceIdGenerate
    """
    # We would like this device_id to be long so hackers can't cycle through all possible device ids to get access to
    # a voter's sign in session. As of this writing, all 8 digit strings can be cracked locally in 5.5 hours given the
    # right hardware:
    # http://arstechnica.com/security/2012/12/25-gpu-cluster-cracks-every-standard-windows-password-in-6-hours/
    # But there are limits to how much cookie real-estate every site has.
    # See: http://browsercookielimits.squawky.net/ If you use characters only in the ASCII range, each character
    # takes 1 byte, so you can typically store 4096 characters
    # We use 88 characters to secure us for the foreseeable future, which gives us a unique identifier space of
    # 2.79 with 124 zeros after it
    #  26 + 26 + 10 = 62 character options per "digit"
    #  88(62) = 2.798279e+124
    new_device_id = generate_random_string(88)

    # We do not currently check that this device_id is already in the database because it is such a large number space
    return new_device_id


def list_intersection(list1, list2):
    return list(set(list1) & set(list2))


def positive_value_exists(value):
    """
    This is a test to see if a positive value exists. All of these return false:
        "" (an empty string)
        0 (0 as an integer)
        -1
        0.0 (0 as a float)
        "0" (0 as a string)
        NULL
        FALSE
        array() (an empty array)
    :param value:
    :return: bool
    """
    try:
        if value in [None, '', 'None', False, 'FALSE', 'False', 'false', '0']:
            return False
        if value in ['TRUE', 'True', 'true', '1']:
            return True
        if isinstance(value, list):
            return bool(len(value))
        if isinstance(value, dict):
            return bool(len(value))
        if isinstance(value, datetime.date):
            return bool(value is not None)
        if isinstance(value, str):
            return bool(len(value))
        if not isinstance(value, tuple):
            value = float(value)
            if value <= 0:
                return False
    except ValueError:
        return False
    except Exception as e:
        return False
    return bool(value)


def convert_state_text_to_state_code(state_text):
    if not positive_value_exists(state_text):
        return ""
    for state_code, state_name in STATE_CODE_MAP.items():
        if state_text.lower() == state_name.lower():
            return state_code
        elif state_text.lower() == state_code.lower():
            return state_code
    else:
        return ""


def convert_state_code_to_state_text(incoming_state_code):
    if not positive_value_exists(incoming_state_code):
        return ""
    for state_code, state_name in STATE_CODE_MAP.items():
        if incoming_state_code.lower() == state_code.lower():
            return state_name
    else:
        return ""


def convert_state_code_to_utc_offset(state_code):
    return UTC_OFFSET_MAP.get(state_code, None)


def convert_integer_to_string_with_comma_for_thousands_separator(integer_number):
    try:
        number_with_commas = "{:,}".format(integer_number)
    except Exception:
        number_with_commas = ""

    return number_with_commas


def process_request_from_master(request, message_text, get_url, get_params):
    """

    :param request:
    :param message_text:
    :param get_url:
    :param get_params:
    :return: structured_json and import_results
    """
    status_message = ""
    try:
        if 'google_civic_election_id' in get_params:
            message_text += " for google_civic_election_id " + str(get_params['google_civic_election_id'])
        messages.add_message(request, messages.INFO, message_text)
        logger.info(message_text)
        print("process_request_from_master: " + message_text)  # Please don't remove this line
    except Exception as e:
        status_message += "ERROR_PRINTING_MESSAGE_TEXT: " + str(e) + " "

    response = requests.get(get_url, params=get_params)

    structured_json = json.loads(response.text)

    if 'success' in structured_json and not structured_json['success']:
        import_results = {
            'success': False,
            'status': "Error: " + structured_json['status'],
        }
    else:
        import_results = {
            'success': True,
            'status': "",
        }

    if 'google_civic_election_id' in get_params:
        status_message += "... the master server returned " + str(len(structured_json)) + " items.  Election " \
                                 + str(get_params['google_civic_election_id'])  # Please don't remove this line
        print(status_message)
    else:
        # Please don't remove this line
        status_message += "... the master server returned " + str(len(structured_json)) + " items."
        print(status_message)

    return import_results, structured_json


def add_period_to_middle_name_initial(name):
    modified_name = name.replace(' A ', ' A. ')
    modified_name = modified_name.replace(' B ', ' B. ')
    modified_name = modified_name.replace(' C ', ' C. ')
    modified_name = modified_name.replace(' D ', ' D. ')
    modified_name = modified_name.replace(' E ', ' E. ')
    modified_name = modified_name.replace(' F ', ' F. ')
    modified_name = modified_name.replace(' G ', ' G. ')
    modified_name = modified_name.replace(' H ', ' H. ')
    modified_name = modified_name.replace(' I ', ' I. ')
    modified_name = modified_name.replace(' J ', ' J. ')
    modified_name = modified_name.replace(' K ', ' K. ')
    modified_name = modified_name.replace(' L ', ' L. ')
    modified_name = modified_name.replace(' M ', ' M. ')
    modified_name = modified_name.replace(' N ', ' N. ')
    modified_name = modified_name.replace(' O ', ' O. ')
    modified_name = modified_name.replace(' P ', ' P. ')
    modified_name = modified_name.replace(' Q ', ' Q. ')
    modified_name = modified_name.replace(' R ', ' R. ')
    modified_name = modified_name.replace(' S ', ' S. ')
    modified_name = modified_name.replace(' T ', ' T. ')
    modified_name = modified_name.replace(' U ', ' U. ')
    modified_name = modified_name.replace(' V ', ' V. ')
    modified_name = modified_name.replace(' W ', ' W. ')
    modified_name = modified_name.replace(' X ', ' X. ')
    modified_name = modified_name.replace(' Y ', ' Y. ')
    modified_name = modified_name.replace(' Z ', ' Z. ')
    if len(name) != len(modified_name):
        name_changed = True
    else:
        name_changed = False
    results = {
        'status': "ADD_PERIOD_TO_MIDDLE_NAME_INITIAL ",
        'success': True,
        'incoming_name': name,
        'modified_name': modified_name,
        'name_changed': name_changed,
    }
    return results


def remove_middle_initial_from_name(name):
    modified_name = name
    uppercase_a_through_z = list(string.ascii_uppercase)
    for middle_initial in uppercase_a_through_z:
        modified_name = modified_name.replace(" {middle_initial} ".format(middle_initial=middle_initial), ' ')
        modified_name = modified_name.replace(" {middle_initial}. ".format(middle_initial=middle_initial), ' ')
    if len(name) != len(modified_name):
        name_changed = True
    else:
        name_changed = False
    results = {
        'status': "REMOVE_MIDDLE_INITIAL ",
        'success': True,
        'incoming_name': name,
        'modified_name': modified_name,
        'name_changed': name_changed,
    }
    return results


def remove_period_from_middle_name_initial(name):
    modified_name = name.replace(' A. ', ' A ')
    modified_name = modified_name.replace(' B. ', ' B ')
    modified_name = modified_name.replace(' C. ', ' C ')
    modified_name = modified_name.replace(' D. ', ' D ')
    modified_name = modified_name.replace(' E. ', ' E ')
    modified_name = modified_name.replace(' F. ', ' F ')
    modified_name = modified_name.replace(' G. ', ' G ')
    modified_name = modified_name.replace(' H. ', ' H ')
    modified_name = modified_name.replace(' I. ', ' I ')
    modified_name = modified_name.replace(' J. ', ' J ')
    modified_name = modified_name.replace(' K. ', ' K ')
    modified_name = modified_name.replace(' L. ', ' L ')
    modified_name = modified_name.replace(' M. ', ' M ')
    modified_name = modified_name.replace(' N. ', ' N ')
    modified_name = modified_name.replace(' O. ', ' O ')
    modified_name = modified_name.replace(' P. ', ' P ')
    modified_name = modified_name.replace(' Q. ', ' Q ')
    modified_name = modified_name.replace(' R. ', ' R ')
    modified_name = modified_name.replace(' S. ', ' S ')
    modified_name = modified_name.replace(' T. ', ' T ')
    modified_name = modified_name.replace(' U. ', ' U ')
    modified_name = modified_name.replace(' V. ', ' V ')
    modified_name = modified_name.replace(' W. ', ' W ')
    modified_name = modified_name.replace(' X. ', ' X ')
    modified_name = modified_name.replace(' Y. ', ' Y ')
    modified_name = modified_name.replace(' Z. ', ' Z ')
    if len(name) != len(modified_name):
        name_changed = True
    else:
        name_changed = False
    results = {
        'status': "REMOVE_PERIOD_FROM_MIDDLE_NAME_INITIAL ",
        'success': True,
        'incoming_name': name,
        'modified_name': modified_name,
        'name_changed': name_changed,
    }
    return results


def add_period_to_name_prefix_and_suffix(name):
    modified_name = name.replace(', JR', ' JR.')
    modified_name = modified_name.replace(' JR', ' JR.')
    modified_name = modified_name.replace(', Jr', ' Jr.')
    modified_name = modified_name.replace(' Jr', ' Jr.')
    modified_name = modified_name.replace(', SR', ' SR.')
    modified_name = modified_name.replace(' SR', ' SR.')
    modified_name = modified_name.replace(', Sr', ' Sr.')
    modified_name = modified_name.replace(' Sr', ' Sr.')
    if len(name) != len(modified_name):
        name_changed = True
    else:
        name_changed = False
    results = {
        'status': "ADD_PERIOD_TO_NAME_PREFIX_OR_SUFFIX ",
        'success': True,
        'incoming_name': name,
        'modified_name': modified_name,
        'name_changed': name_changed,
    }
    return results


def remove_period_from_name_prefix_and_suffix(name):
    modified_name = name.replace(', JR. ', '  JR')
    modified_name = modified_name.replace(' JR.', ' JR')
    modified_name = modified_name.replace(', Jr.', ' Jr')
    modified_name = modified_name.replace(' Jr.', ' Jr')
    modified_name = modified_name.replace(', SR.', ' SR')
    modified_name = modified_name.replace(' SR.', ' SR')
    modified_name = modified_name.replace(', Sr.', ' Sr')
    modified_name = modified_name.replace(' Sr.', ' Sr')
    if len(name) != len(modified_name):
        name_changed = True
    else:
        name_changed = False
    results = {
        'status': "REMOVE_PERIOD_FROM_NAME_PREFIX_OR_SUFFIX ",
        'success': True,
        'incoming_name': name,
        'modified_name': modified_name,
        'name_changed': name_changed,
    }
    return results


def return_first_x_words(original_string, number_of_words_to_return, include_ellipses=False):
    # Mimics returnFirstXWords in WebApp and Campaigns site
    if not original_string:
        return ''

    need_for_ellipses = False
    words_array = original_string.split()
    x_words = ''
    i = 0
    for one_word in words_array:
        if i >= number_of_words_to_return:
            need_for_ellipses = True
        if i < number_of_words_to_return:
            x_words += one_word + ' '
        i += 1
    # Finally remove leading or trailing spaces
    x_words = x_words.strip()
    if need_for_ellipses and include_ellipses:
        x_words += '...'
    return x_words


def return_value_from_request(
        request={},
        variable_name='',
        is_post=False,
        alternate_value='',
        ):
    if is_post:
        value = request.POST.get(variable_name, alternate_value)
    else:
        value = request.GET.get(variable_name, alternate_value)
    return value


def strip_html_tags(value):
    """
    Creating a separate strip tag function instead of using  django.utils.html.strip_tags directly where required to
    allow for validations/value escaping later
    :param value: Text that needs to be stripped
    :return: stripped value.
    """
    if positive_value_exists(value):
        return django.utils.html.strip_tags(value)
    else:
        return ""
