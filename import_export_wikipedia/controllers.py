# import_export_wikipedia/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from organization.models import Organization
import re
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists
import wikipedia

logger = wevote_functions.admin.get_logger(__name__)

# VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
# VOTE_SMART_API_URL = get_environment_variable("VOTE_SMART_API_URL")


def retrieve_organization_logo_from_wikipedia(organization, force_retrieve=False):
    status = ""
    values_changed = False
    wikipedia_page_id = 0
    wikipedia_page_title = ''

    if not organization:
        status += 'WIKIPEDIA_ORGANIZATION_REQUIRED '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if not positive_value_exists(organization.id):
        status += 'WIKIPEDIA_ORGANIZATION_ID_REQUIRED '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    # Have we already retrieved a Wikipedia photo?
    if positive_value_exists(organization.wikipedia_photo_url) and not force_retrieve:
        status += 'WIKIPEDIA_ORGANIZATION_PHOTO_ALREADY_RETRIEVED-NO_FORCE '
        results = {
            'success':                      True,
            'status':                       status,
        }
        return results

    if positive_value_exists(organization.wikipedia_page_id):
        wikipedia_page_id = organization.wikipedia_page_id
    elif positive_value_exists(organization.wikipedia_page_title):
        wikipedia_page_title = organization.wikipedia_page_title
    elif positive_value_exists(organization.organization_name):
        wikipedia_page_title = organization.organization_name

    if positive_value_exists(wikipedia_page_id) or positive_value_exists(wikipedia_page_title):
        try:
            auto_suggest = False  # If the literal string isn't found, don't try another page
            redirect = False  # I changed this from the default (True), but redirect might be ok
            preload = False
            if wikipedia_page_id:
                wikipedia_page = wikipedia.page(None, wikipedia_page_id, auto_suggest, redirect, preload)
            elif wikipedia_page_title:
                wikipedia_page_id = 0
                wikipedia_page = wikipedia.page(wikipedia_page_title,
                                                wikipedia_page_id, auto_suggest, redirect, preload)
        except wikipedia.PageError:
            # Page does not exist
            status += 'WIKIPEDIA_PAGE_ERROR '
            results = {
                'success':                  False,
                'status':                   status,
            }
            return results
        except wikipedia.RedirectError:
            # When does a page redirect affect us negatively?
            status += 'WIKIPEDIA_REDIRECT_ERROR '
            results = {
                'success':                  False,
                'status':                   status,
            }
            return results
        except wikipedia.DisambiguationError:
            # There are a few possible pages this might refer to
            status += 'WIKIPEDIA_DISAMBIGUATION_ERROR '
            results = {
                'success':                  False,
                'status':                   status,
            }
            return results

        if positive_value_exists(wikipedia_page.pageid):
            if not (organization.wikipedia_page_id == wikipedia_page.pageid):
                organization.wikipedia_page_id = wikipedia_page.pageid
                values_changed = True
        if wikipedia_page.title:
            if not (organization.wikipedia_page_title == wikipedia_page.title):
                organization.wikipedia_page_title = wikipedia_page.title
                values_changed = True
        if wikipedia_page.images and len(wikipedia_page.images):
            for one_image in wikipedia_page.images:
                # We might want to cycle through these images a few times and give points for
                # "the most likely to be the logo", but for now, we choose the first image that matches this criteria
                if re.search('commons-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo
                    pass
                elif re.search('logo', one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_LOGO_IN_NAME '
                    organization.wikipedia_photo_url = one_image
                    values_changed = True
                    break

    if values_changed:
        organization.save()

    results = {
        'success':                      True,
        'status':                       status,
    }
    return results


def retrieve_all_organizations_logos_from_wikipedia():
    organization_list = Organization.objects.order_by('organization_name')
    for organization in organization_list:
        organization_results = retrieve_organization_logo_from_wikipedia(organization)
    status = "ORGANIZATION_LOGOS_RETRIEVED"
    results = {
        'success':                      True,
        'status':                       status,
    }
    return results

# OLDER Method that connects directly with Wikipedia API
# def retrieve_organization_logos_from_wikipedia(self, force_retrieve=False):
#     WIKIPEDIA_API_URL = "https://en.wikipedia.org//w/api.php"
#     wikipedia_thumbnail_url = None
#     wikipedia_thumbnail_width = 0
#     wikipedia_thumbnail_height = 0
#     wikipedia_photo_url = None
#     wikipedia_page_title = None
#
#     if (not positive_value_exists(self.wikipedia_thumbnail_url)) or force_retrieve:
#         # Retrieve the thumbnail photo
#         if positive_value_exists(self.wikipedia_page_title):
#             wikipedia_page_title = self.wikipedia_page_title
#         elif positive_value_exists(self.organization_name):
#             wikipedia_page_title = self.organization_name
#
#         if wikipedia_page_title:
#             request = requests.get(WIKIPEDIA_API_URL, params={
#                 "action": "query",
#                 "prop": "pageimages",
#                 "format": "json",
#                 "piprop": "thumbnail",  # "original"
#                 "titles": wikipedia_page_title,
#             })
#
#             structured_json = json.loads(request.text)
#             if "query" in structured_json:
#                 if "pages" in structured_json['query']:
#                     for one_page_index in structured_json['query']['pages']:
#                         one_page_structured_json = structured_json['query']['pages'][one_page_index]
#                         if "thumbnail" in one_page_structured_json:
#                             if "source" in one_page_structured_json['thumbnail']:
#                                 wikipedia_thumbnail_url = one_page_structured_json['thumbnail']['source']
#                                 wikipedia_thumbnail_width = one_page_structured_json['thumbnail']['width']
#                                 wikipedia_thumbnail_height = one_page_structured_json['thumbnail']['height']
#                                 break
#                         if "title" in one_page_structured_json:
#                             if positive_value_exists(one_page_structured_json['title']):
#                                 wikipedia_page_title_normalized = one_page_structured_json['title']
#                                 wikipedia_page_title = wikipedia_page_title_normalized
#
#     if (not positive_value_exists(self.wikipedia_photo_url)) or positive_value_exists(wikipedia_page_title) \
#             or force_retrieve:
#         # Retrieve the full-size photo
#         if positive_value_exists(wikipedia_page_title):
#             pass
#         elif positive_value_exists(self.wikipedia_page_title):
#             wikipedia_page_title = self.wikipedia_page_title
#         elif positive_value_exists(self.organization_name):
#             wikipedia_page_title = self.organization_name
#
#         if wikipedia_page_title:
#             request = requests.get(WIKIPEDIA_API_URL, params={
#                 "action": "query",
#                 "prop": "pageimages",
#                 "format": "json",
#                 "piprop": "original",
#                 "titles": wikipedia_page_title,
#             })
#
#             structured_json = json.loads(request.text)
#             if "query" in structured_json:
#                 if "pages" in structured_json['query']:
#                     for one_page_index in structured_json['query']['pages']:
#                         one_page_structured_json = structured_json['query']['pages'][one_page_index]
#                         if "thumbnail" in one_page_structured_json:
#                             if "original" in one_page_structured_json['thumbnail']:
#                                 wikipedia_photo_url = one_page_structured_json['thumbnail']['original']
#                                 break
#                         if "title" in one_page_structured_json:
#                             if positive_value_exists(one_page_structured_json['title']):
#                                 wikipedia_page_title_normalized = one_page_structured_json['title']
#                                 wikipedia_page_title = wikipedia_page_title_normalized
#     if positive_value_exists(wikipedia_thumbnail_url):
#         self.wikipedia_thumbnail_url = wikipedia_thumbnail_url
#     if positive_value_exists(wikipedia_thumbnail_width):
#         self.wikipedia_thumbnail_width = wikipedia_thumbnail_width
#     if positive_value_exists(wikipedia_thumbnail_height):
#         self.wikipedia_thumbnail_height = wikipedia_thumbnail_height
#     if positive_value_exists(wikipedia_photo_url):
#         self.wikipedia_photo_url = wikipedia_photo_url
#     if positive_value_exists(wikipedia_page_title):
#         self.wikipedia_page_title = wikipedia_page_title
#
#     self.save()
#
#     # if not data_found:
#     #     messages.add_message(
#     #         request, messages.INFO,
#     #         "No photo information was found.")
#     return

# /w/api.php?action=query&prop=pageimages&format=json&piprop=original&titles=Academy_of_General_Dentistry
# {
#     "batchcomplete": "",
#     "query": {
#         "normalized": [
#             {
#                 "from": "Academy_of_General_Dentistry",
#                 "to": "Academy of General Dentistry"
#             }
#         ],
#         "pages": {
#             "6061933": {
#                 "pageid": 6061933,
#                 "ns": 0,
#                 "title": "Academy of General Dentistry",
#                 "thumbnail": {
#                     "original": "https://upload.wikimedia.org/wikipedia/en/3/37/Academy_of_General_Dentistry_Logo.gif"
#                 }
#             }
#         }
#     }
# }
#
# /w/api.php?action=query&prop=pageimages&format=json&piprop=thumbnail&titles=Academy_of_General_Dentistry
# {
#     "batchcomplete": "",
#     "query": {
#         "normalized": [
#             {
#                 "from": "Academy_of_General_Dentistry",
#                 "to": "Academy of General Dentistry"
#             }
#         ],
#         "pages": {
#             "6061933": {
#                 "pageid": 6061933,
#                 "ns": 0,
#                 "title": "Academy of General Dentistry",
#                 "thumbnail": {
#                     "source": "https://upload.wikimedia.org/wikipedia/en/thumb/3/37/Academy_of_General_Dentistry_Logo.gif/50px-Academy_of_General_Dentistry_Logo.gif",
#                     "width": 50,
#                     "height": 50
#                 }
#             }
#         }
#     }
# }
