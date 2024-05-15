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
    2. Add a URL to urlpatterns:  re_path(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  re_path(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  re_path(r'^blog/', include(blog_urls))
"""

from django.urls import include, re_path
from django.contrib.auth import views as auth_views

from admin_tools.views import login_we_vote, logout_we_vote
from config import startup, views

urlpatterns = [
    re_path(r'^$', views.start_view),  # Default page if none of the other patterns work
    re_path(r'^favicon.ico$', views.favicon_view),
    re_path(r'^google\d.*?\.html$', views.google_verification_view),
    re_path(r'^googlebot_site_map/', include(('googlebot_site_map.urls', 'googlebot_site_map'), namespace="googlebot_site_map")),
    re_path(r'^robots.txt$', views.robots_view),
    re_path(r'^app-ads.txt$', views.app_ads_view),
    re_path(r'^admin/', include(('admin_tools.urls', 'admin_tools'), namespace="admin_tools")),
    re_path(r'^apis/v1/', include(('apis_v1.urls', 'apis_v1'), namespace="apis_v1")),

    re_path(r'^a/', include(('analytics.urls','analytics'), namespace="analytics")),
    re_path(r'^b/', include(('ballot.urls','ballot'), namespace="ballot")),
    re_path(r'^ballotpedia/', include(('import_export_ballotpedia.urls', 'ballotpedia'), namespace="ballotpedia")),
    re_path(r'^bookmark/', include(('bookmark.urls', 'bookmark'), namespace="bookmark")),
    re_path(r'^c/', include(('candidate.urls', 'candidate'), namespace="candidate")),
    re_path(r'^campaign/', include(('campaign.urls', 'campaign'), namespace="campaign")),
    re_path(r'^e/', include(('election.urls', 'election'), namespace="election")),
    re_path(r'^office_held/', include(('office_held.urls', 'office_held'), namespace="office_held")),
    re_path(r'^representative_list/', include(('representative.urls', 'representative_list'), namespace="representative_list")),
    re_path(r'^representative/', include(('representative.urls', 'representative'), namespace="representative")),
    re_path(r'^electoral_district/', include(('electoral_district.urls', 'electoral_district'), namespace="electoral_district")),
    re_path(r'^follow/', include(('follow.urls', 'follow'), namespace="follow")),
    re_path(r'^friend/', include(('friend.urls', 'friend'), namespace="friend")),
    re_path(r'^google_custom_search/', include(('google_custom_search.urls', 'google_custom_search'), namespace="google_custom_search")),
    re_path(r'^health/', views.health_view),  # A simple health check to make sure the site is running
    re_path(r'^image/', include(('image.urls', 'image'), namespace="image")),
    re_path(r'^import_export_batches/', include(('import_export_batches.urls', 'import_export_batches'), namespace="import_export_batches")),
    re_path(r'^import_export_ctcl/', include(('import_export_ctcl.urls', 'import_export_ctcl'), namespace="import_export_ctcl")),
    re_path(r'^import_export_facebook/', include(('import_export_facebook.urls', 'import_export_facebook'), namespace="import_export_facebook")),
    re_path(r'^import_export_google_civic/', include((
        'import_export_google_civic.urls','import_export_google_civic'), namespace="import_export_google_civic")),
    re_path(r'^import_export_maplight/', include(('import_export_maplight.urls', 'import_export_maplight'), namespace="import_export_maplight")),
    re_path(r'^import_export_twitter/', include(('import_export_twitter.urls', 'import_export_twitter'), namespace="import_export_twitter")),
    re_path(r'^import_export_vote_smart/', include(('import_export_vote_smart.urls', 'import_export_vote_smart'), namespace="import_export_vote_smart")),
    re_path(r'^import_export_wikipedia/', include(('import_export_wikipedia.urls', 'import_export_wikipedia'), namespace="import_export_wikipedia")),
    re_path(r'^import_export_endorsements/', include((
        'import_export_endorsements.urls','import_export_endorsements'), namespace="import_export_endorsements")),
    re_path(r'^info/', include(('quick_info.urls', 'quick_info'), namespace="quick_info")),
    re_path(r'^issue/', include(('issue.urls', 'issue'), namespace="issue")),
    re_path(r'^m/', include(('measure.urls', 'measure'), namespace="measure")),
    re_path(r'^off/', include(('office.urls', 'office'), namespace="office")),
    re_path(r'^org/', include(('organization.urls', 'organization'), namespace="organization")),
    re_path(r'^organization_plans/', include(('donate.urls', 'organization_plans'), namespace="organization_plans")),
    re_path(r'^pl/', include(('polling_location.urls', 'polling_location'), namespace="polling_location")),
    re_path(r'^party/', include(('party.urls', 'party'), namespace="party")),
    re_path(r'^politician_list/', include(('politician.urls', 'politician_list'), namespace="politician_list")),
    re_path(r'^politician/', include(('politician.urls', 'politician'), namespace="politician")),
    re_path(r'^pos/', include(('position.urls', 'position'), namespace="position")),
    re_path(r'^retrieve_tables/', include(('retrieve_tables.urls', 'retrieve_tables'), namespace="retrieve_tables")),
    # re_path(r'^scheduled_tasks/', include(('scheduled_tasks.urls', 'scheduled_tasks'), namespace="scheduled_tasks")),
    re_path(r'^share/', include(('share.urls', 'share'), namespace="share")),
    re_path(r'^sod/', include(('support_oppose_deciding.urls', 'support_oppose_deciding'), namespace="support_oppose_deciding")),
    re_path(r'^stripe_donations/', include(('stripe_donations.urls', 'stripe'), namespace="stripe_donations")),
    re_path(r'^tag/', include(('tag.urls', 'tag'), namespace="tag")),
    re_path(r'^twitter/', include(('import_export_twitter.urls', 'twitter'), namespace="twitter")),
    re_path(r'^twitter2/', include(('twitter.urls', 'twitter2'), namespace="twitter2")),
    re_path(r'^volunteer/', include(('volunteer_task.urls', 'volunteer'), namespace="volunteer_task")),
    re_path(r'^voter/', include(('voter.urls', 'voter'), namespace="voter")),
    re_path(r'^vg/', include(('voter_guide.urls', 'voter_guide'), namespace="voter_guide")),
    # Authentication
    # re_path(r'^login/$', auth_views.login, name="login"),
    re_path(r'^login/$', login_we_vote, name="login"),
    re_path(r'^logout/$', auth_views.auth_logout, name="logout"),
    re_path(r'^login_we_vote/$', login_we_vote, name="login_we_vote"),
    re_path(r'^logout_we_vote/$', logout_we_vote, name="logout_we_vote"),
    # This line provides the following patterns:
    # login, logout, password_reset, password_reset_done, password_reset_confirm, password_reset_complete
    re_path('', include(('social_django.urls', 'social'), namespace="social")),
    # socialcomplete/facebook - See wevote_social/utils.py
]

# Execute start-up.
startup.run()
