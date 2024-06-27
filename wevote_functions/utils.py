import os
import re
import urllib.request
from datetime import datetime, date

from django.db import connection
from django.utils.timezone import localtime


def staticUserAgent():
    # Updated March 26, 2024
    user_agent_chrome = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/123.0.0.0 Safari/537.36")
    headers = { 'User-Agent': user_agent_chrome }
    return headers


def scrape_url(site_url, with_soup=True):
    all_html_found = False
    all_html = []
    status = ''
    success = True
    try:
        request = urllib.request.Request(site_url, None, staticUserAgent())
        page = urllib.request.urlopen(request, timeout=5)
        all_html_raw = page.read()
        all_html = all_html_raw.decode("utf8")
        all_html_found = True
        page.close()

        if with_soup:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(all_html, "html.parser")
            soup.find('head').decompose()  # find head tag and decompose/destroy it from the html
            all_html = soup.get_text()

    except Exception as e:
        status = "SCRAPE_URL_ERROR: ", e
        success = False

    return {
        'all_html': all_html,
        'all_html_found': all_html_found,
        'status': status,
        'success': success,
    }


def get_git_commit_date():
    scrape_res = scrape_url(get_git_commit_hash(True), False)
    try:
        reg = re.search(r"<relative-time datetime=\"(.*?)\"", scrape_res['all_html'])
        date_string = "Not found"
        if date and reg.group(1):
            dt = reg.group(1)
            utc_time = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S%z')            # 2024-03-04T21:58:40Z
            date_string = localtime(utc_time).strftime("%m/%d/%Y %H:%M")
        return date_string
    except Exception as e:
        return 'Not found: ' + str(e)


def get_python_version():
    version = os.popen('python --version').read().strip().replace('Python', '')
    print('Python version: ' + version)    # Something like 'Python 3.7.2'
    return version


def get_node_version():
    # Node is not installed on production API/Python servers
    raw = os.popen('node -v').read().replace('\n', '').strip()
    version = 'Node not installed on this server'
    if len(raw) > 0:
        version = os.popen('node -v').read().replace('\n', '').strip()
    print('Node version: ' + version)    # Something like 'v14.15.1'
    return version


def get_git_commit_hash(full):
    try:
        file1 = open('git_commit_hash', 'r')
        hash = file1.readline().strip()
    except:
        hash = 'git_commit_hash-file-not-found'
    if full:
        return "https://github.com/wevote/WeVoteServer/commit/" + hash
    return hash


def get_postgres_version():
    formatted = 'fail'
    try:
        version = str(connection.cursor().connection.server_version)
        version = ' ' + version if len(version) == 5 else version
        formatted = version[0:2] + '.' + version[2:4] + '.' + version[4:6]
    except Exception as e:
        print(e)
        pass
    print('Postgres version: ', formatted)
    return formatted
