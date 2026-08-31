# apis_v1/templatetags/template_filters.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# Note: These template_filters can be used in any template

from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.defaultfilters import _property_resolver

from wevote_functions import functions, functions_date
from wevote_functions.functions import positive_value_exists

register = template.Library()


@register.filter(name="convert_to_int")
def convert_to_int(value):
    return functions.convert_to_int(value)


@register.filter(name="display_nothing_if_zero")
def display_nothing_if_zero(value):
    value_integer = functions.convert_to_int(value)
    if functions.positive_value_exists(value_integer):
        return value
    return ''


@register.filter(name="get_date_from_date_as_integer")
def get_date_from_date_as_integer(value):
    value_integer = functions.convert_to_int(value)
    if functions.positive_value_exists(value_integer):
        return functions_date.convert_date_as_integer_to_date(value_integer)
    return value


@register.filter(name="get_value_from_dict")
def get_value_from_dict(dictionary, key):
    return dictionary.get(key, '')


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


@register.filter(name="dictsort_none_safe")
def dictsort_none_safe(value, arg, reverse_date_order):
    """
    Like Django's built-in dictsort, but treats a null (None) sort field as an
    empty string instead of returning "" for the whole list. Works on both dict
    keys and object attributes. On any other failure, returns the list unsorted.
    """
    resolver = _property_resolver(arg)
    reverse_sort = positive_value_exists(reverse_date_order)

    def sort_key(item):
        resolved = resolver(item)
        # None sorts before any real value, and never gets compared to a str.
        return (resolved is None, resolved if resolved is not None else "")

    try:
        return sorted(value, key=sort_key, reverse=reverse_sort)
    except (AttributeError, TypeError):
        return value


@register.filter(name="sort_election_list_for_dropdown")
def sort_election_list_for_dropdown(election_list, reverse_date_order=False):
    """
    When show_all_elections is True, sort by election_day_text descending (newest
    first). Otherwise use the default state_code, then election_day_text ordering.
    Both paths are null-safe.
    """
    return dictsort_none_safe(
        dictsort_none_safe(election_list, "state_code", False),
        "election_day_text", reverse_date_order)
