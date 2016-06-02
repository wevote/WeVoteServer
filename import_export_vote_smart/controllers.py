# import_export_vote_smart/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import VoteSmartApiCounterManager, VoteSmartCandidate, VoteSmartCandidateManager, \
    vote_smart_candidate_object_filter, VoteSmartCandidateBio, vote_smart_candidate_bio_object_filter, \
    VoteSmartCategory, vote_smart_category_filter, \
    VoteSmartOfficial, VoteSmartOfficialManager, vote_smart_official_object_filter, \
    VoteSmartRating, VoteSmartRatingCategoryLink, vote_smart_candidate_rating_filter, vote_smart_rating_list_filter, \
    VoteSmartRatingOneCandidate, vote_smart_rating_one_candidate_filter, \
    VoteSmartSpecialInterestGroup, VoteSmartSpecialInterestGroupManager, vote_smart_special_interest_group_filter, \
    vote_smart_special_interest_group_list_filter, \
    VoteSmartState, vote_smart_state_filter
from .votesmart_local import votesmart, VotesmartApiError
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
import copy
from exception.models import handle_record_found_more_than_one_exception
from position.models import PositionEnteredManager, PERCENT_RATING
import requests
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
VOTE_SMART_API_URL = get_environment_variable("VOTE_SMART_API_URL")

votesmart.apikey = VOTE_SMART_API_KEY


def retrieve_and_match_candidate_from_vote_smart(we_vote_candidate, force_retrieve=False):
    status = ""
    vote_smart_candidate_just_retrieved = False

    # Has this candidate already been linked to a Vote Smart candidate?
    if positive_value_exists(we_vote_candidate.vote_smart_id) and not force_retrieve:
        vote_smart_candidate_id = we_vote_candidate.vote_smart_id
        status += 'VOTE_SMART_CANDIDATE_ID_PREVIOUSLY_RETRIEVED '
        results = {
            'success':                              True,
            'status':                               status,
            'message_type':                         'INFO',
            'message':                              'Vote Smart candidate id already retrieved previously.',
            'we_vote_candidate_id':                 we_vote_candidate.id,
            'we_vote_candidate':                    we_vote_candidate,
            'vote_smart_candidate_id':              vote_smart_candidate_id,
            'vote_smart_candidate_just_retrieved':  vote_smart_candidate_just_retrieved,
        }
        return results

    first_name = we_vote_candidate.extract_first_name()
    last_name = we_vote_candidate.extract_last_name()

    # Fill the VoteSmartCandidate table with politicians that might match this candidate
    candidate_results = retrieve_vote_smart_candidates_into_local_db(last_name)
    if not candidate_results['success']:
        status += 'VOTE_SMART_CANDIDATES_NOT_RETRIEVED_TO_LOCAL_DB: '
        status += candidate_results['status']
    else:
        # Now look through those Vote Smart candidates and match them
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate_from_name_components(
            first_name, last_name, we_vote_candidate.state_code)
        if results['vote_smart_candidate_found']:
            status += 'VOTE_SMART_CANDIDATE_MATCHED '
            vote_smart_candidate = results['vote_smart_candidate']
            vote_smart_candidate_id = convert_to_int(vote_smart_candidate.candidateId)
            we_vote_candidate.vote_smart_id = vote_smart_candidate_id
            we_vote_candidate.save()
            vote_smart_candidate_just_retrieved = True
            # messages.add_message(request, messages.INFO,
            #                      "Vote Smart Candidate db entry found for '{first_name} {last_name}'.".format(
            #                          first_name=first_name, last_name=last_name))
            # If here, we were able to match this candidate from the We Vote database to a candidate
            # from the Vote Smart database with this last name
            results = {
                'success':                              True,
                'status':                               status,
                'message_type':                         'INFO',
                'message':                              candidate_results['status'],
                'we_vote_candidate_id':                 we_vote_candidate.id,
                'we_vote_candidate':                    we_vote_candidate,
                'vote_smart_candidate_id':              vote_smart_candidate_id,
                'vote_smart_candidate_just_retrieved':  vote_smart_candidate_just_retrieved,
            }
            return results
        else:
            # If here, we were NOT able to find any possible candidates from the Vote Smart database,
            # but we still will look in the Vote Smart Officials table below
            status += 'MATCHING_CANDIDATE_NOT_FOUND_FROM_VOTE_SMART_OPTIONS (first_name: {first_name}, ' \
                      'last_name: {last_name}) '.format(first_name=first_name, last_name=last_name)

    # If we didn't find a person from the Vote Smart candidate search, look through Vote Smart officials

    # Fill the VoteSmartOfficial table with politicians that might match this candidate
    officials_results = retrieve_vote_smart_officials_into_local_db(last_name)
    if not officials_results['success']:
        success = False
        vote_smart_candidate_id = 0
        status += 'VOTE_SMART_OFFICIALS_NOT_RETRIEVED_TO_LOCAL_DB: '
        status += officials_results['status']
    else:
        vote_smart_official_manager = VoteSmartOfficialManager()
        results = vote_smart_official_manager.retrieve_vote_smart_official_from_name_components(
            first_name, last_name, we_vote_candidate.state_code)
        if results['vote_smart_official_found']:
            vote_smart_official = results['vote_smart_official']
            vote_smart_candidate_id = convert_to_int(vote_smart_official.candidateId)
            we_vote_candidate.vote_smart_id = vote_smart_candidate_id
            we_vote_candidate.save()
            success = True
            status += 'VOTE_SMART_OFFICIAL_MATCHED '
            vote_smart_candidate_just_retrieved = True
        else:
            vote_smart_candidate_id = 0
            success = False
            status += 'MATCHING_OFFICIAL_NOT_FOUND_FROM_VOTE_SMART_OPTIONS (first_name: {first_name}, ' \
                      'last_name: {last_name}) '.format(first_name=first_name, last_name=last_name)

    results = {
        'success':                              success,
        'status':                               status,
        'message_type':                         'INFO',
        'message':                              candidate_results['status'],
        'we_vote_candidate_id':                 we_vote_candidate.id,
        'vote_smart_candidate_id':              vote_smart_candidate_id,
        'we_vote_candidate':                    we_vote_candidate,
        'vote_smart_candidate_just_retrieved':  vote_smart_candidate_just_retrieved,
    }
    return results


def retrieve_candidate_photo_from_vote_smart(we_vote_candidate, force_retrieve=False):
    status = ""
    vote_smart_candidate_id = we_vote_candidate.vote_smart_id
    vote_smart_candidate_photo_exists = False
    vote_smart_candidate_photo_just_retrieved = False

    # Has this candidate been linked to a Vote Smart candidate? If not, error out
    if not positive_value_exists(vote_smart_candidate_id):
        status += 'VOTE_SMART_CANDIDATE_ID_REQUIRED '
        results = {
            'success':                                      False,
            'status':                                       status,
            'message_type':                                 'INFO',
            'message':                                      'Vote Smart candidate id needs to be retrieved before '
                                                            'the photo can be retrieved.',
            'we_vote_candidate_id':                         we_vote_candidate.id,
            'vote_smart_candidate_id':                      vote_smart_candidate_id,
            'vote_smart_candidate_photo_exists':            vote_smart_candidate_photo_exists,
            'vote_smart_candidate_photo_just_retrieved':    vote_smart_candidate_photo_just_retrieved,
        }
        return results

    # Have we already retrieved a Vote Smart photo?
    if positive_value_exists(we_vote_candidate.photo_url_from_vote_smart) and not force_retrieve:
        status += 'VOTE_SMART_CANDIDATE_ID_PREVIOUSLY_RETRIEVED '
        vote_smart_candidate_photo_exists = True
        results = {
            'success':                      True,
            'status':                       status,
            'message_type':                 'INFO',
            'message':                      'Vote Smart candidate photo already retrieved previously.',
            'we_vote_candidate_id':         we_vote_candidate.id,
            'vote_smart_candidate_id':      vote_smart_candidate_id,
            'photo_url_from_vote_smart':    we_vote_candidate.photo_url_from_vote_smart,
            'vote_smart_candidate_photo_exists':            vote_smart_candidate_photo_exists,
            'vote_smart_candidate_photo_just_retrieved':    vote_smart_candidate_photo_just_retrieved,
        }
        return results

    candidate_results = retrieve_vote_smart_candidate_bio_into_local_db(vote_smart_candidate_id)

    photo_url_from_vote_smart = ""
    if not candidate_results['success']:
        status += 'VOTE_SMART_CANDIDATE_BIO_NOT_RETRIEVED_TO_LOCAL_DB: '
        status += candidate_results['status']
        success = False
    else:
        # Now look through those Vote Smart candidates and match them
        vote_smart_candidate_manager = VoteSmartCandidateManager()
        results = vote_smart_candidate_manager.retrieve_vote_smart_candidate_bio(vote_smart_candidate_id)
        if results['vote_smart_candidate_bio_found']:
            status += 'VOTE_SMART_CANDIDATE_BIO_MATCHED '
            vote_smart_candidate_bio = results['vote_smart_candidate_bio']
            we_vote_candidate.photo_url_from_vote_smart = vote_smart_candidate_bio.photo
            we_vote_candidate.save()
            # If here, we were able to match this candidate from the We Vote database to a candidate
            # from the Vote Smart database
            photo_url_from_vote_smart = vote_smart_candidate_bio.photo
            vote_smart_candidate_photo_exists = True if positive_value_exists(vote_smart_candidate_bio.photo) else False
            vote_smart_candidate_photo_just_retrieved = vote_smart_candidate_photo_exists
            success = True
        else:
            # If here, we were NOT able to find any possible candidates from the Vote Smart database,
            # but we still will look in the Vote Smart Officials table below
            status += 'MATCHING_CANDIDATE_BIO_NOT_FOUND_FROM_ID ' \
                      '(vote_smart_candidate_id: ' \
                      '{vote_smart_candidate_id}) '.format(vote_smart_candidate_id=vote_smart_candidate_id)
            success = False

    results = {
        'success':                      success,
        'status':                       status,
        'message_type':                 'INFO',
        'message':                      status,
        'we_vote_candidate_id':         we_vote_candidate.id,
        'vote_smart_candidate_id':      vote_smart_candidate_id,
        'photo_url_from_vote_smart':    photo_url_from_vote_smart,
        'vote_smart_candidate_photo_exists':            vote_smart_candidate_photo_exists,
        'vote_smart_candidate_photo_just_retrieved':    vote_smart_candidate_photo_just_retrieved,
    }
    return results


def retrieve_vote_smart_candidates_into_local_db(last_name):
    try:
        last_name = last_name.replace("`", "'")  # Vote Smart doesn't like this kind of apostrophe: `

        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Candidates.getByLastname')

        candidates_list = votesmart.candidates.getByLastname(last_name)
        for one_candidate in candidates_list:
            one_candidate_filtered = vote_smart_candidate_object_filter(one_candidate)
            vote_smart_candidate, created = VoteSmartCandidate.objects.update_or_create(
                candidateId=one_candidate.candidateId, defaults=one_candidate_filtered)
            vote_smart_candidate.save()
        status = "VOTE_SMART_CANDIDATES_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def retrieve_vote_smart_candidate_bio_into_local_db(candidate_id):
    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('CandidateBio.getBio')

        one_candidate_bio = votesmart.candidatebio.getBio(candidate_id)
        candidate_bio_filtered = vote_smart_candidate_bio_object_filter(one_candidate_bio)
        candidate_bio, created = VoteSmartCandidateBio.objects.update_or_create(
            candidateId=one_candidate_bio.candidateId, defaults=candidate_bio_filtered)
        candidate_bio.save()
        status = "VOTE_SMART_CANDIDATE_BIO_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def retrieve_vote_smart_officials_into_local_db(last_name):
    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Officials.getByLastname')

        officials_list = votesmart.officials.getByLastname(last_name)
        for one_official in officials_list:
            one_official_filtered = vote_smart_official_object_filter(one_official)
            vote_smart_official, created = VoteSmartOfficial.objects.update_or_create(
                candidateId=one_official.candidateId, defaults=one_official_filtered)
            vote_smart_official.save()
        status = "VOTE_SMART_OFFICIALS_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def retrieve_vote_smart_position_categories_into_local_db(state_code='NA'):
    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Rating.getCategories')

        position_categories_list = votesmart.rating.getCategories(state_code)
        for vote_smart_category in position_categories_list:
            vote_smart_category_filtered = vote_smart_category_filter(vote_smart_category)
            vote_smart_category_object, created = VoteSmartCategory.objects.update_or_create(
                categoryId=vote_smart_category.categoryId, defaults=vote_smart_category_filtered)
            vote_smart_category_object.save()
        status = "VOTE_SMART_CATEGORIES_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def retrieve_vote_smart_ratings_for_candidate_into_local_db(vote_smart_candidate_id):
    rating_one_candidate_exists = False
    rating_one_candidate_created = False

    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Rating.getCandidateRating')

        ratings_list = votesmart.rating.getCandidateRating(vote_smart_candidate_id)

        # A Vote Smart "rating" is like a the voter guide for that group for that election. It contains multiple
        # positions about a variety of candidates.
        for one_rating in ratings_list:
            # Note that this filter is specific to the getCandidateRating call
            one_rating_filtered = vote_smart_candidate_rating_filter(one_rating)
            one_rating_filtered['candidateId'] = vote_smart_candidate_id
            try:
                vote_smart_rating_one_candidate, rating_one_candidate_created_temp = \
                    VoteSmartRatingOneCandidate.objects.update_or_create(
                        ratingId=one_rating_filtered['ratingId'],
                        sigId=one_rating_filtered['sigId'],
                        candidateId=one_rating_filtered['candidateId'],
                        timeSpan=one_rating_filtered['timeSpan'],
                        defaults=one_rating_filtered)

                if not rating_one_candidate_exists:
                    # Once set to True, this stays true
                    rating_one_candidate_exists = True if vote_smart_rating_one_candidate.candidateId else False

                if not rating_one_candidate_created:
                    # Once set to True, this stays true
                    rating_one_candidate_created = True if rating_one_candidate_created_temp else False

                if vote_smart_rating_one_candidate.candidateId:
                    # We start with one_rating_filtered, and add additional data with each loop below
                    category_branch = one_rating.categories['category']
                    if type(category_branch) is list:
                        category_list = category_branch
                    else:
                        category_list = [category_branch]
                    for one_category in category_list:
                        # Now save the category/categories for this rating
                        rating_values_for_category_save = copy.deepcopy(one_rating_filtered)
                        rating_values_for_category_save['categoryId'] = one_category['categoryId']
                        rating_values_for_category_save['categoryName'] = one_category['name']
                        del rating_values_for_category_save['ratingText']
                        del rating_values_for_category_save['ratingName']
                        del rating_values_for_category_save['rating']
                        try:
                            vote_smart_category_link, created = VoteSmartRatingCategoryLink.objects.update_or_create(
                                    ratingId=one_rating_filtered['ratingId'],
                                    sigId=one_rating_filtered['sigId'],
                                    candidateId=one_rating_filtered['candidateId'],
                                    timeSpan=one_rating_filtered['timeSpan'],
                                    categoryId=one_category['categoryId'],
                                    defaults=rating_values_for_category_save)
                        except VoteSmartRatingCategoryLink.MultipleObjectsReturned as e:
                            exception_message_optional = "retrieve_vote_smart_ratings_for_candidate_into_local_db, " \
                                                         "VoteSmartRatingCategoryLink.objects.update_or_create: " \
                                                         "ratingId: {ratingId}, " \
                                                         "sigId: {sigId}, " \
                                                         "candidateId: {candidateId}, " \
                                                         "timeSpan: {timeSpan}, " \
                                                         "categoryId: {categoryId}, " \
                                                         "".format(ratingId=one_rating_filtered['ratingId'],
                                                                   sigId=one_rating_filtered['sigId'],
                                                                   candidateId=one_rating_filtered['candidateId'],
                                                                   timeSpan=one_rating_filtered['timeSpan'],
                                                                   categoryId=one_category['categoryId'])
                            handle_record_found_more_than_one_exception(
                                e, logger=logger, exception_message_optional=exception_message_optional)
            except VoteSmartRatingOneCandidate.MultipleObjectsReturned as e:
                exception_message_optional = "retrieve_vote_smart_ratings_for_candidate_into_local_db, " \
                                             "VoteSmartRatingOneCandidate.objects.update_or_create: " \
                                             "ratingId: {ratingId}, " \
                                             "sigId: {sigId}, " \
                                             "candidateId: {candidateId}, " \
                                             "timeSpan: {timeSpan}, " \
                                             "".format(ratingId=one_rating_filtered['ratingId'],
                                                       sigId=one_rating_filtered['sigId'],
                                                       candidateId=one_rating_filtered['candidateId'],
                                                       timeSpan=one_rating_filtered['timeSpan'])
                handle_record_found_more_than_one_exception(
                    e, logger=logger, exception_message_optional=exception_message_optional)
            status = "VOTE_SMART_RATINGS_BY_CANDIDATE_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status':                       status,
        'success':                      success,
        'rating_one_candidate_exists':  rating_one_candidate_exists,
        'rating_one_candidate_created': rating_one_candidate_created,
    }
    return results


def retrieve_vote_smart_ratings_by_group_into_local_db(special_interest_group_id):
    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Rating.getSigRatings')

        ratings_list = votesmart.rating.getSigRatings(special_interest_group_id)
        # A Vote Smart "rating" is like a the voter guide for that group for that election. It contains multiple
        # positions about a variety of candidates.
        for one_rating in ratings_list:
            # Note that this filter is specific to the getSigRatings call
            one_rating_filtered = vote_smart_rating_list_filter(one_rating)
            one_rating_filtered['sigId'] = special_interest_group_id
            vote_smart_rating, rating_created = VoteSmartRating.objects.update_or_create(
                ratingId=one_rating.ratingId, defaults=one_rating_filtered)

            # Use Vote Smart API call counter to track the number of queries we are doing each day
            vote_smart_api_counter_manager = VoteSmartApiCounterManager()
            vote_smart_api_counter_manager.create_counter_entry('Rating.getRating')

            rating_candidates_list = votesmart.rating.getRating(one_rating.ratingId)
            for rating_one_candidate in rating_candidates_list:
                # Note that this filter is specific to the getRating call
                rating_one_candidate_filtered = vote_smart_rating_one_candidate_filter(rating_one_candidate)
                rating_one_candidate_filtered['ratingId'] = one_rating.ratingId
                rating_one_candidate_filtered['sigId'] = special_interest_group_id
                rating_one_candidate_filtered['timeSpan'] = one_rating.timespan
                rating_one_candidate_filtered['ratingName'] = one_rating.ratingName
                rating_one_candidate_filtered['ratingText'] = one_rating.ratingText
                try:
                    vote_smart_rating_one_candidate, rating_one_candidate_created = \
                        VoteSmartRatingOneCandidate.objects.update_or_create(
                            ratingId=one_rating.ratingId,
                            sigId=special_interest_group_id,
                            candidateId=rating_one_candidate_filtered['candidateId'],
                            timeSpan=one_rating.timespan,
                            defaults=rating_one_candidate_filtered)
                except VoteSmartRatingOneCandidate.MultipleObjectsReturned as e:
                    exception_message_optional = "retrieve_vote_smart_ratings_for_candidate_into_local_db, " \
                                                 "VoteSmartRatingOneCandidate.objects.update_or_create: " \
                                                 "ratingId: {ratingId}, " \
                                                 "sigId: {sigId}, " \
                                                 "candidateId: {candidateId}, " \
                                                 "timeSpan: {timeSpan}, " \
                                                 "".format(ratingId=one_rating_filtered['ratingId'],
                                                           sigId=one_rating_filtered['sigId'],
                                                           candidateId=one_rating_filtered['candidateId'],
                                                           timeSpan=one_rating_filtered['timeSpan'])
                    handle_record_found_more_than_one_exception(
                        e, logger=logger, exception_message_optional=exception_message_optional)
        status = "VOTE_SMART_RATINGS_BY_GROUP_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


# Retrieve the details about one group
def retrieve_vote_smart_special_interest_group_into_local_db(special_interest_group_id):
    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Rating.getSig')

        vote_smart_special_interest_group = votesmart.rating.getSig(special_interest_group_id)
        # Note that we use a different filter function when retrieving one group, than when we retrieve a list of groups
        vote_smart_special_interest_group_filtered = vote_smart_special_interest_group_filter(
            vote_smart_special_interest_group)
        vote_smart_special_interest_group_object, created = VoteSmartSpecialInterestGroup.objects.update_or_create(
            sigId=vote_smart_special_interest_group.sigId,
            defaults=vote_smart_special_interest_group_filtered)
        vote_smart_special_interest_group_object.save()
        status = "VOTE_SMART_SPECIAL_INTEREST_GROUP_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


# Retrieve list of groups
def retrieve_vote_smart_special_interest_groups_into_local_db(category_id, state_code='NA'):
    try:
        # Use Vote Smart API call counter to track the number of queries we are doing each day
        vote_smart_api_counter_manager = VoteSmartApiCounterManager()
        vote_smart_api_counter_manager.create_counter_entry('Rating.getSigList')

        special_interest_group_list = votesmart.rating.getSigList(category_id, state_code)
        for vote_smart_special_interest_group in special_interest_group_list:
            # Note that we use a different filter function when retrieving a list of groups vs. one group
            vote_smart_special_interest_group_filtered = vote_smart_special_interest_group_list_filter(
                vote_smart_special_interest_group)
            vote_smart_special_interest_group_object, created = VoteSmartSpecialInterestGroup.objects.update_or_create(
                sigId=vote_smart_special_interest_group.sigId,
                defaults=vote_smart_special_interest_group_filtered)
            vote_smart_special_interest_group_object.save()
        status = "VOTE_SMART_SPECIAL_INTEREST_GROUPS_PROCESSED"
        success = True
    except VotesmartApiError as error_instance:
        # Catch the error message coming back from Vote Smart and pass it in the status
        error_message = error_instance.args
        status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
        success = False

    results = {
        'status': status,
        'success': success,
    }
    return results


def _get_state_by_id_as_dict(state_id):
    """Access Vote Smart API and return dictionary representing state."""
    return votesmart.state.getState(state_id).__dict__


def _get_state_names():
    """Access Vote Smart API and return generator of all stateIds."""
    # Use Vote Smart API call counter to track the number of queries we are doing each day
    vote_smart_api_counter_manager = VoteSmartApiCounterManager()
    vote_smart_api_counter_manager.create_counter_entry('State.getStateIDs')

    state_ids_dict = votesmart.state.getStateIDs()
    return (state.stateId for state in state_ids_dict)


def retrieve_and_save_vote_smart_states():
    """Load/Update all states into database."""
    state_names_dict = _get_state_names()
    state_count = 0
    for stateId in state_names_dict:
        one_state = _get_state_by_id_as_dict(stateId)
        one_state_filtered = vote_smart_state_filter(one_state)
        state, created = VoteSmartState.objects.get_or_create(**one_state_filtered)
        # state, created = State.objects.get_or_create(**_get_state_by_id_as_dict(stateId))
        state.save()
        if state_count > 3:
            break
        state_count += 1


def get_api_route(cls, method):
    """Return full URI."""
    return "{url}/{cls}.{method}".format(
        url=VOTE_SMART_API_URL,
        cls=cls,
        method=method
    )


def make_request(cls, method, **kwargs):
    kwargs['key'] = VOTE_SMART_API_KEY
    if not kwargs.get('o'):
        kwargs['o'] = "JSON"
    url = get_api_route(cls, method)
    resp = requests.get(url, params=kwargs)
    if resp.status_code == 200:
        return resp.json()
    else:
        return resp.text


def transfer_vote_smart_ratings_to_positions_for_candidate(candidate_campaign_id):
    we_vote_organizations_created = 0
    organization_positions_that_exist = 0
    organization_positions_created = 0
    candidate_manager = CandidateCampaignManager()
    candidate_results = candidate_manager.retrieve_candidate_campaign_from_id(candidate_campaign_id)

    if candidate_results['candidate_campaign_found']:
        # Working with Vote Smart data
        candidate_campaign = candidate_results['candidate_campaign']
        if not positive_value_exists(candidate_campaign.vote_smart_id):
            status = "VOTE_SMART_ID_HAS_NOT_BEEN_RETRIEVED_YET_FOR_THIS_CANDIDATE: " \
                     "{candidate_campaign_id}".format(candidate_campaign_id=candidate_campaign_id)
            success = False
            results = {
                'status':   status,
                'success':  success,
                'we_vote_organizations_created':        we_vote_organizations_created,
                'organization_positions_that_exist':    organization_positions_that_exist,
                'organization_positions_created':       organization_positions_created,
            }
            return results
        else:
            try:
                rating_list_query = VoteSmartRatingOneCandidate.objects.order_by('-timeSpan')  # Desc order
                rating_list = rating_list_query.filter(candidateId=candidate_campaign.vote_smart_id)
            except Exception as error_instance:
                # Catch the error message coming back from Vote Smart and pass it in the status
                error_message = error_instance.args
                status = "EXCEPTION_RAISED: {error_message}".format(error_message=error_message)
                success = False
                results = {
                    'status':   status,
                    'success':  success,
                    'we_vote_organizations_created':        we_vote_organizations_created,
                    'organization_positions_that_exist':    organization_positions_that_exist,
                    'organization_positions_created':       organization_positions_created,
                }
                return results

        ratings_status = ""
        position_manager = PositionEnteredManager()
        special_interest_group_manager = VoteSmartSpecialInterestGroupManager()
        for one_candidate_rating in rating_list:
            # Make sure we have all of the required variables
            if not one_candidate_rating.sigId:
                ratings_status += "MISSING_SPECIAL_INTEREST_GROUP_ID-{ratingId} * " \
                                  "".format(ratingId=one_candidate_rating.ratingId)
                continue
            # Make sure an organization exists and is updated with Vote Smart info
            update_results = special_interest_group_manager.update_or_create_we_vote_organization(
                one_candidate_rating.sigId)
            if not update_results['organization_found']:
                # TRY AGAIN: Reach out to Vote Smart and try to retrieve this special interest group by sigId
                one_group_results = retrieve_vote_smart_special_interest_group_into_local_db(one_candidate_rating.sigId)

                if one_group_results['success']:
                    update_results = special_interest_group_manager.update_or_create_we_vote_organization(
                        one_candidate_rating.sigId)

            if not update_results['organization_found']:
                ratings_status += "COULD_NOT_FIND_OR_SAVE_NEW_SIG-{sigId}-{status} * " \
                                  "".format(sigId=one_candidate_rating.sigId,
                                            status=update_results['status'])
                continue
            else:
                we_vote_organization = update_results['organization']
                if update_results['organization_created']:
                    we_vote_organizations_created += 1

            # Check to see if a position already exists
            # TODO DALE Note: we need to consider searching with a time span variable
            # (in addition to just org and candidate identifiers) since I believe
            # Google Civic gives a person a new candidate campaign ID each election,
            # while Vote Smart uses the same candidateId from year to year
            organization_position_results = position_manager.retrieve_organization_candidate_campaign_position(
                we_vote_organization.id, candidate_campaign_id)

            if positive_value_exists(organization_position_results['position_found']):
                # For now, we only want to create positions that don't exist
                organization_positions_that_exist += 1
                continue
            else:
                position_results = position_manager.update_or_create_position(
                    position_id=0,
                    position_we_vote_id=False,
                    organization_we_vote_id=we_vote_organization.we_vote_id,
                    public_figure_we_vote_id=False,
                    voter_we_vote_id=False,
                    google_civic_election_id=False,
                    ballot_item_display_name=candidate_campaign.display_candidate_name(),
                    office_we_vote_id=False,
                    candidate_we_vote_id=candidate_campaign.we_vote_id,
                    measure_we_vote_id=False,
                    stance=PERCENT_RATING,
                    statement_text=one_candidate_rating.ratingText,
                    statement_html=False,
                    more_info_url=False,
                    vote_smart_time_span=one_candidate_rating.timeSpan,
                    vote_smart_rating_id=one_candidate_rating.ratingId,
                    vote_smart_rating=one_candidate_rating.rating,
                    vote_smart_rating_name=one_candidate_rating.ratingName,
                )

                if positive_value_exists(position_results['success']):
                    organization_positions_created += 1
                else:
                    ratings_status += "COULD_NOT_CREATE_POSITION-{sigId}-{status} * " \
                                      "".format(sigId=one_candidate_rating.sigId,
                                                status=position_results['status'])

    success = True
    status = "TRANSFER_PROCESS_COMPLETED: " + ratings_status

    results = {
        'status':   status,
        'success':  success,
        'we_vote_organizations_created':        we_vote_organizations_created,
        'organization_positions_that_exist':    organization_positions_that_exist,
        'organization_positions_created':       organization_positions_created,
    }

    return results


def transfer_vote_smart_special_interest_groups_to_we_vote_organizations():
    organizations_errors = ''
    number_of_we_vote_organizations_created = 0
    number_of_we_vote_organizations_updated = 0

    special_interest_group_query = VoteSmartSpecialInterestGroup.objects.order_by('sigId')
    special_interest_group_list = special_interest_group_query

    special_interest_group_manager = VoteSmartSpecialInterestGroupManager()

    # process_count = 0
    for special_interest_group in special_interest_group_list:
        # NOTE As of 2016-02-13 We are creating new org entries with all data, and updating email and url
        #  only if the fields are empty updating
        update_results = special_interest_group_manager.update_or_create_we_vote_organization(
            special_interest_group.sigId)

        if not update_results['organization_found']:
            organizations_errors += "FAILED-{sigId}-{status} * " \
                              "".format(sigId=special_interest_group.sigId,
                                        status=update_results['status'])

        if update_results['organization_created']:
            number_of_we_vote_organizations_created += 1
        if update_results['organization_updated']:
            number_of_we_vote_organizations_updated += 1
        # process_count += 1
        # if process_count > 50:  # TODO DALE Temp limit
        #     break

    success = True
    status = "SIG_TRANSFER_PROCESS_COMPLETED, {number_created} orgs created, " \
             " {number_updated} orgs updated. {organizations_errors}" \
             "".format(number_created=number_of_we_vote_organizations_created,
                       number_updated=number_of_we_vote_organizations_updated,
                       organizations_errors=organizations_errors)

    results = {
        'status':   status,
        'success':  success,
    }

    return results
