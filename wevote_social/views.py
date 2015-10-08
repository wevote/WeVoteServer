
from django.shortcuts import render

def login_view(request):
    next = request.GET.get('next', '/')
    return render(request, 'wevote_social/login.html', {'next': next})
