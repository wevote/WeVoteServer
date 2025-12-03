# politician/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-


def is_tag_valid(new_tag):
    if not bool(new_tag.strip()):  # If this doesn't evaluate true here, then it is empty and isn't valid
        return False
    return True
