"""Social template context processors"""

def profile_photo(request):
    context_extras = {}
    if hasattr(request, 'facebook'):
        context_extras = {
            'social': {
                'profile_photo': request.facebook.profile_url()
            }
        }

    return context_extras
