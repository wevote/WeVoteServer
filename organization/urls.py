# organization/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^(?P<organization_id>[0-9]+)/edit/$', views.organization_edit_view, name='organization_edit'),
    url(r'^edit_process/$', views.organization_edit_process_view, name='organization_edit_process'),
    url(r'^$', views.organization_list_view, name='organization_list',),
    url(r'^edit/$', views.organization_new_view, name='organization_new'),
    url(r'^(?P<organization_id>[0-9]+)/pos/$', views.organization_position_list_view,
        name='organization_position_list',),
    url(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_id>[0-9]+)/delete/$',
        views.organization_delete_existing_position_process_form_view,
        name='organization_position_delete',),
    url(r'^(?P<organization_id>[0-9]+)/pos/(?P<position_id>[0-9]+)/$',
        views.organization_edit_existing_position_form_view,
        name='organization_position_edit',),
    url(r'^(?P<organization_id>[0-9]+)/pos/new/$', views.organization_add_new_position_form_view,
        name='organization_position_new',),
    url(r'^pos/edit_process/$', views.organization_save_new_or_edit_existing_position_process_form_view,
        name='organization_position_edit_process'),

    # This is used for a voter to follow an organization
    url(r'^(?P<organization_id>[0-9]+)/follow/$', views.organization_follow_view,
        name='organization_follow_view',),
    # This is used for a voter to unfollow an organization
    url(r'^(?P<organization_id>[0-9]+)/unfollow/$', views.organization_unfollow_view,
        name='organization_unfollow_view',),
]
