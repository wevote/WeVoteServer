# apis_v1/views/views_googlebot_site_map.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse

import wevote_functions.admin
from config.base import get_environment_variable
from googlebot_site_map.views_admin import log_request, get_googlebot_map_file_body, get_googlebot_map_xml_body
from politician.models import Politician

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


# To test XML queries from Chrome try the "Tabbed Postman - REST Client"
# https://chromewebstore.google.com/detail/tabbed-postman-rest-clien/coohjcphdfgbiolnekdpbcijmhambjff?hl=en-US&utm_source=ext_sidebar
# Add a header "content-type" "application/xml", put in the URL and press Send
# Test url is https://wevotedeveloper.com:8000/apis/v1/googlebotSiteMap/sitemap_index.xml
def xml_for_n_maps(n):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for i in range(n):
        xml += '  <sitemap>'
        xml += '    <loc>https://wevote.us/map%s.xml</loc>' % (i)
        xml += '  </sitemap>'
    xml += '</sitemapindex>'
    return xml

# Test url is https://wevotedeveloper.com:8000/apis/v1/googlebotSiteMap/map1.xml
def get_sitemap_index_xml(request):
    log_request(request)

    try:
        politician_count = Politician.objects.using('readonly').all().count()
        float_n = politician_count / 40000
        if float_n < 1:
            n = 1
        else:
            n = int(float_n) + 1

        xml = xml_for_n_maps(n)
    except Exception as e:
        logger.error('googlebot_site_map get_sitemap_index_xml threw ', e)
        xml = "error"

    return HttpResponse(xml)


def get_sitemap_text_file(request):
    log_request(request)

    # print(request)
    html = "<html><body>"
    try:
        html += get_googlebot_map_file_body(request)
    except Exception as e:
        logger.error('googlebost_site_map get_sitemap_text_file threw ', e)
    html += "</html></body><br>"
    return HttpResponse(html)


def get_sitemap_xml_file(request):
    log_request(request)

    # print(request)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    try:
        xml += get_googlebot_map_xml_body(request)
    except Exception as e:
        logger.error('get_sitemap_xml_file get_googlebot_map_xml_body threw ', e)
    xml += "</urlset>"
    return HttpResponse(xml)
