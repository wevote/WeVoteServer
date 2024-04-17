# import_export_wikipedia/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from organization.models import Organization
import re
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
import wikipedia  # https://pypi.python.org/pypi/wikipedia
from bs4 import BeautifulSoup

logger = wevote_functions.admin.get_logger(__name__)

# NOTE: There are other wrappers to the MediaWiki API that we can use to access Ballotpedia:
# https://www.mediawiki.org/wiki/API:Client_code#Python


def retrieve_wikipedia_page_from_wikipedia(organization, force_retrieve=False):
    status = ""
    success = False
    page_found = False
    wikipedia_page_id = 0
    wikipedia_page = False
    wikipedia_page_title = ''

    if not organization:
        status += 'WIKIPEDIA_ORGANIZATION_REQUIRED '
        results = {
            'success':              False,
            'status':               status,
            'wikipedia_page_found': False,
            'wikipedia_page':       wikipedia_page,
        }
        return results

    if not positive_value_exists(organization.id):
        status += 'WIKIPEDIA_ORGANIZATION_ID_REQUIRED '
        results = {
            'success':              False,
            'status':               status,
            'wikipedia_page_found': False,
            'wikipedia_page':       wikipedia_page,
        }
        return results

    if positive_value_exists(organization.wikipedia_page_id) and not force_retrieve:
        # Simply return the page without any investigation
        try:
            auto_suggest = False  # If the literal string isn't found, don't try another page
            redirect = False  # I changed this from the default (True), but redirect might be ok
            preload = False
            if wikipedia_page_id:
                wikipedia_page = wikipedia.page(None, wikipedia_page_id, auto_suggest, redirect, preload)
                page_found = True
            status += 'WIKIPEDIA_PAGE_FOUND_FROM_PAGEID '
        except wikipedia.PageError:
            # Page does not exist
            status += 'WIKIPEDIA_PAGE_ERROR_FROM_PAGEID '
            page_found = False
        except wikipedia.RedirectError:
            # When does a page redirect affect us negatively?
            status += 'WIKIPEDIA_REDIRECT_ERROR_FROM_PAGEID '
            page_found = False
        except wikipedia.DisambiguationError:
            # There are a few possible pages this might refer to
            status += 'WIKIPEDIA_DISAMBIGUATION_ERROR_FROM_PAGEID '
            page_found = False
        results = {
            'success':              False,
            'status':               status,
            'wikipedia_page_found': page_found,
            'wikipedia_page':       wikipedia_page,
        }
        return results

    wikipedia_page_title_guess2 = ''
    wikipedia_page_title_guess3 = ''
    wikipedia_page_title_guess4 = ''
    wikipedia_page_title_guess5 = ''
    wikipedia_page_title_guess6 = ''
    wikipedia_page_title_guess7 = ''
    wikipedia_page_title_guess8 = ''
    wikipedia_page_title_guess9 = ''
    wikipedia_page_title_guess10 = ''
    wikipedia_page_title_guess11 = ''
    wikipedia_page_title_guess12 = ''
    if positive_value_exists(organization.organization_name):
        wikipedia_page_title = organization.organization_name

        # Try it without the leading "The "
        if organization.organization_name.find("The ", 0, 4) == 0:
            wikipedia_page_title_guess2 = organization.organization_name[4:]

        # Try it replacing " and" with " &"
        insensitive_org_name_with_and = re.compile(re.escape(' and'), re.IGNORECASE)
        wikipedia_page_title_guess3 = insensitive_org_name_with_and.sub(' &', organization.organization_name)

        # Try it replacing " &" with " and"
        insensitive_org_name_with_ampersand = re.compile(re.escape(' &'), re.IGNORECASE)
        wikipedia_page_title_guess4 = insensitive_org_name_with_ampersand.sub(' and', organization.organization_name)

        # Try it without the " Action Fund"
        if organization.organization_name.endswith(' Action Fund'):
            wikipedia_page_title_guess5 = organization.organization_name[:-12]

        # Try it without any "the" words in the name
        insensitive_org_name_with_the = re.compile(re.escape('the '), re.IGNORECASE)
        wikipedia_page_title_guess6 = insensitive_org_name_with_the.sub('', organization.organization_name)

        # Try it with just the initials tacked on the end
        # ex/ American Federation of Labor and Congress of Industrial Organizations (AFL-CIO)
        parenthesis_start_index = organization.organization_name.find(" (")
        if positive_value_exists(parenthesis_start_index):
            parenthesis_end_index = organization.organization_name.find(")")
            if positive_value_exists(parenthesis_end_index):
                wikipedia_page_title_guess7 = \
                    organization.organization_name[parenthesis_start_index+2:parenthesis_end_index]
                # Try it without the initials tacked on the end
                # ex/ American Federation of Labor and Congress of Industrial Organizations (AFL-CIO)
                wikipedia_page_title_guess8 = organization.organization_name[:parenthesis_start_index]

        if positive_value_exists(wikipedia_page_title_guess7):
            wikipedia_page_title_guess9 = wikipedia_page_title_guess7.replace("-", "–")

        if positive_value_exists(wikipedia_page_title_guess8):
            # Try it without the leading "The "
            if wikipedia_page_title_guess8.find("The ", 0, 4) == 0:
                wikipedia_page_title_guess10 = wikipedia_page_title_guess8[4:]

            # Try it replacing " and" with " &"
            insensitive_org_name_with_and = re.compile(re.escape(' and'), re.IGNORECASE)
            wikipedia_page_title_guess11 = insensitive_org_name_with_and.sub(' &', wikipedia_page_title_guess8)

            # Try it replacing " &" with " and"
            insensitive_org_name_with_ampersand = re.compile(re.escape(' &'), re.IGNORECASE)
            wikipedia_page_title_guess12 = insensitive_org_name_with_ampersand.sub(' and', wikipedia_page_title_guess8)

    if positive_value_exists(wikipedia_page_title):
        results = reach_out_to_wikipedia_with_guess(wikipedia_page_title)
        status += results['status'] + 'TRY1, '
        page_found = results['page_found']
        if page_found:
            wikipedia_page = results['wikipedia_page']

        # Page title Guess 2, without "The"
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess2) and \
                            wikipedia_page_title_guess2 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess2)
                status += results['status'] + 'TRY2, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 3 - Convert "and" to "&"
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess3) and \
                            wikipedia_page_title_guess3 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess3)
                status += results['status'] + 'TRY3, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 4 - Convert "&" to "and"
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess4) and \
                            wikipedia_page_title_guess4 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess4)
                status += results['status'] + 'TRY4, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 5 - Remove "Action Fund"
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess5) and \
                            wikipedia_page_title_guess5 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess5)
                status += results['status'] + 'TRY5, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 6 - remove any "the" from the name
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess6) and \
                            wikipedia_page_title_guess6 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess6)
                status += results['status'] + 'TRY6, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 7 - search for the organization's initials within "()"
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess7) and \
                            wikipedia_page_title_guess7 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess7)
                status += results['status'] + 'TRY7, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 8 - search for the organization's initials within "()", switching "-" for "–"
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess8) and \
                            wikipedia_page_title_guess8 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess8)
                status += results['status'] + 'TRY8, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 9
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess9) and \
                            wikipedia_page_title_guess8 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess9)
                status += results['status'] + 'TRY9, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 10
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess10) and \
                            wikipedia_page_title_guess10 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess10)
                status += results['status'] + 'TRY10, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 11
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess11) and \
                            wikipedia_page_title_guess11 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess11)
                status += results['status'] + 'TRY11, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

        # Page title Guess 12
        if not page_found:
            if positive_value_exists(wikipedia_page_title_guess12) and \
                            wikipedia_page_title_guess12 != wikipedia_page_title:
                results = reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess12)
                status += results['status'] + 'TRY12, '
                page_found = results['page_found']
                if page_found:
                    wikipedia_page = results['wikipedia_page']

    if page_found:
        values_changed = False
        if not (organization.wikipedia_page_id == wikipedia_page.pageid):
            # We make sure the values in the organization match
            values_changed = True
            organization.wikipedia_page_id = wikipedia_page.pageid
        if not (organization.wikipedia_page_title == wikipedia_page.title):
            organization.wikipedia_page_title = wikipedia_page.title
            values_changed = True
        if values_changed:
            # Only save if we need to
            organization.save()
        success = True

    results = {
        'success':              success,
        'status':               status,
        'wikipedia_page_found': page_found,
        'wikipedia_page':       wikipedia_page,
    }
    return results


def reach_out_to_wikipedia_with_guess(wikipedia_page_title_guess, auto_suggest=False, redirect=False, preload=False):
    # auto_suggest = False  # If the literal string isn't found, don't try another page
    # redirect = False  # I changed this from the default (True), but redirect might be ok
    # preload = False
    status = ''
    wikipedia_page = False
    try:
        wikipedia_page_id = 0
        wikipedia_page = wikipedia.page(wikipedia_page_title_guess,
                                        wikipedia_page_id, auto_suggest, redirect, preload)
        page_found = True
    except wikipedia.PageError:
        # Page does not exist
        status = 'WIKIPEDIA_PAGE_ERROR '
        page_found = False
    except wikipedia.RedirectError:
        # When does a page redirect affect us negatively?
        status = 'WIKIPEDIA_REDIRECT_ERROR '
        page_found = False
    except wikipedia.DisambiguationError:
        # There are a few possible pages this might refer to
        status = 'WIKIPEDIA_DISAMBIGUATION_ERROR '
        page_found = False
    except Exception as e:
        status = "WIKIPEDIA_UNKNOWN_ERROR "
        page_found = False

    results = {
        'success':          page_found,
        'status':           status,
        'page_found':       page_found,
        'wikipedia_page':   wikipedia_page,
    }
    return results


def retrieve_organization_logo_from_wikipedia_page(organization, wikipedia_page, force_retrieve=False):
    status = ''
    image_options = []
    logo_found = False
    values_changed = False

    if not organization:
        status += 'WIKIPEDIA_ORGANIZATION_REQUIRED_FOR_LOGO '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if not positive_value_exists(organization.id):
        status += 'WIKIPEDIA_ORGANIZATION_ID_REQUIRED_FOR_LOGO '
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

    if not wikipedia_page:
        status += 'WIKIPEDIA_OBJECT_REQUIRED_FOR_LOGO '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if not positive_value_exists(wikipedia_page.pageid):
        status += 'WIKIPEDIA_PAGE_ID_REQUIRED_FOR_LOGO '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if force_retrieve and wikipedia_page.images and len(wikipedia_page.images):
        # Capture the possible image URLS to display on the admin page
        for one_image in wikipedia_page.images:
            image_options.append(one_image)

    if wikipedia_page.images and len(wikipedia_page.images):
        logo_found = False
        # Pass one
        for one_image in wikipedia_page.images:
            if re.search('commons-logo', one_image, re.IGNORECASE) or \
                    re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                    re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                    re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                    re.search('wikiquote-logo', one_image, re.IGNORECASE):
                # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                pass
            elif re.search('logo', one_image, re.IGNORECASE):
                status += 'WIKIPEDIA_IMAGE_FOUND_WITH_LOGO_IN_URL '
                organization.wikipedia_photo_url = one_image
                values_changed = True
                logo_found = True
                break
        # Pass two - Once we have checked all URLs for "logo", now look for org name in the image title
        if not logo_found:
            # Find any images that have the organization's name in the image url
            name_with_underscores = organization.wikipedia_page_title.replace(" ", "_")
            name_without_spaces = organization.wikipedia_page_title.replace(" ", "")
            # Try it without the leading "The "
            if organization.organization_name.find("The ", 0, 4) == 0:
                name_without_the = organization.organization_name[4:]
            else:
                name_without_the = ''
            for one_image in wikipedia_page.images:
                if re.search('commons-logo', one_image, re.IGNORECASE) or \
                        re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                        re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                        re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                        re.search('wikiquote-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                    pass
                elif re.search(name_with_underscores, one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_ORG_NAME_UNDERLINES_IN_URL '
                    organization.wikipedia_photo_url = one_image
                    values_changed = True
                    logo_found = True
                    break
                elif re.search(name_without_spaces, one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_ORG_NAME_NO_SPACES_URL '
                    organization.wikipedia_photo_url = one_image
                    values_changed = True
                    logo_found = True
                    break
                elif positive_value_exists(name_without_the) and \
                        re.search(name_without_the, one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_ORG_NAME_MINUS_THE_IN_URL '
                    organization.wikipedia_photo_url = one_image
                    values_changed = True
                    logo_found = True
                    break
        # Pass three - Remove images we know are not the logo, and if one remains, use that as the logo
        if not logo_found:
            filtered_image_list = []
            for one_image in wikipedia_page.images:
                if re.search('commons-logo', one_image, re.IGNORECASE) or \
                        re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                        re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                        re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                        re.search('wikiquote-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                    pass
                else:
                    filtered_image_list.append(one_image)
            if len(filtered_image_list) == 1:
                organization.wikipedia_photo_url = filtered_image_list[0]
                values_changed = True
                logo_found = True
        # Pass four - Remove images we know are not the logo, and look for any that have the word "banner"
        if not logo_found:
            for one_image in wikipedia_page.images:
                if re.search('commons-logo', one_image, re.IGNORECASE) or \
                        re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                        re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                        re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                        re.search('wikiquote-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                    pass
                elif re.search('banner', one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_BANNER_IN_URL '
                    organization.wikipedia_photo_url = one_image
                    values_changed = True
                    # logo_found = True
                    break

    if values_changed:
        organization.save()
        success = True
    else:
        success = False

    results = {
        'success':          success,
        'status':           status,
        'logo_found':       logo_found,
        'image_options':    image_options,
    }
    return results


def retrieve_all_organizations_logos_from_wikipedia(state_code=''):
    logos_found = 0
    force_retrieve = False

    organization_list_query = Organization.objects.order_by('organization_name')
    if positive_value_exists(state_code):
        organization_list_query = organization_list_query.filter(state_served_code=state_code)

    organization_list = organization_list_query
    for organization in organization_list:
        organization_results = retrieve_wikipedia_page_from_wikipedia(organization, force_retrieve)
        if organization_results['wikipedia_page_found']:
            wikipedia_page = organization_results['wikipedia_page']

            logo_results = retrieve_organization_logo_from_wikipedia_page(organization, wikipedia_page, force_retrieve)
            if logo_results['logo_found']:
                logos_found += 1
    status = "ORGANIZATION_LOGOS_RETRIEVED"
    results = {
        'success':      True,
        'status':       status,
        'logos_found':  logos_found,
    }
    return results


def retrieve_candidate_images_from_wikipedia_page(candidate, wikipedia_page, force_retrieve=False):
    status = ''
    wikipedia_photo_url = ''
    image_options = []
    image_found = False
    values_changed = False

    if not candidate:
        status += 'WIKIPEDIA_CANDIDATE_REQUIRED_FOR_IMAGE '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if not positive_value_exists(candidate.id):
        status += 'WIKIPEDIA_CANDIDATE_ID_REQUIRED_FOR_IMAGE '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    # Have we already retrieved a Wikipedia photo?
    if positive_value_exists(candidate.wikipedia_photo_url) and not force_retrieve:
        status += 'WIKIPEDIA_CANDIDATE_IMAGE_ALREADY_RETRIEVED-NO_FORCE '
        results = {
            'success':                      True,
            'status':                       status,
        }
        return results

    if not wikipedia_page:
        status += 'WIKIPEDIA_OBJECT_REQUIRED_FOR_IMAGE '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if not positive_value_exists(wikipedia_page.pageid):
        status += 'WIKIPEDIA_PAGE_ID_REQUIRED_FOR_IMAGE '
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if force_retrieve and wikipedia_page.images and len(wikipedia_page.images):
        # Capture the possible image URLS to display on the admin page
        for one_image in wikipedia_page.images:
            image_options.append(one_image)

    if wikipedia_page.images and len(wikipedia_page.images):
        image_found = False
        # Pass one
        for one_image in wikipedia_page.images:
            if re.search('commons-logo', one_image, re.IGNORECASE) or \
                    re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                    re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                    re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                    re.search('wikiquote-logo', one_image, re.IGNORECASE):
                # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                pass
            elif re.search('logo', one_image, re.IGNORECASE):
                status += 'WIKIPEDIA_IMAGE_FOUND_WITH_IMAGE_IN_URL '
                wikipedia_photo_url = one_image
                image_found = True
                break
        # Pass two - Once we have checked all URLs for "logo", now look for org name in the image title
        if not image_found:
            # Find any images that have the organization's name in the image url
            name_with_underscores = wikipedia_page.title.replace(" ", "_")
            name_without_spaces = wikipedia_page.title.replace(" ", "")
            # Try it without the leading "The "
            if candidate.candidate_name.find("The ", 0, 4) == 0:
                name_without_the = candidate.candidate_name[4:]
            else:
                name_without_the = ''
            for one_image in wikipedia_page.images:
                if re.search('commons-logo', one_image, re.IGNORECASE) or \
                        re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                        re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                        re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                        re.search('wikiquote-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                    pass
                elif re.search(name_with_underscores, one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_CANDIDATE_NAME_UNDERLINES_IN_URL '
                    wikipedia_photo_url = one_image
                    image_found = True
                    break
                elif re.search(name_without_spaces, one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_CANDIDATE_NAME_NO_SPACES_URL '
                    wikipedia_photo_url = one_image
                    image_found = True
                    break
                elif positive_value_exists(name_without_the) and \
                        re.search(name_without_the, one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_CANDIDATE_NAME_MINUS_THE_IN_URL '
                    wikipedia_photo_url = one_image
                    image_found = True
                    break
        # Pass three - Remove images we know are not the logo, and if one remains, use that as the logo
        if not image_found:
            filtered_image_list = []
            for one_image in wikipedia_page.images:
                if re.search('commons-logo', one_image, re.IGNORECASE) or \
                        re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                        re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                        re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                        re.search('wikiquote-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                    pass
                else:
                    filtered_image_list.append(one_image)
            if len(filtered_image_list) == 1:
                wikipedia_photo_url = filtered_image_list[0]
                image_found = True
        # Pass four - Remove images we know are not the logo, and look for any that have the word "banner"
        if not image_found:
            for one_image in wikipedia_page.images:
                if re.search('commons-logo', one_image, re.IGNORECASE) or \
                        re.search('wikidata-logo', one_image, re.IGNORECASE) or \
                        re.search('wikinews-logo', one_image, re.IGNORECASE) or \
                        re.search('wikisource-logo', one_image, re.IGNORECASE) or \
                        re.search('wikiquote-logo', one_image, re.IGNORECASE):
                    # We don't want to pay attention to the Creative Commons logo or other Wikipedia logos
                    pass
                elif re.search('banner', one_image, re.IGNORECASE):
                    status += 'WIKIPEDIA_IMAGE_FOUND_WITH_BANNER_IN_URL '
                    wikipedia_photo_url = one_image
                    image_found = True
                    break

    if image_found:
        success = True
    else:
        success = False

    results = {
        'success':          success,
        'status':           status,
        'image_found':      image_found,
        'image_options':    image_options,
        'image':            wikipedia_photo_url,
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
#                     "source": "https://upload.wikimedia.org/wikipedia/en/thumb/3/37/
# Academy_of_General_Dentistry_Logo.gif/50px-Academy_of_General_Dentistry_Logo.gif",
#                     "width": 50,
#                     "height": 50
#                 }
#             }
#         }
#     }
# }


def retrieve_images_from_wikipedia(page_title):
    response = {"success": True, "status": "", "result": ""}
    try:
        page = wikipedia.page(title=page_title, pageid=None, auto_suggest=False)
        page_html = page.html()
        # TODO what if wikipedia layout changes?
        page_dom = BeautifulSoup(page_html, 'html.parser')
        img_link = page_dom.find('img').get('src')
        response["status"] += "SUCCESS "
        response["result"] = "retrieved the following picture from Wikipedia: {}".format(img_link)
    except Exception as retrievePageError:
        response["success"] = False
        response["status"] += "RETRIEVE_IMAGES_FROM_WIKIPEDIA_ERROR "
        response["result"] = "retrieve_images_from_wikipedia error: {}".format(retrievePageError)
    return response