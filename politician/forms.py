# politician/forms.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _, ugettext
from django.contrib.auth.models import User

from politician.models import Politician, PoliticianTagLink
from tag.models import Tag
