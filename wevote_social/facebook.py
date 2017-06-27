# wevote_social/facebook.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from future.standard_library import install_aliases
install_aliases()

# from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
# from urllib.error import HTTPError
import logging
import json
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class FacebookAPI(object):
    """API to Facebook's opengraph."""

    def __init__(self, social_user):
        self.social_user = social_user

    def fetch_friends(self):
        request = self._request()
        friends = []

        try:
            friends = json.loads(urlopen(request).read()).get('data')
        except Exception as err:
            logger.error(err)

        return friends

    def profile_url(self):
        # Facebook will 302 redirect to the profile photo.
        return u'https://graph.facebook.com/{0}/picture'.format(self.social_user.uid)

    def _request(self, **params):
        url = u'https://graph.facebook.com/{0}/' \
              u'friends?fields=id,name,location,picture' \
              u'&access_token={1}'.format(
                  self.social_user.uid,
                  self.social_user.extra_data['access_token'],
              )

        request = Request(url)
        return request
