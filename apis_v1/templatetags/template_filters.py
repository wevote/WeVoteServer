# apis_v1/templatetags/template_filters.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# Note: These template_filters can be used in any template

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

from wevote_functions import functions

register = template.Library()


@register.filter(name="convert_to_int")
def convert_to_int(value):
    return functions.convert_to_int(value)


@register.filter(name="get_value_from_dict")
def get_value_from_dict(dict_variable, dict_key):
    return dict_variable[dict_key]


@register.filter(name="get_list_from_dict")
def get_list_from_dict(dict_variable, dict_key):
    try:
        return dict_variable[dict_key]
    except Exception as e:
        return []

@register.filter
def pennies_to_money(number):
    number_string = str(number)
    rest = number_string[:-2]
    is_neg = rest[0] == '-'
    result = '-$' if is_neg else '$'
    result += intcomma(rest[1:]) if is_neg else intcomma(rest)
    result += '.' + number_string[-2:]
    return result
