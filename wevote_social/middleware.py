# wevote_social/middleware.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""Social middleware"""

from django.http import HttpResponse
from wevote_social.facebook import FacebookAPI
from social import exceptions as social_exceptions
from social.apps.django_app.middleware import SocialAuthExceptionMiddleware
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from wevote_functions.functions import get_voter_api_device_id, positive_value_exists


class SocialMiddleware(object):
    def process_request(self, request):
        if request.user and hasattr(request.user, 'social_auth'):
            social_user = request.user.social_auth.filter(
                provider='facebook',
            ).first()
            if social_user:
                request.facebook = FacebookAPI(social_user)

        return None


class WeVoteSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    """
    We want to catch these exceptions and deal with them:
    AuthAlreadyAssociated
    """
    def process_exception(self, request, exception):
        if hasattr(social_exceptions, exception.__class__.__name__):
            if exception.__class__.__name__ == 'AuthAlreadyAssociated':
                return HttpResponse("AuthAlreadyAssociated: %s" % exception)
            else:
                raise exception
        else:
            raise exception
