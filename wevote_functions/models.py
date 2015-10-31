# wevote_functions/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import datetime
import random
import string
import sys
import types
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class switch(object):
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


# http://stackoverflow.com/questions/1622793/django-cookies-how-can-i-set-them
def set_cookie(response, cookie_name, cookie_value, days_expire=None):
    if days_expire is None:
        max_age = 10 * 365 * 24 * 60 * 60  # ten years
    else:
        max_age = days_expire * 24 * 60 * 60
    expires = datetime.datetime.strftime(datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age),
                                         "%a, %d-%b-%Y %H:%M:%S GMT")
    response.set_cookie(cookie_name, cookie_value, max_age=max_age, expires=expires)


def get_voter_device_id(request, generate_if_no_cookie=False):
    voter_device_id = ''
    if 'voter_device_id' in request.COOKIES:
        voter_device_id = request.COOKIES['voter_device_id']
        logger.debug("from cookie, voter_device_id: {voter_device_id}".format(
            voter_device_id=voter_device_id
        ))
    if voter_device_id == '' and generate_if_no_cookie:
        voter_device_id = generate_voter_device_id()  # Stored in cookie below
        # If we set this here, we won't know whether we need to store the cookie in set_voter_device_id
        # request.COOKIES['voter_device_id'] = voter_device_id  # Set it here for use in the remainder of this page load
        logger.debug("generate_voter_device_id, voter_device_id: {voter_device_id}".format(
            voter_device_id=voter_device_id
        ))
    return voter_device_id


def is_voter_device_id_valid(voter_device_id):
    if not voter_device_id \
            or len(voter_device_id) <= 70 \
            or len(voter_device_id) >= 90:
        success = False
        json_data = {
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'success': False,
            'voter_device_id': voter_device_id,
        }
    else:
        success = True
        json_data = {
            'status': '',
            'success': True,
            'voter_device_id': voter_device_id,
        }

    results = {
        'success': success,
        'json_data': json_data,
    }
    return results


def set_voter_device_id(request, response, voter_device_id):
    if 'voter_device_id' not in request.COOKIES:
        set_cookie(response, 'voter_device_id', voter_device_id)


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
        if value is None:
            return False
        if sys.version_info > (3, 0):
            # Python 3 code in this block
            if isinstance(value, list):
                return bool(len(value))
            if isinstance(value, dict):
                return bool(len(value))
        else:
            # Python 2 code in this block
            if isinstance(value, types.ListType):
                return bool(len(value))
            if isinstance(value, types.DictType):
                return bool(len(value))

        value = float(value)
        if value < 0:
            return False
    except ValueError:
        pass
    return bool(value)


def get_google_civic_election_id_from_cookie(request):
    google_civic_election_id = 0
    if 'google_civic_election_id' in request.COOKIES:
        google_civic_election_id = request.COOKIES['google_civic_election_id']
        logger.debug("from cookie, google_civic_election_id: {google_civic_election_id}".format(
            google_civic_election_id=google_civic_election_id
        ))
    return google_civic_election_id


def set_google_civic_election_id_cookie(request, response, google_civic_election_id):
    set_cookie(response, 'google_civic_election_id', google_civic_election_id)
