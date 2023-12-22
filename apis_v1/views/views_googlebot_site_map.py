# apis_v1/views/views_googlebot_site_map.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from googlebot_site_map.views_admin import get_googlebot_map_file_body
from politician.models import Politician

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


# To test XML queries from Chrome I recommend the "Tabbed Postman - REST Client
# https://chromewebstore.google.com/detail/tabbed-postman-rest-clien/coohjcphdfgbiolnekdpbcijmhambjff?hl=en-US&utm_source=ext_sidebar
# Add a header "content-type" "application/xml", put in the URL and press Send
# My test url is https://localhost:8000/apis/v1/googlebotSiteMap/sitemap_index.xml
def xml_for_n_maps(n):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for i in range(n):
        xml += '  <sitemap>'
        xml += '    <loc>https://wevotedeveloper.com:8000/apis/v1/googlebotSiteMap/map%s.html</loc>' % i
        xml += '  </sitemap>'
    xml += '</sitemapindex>'
    return xml


def get_sitemap_index_xml(request):
    politician_count = Politician.objects.using('readonly').all().count()
    # print('politician count    ', politician_count)

    float_n = politician_count / 40000
    if float_n < 1:
        n = 1
    else:
        n = int(float_n) + 1

    xml = xml_for_n_maps(n)

    return HttpResponse(xml)


def get_sitemap_text_file(request):
    print(request)
    html = "<html><body>"
    html += get_googlebot_map_file_body(request)
    html += "</html></body><br>"
    return HttpResponse(html)
