# google_custom_search/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/controllers.py for routines that manage incoming twitter data
from image.functions import analyze_remote_url
from .models import GoogleSearchUserManager, GOOGLE_SEARCH_API_NAME, GOOGLE_SEARCH_API_VERSION, GOOGLE_SEARCH_API_KEY, \
    GOOGLE_SEARCH_ENGINE_ID, BALLOTPEDIA_LOGO_URL, MAXIMUM_CHARACTERS_LENGTH, MAXIMUM_GOOGLE_SEARCH_USERS
from googleapiclient.discovery import build
from image.controllers import BALLOTPEDIA_IMAGE_SOURCE, LINKEDIN, FACEBOOK, TWITTER, WIKIPEDIA
from import_export_facebook.models import FacebookManager
from import_export_wikipedia.controllers import reach_out_to_wikipedia_with_guess, \
    retrieve_candidate_images_from_wikipedia_page
from re import sub
from wevote_functions.functions import positive_value_exists, convert_state_code_to_state_text, \
    POSITIVE_SEARCH_KEYWORDS, NEGATIVE_SEARCH_KEYWORDS, extract_facebook_username_from_text_string
from wevote_settings.models import RemoteRequestHistoryManager, RETRIEVE_POSSIBLE_GOOGLE_LINKS


def delete_possible_google_search_users(candidate_campaign):
    status = ""
    google_search_user_manager = GoogleSearchUserManager()

    if not candidate_campaign:
        status += "DELETE_POSSIBLE_GOOGLE_SEARCH_USER-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    results = google_search_user_manager.delete_google_search_users_possibilities(candidate_campaign.we_vote_id)
    status += results['status']

    results = {
        'success':                  True,
        'status':                   status,
    }

    return results


def bulk_possible_google_search_users_do_not_match(candidate_campaign):
    status = ""
    google_search_user_manager = GoogleSearchUserManager()

    if not candidate_campaign:
        status += "BULK_POSSIBLE_GOOGLE_SEARCH_USERS_DO_NOT_MATCH-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    results = google_search_user_manager.retrieve_google_search_users_list(candidate_campaign.we_vote_id)
    status += results['status']
    google_search_users_list = results['google_search_users_list']
    try:
        for google_search_user in google_search_users_list:
            if not google_search_user.chosen_and_updated:
                google_search_user.not_a_match = True
                google_search_user.save()
    except Exception as e:
        pass

    results = {
        'success':                  True,
        'status':                   status,
    }

    return results


def possible_google_search_user_do_not_match(candidate_we_vote_id, item_link):
    status = ""
    google_search_user_manager = GoogleSearchUserManager()

    if not positive_value_exists(candidate_we_vote_id):
        status += "DELETE_POSSIBLE_GOOGLE_SEARCH_USER-CANDIDATE_WE_VOTE_ID_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    if not positive_value_exists(item_link):
        status += "DELETE_POSSIBLE_GOOGLE_SEARCH_USER-ITEM_LINK_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    results = google_search_user_manager.retrieve_google_search_user_from_item_link(candidate_we_vote_id, item_link)
    status += results['status']
    if results['google_search_user_found']:
        google_search_user = results['google_search_user']
        try:
            if not google_search_user.chosen_and_updated:
                google_search_user.not_a_match = True
                google_search_user.save()
        except Exception as e:
            pass
    results = {
        'success':                  True,
        'status':                   status,
    }
    return results


def retrieve_possible_google_search_users(candidate_campaign, voter_device_id):
    status = ""
    google_search_users_list = []
    possible_google_search_users_list = []
    google_search_user_manager = GoogleSearchUserManager()

    if not candidate_campaign:
        status = "RETRIEVE_POSSIBLE_GOOGLE_SEARCH_USERS-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    status += "RETRIEVE_POSSIBLE_GOOGLE_SEARCH_USERS-REACHING_OUT_TO_GOOGLE "
    name_handling_regex = r"[^ \w'-]"
    candidate_name = {
        'title':       sub(name_handling_regex, "", candidate_campaign.extract_title().lower()),
        'first_name':  sub(name_handling_regex, "", candidate_campaign.extract_first_name().lower()),
        'middle_name': sub(name_handling_regex, "", candidate_campaign.extract_middle_name().lower()),
        'last_name':   sub(name_handling_regex, "", candidate_campaign.extract_last_name().lower()),
        'suffix':      sub(name_handling_regex, "", candidate_campaign.extract_suffix().lower()),
        'nickname':    sub(name_handling_regex, "", candidate_campaign.extract_nickname().lower()),
    }

    search_term = candidate_campaign.candidate_name
    google_api = build(GOOGLE_SEARCH_API_NAME, GOOGLE_SEARCH_API_VERSION,
                       developerKey=GOOGLE_SEARCH_API_KEY)
    try:
        search_results = google_api.cse().list(q=search_term, cx=GOOGLE_SEARCH_ENGINE_ID, gl="countryUS",
                                               filter='1').execute()
        google_search_users_list.extend(analyze_google_search_results(search_results, search_term, candidate_name,
                                                                      candidate_campaign, voter_device_id))
    except Exception as e:
        pass

    # Also include search results omitting any single-letter initials and periods in name.
    # Example: "A." is ignored while "A.J." becomes "AJ"
    modified_search_term = ""
    modified_search_term_base = ""
    if len(candidate_name['first_name']) > 1:
        modified_search_term += candidate_name['first_name'] + " "
    if len(candidate_name['middle_name']) > 1:
        modified_search_term_base += candidate_name['middle_name'] + " "
    if len(candidate_name['last_name']) > 1:
        modified_search_term_base += candidate_name['last_name']
    if len(candidate_name['suffix']):
        modified_search_term_base += " " + candidate_name['suffix']
    modified_search_term += modified_search_term_base
    if search_term != modified_search_term:
        try:
            modified_search_results = google_api.cse().list(q=modified_search_term, cx=GOOGLE_SEARCH_ENGINE_ID,
                                                            gl="countryUS", filter='1').execute()
            google_search_users_list.extend(analyze_google_search_results(modified_search_results,
                                                                          modified_search_term, candidate_name,
                                                                          candidate_campaign, voter_device_id))
        except Exception as e:
            pass

    # If nickname exists, try searching with nickname instead of first name
    if len(candidate_name['nickname']):
        modified_search_term_2 = candidate_name['nickname'] + " " + modified_search_term_base
        try:
            modified_search_results_2 = google_api.cse().list(q=modified_search_term_2, cx=GOOGLE_SEARCH_ENGINE_ID,
                                                              gl="countryUS", filter='1').execute()
            google_search_users_list.extend(analyze_google_search_results(modified_search_results_2,
                                                                          modified_search_term_2, candidate_name,
                                                                          candidate_campaign, voter_device_id))
        except Exception as e:
            pass

    # remove duplicates
    for possible_user in google_search_users_list:
        for existing_user in possible_google_search_users_list:
            if possible_user['google_json']['item_link'] == existing_user['google_json']['item_link']:
                break
        else:
            possible_google_search_users_list.append(possible_user)

    wikipedia_page_results = retrieve_possible_wikipedia_page(search_term)
    if wikipedia_page_results['wikipedia_page_found']:
        update_results = update_google_search_with_wikipedia_results(wikipedia_page_results['wikipedia_page'],
                                                                     search_term, candidate_name, candidate_campaign,
                                                                     possible_google_search_users_list)
        if not update_results['wikipedia_user_exist_in_google_search']:
            possible_google_search_users_list.extend(update_results['possible_wikipedia_search_user'])

    success = bool(possible_google_search_users_list)
    possible_google_search_users_list.sort(key=lambda possible_candidate: possible_candidate['likelihood_score'],
                                           reverse=True)

    google_search_user_count = 0
    if success:
        status += "RETRIEVE_POSSIBLE_GOOGLE_SEARCH_USERS-RETRIEVED_FROM_GOOGLE"
        for possibility_result in possible_google_search_users_list:
            save_google_search_user_results = google_search_user_manager.\
                update_or_create_google_search_user_possibility(
                    candidate_campaign.we_vote_id, possibility_result['google_json'], possibility_result['search_term'],
                    possibility_result['likelihood_score'], possibility_result['facebook_json'],
                    possibility_result['from_ballotpedia'], possibility_result['from_facebook'],
                    possibility_result['from_linkedin'], possibility_result['from_twitter'],
                    possibility_result['from_wikipedia'])
            if save_google_search_user_results['success'] and \
                    save_google_search_user_results['google_search_user_created']:
                google_search_user_count += 1
                if google_search_user_count == MAXIMUM_GOOGLE_SEARCH_USERS:
                    break

    # Create a record denoting that we have retrieved from Google for this candidate
    remote_request_history_manager = RemoteRequestHistoryManager()
    save_results_history = remote_request_history_manager.create_remote_request_history_entry(
        RETRIEVE_POSSIBLE_GOOGLE_LINKS, candidate_campaign.google_civic_election_id,
        candidate_campaign.we_vote_id, None, len(possible_google_search_users_list), status)

    results = {
        'success':                  True,
        'status':                   status,
        'num_of_possibilities':     str(google_search_user_count),
    }

    return results


def analyze_google_search_results(search_results, search_term, candidate_name,
                                  candidate_campaign, voter_device_id):
    total_search_results = 0
    state_code = candidate_campaign.state_code
    state_full_name = convert_state_code_to_state_text(state_code)
    possible_google_search_users_list = []

    if positive_value_exists(search_results):
        total_search_results = (search_results.get('searchInformation').get('totalResults')
                                if 'searchInformation' in search_results.keys() and
                                search_results.get('searchInformation', {}).get('totalResults', 0) else 0)

    if positive_value_exists(total_search_results):
        all_search_items = search_results.get('items', [])
        for one_result in all_search_items:
            likelihood_score = 0
            from_ballotpedia = False
            from_facebook = False
            from_linkedin = False
            from_twitter = False
            from_wikipedia = False
            google_json = parse_google_search_results(search_term, one_result)

            if FACEBOOK in google_json['item_link']:
                current_candidate_facebook_search_info = analyze_facebook_search_results(
                    google_json, search_term, candidate_name, candidate_campaign, voter_device_id)
                if positive_value_exists(current_candidate_facebook_search_info):
                    possible_google_search_users_list.append(current_candidate_facebook_search_info)
                    continue

            # if item_image does not exist and this link is not from ballotpedia then skip this
            if not positive_value_exists(google_json['item_image']) and BALLOTPEDIA_IMAGE_SOURCE not in google_json['item_link']:
                continue
            elif BALLOTPEDIA_LOGO_URL in google_json['item_image']:
                google_json['item_image'] = ""

            # Check if name (or parts of name) are in title, snippet and description
            name_found_in_title = False
            name_found_in_description = False
            for name in candidate_name.values():
                if len(name) and name in google_json['item_title'].lower():
                    likelihood_score += 10
                    name_found_in_title = True
                if len(name) and (name in google_json['item_snippet'].lower() or
                                  name in google_json['item_meta_tags_description'].lower()):
                    likelihood_score += 5
                    name_found_in_description = True
            # If candidate_name is not present in title, snippet and description then skip this search entry
            if not name_found_in_title and not name_found_in_description:
                continue
            if not name_found_in_title:
                likelihood_score -= 10
            if not name_found_in_description:
                likelihood_score -= 5

            # Check if state or state code is in location or description
            if google_json['item_person_location'] and positive_value_exists(state_full_name) and \
                    state_full_name in google_json['item_person_location']:
                likelihood_score += 20
            elif google_json['item_person_location'] and positive_value_exists(state_code) and \
                    state_code in google_json['item_person_location']:
                likelihood_score += 20
            if google_json['item_snippet'] and positive_value_exists(state_full_name) and \
                    state_full_name in google_json['item_snippet']:
                likelihood_score += 20
            elif google_json['item_meta_tags_description'] and positive_value_exists(state_full_name) and \
                    state_full_name in google_json['item_meta_tags_description']:
                likelihood_score += 20

            # Check if candidate's party is in description
            political_party = candidate_campaign.political_party_display()
            if google_json['item_snippet'] and positive_value_exists(political_party) and \
                    political_party in google_json['item_snippet']:
                likelihood_score += 20
            elif google_json['item_meta_tags_description'] and positive_value_exists(political_party) and \
                    political_party in google_json['item_meta_tags_description']:
                likelihood_score += 20

            if BALLOTPEDIA_IMAGE_SOURCE in google_json['item_link']:
                from_ballotpedia = True
                likelihood_score += 20
            if LINKEDIN in google_json['item_link']:
                from_linkedin = True
                likelihood_score += 20
            if FACEBOOK in google_json['item_link']:
                from_facebook = True
                likelihood_score += 20
            if TWITTER in google_json['item_link']:
                from_twitter = True
                likelihood_score += 20
            if WIKIPEDIA in google_json['item_link']:
                from_wikipedia = True
                likelihood_score += 20

            # Check (each word individually) if office name is in description
            # This also checks if state code is in description
            office_name = candidate_campaign.contest_office_name
            if positive_value_exists(office_name) and (google_json['item_snippet'] or
                                                       google_json['item_meta_tags_description']):
                office_name = office_name.split()
                office_found_in_description = False
                for word in office_name:
                    if len(word) > 1 and (word in google_json['item_snippet'] or
                                          word in google_json['item_meta_tags_description']):
                        likelihood_score += 10
                        office_found_in_description = True
                if not office_found_in_description:
                    likelihood_score -= 5

            # Increase the score for every positive keyword we find
            for keyword in POSITIVE_SEARCH_KEYWORDS:
                if google_json['item_snippet'] and keyword in google_json['item_snippet'].lower() or \
                        google_json['item_meta_tags_description'] and \
                        keyword in google_json['item_meta_tags_description'].lower():
                    likelihood_score += 5

            # Decrease the score for every negative keyword we find
            for keyword in NEGATIVE_SEARCH_KEYWORDS:
                if (google_json['item_snippet'] and keyword in google_json['item_snippet'].lower()) or \
                    (google_json['item_meta_tags_description'] and
                     keyword in google_json['item_meta_tags_description'].lower()):
                    likelihood_score -= 20

            if likelihood_score < 0:
                continue

            current_candidate_google_search_info = {
                'search_term':              search_term,
                'likelihood_score':         likelihood_score,
                'from_ballotpedia':         from_ballotpedia,
                'from_facebook':            from_facebook,
                'from_linkedin':            from_linkedin,
                'from_twitter':             from_twitter,
                'from_wikipedia':           from_wikipedia,
                'google_json':              google_json,
                'facebook_json':            None
            }
            possible_google_search_users_list.append(current_candidate_google_search_info)
    return possible_google_search_users_list


def parse_google_search_results(search_term, result):
    search_request_url = "https://www.googleapis.com/customsearch/v1?q={search_term}&" \
                         "cx={google_search_engine_id}&filter=1&fl=countryUS&key={google_search_api_key}". \
        format(search_term=search_term, google_search_engine_id=GOOGLE_SEARCH_ENGINE_ID,
               google_search_api_key=GOOGLE_SEARCH_API_KEY)

    item_title = result['title'] if 'title' in result else ''
    item_link = result['link'] if 'link' in result else ''
    item_snippet = result['snippet'] if 'snippet' in result else ''
    item_formatted_url = result['formattedUrl'] if 'formattedUrl' in result else ''
    item_image = (result.get('pagemap').get('metatags')[0].get('og:image')
                  if 'pagemap' in result and result.get('pagemap', {}).get('metatags', []) and
                  result.get('pagemap', {}).get('metatags', [])[0].get('og:image') else '')
    if item_image:
        image_results = analyze_remote_url(item_image)
        item_image = None if not image_results['image_url_valid'] else item_image
    if not item_image:
        item_image = (result.get('pagemap').get('cse_image')[0].get('src')
                      if 'pagemap' in result and result.get('pagemap', {}).get('cse_image', []) and
                         result.get('pagemap', {}).get('cse_image', [])[0].get('src') else '')
        if item_image:
            image_results = analyze_remote_url(item_image)
            item_image = None if not image_results['image_url_valid'] else item_image
        if not item_image:
            item_image = (result.get('pagemap').get('cse_thumbnail')[0].get('src')
                          if 'pagemap' in result and result.get('pagemap', {}).get('cse_thumbnail', []) and
                             result.get('pagemap', {}).get('cse_thumbnail', [])[0].get('src') else '')
            if item_image:
                image_results = analyze_remote_url(item_image)
                item_image = None if not image_results['image_url_valid'] else item_image

    item_meta_tags_description = (result.get('pagemap').get('metatags')[0].get('og:description')
                                  if 'pagemap' in result and result.get('pagemap', {}).get('metatags', []) and
                                  result.get('pagemap', {}).get('metatags', [])[0].get('og:description') else '')
    item_formatted_url = (item_formatted_url
                          if item_link.split("//")[-1] != item_formatted_url.split("//")[-1] else "")
    item_person_location = (result.get('pagemap').get('person')[0].get('location')
                            if 'pagemap' in result and result.get('pagemap', {}).get('person', []) and
                            result.get('pagemap', {}).get('person', [])[0].get('location', {}) else None)
    google_json = {
        'item_title':                   item_title,
        'item_link':                    item_link,
        'item_snippet':                 item_snippet[:MAXIMUM_CHARACTERS_LENGTH],
        'item_image':                   item_image,
        'item_formatted_url':           item_formatted_url,
        'item_meta_tags_description':   item_meta_tags_description[:MAXIMUM_CHARACTERS_LENGTH],
        'item_person_location':         item_person_location,
        'search_request_url':           search_request_url,
    }
    return google_json


def retrieve_possible_wikipedia_page(search_term):
    status = ""
    wikipedia_results = reach_out_to_wikipedia_with_guess(search_term, auto_suggest=False, preload=True)
    page_found = wikipedia_results['page_found']
    wikipedia_page = wikipedia_results['wikipedia_page']
    if not page_found:
        # search with auto_suggest as True (auto_suggest: If the literal string isn't found, try another page)
        wikipedia_auto_suggest_results = reach_out_to_wikipedia_with_guess(search_term, auto_suggest=True, preload=True)
        page_found = wikipedia_auto_suggest_results['page_found']
        wikipedia_page = wikipedia_auto_suggest_results['wikipedia_page']

    if page_found:
        status += "RETRIEVED_CANDIDATE_WIKIPEDIA_RESULTS"
    else:
        status += "RETRIEVE_CANDIDATE_WIKIPEDIA_RESULTS_FALIED"

    results = {
        'status':                  status,
        'wikipedia_page_found':    page_found,
        'wikipedia_page':          wikipedia_page,
    }
    return results


def update_google_search_with_wikipedia_results(wikipedia_page, search_term, candidate_name, candidate_campaign,
                                                possible_google_search_users_list):
    wikipedia_user_exist_in_google_search = False
    possible_wikipedia_search_user = analyze_wikipedia_search_results(wikipedia_page, search_term, candidate_name,
                                                                      candidate_campaign)
    for google_search_user in possible_google_search_users_list:
        if wikipedia_page and wikipedia_page.url == google_search_user['google_json']['item_link']:
            wikipedia_user_exist_in_google_search = True
            possible_wikipedia_search_user = possible_wikipedia_search_user[0]
            google_search_user['likelihood_score'] = possible_wikipedia_search_user['likelihood_score']
            break

    results = {
        'wikipedia_user_exist_in_google_search':    wikipedia_user_exist_in_google_search,
        'possible_wikipedia_search_user':           possible_wikipedia_search_user
    }
    return results


def analyze_wikipedia_search_results(wikipedia_page, search_term, candidate_name,
                                     candidate_campaign):
    likelihood_score = 20
    possible_google_search_users_list = []
    state_code = candidate_campaign.state_code
    state_full_name = convert_state_code_to_state_text(state_code)
    wikipedia_images_result = retrieve_candidate_images_from_wikipedia_page(candidate_campaign, wikipedia_page,
                                                                            force_retrieve=True)

    google_json = {
        'item_title':                   wikipedia_page.original_title,
        'item_link':                    wikipedia_page.url,
        'item_snippet':                 wikipedia_page.summary[:MAXIMUM_CHARACTERS_LENGTH],
        'item_image':                   wikipedia_images_result['image'] if wikipedia_images_result['success'] else '',
        'item_formatted_url':           '',
        'item_meta_tags_description':   '',
        'item_person_location':         '',
        'search_request_url':           '',
    }

    # Check if name (or parts of name) are in title, snippet and description
    name_found_in_title = False
    name_found_in_description = False
    for name in candidate_name.values():
        if len(name) and name in google_json['item_title'].lower():
            likelihood_score += 10
            name_found_in_title = True
        if len(name) and name in google_json['item_snippet'].lower():
            likelihood_score += 5
            name_found_in_description = True

    if not name_found_in_title and not name_found_in_description:
        return possible_google_search_users_list
    if not name_found_in_title:
        likelihood_score -= 10
    if not name_found_in_description:
        likelihood_score -= 5

    if google_json['item_snippet'] and positive_value_exists(state_full_name) and \
            state_full_name in google_json['item_snippet']:
        likelihood_score += 20

    # Check if candidate's party is in description
    political_party = candidate_campaign.political_party_display()
    if google_json['item_snippet'] and positive_value_exists(political_party) and \
            political_party in google_json['item_snippet']:
        likelihood_score += 20

    # Check (each word individually) if office name is in description
    # This also checks if state code is in description
    office_name = candidate_campaign.contest_office_name
    if positive_value_exists(office_name) and google_json['item_snippet']:
        office_name = office_name.lower()
        office_name = office_name.split()
        office_found_in_description = False
        for word in office_name:
            if len(word) > 1 and word in google_json['item_snippet'].lower():
                likelihood_score += 10
                office_found_in_description = True
        if not office_found_in_description:
            likelihood_score -= 5

    # Increase the score for every positive keyword we find
    for keyword in POSITIVE_SEARCH_KEYWORDS:
        if google_json['item_snippet'] and keyword in google_json['item_snippet'].lower():
            likelihood_score += 5

    # Decrease the score for every negative keyword we find
    for keyword in NEGATIVE_SEARCH_KEYWORDS:
        if google_json['item_snippet'] and keyword in google_json['item_snippet'].lower():
            likelihood_score -= 20

    if likelihood_score < 0:
        return possible_google_search_users_list

    current_candidate_wikipedia_search_info = {
        'search_term':              search_term,
        'likelihood_score':         likelihood_score,
        'from_ballotpedia':         False,
        'from_facebook':            False,
        'from_linkedin':            False,
        'from_twitter':             False,
        'from_wikipedia':           True,
        'google_json':              google_json,
        'facebook_json':            None
    }
    possible_google_search_users_list.append(current_candidate_wikipedia_search_info)
    return possible_google_search_users_list


def analyze_facebook_search_results(google_json, search_term, candidate_name,
                                    candidate_campaign, voter_device_id):
    likelihood_score = 20
    state_code = candidate_campaign.state_code
    state_full_name = convert_state_code_to_state_text(state_code)

    facebook_user_manager = FacebookManager()
    facebook_user_name = extract_facebook_username_from_text_string(google_json['item_link'])
    facebook_user_details_results = facebook_user_manager.retrieve_facebook_user_details_from_facebook(
        voter_device_id, facebook_user_name)
    facebook_user_details = facebook_user_details_results['facebook_user_details']
    if facebook_user_details_results['success']:
        # Check if name (or parts of name) are in title, snippet and description
        name_found_in_title = False
        name_found_in_description = False
        for name in candidate_name.values():
            if len(name) and (name in facebook_user_details['name'].lower()):
                likelihood_score += 10
                name_found_in_title = True
            if len(name) and (name in facebook_user_details['description'].lower() or
                              name in facebook_user_details['about'].lower() or
                              name in facebook_user_details['mission'].lower() or
                              name in facebook_user_details['bio'].lower()):
                likelihood_score += 5
                name_found_in_description = True
        if not name_found_in_title:
            likelihood_score -= 10
        if not name_found_in_description:
            likelihood_score -= 5

        # Check if state or state code is in location or description
        if positive_value_exists(state_full_name):
            if state_full_name in facebook_user_details['location']:
                likelihood_score += 20
            if state_full_name in facebook_user_details['description'] or \
                    state_full_name in facebook_user_details['bio'] or \
                    state_full_name in facebook_user_details['about'] or \
                    state_full_name in facebook_user_details['general_info'] or \
                    state_full_name in facebook_user_details['personal_info']:
                likelihood_score += 20
        elif positive_value_exists(state_code):
            if state_code in facebook_user_details['location']:
                likelihood_score += 20
            if state_code in facebook_user_details['description'] or \
                    state_code in facebook_user_details['bio'] or \
                    state_code in facebook_user_details['about'] or \
                    state_full_name in facebook_user_details['general_info'] or \
                    state_full_name in facebook_user_details['personal_info']:
                likelihood_score += 20

        # Check if candidate's party is in description
        political_party = candidate_campaign.political_party_display()
        if positive_value_exists(political_party):
            if political_party in facebook_user_details['description'] or \
                    political_party in facebook_user_details['bio'] or \
                    political_party in facebook_user_details['about'] or \
                    political_party in facebook_user_details['mission'] or \
                    political_party in facebook_user_details['general_info'] or \
                    political_party in facebook_user_details['personal_info'] or \
                    political_party in facebook_user_details['posts']:
                likelihood_score += 20

        # Check (each word individually) if office name is in description
        # This also checks if state code is in description
        office_name = candidate_campaign.contest_office_name
        if positive_value_exists(office_name):
            office_name = office_name.split()
            office_found_in_description = False
            for word in office_name:
                if len(word) > 1 and (word in facebook_user_details['description'] or
                                      word in facebook_user_details['bio'] or
                                      word in facebook_user_details['about'] or
                                      word in facebook_user_details['mission'] or
                                      word in facebook_user_details['general_info'] or
                                      word in facebook_user_details['personal_info']):
                    likelihood_score += 10
                    office_found_in_description = True
            if not office_found_in_description:
                likelihood_score -= 5

        # Increase the score for every positive keyword we find
        for keyword in POSITIVE_SEARCH_KEYWORDS:
            if keyword in facebook_user_details['description'] or \
                    keyword in facebook_user_details['bio'] or \
                    keyword in facebook_user_details['about'] or \
                    keyword in facebook_user_details['mission'] or \
                    keyword in facebook_user_details['general_info'] or \
                    keyword in facebook_user_details['personal_info'] or \
                    keyword in facebook_user_details['posts']:
                likelihood_score += 5

        # Decrease the score for every negative keyword we find
        for keyword in NEGATIVE_SEARCH_KEYWORDS:
            if keyword in facebook_user_details['description'] or \
                    keyword in facebook_user_details['bio'] or \
                    keyword in facebook_user_details['about'] or \
                    keyword in facebook_user_details['mission'] or \
                    keyword in facebook_user_details['general_info'] or \
                    keyword in facebook_user_details['personal_info'] or \
                    keyword in facebook_user_details['posts']:
                likelihood_score -= 20

        if likelihood_score < 0:
            return dict

    current_candidate_facebook_search_info = {
        'search_term':              search_term,
        'likelihood_score':         likelihood_score,
        'from_ballotpedia':         False,
        'from_facebook':            True,
        'from_linkedin':            False,
        'from_twitter':             False,
        'from_wikipedia':           False,
        'google_json':              google_json,
        'facebook_json':            facebook_user_details
    }
    return current_candidate_facebook_search_info
