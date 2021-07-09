# stripe_donations/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.conf.urls import url

from . import views_admin


urlpatterns = [
    url(r'^plan_list/$', views_admin.organization_subscription_list_view, name='plan_list'),
]
