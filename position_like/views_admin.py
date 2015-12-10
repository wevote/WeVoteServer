# position_like/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# from .models import PositionLike
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


# NOTE: @login_required() throws an error. Needs to be figured out if we ever want to secure this page.
def export_position_like_data_view():
    pass
