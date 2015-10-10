# wevote_social/middleware.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""Social middleware"""

from facebook import FacebookAPI


class SocialMiddleware(object):
    def process_request(self, request):
        if request.user and hasattr(request.user, 'social_auth'):
            social_user = request.user.social_auth.filter(
                provider='facebook',
            ).first()
            if social_user:
                request.facebook = FacebookAPI(social_user)

        return None
