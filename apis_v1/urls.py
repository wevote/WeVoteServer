# apis_v1/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
"""
This is called from config/urls.py like this:
    url(r'^apis/v1/', include('apis_v1.urls', namespace="apis_v1")),
"""

from django.conf.urls import url
from . import views
from . import views_docs

urlpatterns = [
    url(r'^candidatesRetrieve/', views.candidates_retrieve_view, name='candidatesRetrieveView'),
    url(r'^deviceIdGenerate/$', views.device_id_generate_view, name='deviceIdGenerateView'),
    url(r'^organizationCount/', views.organization_count_view, name='organizationCountView'),
    url(r'^organizationFollow/', views.organization_follow_api_view, name='organizationFollowView'),
    url(r'^organizationFollowIgnore/', views.organization_follow_ignore_api_view, name='organizationFollowIgnoreView'),
    url(r'^organizationRetrieve/', views.organization_retrieve_view, name='organizationRetrieveView'),
    url(r'^organizationStopFollowing/', views.organization_stop_following_api_view, name='organizationStopFollowingView'),
    url(r'^voterAddressRetrieve/', views.voter_address_retrieve_view, name='voterAddressRetrieveView'),
    url(r'^voterAddressSave/', views.voter_address_save_view, name='voterAddressSaveView'),
    url(r'^voterBallotItemsRetrieve/', views.voter_ballot_items_retrieve_view, name='voterBallotItemsRetrieveView'),
    url(r'^voterCount/', views.voter_count_view, name='voterCountView'),
    url(r'^voterCreate/', views.voter_create_view, name='voterCreateView'),
    url(r'^voterGuidesToFollowRetrieve/',
        views.voter_guides_to_follow_retrieve_view, name='voterGuidesToFollowRetrieveView'),
    url(r'^voterRetrieve/', views.VoterRetrieveView.as_view(), name='voterRetrieveView'),

    url(r'^docs/$', views_docs.apis_index_doc_view, name='apisIndex'),
    url(r'^docs/candidatesRetrieve/$', views_docs.candidates_retrieve_doc_view, name='candidatesRetrieveDocs'),
    url(r'^docs/deviceIdGenerate/$', views_docs.device_id_generate_doc_view, name='deviceIdGenerateDocs'),
    url(r'^docs/organizationCount/$', views_docs.organization_count_doc_view, name='organizationCountDocs'),
    url(r'^docs/organizationFollow/', views_docs.organization_follow_doc_view, name='organizationFollowDocs'),
    url(r'^docs/organizationFollowIgnore/',
        views_docs.organization_follow_ignore_doc_view, name='organizationFollowIgnoreDocs'),
    url(r'^docs/organizationRetrieve/$', views_docs.organization_retrieve_doc_view, name='organizationRetrieveDocs'),
    url(r'^docs/organizationStopFollowing/',
        views_docs.organization_stop_following_doc_view, name='organizationStopFollowingDocs'),
    url(r'^docs/voterAddressRetrieve/$', views_docs.voter_address_retrieve_doc_view, name='voterAddressRetrieveDocs'),
    url(r'^docs/voterAddressSave/$', views_docs.voter_address_save_doc_view, name='voterAddressSaveDocs'),
    url(r'^docs/voterBallotItemsRetrieve/$',
        views_docs.voter_ballot_items_retrieve_doc_view, name='voterBallotItemsRetrieveDocs'),
    url(r'^docs/voterCount/$', views_docs.voter_count_doc_view, name='voterCountDocs'),
    url(r'^docs/voterCreate/$', views_docs.voter_create_doc_view, name='voterCreateDocs'),
    url(r'^docs/voterGuidesToFollowRetrieve/$',
        views_docs.voter_guides_to_follow_retrieve_doc_view, name='voterGuidesToFollowRetrieveDocs'),
    url(r'^docs/voterRetrieve/$', views_docs.voter_retrieve_doc_view, name='voterRetrieveDocs'),
]
