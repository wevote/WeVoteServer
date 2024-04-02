# donate/urls.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import path

from . import views_admin


urlpatterns = [
    path('plan_list/', views_admin.organization_subscription_list_view, name='plan_list'),
]
