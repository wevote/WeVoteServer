# wevote_social/middleware.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""Social middleware"""

from inspect import getmembers
from types import FunctionType

from django.http import HttpResponse

import wevote_functions.admin
from wevote_social.facebook import FacebookAPI

logger = wevote_functions.admin.get_logger(__name__)


class SocialMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def attributes(self, obj):
        disallowed_names = {
            name for name, value in getmembers(type(obj))
            if isinstance(value, FunctionType)}
        return {
            name: getattr(obj, name) for name in dir(obj)
            if name[0] != '_' and name not in disallowed_names and hasattr(obj, name)}

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.


        if "/complete/twitter/" in request.path:
            print('MIDDLEWARE:request.path: ', request.path)
            print("MIDDLEWARE: object: " + str(request))
            if 'redirect_state' in request.GET:
                print("MIDDLEWARE: redirect_state: " + request.GET['redirect_state'])
            else:
                print("MIDDLEWARE: redirect_state: NO REDIRECT STATE RECEIVED (this could be a problem)")

            print("MIDDLEWARE: headers: " + str(request.headers))
            print("MIDDLEWARE: session: " + str(self.attributes(request.session)))
            tok = request.GET['oauth_token'] if request.GET['oauth_token'] else ""
            ver = request.GET['oauth_verifier'] if request.GET['oauth_verifier'] else ""
            # respURL = 'https://' + request.headers['Host'] + '/twittersigninprocess?oauth_token=' + tok + '&oauth_verifier=' + ver
            # respURL = request.build_absolute_uri()  loops exactly to here
            respURL = 'https://' + request.headers['Host'] + '/login_we_vote'
            print("MIDDLEWARE: respURL: " + respURL)

            # Bypass the state check in middleware for Twitter V2 API and the '/complete/twitter/' request ...
            #   In this case unconditionally return a 200
            # response = redirect(respURL)
            # return response
            # return HttpResponse()       TODO March 13, 2024 ... let fall through in all cases for now


        response = self.get_response(request)
    # def process_request(self, request):
        if hasattr(request, 'user'):
            if request.user and hasattr(request.user, 'social_auth'):
                social_user = request.user.social_auth.filter(
                    provider='facebook',
                ).first()
                if social_user:
                    request.facebook = FacebookAPI(social_user)

        return response

    def process_exception(request, exception):
        # if hasattr(social_exceptions, exception.__class__.__name__):
        #     if exception.__class__.__name__ == 'AuthAlreadyAssociated':
        #         return HttpResponse("AuthAlreadyAssociated: %s" % exception)
        #     else:
        #         raise exception
        # else:
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
                print("Middleware custom: " + error_exception)

        try:
            print_path = request.path
        except Exception as e2:
            pass

        logger.error('From \'{path}\' caught \'{error}\', type: {error_type}'.format(
            path=print_path, error=error_exception, error_type=type(exception)))
        raise exception
