# googlebot_site_map/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import datetime
import re
import subprocess

import pytz
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from googlebot_site_map import supplemental_urls
from googlebot_site_map.models import GooglebotRequest
from politician.models import Politician
from voter.models import voter_has_authority
from wevote_functions.functions import get_ip_from_headers, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

def log_request(request):
    ip = get_ip_from_headers(request)
    user_agent = request.META['HTTP_USER_AGENT']
    host = googlebot_reverse_dns(ip)
    path = request.path
    url_bits = path.split('/')
    request_url_type = '/' + url_bits[-1]

    is_from_google = "googlebot.com" in host or "google.com" in host or \
                     "googleusercontent.com" in host

    obj = GooglebotRequest.objects.create(
        request_url_type=request_url_type,
        remote_address=ip,
        remote_dns=host,
        is_from_google=is_from_google,
        user_agent=user_agent
    )


def googlebot_reverse_dns(ip):
    host = 'localhost'
    # ip = '66.249.66.9'
    if ip != '127.0.0.1':
        run_cmd = 'host ' + ip
        process = subprocess.run([run_cmd], shell=True, stdout=subprocess.PIPE)
        output_raw = process.stdout
        host = output_raw.decode("utf-8")
        if positive_value_exists(host):
            host = host.replace('\n', '')

    logger.error('Not an error: host ip: ' + ip + ', raw output from host cmd: ' + host)

    return host


# https://localhost:8000/apis/v1/googlebotSiteMap/sitemap_index.xml
def get_googlebot_map_file_body(request):
    map_num_result = re.findall(r'googlebotSiteMap\/map(\d+)', request.path)
    num = int(map_num_result[0])
    https_root = "https://wevote.us/"
    map_text = ''
    queryset = Politician.objects.using('readonly').order_by('id').filter(id__range=(num * 40000, (num + 1) * 40000))
    politician_list = list(queryset)
    if num == 0:
        for u in supplemental_urls.crawlable_urls:
            map_text += u + '<br>'
    for pol in politician_list:
        map_text += https_root + pol.seo_friendly_path + '/-/<br>'

    return map_text


def xml_chunk(loc, lastmod):
    chunk = '  <url>\n'
    chunk += '    <loc>' + loc + '</loc>\n'
    chunk += '    <lastmod>' + lastmod + '</lastmod>\n'
    chunk += '  </url>\n'

    return chunk


def get_googlebot_map_xml_body(request):
    map_num_result = re.findall(r'googlebotSiteMap\/map(\d+)', request.path)
    num = int(map_num_result[0])
    https_root = "https://wevote.us/"
    dt = datetime.date.today()
    lastmod = dt.strftime("%Y-%m-%d")
    map_xml = ''
    queryset = Politician.objects.using('readonly').order_by('id').filter(id__range=(num * 40000, (num + 1) * 40000))
    politician_list = list(queryset)
    if num == 0:
        for loc in supplemental_urls.crawlable_urls:
            map_xml += xml_chunk(loc, lastmod)
    for pol in politician_list:
        map_xml += xml_chunk(https_root + pol.seo_friendly_path + "/-/", lastmod)

    return map_xml


@login_required
def googlebot_site_map_list_view(request):
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    query = GooglebotRequest.objects.all().order_by('-date_requested')
    date = datetime.datetime.now(tz=datetime.timezone.utc)
    start_date = date - datetime.timedelta(days=365/2)
    query = query.filter(date_requested__gte=start_date)

    request_list = list(query)
    for req in request_list:
        # Convert non-naive datetime in GMT to PST
        date_pst = req.date_requested.astimezone(pytz.timezone('US/Pacific'))
        ds = date_pst.strftime('%m/%d/%Y  %I:%M:%S %p')
        new_date = ds[0:20] + ds[28:]
        req.date_requested = new_date

    dates, counts_google_xml, counts_google_map, counts_other_xml, counts_other_map = fetch_graph_data()

    template_values = {
        'request_list':         request_list,
        'dates':                dates,
        'counts_google_xml':    counts_google_xml,
        'counts_google_map':    counts_google_map,
        'counts_other_xml':     counts_other_xml,
        'counts_other_map':     counts_other_map,
        # 'request_details':      format_prepared_request(request),
    }
    return render(request, 'googlebot_stats/googlebot_stats.html', template_values)

def fetch_graph_data():
    dates = []
    # counts_all = []
    counts_google_xml = [0 for i in range(90)]
    counts_google_map = [0 for i in range(90)]
    counts_other_xml = [0 for i in range(90)]
    counts_other_map = [0 for i in range(90)]

    date = datetime.datetime.now(tz=datetime.timezone.utc)
    for i in range(90):
        ds = date.strftime('%m/%d/%Y')
        dates.append(ds)
        date -= datetime.timedelta(days=1)

    start_date = date - datetime.timedelta(days=90)
    query = GooglebotRequest.objects.all()
    query = query.filter(date_requested__gte=start_date)
    request_list = list(query)
    for req in request_list:
        req_date_string = req.date_requested.strftime('%m/%d/%Y')
        try:
            offset = dates.index(req_date_string)
            if req.is_from_google:
                if 'sitemap_index.xml' in req.request_url_type:
                    counts_google_xml[offset] += 1
                else:
                    counts_google_map[offset] += 1
            elif 'sitemap_index.xml' in req.request_url_type:
                counts_other_xml[offset] += 1
            else:
                counts_other_map[offset] += 1
        except ValueError:
            # Exception is thrown for dates prior to the range of the dates list
            pass

    return dates, counts_google_xml, counts_google_map, counts_other_xml, counts_other_map