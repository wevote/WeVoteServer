# wevote_functions/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import datetime
import random
import string
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


def convert_to_int(value):
    try:
        new_value = int(value)
    except ValueError:
        new_value = 0
    return new_value


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

    # Check that this device_id isn't already in the database
    # TODO Implement the check
    return new_device_id


def value_exists(value):
    """
    This is a test to see if a positive value exists. All of these return false:
        "" (an empty string)
        0 (0 as an integer)
        0.0 (0 as a float)
        "0" (0 as a string)
        NULL
        FALSE
        array() (an empty array)
    :param value:
    :return: bool
    """
    try:
        value = float(value)
    except ValueError:
        pass
    return bool(value)
