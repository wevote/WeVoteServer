# google_custom_search/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/controllers.py for routines that manage incoming twitter data
from googleapiclient.discovery import build
from .models import GoogleSearchUserManager
from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists

GOOGLE_SEARCH_ENGINE_ID = get_environment_variable("GOOGLE_SEARCH_ENGINE_ID")
GOOGLE_SEARCH_API_KEY = get_environment_variable("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_API_NAME = get_environment_variable("GOOGLE_SEARCH_API_NAME")
GOOGLE_SEARCH_API_VERSION = get_environment_variable("GOOGLE_SEARCH_API_VERSION")


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


def retrieve_possible_google_search_users(candidate_campaign):
    status = ""
    total_search_results = 0
    possible_google_search_users_list = []
    google_search_user_manager = GoogleSearchUserManager()

    if not candidate_campaign:
        status = "RETRIEVE_POSSIBLE_TWITTER_HANDLES-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES-REACHING_OUT_TO_TWITTER "

    search_term = candidate_campaign.candidate_name
    google_api = build(GOOGLE_SEARCH_API_NAME, GOOGLE_SEARCH_API_VERSION,
                       developerKey=GOOGLE_SEARCH_API_KEY)
    search_results = google_api.cse().list(q=search_term, cx=GOOGLE_SEARCH_ENGINE_ID, filter='1').execute()
    search_request_url = "https://www.googleapis.com/customsearch/v1?q={search_term}&" \
                         "cx={google_search_engine_id}&filter=1&key={google_search_api_key}".\
                         format(search_term=search_term, google_search_engine_id=GOOGLE_SEARCH_ENGINE_ID,
                                google_search_api_key=GOOGLE_SEARCH_API_KEY)

    if positive_value_exists(search_results):
        total_search_results = (search_results.get('searchInformation').get('totalResults')
                                if 'searchInformation' in search_results.keys() and
                                search_results.get('searchInformation', {}).get('totalResults', 0) else 0)

        search_results_found = total_search_results
        if not positive_value_exists(search_results_found):
            # No results found with name "as-is". Try searching for only first and last name (without middle names)
            modified_search_term = candidate_campaign.extract_first_name() + " " + \
                                   candidate_campaign.extract_last_name()
            search_results = google_api.cse().list(q=modified_search_term, cx=GOOGLE_SEARCH_ENGINE_ID).execute()
            # search_results.sort(key=lambda possible_candidate: possible_candidate.followers_count, reverse=True)
            total_search_results = (search_results.get('searchInformation').get('totalResults')
                                    if 'searchInformation' in search_results.keys() and
                                    search_results.get('searchInformation', {}).get('totalResults', 0) else 0)

    election_name = candidate_campaign.election().election_name
    if positive_value_exists(total_search_results):
        all_search_items = search_results.get('items', [])
        for one_result in all_search_items:

            item_title = one_result['title'] if 'title' in one_result else ''
            item_link = one_result['link'] if 'link' in one_result else ''
            item_snippet = one_result['snippet'] if 'snippet' in one_result else ''
            item_formatted_url = one_result['formattedUrl'] if 'formattedUrl' in one_result else ''
            item_image = (one_result.get('pagemap').get('metatags')[0].get('og:image') if 'pagemap' in one_result and
                          one_result.get('pagemap', {}).get('metatags', []) and
                          one_result.get('pagemap', {}).get('metatags', [])[0].get('og:image') else '')
            item_meta_tags_description = (one_result.get('pagemap').get('metatags')[0].get('og:description')
                                          if 'pagemap' in one_result and
                                          one_result.get('pagemap', {}).get('metatags', []) and
                                          one_result.get('pagemap', {}).get('metatags', [])[0].get('og:description')
                                          else '')
            item_formatted_url = (item_formatted_url
                                  if item_link.split("//")[-1] != item_formatted_url.split("//")[-1] else "")

            item_person_location = (one_result.get('pagemap').get('person')[0].get('location')
                                    if 'pagemap' in one_result and one_result.get('pagemap', {}).get('person', []) and
                                    one_result.get('pagemap', {}).get('person', [])[0].get('location', {}) else None)

            if item_person_location and item_person_location.lower() not in election_name.lower():
                # If candidate_location is not same as election location then skip this search entry
                continue

            if candidate_campaign.candidate_name.lower() not in item_title.lower() and \
                    candidate_campaign.candidate_name.lower() not in item_snippet.lower() and \
                    candidate_campaign.candidate_name.lower() not in item_meta_tags_description.lower():
                # If candidate_name is not present in title, snippet and description then skip this search entry
                continue

            google_json = {
                'item_title':                   item_title,
                'item_link':                    item_link,
                'item_snippet':                 item_snippet,
                'item_image':                   item_image,
                'item_formatted_url':           item_formatted_url,
                'item_meta_tags_description':   item_meta_tags_description,
                'search_request_url':           search_request_url,
            }

            likelihood_percentage = 0
            if candidate_campaign.candidate_name.lower() in item_title.lower():
                # If exact name match
                likelihood_percentage += 20
            if "ballotpedia" in item_link:
                likelihood_percentage += 80
            if "linkedin" in item_link:
                likelihood_percentage += 50
            if "facebook" in item_link:
                likelihood_percentage += 40

            current_candidate_google_search_info = {
                'search_term':              search_term,
                'likelihood_percentage':    likelihood_percentage,
                'google_json':              google_json
            }
            possible_google_search_users_list.append(current_candidate_google_search_info)

    success = bool(possible_google_search_users_list)

    if success:
        status += "RETRIEVE_POSSIBLE_GOOGLE_SEARCH_USERS-RETRIEVED_FROM_GOOGLE"
        for possibility_result in possible_google_search_users_list:
            save_google_search_user_results = google_search_user_manager.\
                update_or_create_google_search_user_possibility(candidate_campaign.we_vote_id,
                                                                possibility_result['google_json'],
                                                                possibility_result['search_term'],
                                                                possibility_result['likelihood_percentage'])

    results = {
        'success':                  True,
        'status':                   status,
        'num_of_possibilities':     str(len(possible_google_search_users_list)),
    }

    return results
