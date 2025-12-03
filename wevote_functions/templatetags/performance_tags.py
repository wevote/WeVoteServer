# wevote_functions/templatetags/performance_tags.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django import template

register = template.Library()

@register.filter
def performance_total(performance_dict):
    total = 0
    for time in performance_dict:
        # Don't include sub-snapshots (nested snapshots) in the total
        name = time.get('name', '') if isinstance(time, dict) else getattr(time, 'name', '')
        if isinstance(name, str) and 'subsnapshot' in name.lower():
            continue
        time_diff = time.get('time_difference') if isinstance(time, dict) else getattr(time, 'time_difference', 0)
        if time_diff:
            total += time_diff
    return total
