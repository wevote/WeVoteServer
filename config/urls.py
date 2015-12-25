# config/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

"""
URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

from django.conf.urls import include, url

from config import startup
from config import views


urlpatterns = [
    url(r'^$', views.start_view),  # Default page if none of the other patterns work
    url(r'^admin/', include('admin_tools.urls', namespace="admin_tools")),
    url(r'^apis/v1/', include('apis_v1.urls', namespace="apis_v1")),

    url(r'^c/', include('candidate.urls', namespace="candidate")),
    url(r'^e/', include('election.urls', namespace="election")),
    url(r'^follow/', include('follow.urls', namespace="follow")),
    url(r'^import_export_google_civic/', include(
        'import_export_google_civic.urls', namespace="import_export_google_civic")),
    url(r'^import_export_vote_smart/', include(
        'import_export_vote_smart.urls', namespace="import_export_vote_smart")),
    url(r'^info/', include('quick_info.urls', namespace="quick_info")),
    url(r'^m/', include('measure.urls', namespace="measure")),
    url(r'^o/', include('office.urls', namespace="office")),
    url(r'^org/', include('organization.urls', namespace="organization")),
    url(r'^pl/', include('polling_location.urls', namespace="polling_location")),
    url(r'^politician_list/', include('politician.urls', namespace="politician_list")),
    url(r'^politician/', include('politician.urls', namespace="politician")),
    url(r'^pos/', include('position.urls', namespace="position")),
    url(r'^sod/', include('support_oppose_deciding.urls', namespace="support_oppose_deciding")),
    url(r'^tag/', include('tag.urls', namespace="tag")),
    # url('', include('wevote_social.urls', namespace='wevote_social')),
    url('social', include('social.apps.django_app.urls', namespace="social")),
    url(r'^voter/', include('voter.urls', namespace="voter")),
    url(r'^vg/', include('voter_guide.urls', namespace="voter_guide")),
    # Authentication
    url('', include('django.contrib.auth.urls', namespace="auth")),  # This line provides all of the following patterns:
    # login, logout, password_reset, password_reset_done, password_reset_confirm, password_reset_complete
]

# Execute start-up.
startup.run()
