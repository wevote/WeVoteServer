# wevote_functions/functions.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import datetime
from nameparser import HumanName
import random
import re
import string
import sys
import types
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


STATE_CODE_MAP = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    'AS': 'American Samoa',
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
    'MP': 'Northern Mariana Islands',
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
    'PR': 'Puerto Rico',
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
    'WY': 'Wyoming'
}

AMERICAN_INDEPENDENT = 'AMERICAN_INDEPENDENT'
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


# This is how we make sure a variable is a boolean
def convert_to_bool(value):
    if value is True:
        return True
    elif value is 1:
        return True
    elif value is False:
        return False
    elif value is 0:
        return True

    value = value.lower()
    if value in ['true', '1']:
        return True
    elif value in ['false', '0']:
        return False
    return False


# This is how we make sure a variable is an integer
def convert_to_int(value):
    try:
        new_value = int(value)
    except ValueError:
        new_value = 0
    return new_value


# This is how we make sure a variable is a string
def convert_to_str(value):
    try:
        new_value = str(value)
    except ValueError:
        new_value = ''
    return new_value


# See also 'candidate_party_display' in candidate/models.py
def convert_to_political_party_constant(raw_party_incoming):
    raw_party = raw_party_incoming.lower()
    raw_party = raw_party.replace("Party Preference: ", "")

    if raw_party == 'amer. ind.':
        return AMERICAN_INDEPENDENT
    if raw_party == 'american independent':
        return AMERICAN_INDEPENDENT
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
    if raw_party == 'independent':
        return INDEPENDENT
    if raw_party == 'independent green':
        return INDEPENDENT_GREEN
    if raw_party == 'lib':
        return LIBERTARIAN
    if raw_party == 'Libertarian':
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
    if raw_party == 'peace and freedom':
        return PEACE_AND_FREEDOM
    if raw_party == 'reform':
        return REFORM
    if raw_party == 'rep':
        return REPUBLICAN
    if raw_party == 'republican':
        return REPUBLICAN
    if raw_party == 'republican party':
        return REPUBLICAN
    else:
        return raw_party_incoming


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

    if pieces[1][0] != 'state':
        # raise ValueError('Expecting state from OCD, and state not found')
        return ''

    fields['state'] = pieces[1][1]

    return fields['state']


def extract_zip5_from_zip9(zip9):
    zip5_text = zip9[0:5]
    if len(zip5_text) == 5:
        return zip5_text
    elif len(zip5_text) == 4:
        return '0' + zip5_text
    elif len(zip5_text) == 3:
        return '00' + zip5_text
    return zip5_text


def extract_zip4_from_zip9(zip9):
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


def display_full_name_with_correct_capitalization(full_name):
    """
    See documentation here: https://github.com/derek73/python-nameparser
    :param full_name:
    :return:
    """
    if full_name is not None and not callable(full_name):
        full_name = str(full_name)
        full_name.strip()
        full_name_parsed = HumanName(full_name)
        full_name_parsed.capitalize()
        full_name_capitalized = str(full_name_parsed)
        return full_name_capitalized
    return ""


def extract_email_addresses_from_string(incoming_string):
    """
    Thanks to https://gist.github.com/dideler/5219706
    :param incoming_string:
    :return:
    """
    string_lower_case = incoming_string.lower()
    regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                        "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                        "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

    collection_of_emails = (email[0] for email in re.findall(regex, string_lower_case) if not email[0].startswith('//'))

    list_of_emails = []
    for email in collection_of_emails:
        list_of_emails.append(email)

    return list_of_emails


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
    twitter_text_string = twitter_text_string.lower()
    twitter_text_string = twitter_text_string.replace("http://twitter.com", "")
    twitter_text_string = twitter_text_string.replace("http://www.twitter.com", "")
    twitter_text_string = twitter_text_string.replace("https://twitter.com", "")
    twitter_text_string = twitter_text_string.replace("https://www.twitter.com", "")
    twitter_text_string = twitter_text_string.replace("www.twitter.com", "")
    twitter_text_string = twitter_text_string.replace("twitter.com", "")
    twitter_text_string = twitter_text_string.replace("@", "")
    twitter_text_string = twitter_text_string.replace("/", "")
    return twitter_text_string


def get_ip_from_headers(request):
    x_forwarded_for = request.META.get('X-Forwarded-For')
    http_x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[-1].strip()
    elif http_x_forwarded_for:
        return http_x_forwarded_for.split(',')[0].strip()
    else:
        return request.META.get('REMOTE_ADDR')


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
    if 'voter_api_device_id' in request.COOKIES:
        voter_api_device_id = request.COOKIES['voter_api_device_id']
        logger.debug("from cookie, voter_api_device_id: {voter_api_device_id}".format(
            voter_api_device_id=voter_api_device_id
        ))
    if voter_api_device_id == '' and generate_if_no_cookie:
        voter_api_device_id = generate_voter_device_id()  # Stored in cookie below
        logger.debug("generate_voter_device_id, voter_api_device_id: {voter_api_device_id}".format(
            voter_api_device_id=voter_api_device_id
        ))
    return voter_api_device_id


def get_voter_device_id(request, generate_if_no_value=False):
    """
    This function retrieves the voter_device_id from the GET values coming from a client
    :param request:
    :param generate_if_no_value:
    :return:
    """
    # First check the headers
    voter_device_id = request.META.get('HTTP_X_HEADER_DEVICEID', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    # Then check for incoming GET value
    voter_device_id = request.GET.get('voter_device_id', '')
    if positive_value_exists(voter_device_id):
        return voter_device_id

    if generate_if_no_value:
        voter_device_id = generate_voter_device_id()
        logger.debug("generate_voter_device_id, voter_device_id: {voter_device_id}".format(
            voter_device_id=voter_device_id
        ))
        return voter_device_id
    else:
        return ''


def is_voter_device_id_valid(voter_device_id):
    if not voter_device_id \
            or len(voter_device_id) <= 70 \
            or len(voter_device_id) >= 90:
        success = False
        status = "VALID_VOTER_DEVICE_ID_MISSING"
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
        }
    else:
        success = True
        status = "VALID_VOTER_DEVICE_ID_FOUND"
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
    if 'voter_api_device_id' not in request.COOKIES:
        set_cookie(response, 'voter_api_device_id', voter_api_device_id)


def delete_voter_api_device_id_cookie(response):
    delete_cookie(response, 'voter_api_device_id')


def generate_random_string(string_length=88, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    """
    Generate a random string.
    :param string_length:
    :param chars:
    :return:
    """
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
        if value in [None, '', 'None', False, 'False', 'false']:
            return False
        if sys.version_info > (3, 0):
            # Python 3 code in this block
            if isinstance(value, list):
                return bool(len(value))
            if isinstance(value, dict):
                return bool(len(value))
            if isinstance(value, datetime.date):
                return bool(value is not None)
        else:
            # Python 2 code in this block
            if isinstance(value, types.ListType):
                return bool(len(value))
            if isinstance(value, types.DictType):
                return bool(len(value))
            # TODO We aren't checking for datetime format and need to

        value = float(value)
        if value < 0:
            return False
    except ValueError:
        pass
    return bool(value)


def convert_state_text_to_state_code(state_text):
    for state_code, state_name in STATE_CODE_MAP.items():
        if state_text.lower() == state_name.lower():
            return state_code
    else:
        return ""


def convert_state_code_to_state_text(incoming_state_code):
    for state_code, state_name in STATE_CODE_MAP.items():
        if incoming_state_code.lower() == state_code.lower():
            return state_name
    else:
        return ""
