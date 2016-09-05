# apis_v1/templatetags/template_filters.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# Note: These template_filters can be used in any template

from django import template
from wevote_functions import functions

register = template.Library()


@register.filter(name="convert_to_int")
def convert_to_int(value):
    return functions.convert_to_int(value)


@register.filter(name="get_value_from_dict")
def get_value_from_dict(dict_variable, dict_key):
    return dict_variable[dict_key]
