# wevote_social/middleware.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""Social middleware"""

from django.http import HttpResponse
from wevote_social.facebook import FacebookAPI
from social import exceptions as social_exceptions
from social.apps.django_app.middleware import SocialAuthExceptionMiddleware
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


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
            error_exception = ""
            print_path = ""
            try:
                error_exception = exception.args[0]
            except Exception as e1:
                pass

            if len(error_exception) == 0:
                try:
                    error_exception = exception.message
                except Exception as e2:
                    error_exception = "Failure in exception processing in our middleware"
                    print(error_exception)

            try:
                print_path = request.path
            except Exception as e2:
                pass

            logger.error('WeVoteSocialAuthExceptionMiddleware threw {error} [type: {error_type}]'.format(
                error=error_exception, error_type=type(exception)))
            raise exception
