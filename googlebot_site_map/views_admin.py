# googlebot_site_map/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import re

import wevote_functions.admin
from politician.models import Politician

logger = wevote_functions.admin.get_logger(__name__)

def get_googlebot_map_file_body(request):
    print(request.META['HTTP_USER_AGENT'])
    map_num_result = re.findall(r'googlebotSiteMap\/map(\d+)', request.path)
    num = int(map_num_result[0])
    https_root = "https://wevote.us/"
    map_text = ''
    queryset = Politician.objects.using('readonly').order_by('id').filter(id__range=(num * 40000, (num + 1) * 40000))
    politician_list = list(queryset)
    for pol in politician_list:
        map_text += https_root + pol.seo_friendly_path + '/-<br>'

    return map_text
