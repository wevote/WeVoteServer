# apis_v1/views/views_representative.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from representative.controllers import representatives_query_for_api
from config.base import get_environment_variable
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def representatives_query_view(request):  # representativesQuery
    index_start = request.GET.get('index_start', 0)
    limit_to_this_state_code = request.GET.get('state', '')
    race_office_level_list = request.GET.getlist('race_office_level[]', False)
    search_text = request.GET.get('search_text', '')
    year = request.GET.get('year', '')
    return representatives_query_for_api(
        index_start=index_start,
        limit_to_this_state_code=limit_to_this_state_code,
        race_office_level_list=race_office_level_list,
        search_text=search_text,
        year=year)
