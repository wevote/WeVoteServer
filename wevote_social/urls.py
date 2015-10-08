from django.conf.urls import url

from wevote_social import views

urlpatterns = [
    url(r'^login/$', views.login_view, name='login'),
]
