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
from django.contrib.auth import views as auth_views
from config import startup, views
from admin_tools.views import login_we_vote, logout_we_vote

urlpatterns = [
    url(r'^$', views.start_view),  # Default page if none of the other patterns work
    url(r'^admin/', include(('admin_tools.urls', 'admin_tools'), namespace="admin_tools")),
    url(r'^apis/v1/', include(('apis_v1.urls', 'apis_v1'), namespace="apis_v1")),

    url(r'^a/', include(('analytics.urls','analytics'), namespace="analytics")),
    url(r'^b/', include(('ballot.urls','ballot'), namespace="ballot")),
    url(r'^ballotpedia/', include(('import_export_ballotpedia.urls','ballotpedia'), namespace="ballotpedia")),
    url(r'^bookmark/', include(('bookmark.urls','bookmark'), namespace="bookmark")),
    url(r'^c/', include(('candidate.urls', 'candidate'), namespace="candidate")),
    url(r'^e/', include(('election.urls', 'election'), namespace="election")),
    url(r'^elected_office/', include(('elected_office.urls', 'elected_office'), namespace="elected_office")),
    url(r'^elected_official_list/', include(('elected_official.urls', 'elected_official_list'), namespace="elected_official_list")),
    url(r'^elected_official/', include(('elected_official.urls', 'elected_official'), namespace="elected_official")),
    url(r'^electoral_district/', include(('electoral_district.urls', 'electoral_district'), namespace="electoral_district")),
    url(r'^follow/', include(('follow.urls', 'follow'), namespace="follow")),
    url(r'^google_custom_search/', include(('google_custom_search.urls', 'google_custom_search'), namespace="google_custom_search")),
    url(r'^health/', views.health_view),  # A simple health check to make sure the site is running
    url(r'^image/', include(('image.urls', 'image'), namespace="image")),
    url(r'^import_export_batches/', include(('import_export_batches.urls', 'import_export_batches'), namespace="import_export_batches")),
    url(r'^import_export_ctcl/', include(('import_export_ctcl.urls', 'import_export_ctcl'), namespace="import_export_ctcl")),
    url(r'^import_export_facebook/', include(('import_export_facebook.urls', 'import_export_facebook'), namespace="import_export_facebook")),
    url(r'^import_export_google_civic/', include((
        'import_export_google_civic.urls','import_export_google_civic'), namespace="import_export_google_civic")),
    url(r'^import_export_maplight/', include(('import_export_maplight.urls', 'import_export_maplight'), namespace="import_export_maplight")),
    url(r'^import_export_twitter/', include(('import_export_twitter.urls', 'import_export_twitter'), namespace="import_export_twitter")),
    url(r'^import_export_vote_smart/', include(('import_export_vote_smart.urls', 'import_export_vote_smart'), namespace="import_export_vote_smart")),
    url(r'^import_export_wikipedia/', include(('import_export_wikipedia.urls', 'import_export_wikipedia'), namespace="import_export_wikipedia")),
    url(r'^import_export_endorsements/', include((
        'import_export_endorsements.urls','import_export_endorsements'), namespace="import_export_endorsements")),
    url(r'^info/', include(('quick_info.urls', 'quick_info'), namespace="quick_info")),
    url(r'^issue/', include(('issue.urls', 'issue'), namespace="issue")),
    url(r'^m/', include(('measure.urls', 'measure'), namespace="measure")),
    url(r'^off/', include(('office.urls', 'office'), namespace="office")),
    url(r'^org/', include(('organization.urls', 'organization'), namespace="organization")),
    url(r'^pl/', include(('polling_location.urls', 'polling_location'), namespace="polling_location")),
    url(r'^party/', include(('party.urls', 'party'), namespace="party")),
    url(r'^politician_list/', include(('politician.urls', 'politician_list'), namespace="politician_list")),
    url(r'^politician/', include(('politician.urls', 'politician'), namespace="politician")),
    url(r'^pos/', include(('position.urls', 'position'), namespace="position")),
    url(r'^scheduled_tasks/', include(('scheduled_tasks.urls', 'scheduled_tasks'), namespace="scheduled_tasks")),
    url(r'^sod/', include(('support_oppose_deciding.urls', 'support_oppose_deciding'), namespace="support_oppose_deciding")),
    url(r'^tag/', include(('tag.urls', 'tag'), namespace="tag")),
    url(r'^twitter/', include(('import_export_twitter.urls', 'twitter'), namespace="twitter")),
    url(r'^twitter2/', include(('twitter.urls', 'twitter2'), namespace="twitter2")),
    url(r'^voter/', include(('voter.urls', 'voter'), namespace="voter")),
    url(r'^vg/', include(('voter_guide.urls', 'voter_guide'), namespace="voter_guide")),
    # Authentication
    # url(r'^login/$', auth_views.login, name="login"),
    url(r'^login/$', login_we_vote, name="login"),
    url(r'^logout/$', auth_views.auth_logout, name="logout"),
    url(r'^login_we_vote/$', login_we_vote, name="login_we_vote"),
    url(r'^logout_we_vote/$', logout_we_vote, name="logout_we_vote"),
    # This line provides the following patterns:
    # login, logout, password_reset, password_reset_done, password_reset_confirm, password_reset_complete
    url('', include(('social_django.urls', 'social'), namespace="social")),
    # socialcomplete/facebook - See wevote_social/utils.py
]

# Execute start-up.
startup.run()
