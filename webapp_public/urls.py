from django.conf.urls import patterns, url

from webapp_public.views import IndexView

urlpatterns = patterns(
    '',

    url('^.*$', IndexView.as_view(), name='index'),
)
