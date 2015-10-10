# wevote_social/context_processors.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

def profile_photo(request):
    """Social template context processors"""
    context_extras = {}
    if hasattr(request, 'facebook'):
        context_extras = {
            'social': {
                'profile_photo': request.facebook.profile_url()
            }
        }

    return context_extras
