# campaign/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^$', views_admin.campaign_list_view, name='campaignx_list',),
    url(r'^(?P<campaignx_we_vote_id>wv[\w]{2}camp[\w]+)/edit$', views_admin.campaign_edit_view, name='campaignx_edit'),
    # url(r'^edit_process/$', views_admin.campaign_edit_process_view, name='campaignx_edit_process'),
]
