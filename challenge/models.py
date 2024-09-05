# challenge/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json

from django.db import models
from django.db.models import Q

import wevote_functions.admin
from exception.models import handle_record_found_more_than_one_exception, \
    handle_record_not_found_exception
from organization.models import Organization, OrganizationManager, OrganizationTeamMember
from politician.models import Politician
from wevote_functions.functions import convert_to_int, \
    extract_first_name_from_full_name, extract_middle_name_from_full_name, \
    extract_last_name_from_full_name, \
    positive_value_exists
from wevote_functions.functions_date import generate_date_as_integer
from wevote_settings.models import fetch_next_we_vote_id_challenge_integer, \
    fetch_next_we_vote_id_challenge_news_item_integer, fetch_site_unique_id_prefix

logger = wevote_functions.admin.get_logger(__name__)

# When merging Challenge entries, these are the fields we check for figure_out_challenge_conflict_values
CHALLENGE_UNIQUE_IDENTIFIERS = [
    'challenge_description',
    'challenge_title',
    'date_challenge_started',
    'final_election_date_as_integer',
    'in_draft_mode',
    'is_blocked_by_we_vote',
    'is_blocked_by_we_vote_reason',
    'is_in_team_review_mode',
    'is_not_promoted_by_we_vote',
    'is_not_promoted_by_we_vote_reason',
    'is_ok_to_promote_on_we_vote',
    'is_still_active',
    'is_victorious',
    'politician_we_vote_id',
    'politician_starter_list_serialized',
    'seo_friendly_path',
    'state_code',
    'started_by_voter_we_vote_id',
    'supporters_count',
    'supporters_count_minimum_ignored',
    'supporters_count_victory_goal',
    'we_vote_hosted_challenge_photo_large_url',
    'we_vote_hosted_challenge_photo_medium_url',
    'we_vote_hosted_challenge_photo_original_url',
    'we_vote_hosted_challenge_photo_small_url',
    'we_vote_hosted_profile_image_url_large',
    'we_vote_hosted_profile_image_url_medium',
    'we_vote_hosted_profile_image_url_tiny',
]

CHALLENGE_UNIQUE_ATTRIBUTES_TO_BE_CLEARED = [
    'seo_friendly_path',
]

FINAL_ELECTION_DATE_COOL_DOWN = 7
SUPPORTERS_COUNT_MINIMUM_FOR_LISTING = 0  # How many supporters are required before we will show challenge on We Vote


class Challenge(models.Model):
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None

    def __unicode__(self):
        return "Challenge"

    # These are challenges anyone can start to encourage other voters to do specific actions.
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "chal", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_challenge_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)
    challenge_description = models.TextField(null=True, blank=True)
    challenge_title = models.CharField(verbose_name="title of challenge", max_length=255, null=False, blank=False)
    date_last_updated_from_politician = models.DateTimeField(null=True, default=None)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20240901" for September, 1, 2024)
    final_election_date_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    # Has not been released for view
    in_draft_mode = models.BooleanField(default=True, db_index=True)
    # Challenge owner allows challenge to be promoted by We Vote on free home page and elsewhere
    is_ok_to_promote_on_we_vote = models.BooleanField(default=True, db_index=True)
    # Settings controlled by We Vote staff
    is_blocked_by_we_vote = models.BooleanField(default=False, db_index=True)
    is_blocked_by_we_vote_reason = models.TextField(null=True, blank=True)
    is_in_team_review_mode = models.BooleanField(default=False, db_index=True)
    is_not_promoted_by_we_vote = models.BooleanField(default=False, db_index=True)
    is_not_promoted_by_we_vote_reason = models.TextField(null=True, blank=True)
    is_still_active = models.BooleanField(default=True, db_index=True)
    is_victorious = models.BooleanField(default=False, db_index=True)
    # This is saying that this Challenge is in service of this politician
    #  We use the ChallengePolitician table to store links to politicians when supporting or opposing.
    politician_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    politician_we_vote_id_verified = models.BooleanField(default=False, null=False)
    # If this Challenge has a politician_we_vote_id, then opposers_count comes from Organization opposers
    opposers_count = models.PositiveIntegerField(default=0)
    # organization_we_vote_id is the id of the Endorser/Politician/Organization that started this challenge
    organization_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    politician_starter_list_serialized = models.TextField(null=True, blank=True)
    profile_image_background_color = models.CharField(blank=True, null=True, max_length=7)
    seo_friendly_path = models.CharField(max_length=255, null=True, unique=False, db_index=True)
    started_by_voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    state_code = models.CharField(max_length=2, null=True)  # If focused on one state. Based on politician state_code.
    # If this Challenge has a politician_we_vote_id, then supporters_count comes from Organization followers
    supporters_count = models.PositiveIntegerField(default=0)
    # Updates both supporters_count and opposers_count from the position_list page in position/views_admin.py
    supporters_count_to_update_with_bulk_script = models.BooleanField(default=True)
    # How many supporters are required before showing in We Vote lists
    supporters_count_minimum_ignored = models.BooleanField(default=False, db_index=True)
    supporters_count_victory_goal = models.PositiveIntegerField(default=0)
    we_vote_hosted_challenge_photo_original_url = models.TextField(blank=True, null=True)
    # Full sized desktop
    we_vote_hosted_challenge_photo_large_url = models.TextField(blank=True, null=True)
    # Maximum size needed for desktop lists
    we_vote_hosted_challenge_photo_medium_url = models.TextField(blank=True, null=True)
    # Maximum size needed for image grids - Stored as "tiny" image
    we_vote_hosted_challenge_photo_small_url = models.TextField(blank=True, null=True)
    # Image we are using as the profile photo for politician (copied over and cached here)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    date_challenge_started = models.DateTimeField(null=True, auto_now_add=True, db_index=True)

    def is_supporters_count_minimum_exceeded(self):
        if positive_value_exists(self.supporters_count_minimum_ignored) or \
                self.supporters_count >= SUPPORTERS_COUNT_MINIMUM_FOR_LISTING:
            return True
        return False

    def politician(self):
        try:
            politician = Politician.objects.using('readonly').get(we_vote_id=self.politician_we_vote_id)
        except Politician.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("Challenge.politician Found multiple")
            return
        except Politician.DoesNotExist:
            logger.error("Challenge.politician not attached to object, id: " + str(self.politician_we_vote_id))
            return
        except Exception as e:
            return
        return politician

    # We override the save function, so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_challenge_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "chal" = tells us this is a unique id for a Challenge
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}chal{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(Challenge, self).save(*args, **kwargs)


class ChallengesAreNotDuplicates(models.Model):
    """
    When checking for duplicates, there are times we want to explicitly mark two Challenge entries as NOT duplicates
    """
    challenge1_we_vote_id = models.CharField(
        verbose_name="first challenge we are tracking", max_length=255, null=True, unique=False, db_index=True)
    challenge2_we_vote_id = models.CharField(
        verbose_name="second challenge we are tracking", max_length=255, null=True, unique=False, db_index=True)

    def fetch_other_challenge_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.challenge1_we_vote_id:
            return self.challenge2_we_vote_id
        elif one_we_vote_id == self.challenge2_we_vote_id:
            return self.challenge1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class ChallengesArePossibleDuplicates(models.Model):
    """
    When checking for duplicates, there are times when we want to explicitly mark two entries as possible duplicates
    """
    challenge1_we_vote_id = models.CharField(max_length=255, null=True, unique=False, db_index=True)
    challenge2_we_vote_id = models.CharField(max_length=255, null=True, unique=False, db_index=True)
    state_code = models.CharField(max_length=2, null=True)

    def fetch_other_challenge_we_vote_id(self, one_we_vote_id):
        if one_we_vote_id == self.challenge1_we_vote_id:
            return self.challenge2_we_vote_id
        elif one_we_vote_id == self.challenge2_we_vote_id:
            return self.challenge1_we_vote_id
        else:
            # If the we_vote_id passed in wasn't found, don't return another we_vote_id
            return ""


class ChallengeListedByOrganization(models.Model):
    """
    An individual or organization can specify a challenge as one they want to list on their private-labeled site.
    This is the link that says "show this challenge on my promotion site".
    """
    objects = None

    def __unicode__(self):
        return "ChallengeListedByOrganization"

    challenge_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    site_owner_organization_we_vote_id = models.CharField(
        max_length=255, null=True, blank=True, unique=False, db_index=True)
    # If a candidate or challenge-starter requests to be included in a private label site:
    listing_requested_by_voter_we_vote_id = \
        models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    # Is this link approved and made visible?
    visible_to_public = models.BooleanField(default=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)


class ChallengeManager(models.Manager):

    def __unicode__(self):
        return "ChallengeManager"

    def fetch_challenges_are_not_duplicates_list_we_vote_ids(self, challenge_we_vote_id):
        results = self.retrieve_challenges_are_not_duplicates_list(challenge_we_vote_id)
        return results['challenges_are_not_duplicates_list_we_vote_ids']

    @staticmethod
    def fetch_challenges_from_non_unique_identifiers_count(
            challenge_title='',
            ignore_challenge_we_vote_id_list=[],
            politician_name='',
            state_code=''):
        keep_looking_for_duplicates = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(challenge_title):
            try:
                queryset = Challenge.objects.using('readonly').all()
                queryset = queryset.filter(challenge_title__iexact=challenge_title)

                if positive_value_exists(ignore_challenge_we_vote_id_list):
                    queryset = queryset.exclude(we_vote_id__in=ignore_challenge_we_vote_id_list)

                challenge_count = queryset.count()
                if positive_value_exists(challenge_count):
                    return challenge_count
            except Challenge.DoesNotExist:
                status += "FETCH_CHALLENGES_FROM_NON_UNIQUE_IDENTIFIERS_COUNT1 "

        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search by Candidate name exact match
            try:
                queryset = Challenge.objects.using('readonly').all()
                queryset = queryset.filter(
                    Q(challenge_title__icontains=politician_name) |
                    Q(challenge_description__icontains=politician_name)
                )
                if positive_value_exists(state_code):
                    queryset = queryset.filter(state_code__iexact=state_code)
                if positive_value_exists(ignore_challenge_we_vote_id_list):
                    queryset = queryset.exclude(we_vote_id__in=ignore_challenge_we_vote_id_list)
                challenge_count = queryset.count()
                if positive_value_exists(challenge_count):
                    return challenge_count
            except Challenge.DoesNotExist:
                status += "FETCH_CHALLENGES_FROM_NON_UNIQUE_IDENTIFIERS_COUNT2 "

        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search for Candidate(s) that contains the same first and last names
            first_name = extract_first_name_from_full_name(politician_name)
            last_name = extract_last_name_from_full_name(politician_name)
            if positive_value_exists(first_name) and positive_value_exists(last_name):
                try:
                    queryset = Challenge.objects.using('readonly').all()
                    queryset = Challenge.objects.using('readonly').all()
                    queryset = queryset.filter(
                        (Q(challenge_title__icontains=first_name) & Q(challenge_title__icontains=last_name)) |
                        (Q(challenge_description__icontains=first_name) &
                         Q(challenge_description__icontains=last_name))
                    )
                    if positive_value_exists(state_code):
                        queryset = queryset.filter(state_code__iexact=state_code)
                    if positive_value_exists(ignore_challenge_we_vote_id_list):
                        queryset = queryset.exclude(we_vote_id__in=ignore_challenge_we_vote_id_list)
                    challenge_count = queryset.count()
                    if positive_value_exists(challenge_count):
                        return challenge_count
                except Challenge.DoesNotExist:
                    status += "FETCH_CHALLENGES_FROM_NON_UNIQUE_IDENTIFIERS_COUNT3 "

        return 0

    @staticmethod
    def fetch_challenge_supporter_count(challenge_we_vote_id=None):
        status = ""

        try:
            challenge_queryset = ChallengeSupporter.objects.using('readonly').all()
            challenge_queryset = challenge_queryset.filter(challenge_we_vote_id=challenge_we_vote_id)
            return challenge_queryset.count()
        except Exception as e:
            status += "RETRIEVE_CHALLENGE_SUPPORTER_LIST_FAILED: " + str(e) + " "

        return 0

    @staticmethod
    def fetch_challenge_news_item_count(challenge_we_vote_id=None):
        status = ""

        try:
            challenge_queryset = ChallengeNewsItem.objects.using('readonly').all()
            challenge_queryset = challenge_queryset.filter(challenge_we_vote_id=challenge_we_vote_id)
            return challenge_queryset.count()
        except Exception as e:
            status += "RETRIEVE_CHALLENGE_NEWS_UPDATE_COUNT_FAILED: " + str(e) + " "

        return 0

    @staticmethod
    def fetch_next_goal_level(
            supporters_count=1,
            tier_size=1000):
        try:
            supporters_count = convert_to_int(supporters_count)
        except Exception as e:
            supporters_count = 0
        try:
            tier_size = convert_to_int(tier_size)
        except Exception as e:
            tier_size = 1000
        return supporters_count if supporters_count % tier_size == 0 \
            else supporters_count + tier_size - supporters_count % tier_size

    def fetch_challenge_we_vote_id_list_from_owner_organization_we_vote_id(self, organization_we_vote_id):
        owner_list = self.retrieve_challenge_owner_list(
            organization_we_vote_id=organization_we_vote_id, read_only=True)
        challenge_we_vote_id_list = []
        for owner in owner_list:
            challenge_we_vote_id_list.append(owner.challenge_we_vote_id)
        return challenge_we_vote_id_list

    def fetch_supporters_count_next_goal(
            self,
            supporters_count=1,
            supporters_count_victory_goal=0):
        try:
            supporters_count = convert_to_int(supporters_count)
        except Exception as e:
            supporters_count = 0
        try:
            supporters_count_victory_goal = convert_to_int(supporters_count_victory_goal)
        except Exception as e:
            supporters_count_victory_goal = 0
        if supporters_count_victory_goal >= supporters_count:
            return supporters_count
        try:
            if supporters_count >= 100000:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=50000)
            elif supporters_count >= 25000:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=25000)
            elif supporters_count >= 10000:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=15000)
            elif supporters_count >= 5000:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=5000)
            elif supporters_count >= 2500:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=2500)
            elif supporters_count >= 1000:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=1500)
            elif supporters_count >= 500:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=500)
            elif supporters_count >= 250:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=250)
            elif supporters_count >= 125:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=125)
            elif supporters_count >= 50:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=50)
            elif supporters_count >= 10:
                return self.fetch_next_goal_level(supporters_count=supporters_count, tier_size=10)
            else:
                return 10
        except Exception as e:
            return 0

    @staticmethod
    def generate_seo_friendly_path(base_pathname_string='', challenge_we_vote_id='', challenge_title=None):
        """
        Generate the closest possible SEO friendly path for this challenge. Note that these paths
        are only generated for challenges which are already published.
        :param base_pathname_string:
        :param challenge_we_vote_id:
        :param challenge_title:
        :return:
        """
        from politician.controllers_generate_seo_friendly_path import generate_seo_friendly_path_generic
        return generate_seo_friendly_path_generic(
            base_pathname_string=base_pathname_string,
            for_campaign=False,
            for_challenge=True,
            for_politician=False,
            challenge_title=challenge_title,
            challenge_we_vote_id=challenge_we_vote_id,
        )

    @staticmethod
    def is_voter_challenge_owner(challenge_we_vote_id='', voter_we_vote_id=''):
        """
        We will also need functions that return the rights of the voter:
        - can_edit_challenge_owned_by_organization
        - can_moderate_challenge_owned_by_organization
        - can_send_updates_for_challenge_owned_by_organization
        :param challenge_we_vote_id:
        :param voter_we_vote_id:
        :return:
        """
        status = ''
        continue_checking = True
        voter_is_challenge_owner = False

        try:
            challenge_owner_query = ChallengeOwner.objects.using('readonly').filter(
                challenge_we_vote_id=challenge_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            voter_is_challenge_owner = positive_value_exists(challenge_owner_query.count())
            status += 'VOTER_IS_CHALLENGE_OWNER '
        except ChallengeOwner as e:
            continue_checking = False
            status += 'CHALLENGE_OWNER_QUERY_FAILED: ' + str(e) + ' '

        if continue_checking and not voter_is_challenge_owner:
            teams_voter_is_on_organization_we_vote_id_list = []
            try:
                # Which teams does this voter belong to, with challenge rights?
                team_member_queryset = OrganizationTeamMember.objects.using('readonly').filter(
                    voter_we_vote_id=voter_we_vote_id)
                team_member_queryset = team_member_queryset.filter(
                    Q(can_edit_challenge_owned_by_organization=True) |
                    Q(can_moderate_challenge_owned_by_organization=True) |
                    Q(can_send_updates_for_challenge_owned_by_organization=True))
                team_member_queryset = team_member_queryset.values_list('organization_we_vote_id', flat=True).distinct()
                teams_voter_is_on_organization_we_vote_id_list = list(team_member_queryset)
            except OrganizationTeamMember as e:
                status += 'CHALLENGE_OWNER_FROM_TEAM_QUERY_FAILED: ' + str(e) + ' '
            # Now see if this challenge is owned by any of the teams this voter belongs to
            if len(teams_voter_is_on_organization_we_vote_id_list) > 0:
                try:
                    owner_queryset = ChallengeOwner.objects.using('readonly').filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        organization_we_vote_id__in=teams_voter_is_on_organization_we_vote_id_list)
                    voter_is_challenge_owner = positive_value_exists(owner_queryset.count())
                    status += 'VOTER_IS_CHALLENGE_OWNER_AS_TEAM_MEMBER '
                except ChallengeOwner as e:
                    status += 'CHALLENGE_OWNER_AS_TEAM_MEMBER_QUERY_FAILED: ' + str(e) + ' '

        return voter_is_challenge_owner

    @staticmethod
    def is_voter_challenge_supporter(challenge_we_vote_id='', voter_we_vote_id=''):
        """

        :param challenge_we_vote_id:
        :param voter_we_vote_id:
        :return:
        """
        status = ''
        voter_is_challenge_owner = False

        try:
            queryset = ChallengeSupporter.objects.using('readonly').filter(
                challenge_we_vote_id=challenge_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            voter_is_challenge_owner = positive_value_exists(queryset.count())
            status += 'VOTER_IS_CHALLENGE_SUPPORTER '
        except ChallengeSupporter as e:
            status += 'IS_VOTER_CHALLENGE_SUPPORTER_QUERY_FAILED: ' + str(e) + ' '

        return voter_is_challenge_owner

    def remove_challenge_owner(self, challenge_we_vote_id='', voter_we_vote_id=''):
        return

    @staticmethod
    def remove_challenge_politicians_from_delete_list(challenge_we_vote_id='', politician_delete_list=''):
        success = True
        status = ''
        challenge_manager = ChallengeManager()
        challenge_politician_list = \
            challenge_manager.retrieve_challenge_politician_list(
                challenge_we_vote_id=challenge_we_vote_id, read_only=False)

        for challenge_politician in challenge_politician_list:
            if challenge_politician.id in politician_delete_list:
                try:
                    challenge_politician.delete()
                except Exception as e:
                    status += "DELETE_FAILED: " + str(e) + ' '
                    success = False

        results = {
            'status':                       status,
            'success':                      success,
        }
        return results

    @staticmethod
    def retrieve_challenge_as_owner(
            challenge_we_vote_id='',
            seo_friendly_path='',
            voter_we_vote_id='',
            read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        challenge = None
        challenge_manager = ChallengeManager()
        challenge_owner_list = []
        seo_friendly_path_list = []
        status = ''
        viewer_is_owner = False

        if positive_value_exists(challenge_we_vote_id):
            viewer_is_owner = challenge_manager.is_voter_challenge_owner(
                challenge_we_vote_id=challenge_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)

        try:
            if positive_value_exists(challenge_we_vote_id):
                if positive_value_exists(read_only):
                    challenge = Challenge.objects.using('readonly').get(we_vote_id=challenge_we_vote_id)
                else:
                    challenge = Challenge.objects.get(we_vote_id=challenge_we_vote_id)
                challenge_found = True
                challenge_we_vote_id = challenge.we_vote_id
                status += 'RETRIEVE_CHALLENGE_AS_OWNER_FOUND_WITH_WE_VOTE_ID '
                success = True
            elif positive_value_exists(seo_friendly_path):
                if positive_value_exists(read_only):
                    challenge = Challenge.objects.using('readonly').get(seo_friendly_path__iexact=seo_friendly_path)
                else:
                    challenge = Challenge.objects.get(seo_friendly_path__iexact=seo_friendly_path)
                challenge_found = True
                challenge_we_vote_id = challenge.we_vote_id
                status += 'RETRIEVE_CHALLENGE_AS_OWNER_FOUND_WITH_SEO_FRIENDLY_PATH '
                success = True
            elif positive_value_exists(voter_we_vote_id):
                # If ONLY the voter_we_vote_id is passed in, get the challenge for that voter in draft mode
                if positive_value_exists(read_only):
                    query = Challenge.objects.using('readonly').filter(
                        in_draft_mode=True,
                        started_by_voter_we_vote_id=voter_we_vote_id)
                else:
                    query = Challenge.objects.filter(
                        in_draft_mode=True,
                        started_by_voter_we_vote_id=voter_we_vote_id)
                query = query.order_by('-id')
                draft_challenge_list = list(query)
                if len(draft_challenge_list) > 0:
                    challenge = draft_challenge_list[0]
                    challenge_found = True
                    challenge_we_vote_id = challenge.we_vote_id
                    viewer_is_owner = True
                    status += 'RETRIEVE_CHALLENGE_AS_OWNER_FOUND_WITH_VOTER_WE_VOTE_ID-IN_DRAFT_MODE '
                    if len(draft_challenge_list) > 1:
                        exception_multiple_object_returned = True
                        status += '(NUMBER_FOUND: ' + str(len(draft_challenge_list)) + ') '
                else:
                    challenge_found = False
                    status += 'RETRIEVE_CHALLENGE_AS_OWNER_NOT_FOUND_USING_VOTER_WE_VOTE_ID '
                success = True
            else:
                status += 'RETRIEVE_CHALLENGE_AS_OWNER_NOT_FOUND-MISSING_VARIABLES '
                success = False
                challenge_found = False
        except Challenge.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            challenge_found = False
            challenge_we_vote_id = ''
            exception_multiple_object_returned = True
            status += 'RETRIEVE_CHALLENGE_AS_OWNER_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except Challenge.DoesNotExist:
            challenge_found = False
            challenge_we_vote_id = ''
            exception_does_not_exist = True
            status += 'RETRIEVE_CHALLENGE_AS_OWNER_NOT_FOUND_DoesNotExist '
            success = True
        except Exception as e:
            challenge_found = False
            challenge_we_vote_id = ''
            status += 'RETRIEVE_CHALLENGE_AS_OWNER_NOT_FOUND_ERROR: ' + str(e) + ' '
            success = False

        if positive_value_exists(challenge_found):
            challenge_owner_object_list = challenge_manager.retrieve_challenge_owner_list(
                challenge_we_vote_id_list=[challenge_we_vote_id], viewer_is_owner=viewer_is_owner)

            for challenge_owner in challenge_owner_object_list:
                challenge_owner_organization_name = '' if challenge_owner.organization_name is None \
                    else challenge_owner.organization_name
                challenge_owner_organization_we_vote_id = '' if challenge_owner.organization_we_vote_id is None \
                    else challenge_owner.organization_we_vote_id
                challenge_owner_we_vote_hosted_profile_image_url_medium = '' \
                    if challenge_owner.we_vote_hosted_profile_image_url_medium is None \
                    else challenge_owner.we_vote_hosted_profile_image_url_medium
                challenge_owner_we_vote_hosted_profile_image_url_tiny = '' \
                    if challenge_owner.we_vote_hosted_profile_image_url_tiny is None \
                    else challenge_owner.we_vote_hosted_profile_image_url_tiny
                challenge_owner_dict = {
                    'organization_name':                        challenge_owner_organization_name,
                    'organization_we_vote_id':                  challenge_owner_organization_we_vote_id,
                    'feature_this_profile_image':               challenge_owner.feature_this_profile_image,
                    'visible_to_public':                        challenge_owner.visible_to_public,
                    'we_vote_hosted_profile_image_url_medium':
                        challenge_owner_we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_image_url_tiny': challenge_owner_we_vote_hosted_profile_image_url_tiny,
                }
                challenge_owner_list.append(challenge_owner_dict)

            seo_friendly_path_list = \
                challenge_manager.retrieve_seo_friendly_path_simple_list(
                    challenge_we_vote_id=challenge_we_vote_id)

            # challenge_politician_object_list = challenge_manager.retrieve_challenge_politician_list(
            #     challenge_we_vote_id=challenge_we_vote_id)
            #
            # for challenge_politician in challenge_politician_object_list:
            #     challenge_politician_organization_name = '' if challenge_politician.organization_name is None \
            #         else challenge_politician.organization_name
            #     challenge_politician_organization_we_vote_id = '' \
            #         if challenge_politician.organization_we_vote_id is None \
            #         else challenge_politician.organization_we_vote_id
            #     challenge_politician_we_vote_hosted_profile_image_url_tiny = '' \
            #         if challenge_politician.we_vote_hosted_profile_image_url_tiny is None \
            #         else challenge_politician.we_vote_hosted_profile_image_url_tiny
            #     challenge_politician_dict = {
            #         'organization_name':                        challenge_politician_organization_name,
            #         'organization_we_vote_id':                  challenge_politician_organization_we_vote_id,
            #         'we_vote_hosted_profile_image_url_tiny':
            #         challenge_politician_we_vote_hosted_profile_image_url_tiny,
            #         'visible_to_public':                        challenge_politician.visible_to_public,
            #     }
            #     challenge_politician_list.append(challenge_politician_dict)

        results = {
            'status':                       status,
            'success':                      success,
            'challenge':                    challenge,
            'challenge_found':              challenge_found,
            'challenge_we_vote_id':         challenge_we_vote_id,
            'challenge_owner_list':         challenge_owner_list,
            'seo_friendly_path_list':       seo_friendly_path_list,
            'viewer_is_owner':              viewer_is_owner,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    @staticmethod
    def retrieve_challenge(
            challenge_we_vote_id='',
            politician_we_vote_id='',
            seo_friendly_path='',
            voter_we_vote_id='',
            read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        challenge = None
        challenge_found = False
        challenge_manager = ChallengeManager()
        challenge_owner_list = []
        seo_friendly_path_list = []
        status = ''
        viewer_is_owner = False

        try:
            if positive_value_exists(challenge_we_vote_id):
                if positive_value_exists(read_only):
                    challenge = Challenge.objects.using('readonly').get(we_vote_id=challenge_we_vote_id)
                else:
                    challenge = Challenge.objects.get(we_vote_id=challenge_we_vote_id)
                challenge_found = True
                status += 'CHALLENGE_FOUND_WITH_WE_VOTE_ID '
                success = True
            elif positive_value_exists(politician_we_vote_id):
                if positive_value_exists(read_only):
                    challenge = Challenge.objects.using('readonly')\
                        .get(politician_we_vote_id=politician_we_vote_id)
                else:
                    challenge = Challenge.objects.get(politician_we_vote_id=politician_we_vote_id)
                challenge_found = True
                status += 'CHALLENGE_FOUND_WITH_LINKED_POLITICIAN_WE_VOTE_ID '
                success = True
            elif positive_value_exists(seo_friendly_path):
                if positive_value_exists(read_only):
                    challenge = Challenge.objects.using('readonly').get(seo_friendly_path__iexact=seo_friendly_path)
                else:
                    challenge = Challenge.objects.get(seo_friendly_path__iexact=seo_friendly_path)
                challenge_found = True
                challenge_we_vote_id = challenge.we_vote_id
                status += 'CHALLENGE_FOUND_WITH_SEO_FRIENDLY_PATH '
                success = True
            else:
                status += 'CHALLENGE_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except Challenge.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += 'CHALLENGE_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except Challenge.DoesNotExist:
            exception_does_not_exist = True
            status += 'CHALLENGE_NOT_FOUND_DoesNotExist '
            success = True

        if positive_value_exists(challenge_found):
            if positive_value_exists(challenge_we_vote_id) and positive_value_exists(voter_we_vote_id):
                viewer_is_owner = challenge_manager.is_voter_challenge_owner(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id)

            challenge_owner_object_list = challenge_manager.retrieve_challenge_owner_list(
                challenge_we_vote_id_list=[challenge_we_vote_id], viewer_is_owner=False)
            for challenge_owner in challenge_owner_object_list:
                challenge_owner_dict = {
                    'organization_name':                        challenge_owner.organization_name,
                    'organization_we_vote_id':                  challenge_owner.organization_we_vote_id,
                    'feature_this_profile_image':               challenge_owner.feature_this_profile_image,
                    'visible_to_public':                        challenge_owner.visible_to_public,
                    'we_vote_hosted_profile_image_url_medium':  challenge_owner.we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_image_url_tiny':    challenge_owner.we_vote_hosted_profile_image_url_tiny,
                }
                challenge_owner_list.append(challenge_owner_dict)

            seo_friendly_path_list = \
                challenge_manager.retrieve_seo_friendly_path_simple_list(
                    challenge_we_vote_id=challenge_we_vote_id)

        results = {
            'status':                   status,
            'success':                  success,
            'challenge':                challenge,
            'challenge_found':          challenge_found,
            'challenge_we_vote_id':     challenge_we_vote_id,
            'challenge_owner_list':     challenge_owner_list,
            'seo_friendly_path_list':   seo_friendly_path_list,
            'viewer_is_owner':          viewer_is_owner,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results

    @staticmethod
    def retrieve_challenge_listed_by_organization_list(
            site_owner_organization_we_vote_id='',
            visible_to_public=True,
            ignore_visible_to_public=False,
            read_only=True):
        challenge_listed_by_organization_list_found = False
        challenge_listed_by_organization_list = []
        try:
            if read_only:
                query = ChallengeListedByOrganization.objects.using('readonly').all()
            else:
                query = ChallengeListedByOrganization.objects.all()
            query = query.filter(site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            if not positive_value_exists(ignore_visible_to_public):
                query = query.filter(visible_to_public=visible_to_public)
            challenge_listed_by_organization_list = list(query)
            if len(challenge_listed_by_organization_list):
                challenge_listed_by_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if challenge_listed_by_organization_list_found:
            return challenge_listed_by_organization_list
        else:
            challenge_listed_by_organization_list = []
            return challenge_listed_by_organization_list

    def retrieve_challenge_listed_by_organization_simple_list(
            self,
            site_owner_organization_we_vote_id='',
            visible_to_public=True):
        challenge_listed_by_organization_list = \
            self.retrieve_challenge_listed_by_organization_list(
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
                visible_to_public=visible_to_public,
                read_only=True)
        simple_list = []
        for one_link in challenge_listed_by_organization_list:
            simple_list.append(one_link.challenge_we_vote_id)
        simple_list = list(set(simple_list))
        return simple_list

    def retrieve_challenge_we_vote_ids_in_order(self, site_owner_organization_we_vote_id=''):
        simple_list = []
        challenge_owned_by_organization_list = \
            self.retrieve_challenge_owner_list(
                organization_we_vote_id=site_owner_organization_we_vote_id,
                has_order_in_list=True,
                read_only=True)
        for one_owner in challenge_owned_by_organization_list:
            simple_list.append(one_owner.challenge_we_vote_id)

        return simple_list

    def retrieve_visible_on_this_site_challenge_simple_list(
            self,
            site_owner_organization_we_vote_id='',
            visible_to_public=True):
        challenge_listed_by_organization_list = \
            self.retrieve_challenge_listed_by_organization_list(
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
                visible_to_public=visible_to_public,
                read_only=True)
        simple_list = []
        for one_link in challenge_listed_by_organization_list:
            simple_list.append(one_link.challenge_we_vote_id)

        challenge_owned_by_organization_list = \
            self.retrieve_challenge_owner_list(organization_we_vote_id=site_owner_organization_we_vote_id)
        for one_owner in challenge_owned_by_organization_list:
            simple_list.append(one_owner.challenge_we_vote_id)

        simple_list = list(set(simple_list))
        return simple_list

    @staticmethod
    def retrieve_challenges_are_not_duplicates_list(challenge_we_vote_id, read_only=True):
        """
        Get a list of other challenge_we_vote_id's that are not duplicates
        :param challenge_we_vote_id:
        :param read_only:
        :return:
        """
        # Note that the direction of the linkage does not matter
        challenges_are_not_duplicates_list1 = []
        challenges_are_not_duplicates_list2 = []
        status = ""
        try:
            if positive_value_exists(read_only):
                challenges_are_not_duplicates_list_query = \
                    ChallengesAreNotDuplicates.objects.using('readonly').filter(
                        challenge1_we_vote_id=challenge_we_vote_id,
                    )
            else:
                challenges_are_not_duplicates_list_query = ChallengesAreNotDuplicates.objects.filter(
                    challenge1_we_vote_id=challenge_we_vote_id,
                )
            challenges_are_not_duplicates_list1 = list(challenges_are_not_duplicates_list_query)
            success = True
            status += "CHALLENGES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED1 "
        except ChallengesAreNotDuplicates.DoesNotExist:
            # No data found. Try again below
            success = True
            status += 'NO_CHALLENGES_NOT_DUPLICATES_LIST_RETRIEVED_DoesNotExist1 '
        except Exception as e:
            success = False
            status += "CHALLENGES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED1: " + str(e) + ' '

        if success:
            try:
                if positive_value_exists(read_only):
                    challenges_are_not_duplicates_list_query = \
                        ChallengesAreNotDuplicates.objects.using('readonly').filter(
                            challenge2_we_vote_id=challenge_we_vote_id,
                        )
                else:
                    challenges_are_not_duplicates_list_query = \
                        ChallengesAreNotDuplicates.objects.filter(
                            challenge2_we_vote_id=challenge_we_vote_id,
                        )
                challenges_are_not_duplicates_list2 = list(challenges_are_not_duplicates_list_query)
                success = True
                status += "CHALLENGES_NOT_DUPLICATES_LIST_UPDATED_OR_CREATED2 "
            except ChallengesAreNotDuplicates.DoesNotExist:
                success = True
                status += 'NO_CHALLENGES_NOT_DUPLICATES_LIST_RETRIEVED2_DoesNotExist2 '
            except Exception as e:
                success = False
                status += "CHALLENGES_NOT_DUPLICATES_LIST_NOT_UPDATED_OR_CREATED2: " + str(e) + ' '

        challenges_are_not_duplicates_list = \
            challenges_are_not_duplicates_list1 + challenges_are_not_duplicates_list2
        challenges_are_not_duplicates_list_found = \
            positive_value_exists(len(challenges_are_not_duplicates_list))
        challenges_are_not_duplicates_list_we_vote_ids = []
        for one_entry in challenges_are_not_duplicates_list:
            if one_entry.challenge1_we_vote_id != challenge_we_vote_id:
                challenges_are_not_duplicates_list_we_vote_ids.append(one_entry.challenge1_we_vote_id)
            elif one_entry.challenge2_we_vote_id != challenge_we_vote_id:
                challenges_are_not_duplicates_list_we_vote_ids.append(one_entry.challenge2_we_vote_id)
        results = {
            'success':                                   success,
            'status':                                    status,
            'challenges_are_not_duplicates_list_found':  challenges_are_not_duplicates_list_found,
            'challenges_are_not_duplicates_list':        challenges_are_not_duplicates_list,
            'challenges_are_not_duplicates_list_we_vote_ids':
                challenges_are_not_duplicates_list_we_vote_ids,
        }
        return results

    @staticmethod
    def retrieve_challenges_from_non_unique_identifiers(
            challenge_title='',
            ignore_challenge_we_vote_id_list=[],
            politician_name='',
            state_code='',
            read_only=False):
        """

        :param challenge_title:
        :param ignore_challenge_we_vote_id_list:
        :param politician_name:
        :param state_code:
        :param read_only:
        :return:
        """
        keep_looking_for_duplicates = True
        challenge = None
        challenge_found = False
        challenge_list = []
        challenge_list_found = False
        multiple_entries_found = False
        success = True
        status = ""

        if keep_looking_for_duplicates and positive_value_exists(challenge_title):
            try:
                if positive_value_exists(read_only):
                    queryset = Challenge.objects.using('readonly').all()
                else:
                    queryset = Challenge.objects.all()
                queryset = queryset.filter(challenge_title__iexact=challenge_title)

                if positive_value_exists(ignore_challenge_we_vote_id_list):
                    queryset = queryset.exclude(we_vote_id__in=ignore_challenge_we_vote_id_list)

                challenge_list = list(queryset)
                if len(challenge_list):
                    # At least one entry exists
                    status += 'RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_LIST_RETRIEVED '
                    # if a single entry matches, update that entry
                    if len(challenge_list) == 1:
                        multiple_entries_found = False
                        challenge = challenge_list[0]
                        challenge_found = True
                        keep_looking_for_duplicates = False
                        success = True
                        status += "CHALLENGE_FOUND_BY_TITLE "
                    else:
                        # more than one entry found
                        challenge_list_found = True
                        multiple_entries_found = True
                        keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
                        status += "MULTIPLE_TITLE_MATCHES "
            except Challenge.DoesNotExist:
                success = True
                status += "RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_NOT_FOUND "
            except Exception as e:
                status += "RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_QUERY_FAILED1 " + str(e) + " "
                success = False
                keep_looking_for_duplicates = False

        # twitter handle does not exist, next look up against other data that might match
        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search by Candidate name exact match
            try:
                if positive_value_exists(read_only):
                    queryset = Challenge.objects.using('readonly').all()
                else:
                    queryset = Challenge.objects.all()
                queryset = queryset.filter(
                    Q(challenge_title__icontains=politician_name) |
                    Q(challenge_description__icontains=politician_name)
                )
                if positive_value_exists(state_code):
                    queryset = queryset.filter(state_code__iexact=state_code)
                if positive_value_exists(ignore_challenge_we_vote_id_list):
                    queryset = queryset.exclude(we_vote_id__in=ignore_challenge_we_vote_id_list)
                challenge_list = list(queryset)
                if len(challenge_list):
                    # entry exists
                    status += 'CHALLENGES_EXISTS1 '
                    success = True
                    # if a single entry matches, update that entry
                    if len(challenge_list) == 1:
                        challenge = challenge_list[0]
                        challenge_found = True
                        status += challenge.we_vote_id + " "
                        keep_looking_for_duplicates = False
                    else:
                        # more than one entry found with a match
                        challenge_list_found = True
                        keep_looking_for_duplicates = False
                        multiple_entries_found = True
                else:
                    success = True
                    status += 'CHALLENGES_NOT_FOUND-EXACT '

            except Challenge.DoesNotExist:
                success = True
                status += "RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_NOT_FOUND-EXACT_MATCH "
            except Exception as e:
                status += "RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_QUERY_FAILED2: " + str(e) + " "
                success = False

        if keep_looking_for_duplicates and positive_value_exists(politician_name):
            # Search for Candidate(s) that contains the same first and last names
            first_name = extract_first_name_from_full_name(politician_name)
            last_name = extract_last_name_from_full_name(politician_name)
            if positive_value_exists(first_name) and positive_value_exists(last_name):
                try:
                    if positive_value_exists(read_only):
                        queryset = Challenge.objects.using('readonly').all()
                    else:
                        queryset = Challenge.objects.all()

                    queryset = queryset.filter(
                        (Q(challenge_title__icontains=first_name) & Q(challenge_title__icontains=last_name)) |
                        (Q(challenge_description__icontains=first_name) &
                         Q(challenge_description__icontains=last_name))
                    )
                    if positive_value_exists(state_code):
                        queryset = queryset.filter(state_code__iexact=state_code)
                    if positive_value_exists(ignore_challenge_we_vote_id_list):
                        queryset = queryset.exclude(we_vote_id__in=ignore_challenge_we_vote_id_list)
                    challenge_list = list(queryset)
                    if len(challenge_list):
                        # entry exists
                        status += 'CHALLENGES_EXISTS2 '
                        success = True
                        # if a single entry matches, update that entry
                        if len(challenge_list) == 1:
                            challenge = challenge_list[0]
                            challenge_found = True
                            status += challenge.we_vote_id + " "
                            keep_looking_for_duplicates = False
                        else:
                            # more than one entry found with a match
                            challenge_list_found = True
                            keep_looking_for_duplicates = False
                            multiple_entries_found = True
                    else:
                        status += 'CHALLENGES_NOT_FOUND-FIRST_OR_LAST '
                        success = True
                except Challenge.DoesNotExist:
                    status += "RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_NOT_FOUND-FIRST_OR_LAST_NAME "
                    success = True
                except Exception as e:
                    status += "RETRIEVE_CHALLENGES_FROM_NON_UNIQUE-CHALLENGE_QUERY_FAILED3: " + str(e) + " "
                    success = False

        results = {
            'success':                  success,
            'status':                   status,
            'challenge_found':          challenge_found,
            'challenge':                challenge,
            'challenge_list_found':     challenge_list_found,
            'challenge_list':           challenge_list,
            'multiple_entries_found':   multiple_entries_found,
        }
        return results

    @staticmethod
    def retrieve_challenge_list(
            including_started_by_voter_we_vote_id=None,
            including_challenge_we_vote_id_list=[],
            excluding_challenge_we_vote_id_list=[],
            including_politicians_in_any_of_these_states=None,
            including_politicians_with_support_in_any_of_these_issues=None,
            limit=25,
            limit_to_this_state_code='',
            read_only=True,
            search_text=''):
        challenge_list = []
        challenge_list_found = False
        challenge_manager = ChallengeManager()
        success = True
        status = ""
        voter_started_challenge_we_vote_ids = []
        voter_supported_challenge_we_vote_ids = []

        try:
            if read_only:
                challenge_queryset = Challenge.objects.using('readonly').all()
            else:
                challenge_queryset = Challenge.objects.all()

            # #########
            # All "OR" queries
            filters = []

            challenge_we_vote_id_list = []
            if positive_value_exists(search_text) or positive_value_exists(limit_to_this_state_code):
                politician_list = challenge_manager.retrieve_challenge_politician_list(
                    limit_to_this_state_code=limit_to_this_state_code,
                    search_text=search_text)
                for one_politician in politician_list:
                    if one_politician.challenge_we_vote_id not in challenge_we_vote_id_list:
                        challenge_we_vote_id_list.append(one_politician.challenge_we_vote_id)
                # Find challenges based on this search text
                try:
                    search_words = search_text.split()
                except Exception as e:
                    status += "SEARCH_STRING_INVALID: " + str(e) + ' '
                    search_words = []
                for search_word in search_words:
                    search_filters = []

                    # We want to find candidates with *any* of these values
                    new_search_filter = Q(challenge_description__icontains=search_word)
                    search_filters.append(new_search_filter)
                    new_search_filter = Q(challenge_title__icontains=search_word)
                    search_filters.append(new_search_filter)
                    new_search_filter = Q(seo_friendly_path__icontains=search_word)
                    search_filters.append(new_search_filter)
                    new_search_filter = Q(politician_starter_list_serialized__icontains=search_word)
                    search_filters.append(new_search_filter)
                    # Any politicians with one of the search_words or in the state we care about?
                    if len(challenge_we_vote_id_list) > 0:
                        new_search_filter = Q(we_vote_id__in=challenge_we_vote_id_list)
                        search_filters.append(new_search_filter)

                    # Add the first query
                    final_filters = search_filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in search_filters:
                        final_filters |= item

                    challenge_queryset = challenge_queryset.filter(final_filters)

                # ...but limit with these queries
                challenge_queryset = challenge_queryset.filter(in_draft_mode=False)
                challenge_queryset = challenge_queryset.filter(is_blocked_by_we_vote=False)
                challenge_queryset = challenge_queryset.filter(is_in_team_review_mode=False)
            else:
                if positive_value_exists(including_started_by_voter_we_vote_id):
                    # started_by this voter
                    new_filter = Q(started_by_voter_we_vote_id=including_started_by_voter_we_vote_id)
                    filters.append(new_filter)
                    # Voter is owner of the challenge, or on team that owns it
                    voter_owned_challenge_we_vote_ids = challenge_manager.retrieve_voter_owned_challenge_we_vote_ids(
                        voter_we_vote_id=including_started_by_voter_we_vote_id)
                    new_filter = Q(we_vote_id__in=voter_owned_challenge_we_vote_ids)
                    filters.append(new_filter)
                final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
                new_filter = \
                    Q(in_draft_mode=False,
                      is_blocked_by_we_vote=False,
                      is_in_team_review_mode=False,
                      is_not_promoted_by_we_vote=False,
                      is_still_active=True,
                      is_ok_to_promote_on_we_vote=True) & \
                    (Q(supporters_count__gte=SUPPORTERS_COUNT_MINIMUM_FOR_LISTING) |
                     Q(supporters_count_minimum_ignored=True)) & \
                    (Q(final_election_date_as_integer__isnull=True) |
                     Q(final_election_date_as_integer__gt=final_election_date_plus_cool_down))
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                challenge_queryset = challenge_queryset.filter(final_filters)

            challenge_queryset = challenge_queryset.order_by('-supporters_count')
            challenge_queryset = challenge_queryset.order_by('-in_draft_mode')

            challenge_list = challenge_queryset[:limit]
            challenge_list_found = positive_value_exists(len(challenge_list))
            status += "RETRIEVE_CHALLENGE_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_LIST_FAILED: " + str(e) + " "
            challenge_list_found = False

        challenge_list_modified = []
        for challenge in challenge_list:
            challenge.visible_on_this_site = True
            challenge_list_modified.append(challenge)

        results = {
            'success':                                  success,
            'status':                                   status,
            'challenge_list_found':                     challenge_list_found,
            'challenge_list':                           challenge_list_modified,
            'voter_started_challenge_we_vote_ids':      voter_started_challenge_we_vote_ids,
            'voter_supported_challenge_we_vote_ids':    voter_supported_challenge_we_vote_ids,
        }
        return results

    @staticmethod
    def retrieve_challenge_list_for_private_label(
            including_started_by_voter_we_vote_id='',
            limit=150,
            site_owner_organization_we_vote_id='',
            read_only=True):
        challenge_list = []
        challenge_manager = ChallengeManager()
        success = True
        status = ""
        visible_on_this_site_challenge_we_vote_id_list = []
        challenge_list_modified = []
        challenge_we_vote_ids_in_order = []
        voter_started_challenge_we_vote_ids = []
        voter_supported_challenge_we_vote_ids = []

        # Limit the challenges retrieved to the ones approved by the site owner
        if positive_value_exists(site_owner_organization_we_vote_id):
            try:
                visible_on_this_site_challenge_we_vote_id_list = \
                    challenge_manager.retrieve_visible_on_this_site_challenge_simple_list(
                        site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            except Exception as e:
                success = False
                status += "RETRIEVE_CHALLENGE_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "

            try:
                challenge_we_vote_ids_in_order = challenge_manager.retrieve_challenge_we_vote_ids_in_order(
                    site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            except Exception as e:
                success = False
                status += "RETRIEVE_CHALLENGE_IN_ORDER_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "

        try:
            if read_only:
                challenge_queryset = Challenge.objects.using('readonly').all()
            else:
                challenge_queryset = Challenge.objects.all()

            # #########
            # All "OR" queries
            filters = []
            # Challenges started by this voter
            if positive_value_exists(including_started_by_voter_we_vote_id):
                # started_by this voter
                new_filter = \
                    Q(started_by_voter_we_vote_id=including_started_by_voter_we_vote_id)
                filters.append(new_filter)
                # Voter is owner of the challenge, or on team that owns it
                voter_owned_challenge_we_vote_ids = challenge_manager.retrieve_voter_owned_challenge_we_vote_ids(
                    voter_we_vote_id=including_started_by_voter_we_vote_id)
                new_filter = Q(we_vote_id__in=voter_owned_challenge_we_vote_ids)
                filters.append(new_filter)

            # Challenges approved to be shown on this site
            final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
            # is_not_promoted_by_we_vote = False,  # Removed since it is private labeled
            new_filter = \
                Q(we_vote_id__in=visible_on_this_site_challenge_we_vote_id_list,
                  in_draft_mode=False,
                  is_blocked_by_we_vote=False,
                  is_in_team_review_mode=False,
                  is_still_active=True) & \
                (Q(final_election_date_as_integer__isnull=True) |
                 Q(final_election_date_as_integer__gt=final_election_date_plus_cool_down))
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                challenge_queryset = challenge_queryset.filter(final_filters)

            challenge_queryset = challenge_queryset.order_by('-supporters_count')
            challenge_queryset = challenge_queryset.order_by('-in_draft_mode')

            challenge_list = challenge_queryset[:limit]
            challenge_list_found = positive_value_exists(len(challenge_list))
            for one_challenge in challenge_list:
                if one_challenge.we_vote_id in visible_on_this_site_challenge_we_vote_id_list:
                    one_challenge.visible_on_this_site = True
                else:
                    one_challenge.visible_on_this_site = False
                challenge_list_modified.append(one_challenge)
            challenge_list = challenge_list_modified
            status += "RETRIEVE_CHALLENGE_LIST_FOR_PRIVATE_LABEL_SUCCEEDED "

            # Reorder the challenges
            if len(challenge_we_vote_ids_in_order) > 0:
                challenge_list_modified = []
                challenge_we_vote_id_already_placed = []
                order_in_list = 0
                for challenge_we_vote_id in challenge_we_vote_ids_in_order:
                    for challenge in challenge_list:
                        if challenge_we_vote_id == challenge.we_vote_id:
                            order_in_list += 1
                            challenge.order_in_list = order_in_list
                            challenge_list_modified.append(challenge)
                            challenge_we_vote_id_already_placed.append(challenge.we_vote_id)
                # Now add the rest
                for challenge in challenge_list:
                    if challenge.we_vote_id not in challenge_we_vote_id_already_placed:
                        challenge_list_modified.append(challenge)
                        challenge_we_vote_id_already_placed.append(challenge.we_vote_id)
                challenge_list = challenge_list_modified
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "
            challenge_list_found = False

        results = {
            'success':                                  success,
            'status':                                   status,
            'visible_on_this_site_challenge_we_vote_id_list': visible_on_this_site_challenge_we_vote_id_list,
            'challenge_list_found':                     challenge_list_found,
            'challenge_list':                           challenge_list,
            'voter_started_challenge_we_vote_ids':      voter_started_challenge_we_vote_ids,
            'voter_supported_challenge_we_vote_ids':    voter_supported_challenge_we_vote_ids,
        }
        return results

    @staticmethod
    def retrieve_challenge_we_vote_id_list_filler_options(challenge_we_vote_id_list_to_exclude=[], limit=0):
        """
        Used for "recommended-challenges"
        :param challenge_we_vote_id_list_to_exclude:
        :param limit:
        :return:
        """
        challenge_we_vote_id_list_found = False
        challenge_we_vote_id_list = []
        status = ''
        success = True
        try:
            challenge_query = Challenge.objects.all()
            challenge_query = challenge_query.filter(
                in_draft_mode=False,
                is_blocked_by_we_vote=False,
                is_not_promoted_by_we_vote=False,
                is_still_active=True)
            challenge_query = challenge_query.filter(Q(supporters_count__gte=SUPPORTERS_COUNT_MINIMUM_FOR_LISTING) |
                                                     Q(supporters_count_minimum_ignored=True))
            final_election_date_plus_cool_down = generate_date_as_integer() + FINAL_ELECTION_DATE_COOL_DOWN
            challenge_query = challenge_query.filter(
                Q(final_election_date_as_integer__isnull=True) |
                Q(final_election_date_as_integer__gt=final_election_date_plus_cool_down))
            if len(challenge_we_vote_id_list_to_exclude) > 0:
                challenge_query = challenge_query.exclude(we_vote_id__in=challenge_we_vote_id_list_to_exclude)
            challenge_query = challenge_query.values_list('we_vote_id', flat=True).distinct()
            if positive_value_exists(limit):
                challenge_query = challenge_query[:limit]
            challenge_we_vote_id_list = list(challenge_query)
            challenge_we_vote_id_list_found = len(challenge_we_vote_id_list)
        except Exception as e:
            status += "ERROR_RETRIEVING_CHALLENGE_FILLER_LIST: " + str(e) + ' '
            success = False
        results = {
            'success':                          success,
            'status':                           status,
            'challenge_we_vote_id_list_found':  challenge_we_vote_id_list_found,
            'challenge_we_vote_id_list':        challenge_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_we_vote_id_list_by_politician_we_vote_id(politician_we_vote_id_list=[]):
        challenge_we_vote_id_list = []
        success = True
        status = ""

        try:
            challenge_queryset = ChallengePolitician.objects.using('readonly').all()
            challenge_queryset = challenge_queryset.filter(politician_we_vote_id__in=politician_we_vote_id_list)
            challenge_queryset = challenge_queryset.values_list('challenge_we_vote_id', flat=True).distinct()
            challenge_we_vote_id_list = list(challenge_queryset)
            challenge_we_vote_id_list_found = positive_value_exists(len(challenge_we_vote_id_list))
            status += "RETRIEVE_CHALLENGE_BY_POLITICIAN_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_BY_POLITICIAN_LIST_FAILED: " + str(e) + " "
            challenge_we_vote_id_list_found = False

        results = {
            'success':                          success,
            'status':                           status,
            'challenge_we_vote_id_list_found':  challenge_we_vote_id_list_found,
            'challenge_we_vote_id_list':        challenge_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_we_vote_id_list_started_by_voter(started_by_voter_we_vote_id=''):
        challenge_we_vote_id_list_found = False
        challenge_we_vote_id_list = []
        status = ''
        success = True
        try:
            challenge_query = Challenge.objects.all()
            challenge_query = challenge_query.filter(started_by_voter_we_vote_id=started_by_voter_we_vote_id)
            challenge_query = challenge_query.values_list('we_vote_id', flat=True).distinct()
            challenge_we_vote_id_list = list(challenge_query)
            challenge_we_vote_id_list_found = len(challenge_we_vote_id_list)
        except Exception as e:
            status += "ERROR_RETRIEVING_CHALLENGE: " + str(e) + ' '
            success = False
        results = {
            'success':                          success,
            'status':                           status,
            'challenge_we_vote_id_list_found':  challenge_we_vote_id_list_found,
            'challenge_we_vote_id_list':        challenge_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_we_vote_id_list_supported_by_voter(voter_we_vote_id=None):
        challenge_we_vote_id_list = []
        success = True
        status = ""

        try:
            challenge_queryset = ChallengeSupporter.objects.using('readonly').all()
            challenge_queryset = challenge_queryset.filter(voter_we_vote_id=voter_we_vote_id)
            challenge_queryset = challenge_queryset.values_list('challenge_we_vote_id', flat=True).distinct()
            challenge_we_vote_id_list = list(challenge_queryset)
            challenge_we_vote_id_list_found = positive_value_exists(len(challenge_we_vote_id_list))
            status += "RETRIEVE_CHALLENGE_SUPPORTED_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_SUPPORTED_LIST_FAILED: " + str(e) + " "
            challenge_we_vote_id_list_found = False

        results = {
            'success':                          success,
            'status':                           status,
            'challenge_we_vote_id_list_found':  challenge_we_vote_id_list_found,
            'challenge_we_vote_id_list':        challenge_we_vote_id_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_list_by_challenge_we_vote_id_list(challenge_we_vote_id_list=[], read_only=True):
        challenge_list = []
        challenge_list_found = False
        status = ''
        success = True
        try:
            if positive_value_exists(read_only):
                challenge_query = Challenge.objects.using('readonly').all()
            else:
                challenge_query = Challenge.objects.all()
            challenge_query = challenge_query.filter(we_vote_id__in=challenge_we_vote_id_list)
            challenge_list = list(challenge_query)
            if len(challenge_list):
                challenge_list_found = True
        except Exception as e:
            status += "ERROR_RETRIEVING_CHALLENGE_LIST: " + str(e) + ' '
            success = False

        results = {
            'success':              success,
            'status':               status,
            'challenge_list_found': challenge_list_found,
            'challenge_list':       challenge_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_list_for_voter(started_by_voter_we_vote_id=''):
        challenge_list_found = False
        challenge_list = []
        status = ''
        try:
            challenge_query = Challenge.objects.all()
            challenge_query = challenge_query.filter(started_by_voter_we_vote_id=started_by_voter_we_vote_id)
            challenge_list = list(challenge_query)
            if len(challenge_list):
                challenge_list_found = True
        except Exception as e:
            status += "ERROR_RETRIEVING_CHALLENGE: " + str(e) + ' '

        if challenge_list_found:
            return challenge_list
        else:
            challenge_list = []
            return challenge_list

    @staticmethod
    def retrieve_challenge_owner(challenge_we_vote_id='', voter_we_vote_id='', read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        challenge_owner = None
        challenge_owner_found = False
        status = ''

        try:
            if positive_value_exists(challenge_we_vote_id) and positive_value_exists(voter_we_vote_id):
                if positive_value_exists(read_only):
                    query = ChallengeOwner.objects.using('readonly').filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                else:
                    query = ChallengeOwner.objects.filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                challenge_owner_list = list(query)
                if len(challenge_owner_list) > 0:
                    challenge_owner = challenge_owner_list[0]
                    challenge_owner_found = True
                    status += 'CHALLENGE_OWNER_FOUND_WITH_WE_VOTE_ID '
                    if len(challenge_owner_list) > 1:
                        exception_multiple_object_returned = True
                        status += 'MULTIPLE_CHALLENGE_OWNER_FOUND_WITH_WE_VOTE_ID-'
                        status += '(NUMBER_FOUND: ' + str(len(challenge_owner_list)) + ') '
                else:
                    exception_does_not_exist = True
                success = True
            else:
                exception_multiple_object_returned = True
                status += 'CHALLENGE_OWNER_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except Exception as e:
            status += 'CHALLENGE_OWNER_NOT_FOUND-ERROR: ' + str(e) + ' '
            success = False

        results = {
            'status':                   status,
            'success':                  success,
            'challenge_owner':          challenge_owner,
            'challenge_owner_found':    challenge_owner_found,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results

    @staticmethod
    def retrieve_challenge_owner_list(
            challenge_we_vote_id_list=[],
            has_order_in_list=False,
            organization_we_vote_id='',
            voter_we_vote_id='',
            viewer_is_owner=False,
            read_only=False):
        challenge_owner_list_found = False
        challenge_owner_list = []
        try:
            if positive_value_exists(read_only):
                challenge_owner_query = ChallengeOwner.objects.using('readonly').all()
            else:
                challenge_owner_query = ChallengeOwner.objects.all()
            # if not positive_value_exists(viewer_is_owner):
            #     # If not already an owner, limit to owners who are visible to public
            #     challenge_owner_query = challenge_owner_query.filter(visible_to_public=True)
            if positive_value_exists(len(challenge_we_vote_id_list) > 0):
                challenge_owner_query = challenge_owner_query.filter(challenge_we_vote_id__in=challenge_we_vote_id_list)
            if positive_value_exists(has_order_in_list):
                challenge_owner_query = challenge_owner_query.filter(order_in_list__gte=1)
                challenge_owner_query = challenge_owner_query.order_by('order_in_list')
            if positive_value_exists(organization_we_vote_id):
                challenge_owner_query = challenge_owner_query.filter(organization_we_vote_id=organization_we_vote_id)
            if positive_value_exists(voter_we_vote_id):
                challenge_owner_query = challenge_owner_query.filter(voter_we_vote_id=voter_we_vote_id)
            challenge_owner_list = list(challenge_owner_query)
            if len(challenge_owner_list):
                challenge_owner_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if challenge_owner_list_found:
            return challenge_owner_list
        else:
            challenge_owner_list = []
            return challenge_owner_list

    @staticmethod
    def retrieve_challenge_politician(
            challenge_we_vote_id='',
            politician_we_vote_id='',
            politician_name='',
            read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        challenge_politician = None
        challenge_politician_found = False
        status = ''

        try:
            if positive_value_exists(challenge_we_vote_id) and positive_value_exists(politician_we_vote_id):
                if positive_value_exists(read_only):
                    query = ChallengePolitician.objects.using('readonly').filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        politician_we_vote_id=politician_we_vote_id)
                else:
                    query = ChallengePolitician.objects.filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        politician_we_vote_id=politician_we_vote_id)
                challenge_politician_list = list(query)
                if len(challenge_politician_list) > 0:
                    challenge_politician = challenge_politician_list[0]
                    challenge_politician_found = True
                    status += 'CHALLENGE_POLITICIAN_FOUND_WITH_WE_VOTE_ID '
                    if len(challenge_politician_list) > 1:
                        exception_multiple_object_returned = True
                        status += 'MULTIPLE_POLITICIAN_FOUND_WITH_WE_VOTE_ID-'
                        status += '(NUMBER_FOUND: ' + str(len(challenge_politician_list)) + ') '
                else:
                    status += 'CHALLENGE_POLITICIAN_NOT_FOUND_WITH_WE_VOTE_ID '
                success = True
            elif positive_value_exists(challenge_we_vote_id) and positive_value_exists(politician_name):
                if positive_value_exists(read_only):
                    query = ChallengePolitician.objects.using('readonly').filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        politician_name=politician_name)
                else:
                    query = ChallengePolitician.objects.filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        politician_name=politician_name)
                challenge_politician_list = list(query)
                if len(challenge_politician_list) > 0:
                    challenge_politician = challenge_politician_list[0]
                    challenge_politician_found = True
                    status += 'CHALLENGE_POLITICIAN_FOUND_WITH_NAME '
                    if len(challenge_politician_list) > 1:
                        exception_multiple_object_returned = True
                        status += 'MULTIPLE_POLITICIAN_FOUND_WITH_WE_VOTE_ID-'
                        status += '(NUMBER_FOUND: ' + str(len(challenge_politician_list)) + ') '
                else:
                    status += 'CHALLENGE_POLITICIAN_NOT_FOUND_WITH_NAME '
                success = True
            else:
                status += 'CHALLENGE_POLITICIAN_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except Exception as e:
            status += 'CHALLENGE_POLITICIAN_NOT_FOUND_ERROR: ' + str(e) + ' '
            success = False

        results = {
            'status':                       status,
            'success':                      success,
            'challenge_politician':         challenge_politician,
            'challenge_politician_found':   challenge_politician_found,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    @staticmethod
    def retrieve_challenge_politician_list(
            challenge_we_vote_id='',
            limit_to_this_state_code='',
            read_only=True,
            search_text=''):
        challenge_politician_list_found = False
        challenge_politician_list = []
        try:
            if positive_value_exists(read_only):
                challenge_politician_query = ChallengePolitician.objects.using('readonly').all()
            else:
                challenge_politician_query = ChallengePolitician.objects.all()
            if positive_value_exists(challenge_we_vote_id):
                challenge_politician_query = challenge_politician_query.filter(
                    challenge_we_vote_id=challenge_we_vote_id)
            if positive_value_exists(limit_to_this_state_code):
                challenge_politician_query = challenge_politician_query.filter(
                    state_code__iexact=limit_to_this_state_code)
            if positive_value_exists(search_text):
                try:
                    search_words = search_text.split()
                except Exception as e:
                    return []
                for search_word in search_words:
                    filters = []

                    # We want to find candidates with *any* of these values
                    new_filter = Q(politician_name__icontains=search_word)
                    filters.append(new_filter)

                    # Add the first query
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    # Add as new filter for "AND"
                    challenge_politician_query = challenge_politician_query.filter(final_filters)
            searching_for_specific_challenges = \
                positive_value_exists(challenge_we_vote_id) or positive_value_exists(search_text)
            # NOTE: ChallengePolitician does not have 'supporters_count' field currently
            # if not searching_for_specific_challenges:
            #     # Do not include challenges in general lists with the following conditions
            #     challenge_politician_query = challenge_politician_query.exclude(supporters_count__lte=5)
            challenge_politician_list = list(challenge_politician_query)
            if len(challenge_politician_list):
                challenge_politician_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if challenge_politician_list_found:
            return challenge_politician_list
        else:
            challenge_politician_list = []
            return challenge_politician_list

    @staticmethod
    def repair_challenge_supporter(challenge_we_vote_id='', voter_we_vote_id=''):
        challenge_supporter = None
        challenge_supporter_found = False
        challenge_supporter_repaired = False
        status = ''

        try:
            if positive_value_exists(challenge_we_vote_id) and positive_value_exists(voter_we_vote_id):
                challenge_supporter_query = ChallengeSupporter.objects.filter(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id)
                challenge_supporter_query = challenge_supporter_query.order_by('id')
                challenge_supporter_list = list(challenge_supporter_query)
                number_of_challenge_supporters_found = len(challenge_supporter_list)
                if number_of_challenge_supporters_found == 0:
                    status += 'REPAIR_CHALLENGE_SUPPORTER_FOUND_WITH_WE_VOTE_ID '
                    challenge_supporter_found = False
                elif number_of_challenge_supporters_found == 1:
                    status += 'REPAIR_CHALLENGE_SUPPORTER_FOUND_ONE_WITH_WE_VOTE_ID '
                    challenge_supporter_found = True
                else:
                    status += 'REPAIR_CHALLENGE_SUPPORTER_FOUND_MULTIPLE_WITH_WE_VOTE_ID '
                    challenge_supporter_found = True
                    first_challenge_supporter = challenge_supporter_list[0]
                    # We want to keep the supporter_endorsement with the most characters
                    supporter_endorsement_to_keep = first_challenge_supporter.supporter_endorsement
                    supporter_endorsement_to_keep_length = len(supporter_endorsement_to_keep) \
                        if positive_value_exists(supporter_endorsement_to_keep) else 0
                    visible_to_public = first_challenge_supporter.visible_to_public
                    visibility_blocked_by_we_vote = first_challenge_supporter.visibility_blocked_by_we_vote

                    array_index = 1
                    # We set a "safety valve" of 25
                    while array_index < number_of_challenge_supporters_found and array_index < 25:
                        challenge_supporter_temp = challenge_supporter_list[array_index]
                        # We want to keep the supporter_endorsement with the most characters
                        if supporter_endorsement_to_keep_length < len(challenge_supporter_temp.supporter_endorsement):
                            supporter_endorsement_to_keep = challenge_supporter_temp.supporter_endorsement
                            supporter_endorsement_to_keep_length = len(supporter_endorsement_to_keep) \
                                if positive_value_exists(supporter_endorsement_to_keep) else 0
                        # If any have visible_to_public true, mark the one to keep as true
                        if not positive_value_exists(visible_to_public):
                            visible_to_public = challenge_supporter_temp.visible_to_public
                        # If any have visibility_blocked_by_we_vote true, mark the one to keep as true
                        if not positive_value_exists(visibility_blocked_by_we_vote):
                            visibility_blocked_by_we_vote = challenge_supporter_temp.visibility_blocked_by_we_vote
                        array_index += 1

                    # Now update first_challenge_supporter with values from while loop
                    first_challenge_supporter.supporter_endorsement_to_keep = supporter_endorsement_to_keep
                    first_challenge_supporter.visible_to_public = visible_to_public
                    first_challenge_supporter.visibility_blocked_by_we_vote = visibility_blocked_by_we_vote

                    # Look up the organization_we_vote_id for the voter
                    from voter.models import VoterManager
                    linked_organization_we_vote_id = ''
                    voter_manager = VoterManager()
                    results = voter_manager.retrieve_voter_by_we_vote_id(voter_we_vote_id, read_only=True)
                    if results['voter_found']:
                        voter = results['voter']
                        first_challenge_supporter.organization_we_vote_id = voter.linked_organization_we_vote_id

                    # Get the updated organization_name and we_vote_hosted_profile_image_url_tiny
                    if positive_value_exists(linked_organization_we_vote_id):
                        organization_manager = OrganizationManager()
                        results = organization_manager.retrieve_organization(
                            we_vote_id=linked_organization_we_vote_id,
                            read_only=True)
                        if results['organization_found']:
                            organization = results['organization']
                            first_challenge_supporter.supporter_name = organization.organization_name
                            first_challenge_supporter.we_vote_hosted_profile_image_url_medium = \
                                organization.we_vote_hosted_profile_image_url_medium
                            first_challenge_supporter.we_vote_hosted_profile_image_url_tiny = \
                                organization.we_vote_hosted_profile_image_url_tiny

                    # Look up supporter_name and we_vote_hosted_profile_image_url for the voter's organization
                    try:
                        first_challenge_supporter.save()
                        # Delete all other ChallengeSupporters
                        array_index = 1
                        while array_index < number_of_challenge_supporters_found and array_index < 25:
                            challenge_supporter_temp = challenge_supporter_list[array_index]
                            challenge_supporter_temp.delete()
                            array_index += 1
                    except Exception as e:
                        status += "CHALLENGE_COULD_NOT_SAVE_OR_DELETE: " + str(e) + " "
                success = True
            else:
                status += 'REPAIR_CHALLENGE_SUPPORTER_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except Exception as e:
            status += 'REPAIR_CHALLENGE_SUPPORTER_EXCEPTION: ' + str(e) + " "
            success = False

        results = {
            'status':                       status,
            'success':                      success,
            'challenge_supporter':          challenge_supporter,
            'challenge_supporter_found':    challenge_supporter_found,
            'challenge_supporter_repaired': challenge_supporter_repaired,
        }
        return results

    def retrieve_challenge_supporter(
            self,
            challenge_we_vote_id='',
            voter_we_vote_id='',
            read_only=False,
            recursion_ok=True):
        challenge_supporter = None
        challenge_supporter_found = False
        status = ''
        success = True

        try:
            if positive_value_exists(challenge_we_vote_id) and positive_value_exists(voter_we_vote_id):
                if positive_value_exists(read_only):
                    challenge_supporter_query = ChallengeSupporter.objects.using('readonly').filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                else:
                    challenge_supporter_query = ChallengeSupporter.objects.filter(
                        challenge_we_vote_id=challenge_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                challenge_supporter_list = list(challenge_supporter_query)
                if len(challenge_supporter_list) > 1:
                    if positive_value_exists(recursion_ok):
                        repair_results = self.repair_challenge_supporter(
                            challenge_we_vote_id=challenge_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,

                        )
                        status += repair_results['status']
                        second_retrieve_results = self.retrieve_challenge_supporter(
                            challenge_we_vote_id=challenge_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            read_only=read_only,
                            recursion_ok=False
                        )
                        challenge_supporter_found = second_retrieve_results['challenge_supporter_found']
                        challenge_supporter = second_retrieve_results['challenge_supporter']
                        success = second_retrieve_results['success']
                        status += second_retrieve_results['status']
                    else:
                        challenge_supporter = challenge_supporter_list[0]
                        challenge_supporter_found = True
                elif len(challenge_supporter_list) == 1:
                    challenge_supporter = challenge_supporter_list[0]
                    challenge_supporter_found = True
                    status += 'CHALLENGE_SUPPORTER_FOUND_WITH_WE_VOTE_ID '
                else:
                    challenge_supporter_found = False
                    status += 'CHALLENGE_SUPPORTER_NOT_FOUND_WITH_WE_VOTE_ID '
            else:
                status += 'CHALLENGE_SUPPORTER_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except Exception as e:
            status += 'CHALLENGE_SUPPORTER_NOT_FOUND_EXCEPTION: ' + str(e) + ' '
            success = False

        results = {
            'status':                       status,
            'success':                      success,
            'challenge_supporter':          challenge_supporter,
            'challenge_supporter_found':    challenge_supporter_found,
        }
        return results

    @staticmethod
    def retrieve_challenge_supporter_list(
            challenge_we_vote_id=None,
            voter_we_vote_id=None,
            require_supporter_endorsement=False,
            require_visible_to_public=True,
            require_not_blocked_by_we_vote=True,
            limit=10,
            read_only=True):
        supporter_list = []
        success = True
        status = ""

        try:
            if read_only:
                challenge_queryset = ChallengeSupporter.objects.using('readonly').all()
            else:
                challenge_queryset = ChallengeSupporter.objects.all()

            if positive_value_exists(challenge_we_vote_id):
                challenge_queryset = challenge_queryset.filter(challenge_we_vote_id=challenge_we_vote_id)
            else:
                challenge_queryset = challenge_queryset.filter(voter_we_vote_id=voter_we_vote_id)
            if positive_value_exists(require_visible_to_public):
                challenge_queryset = challenge_queryset.filter(visible_to_public=True)
            if positive_value_exists(require_not_blocked_by_we_vote):
                challenge_queryset = challenge_queryset.filter(visibility_blocked_by_we_vote=False)
            if positive_value_exists(require_supporter_endorsement):
                challenge_queryset = challenge_queryset.exclude(
                    Q(supporter_endorsement__isnull=True) |
                    Q(supporter_endorsement__exact='')
                )
            challenge_queryset = challenge_queryset.order_by('-date_supported')

            if limit > 0:
                supporter_list = challenge_queryset[:limit]
            else:
                supporter_list = list(challenge_queryset)
            supporter_list_found = positive_value_exists(len(supporter_list))
            status += "RETRIEVE_CHALLENGE_SUPPORTER_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_SUPPORTER_LIST_FAILED: " + str(e) + " "
            supporter_list_found = False

        results = {
            'success':                                  success,
            'status':                                   status,
            'supporter_list_found':                     supporter_list_found,
            'supporter_list':                           supporter_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_news_item(
            challenge_news_item_we_vote_id='',
            read_only=False):
        challenge_news_item = None
        challenge_news_item_found = False
        status = ''
        success = True

        try:
            if positive_value_exists(challenge_news_item_we_vote_id):
                if positive_value_exists(read_only):
                    challenge_news_item = ChallengeNewsItem.objects.using('readonly').get(
                        we_vote_id=challenge_news_item_we_vote_id)
                else:
                    challenge_news_item = ChallengeNewsItem.objects.get(
                        we_vote_id=challenge_news_item_we_vote_id)
                challenge_news_item_found = True
                status += 'CHALLENGE_NEWS_ITEM_FOUND_WITH_WE_VOTE_ID '
            else:
                status += 'CHALLENGE_NEWS_ITEM_NOT_FOUND-MISSING_VARIABLE '
                success = False
        except ChallengeNewsItem.DoesNotExist as e:
            status += 'CHALLENGE_NEWS_ITEM_NOT_FOUND '
            success = True
        except Exception as e:
            status += 'CHALLENGE_NEWS_ITEM_NOT_FOUND_EXCEPTION: ' + str(e) + ' '
            success = False

        results = {
            'status':                       status,
            'success':                      success,
            'challenge_news_item':          challenge_news_item,
            'challenge_news_item_found':    challenge_news_item_found,
        }
        return results

    @staticmethod
    def retrieve_challenge_news_item_list(
            challenge_we_vote_id=None,
            limit=0,
            read_only=True,
            voter_is_challenge_owner=False,
    ):
        success = True
        status = ""

        try:
            if read_only:
                queryset = ChallengeNewsItem.objects.using('readonly').all()
            else:
                queryset = ChallengeNewsItem.objects.all()

            queryset = queryset.filter(challenge_we_vote_id=challenge_we_vote_id)
            if positive_value_exists(voter_is_challenge_owner):
                # Return all news items
                pass
            else:
                queryset = queryset.filter(in_draft_mode=False)
                queryset = queryset.filter(visibility_blocked_by_we_vote=False)
                queryset = queryset.filter(visible_to_public=True)
            queryset = queryset.order_by('-date_posted')
            if limit > 0:
                queryset = queryset[:limit]
            else:
                queryset = queryset
            challenge_news_item_list = list(queryset)
            challenge_news_item_list_found = positive_value_exists(len(challenge_news_item_list))
            status += "RETRIEVE_CHALLENGE_NEWS_ITEM_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CHALLENGE_NEWS_ITEM_LIST_FAILED: " + str(e) + " "
            challenge_news_item_list = []
            challenge_news_item_list_found = False

        results = {
            'success':                          success,
            'status':                           status,
            'challenge_news_item_list_found':   challenge_news_item_list_found,
            'challenge_news_item_list':         challenge_news_item_list,
        }
        return results

    @staticmethod
    def retrieve_challenge_title(challenge_we_vote_id='', read_only=False):
        if challenge_we_vote_id is None or len(challenge_we_vote_id) == 0:
            return ''
        try:
            if positive_value_exists(read_only):
                challenge = Challenge.objects.using('readonly').get(we_vote_id=challenge_we_vote_id)
            else:
                challenge = Challenge.objects.get(we_vote_id=challenge_we_vote_id)
            return challenge.challenge_title
        except Challenge.DoesNotExist as e:
            # Some test data will throw this, no worries
            return ''

    @staticmethod
    def retrieve_seo_friendly_path_list(challenge_we_vote_id=''):
        seo_friendly_path_list_found = False
        seo_friendly_path_list = []
        try:
            query = ChallengeSEOFriendlyPath.objects.all()
            query = query.filter(challenge_we_vote_id=challenge_we_vote_id)
            seo_friendly_path_list = list(query)
            if len(seo_friendly_path_list):
                seo_friendly_path_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if seo_friendly_path_list_found:
            return seo_friendly_path_list
        else:
            seo_friendly_path_list = []
            return seo_friendly_path_list

    def retrieve_seo_friendly_path_simple_list(self, challenge_we_vote_id=''):
        seo_friendly_path_list = \
            self.retrieve_seo_friendly_path_list(challenge_we_vote_id=challenge_we_vote_id)
        simple_list = []
        for one_path in seo_friendly_path_list:
            if positive_value_exists(one_path.final_pathname_string):
                simple_list.append(one_path.final_pathname_string)
        return simple_list

    @staticmethod
    def retrieve_voter_can_send_updates_challenge_we_vote_ids(voter_we_vote_id=''):
        """
        :param voter_we_vote_id:
        :return:
        """
        status = ''
        challenge_owner_challenge_we_vote_ids = []
        team_member_challenge_we_vote_ids = []

        try:
            challenge_owner_query = ChallengeOwner.objects.using('readonly').filter(
                voter_we_vote_id=voter_we_vote_id)
            challenge_owner_query = challenge_owner_query.values_list('challenge_we_vote_id', flat=True).distinct()
            challenge_owner_challenge_we_vote_ids = list(challenge_owner_query)
        except ChallengeOwner as e:
            status += 'CHALLENGE_OWNER_UPDATE_QUERY_FAILED: ' + str(e) + ' '

        teams_voter_can_send_updates_organization_we_vote_id_list = []
        try:
            # Which teams does this voter belong to, with can_send_updates_for_challenge_owned_by_organization rights?
            team_member_queryset = OrganizationTeamMember.objects.using('readonly').filter(
                voter_we_vote_id=voter_we_vote_id,
                can_send_updates_for_challenge_owned_by_organization=True
            )
            team_member_queryset = team_member_queryset.values_list('organization_we_vote_id', flat=True).distinct()
            teams_voter_can_send_updates_organization_we_vote_id_list = list(team_member_queryset)
        except OrganizationTeamMember as e:
            status += 'CHALLENGE_OWNER_FROM_TEAM_UPDATE_QUERY_FAILED: ' + str(e) + ' '

        # Now see if this challenge is owned by any of the teams this voter belongs to
        if len(teams_voter_can_send_updates_organization_we_vote_id_list) > 0:
            try:
                owner_queryset = ChallengeOwner.objects.using('readonly').filter(
                    organization_we_vote_id__in=teams_voter_can_send_updates_organization_we_vote_id_list)
                owner_queryset = owner_queryset.values_list('challenge_we_vote_id', flat=True).distinct()
                team_member_challenge_we_vote_ids = list(owner_queryset)
            except ChallengeOwner as e:
                status += 'CHALLENGE_OWNER_AS_TEAM_MEMBER_UPDATES_QUERY_FAILED: ' + str(e) + ' '

        challenge_owner_set = set(challenge_owner_challenge_we_vote_ids)
        team_member_set = set(team_member_challenge_we_vote_ids)
        combined_set = challenge_owner_set | team_member_set

        return list(combined_set)

    @staticmethod
    def retrieve_voter_owned_challenge_we_vote_ids(voter_we_vote_id=''):
        """
        :param voter_we_vote_id:
        :return:
        """
        status = ''
        challenge_owner_challenge_we_vote_ids = []
        team_member_challenge_we_vote_ids = []

        try:
            challenge_owner_query = ChallengeOwner.objects.using('readonly').filter(
                voter_we_vote_id=voter_we_vote_id)
            challenge_owner_query = challenge_owner_query.values_list('challenge_we_vote_id', flat=True).distinct()
            challenge_owner_challenge_we_vote_ids = list(challenge_owner_query)
        except ChallengeOwner as e:
            status += 'CHALLENGE_OWNER_QUERY_FAILED: ' + str(e) + ' '

        teams_voter_is_on_organization_we_vote_id_list = []
        try:
            # Which teams does this voter belong to, with challenge rights?
            team_member_queryset = OrganizationTeamMember.objects.using('readonly').filter(
                voter_we_vote_id=voter_we_vote_id)
            team_member_queryset = team_member_queryset.filter(
                Q(can_edit_challenge_owned_by_organization=True) |
                Q(can_moderate_challenge_owned_by_organization=True) |
                Q(can_send_updates_for_challenge_owned_by_organization=True))
            team_member_queryset = team_member_queryset.values_list('organization_we_vote_id', flat=True).distinct()
            teams_voter_is_on_organization_we_vote_id_list = list(team_member_queryset)
        except OrganizationTeamMember as e:
            status += 'CHALLENGE_OWNER_FROM_TEAM_QUERY_FAILED: ' + str(e) + ' '

        # Now see if this challenge is owned by any of the teams this voter belongs to
        if len(teams_voter_is_on_organization_we_vote_id_list) > 0:
            try:
                owner_queryset = ChallengeOwner.objects.using('readonly').filter(
                    organization_we_vote_id__in=teams_voter_is_on_organization_we_vote_id_list)
                owner_queryset = owner_queryset.values_list('challenge_we_vote_id', flat=True).distinct()
                team_member_challenge_we_vote_ids = list(owner_queryset)
            except ChallengeOwner as e:
                status += 'CHALLENGE_OWNER_AS_TEAM_MEMBER_QUERY_FAILED: ' + str(e) + ' '

        challenge_owner_set = set(challenge_owner_challenge_we_vote_ids)
        team_member_set = set(team_member_challenge_we_vote_ids)
        combined_set = challenge_owner_set | team_member_set

        return list(combined_set)

    @staticmethod
    def update_challenge_owners_with_organization_change(
            organization_we_vote_id,
            organization_name,
            we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny):
        status = ''
        success = True
        challenge_owner_entries_updated = 0

        try:
            challenge_owner_entries_updated = ChallengeOwner.objects \
                .filter(organization_we_vote_id=organization_we_vote_id) \
                .update(organization_name=organization_name,
                        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-CHALLENGE_OWNER_UPDATE_WITH_ORGANIZATION_CHANGE: " + str(e) + " "
            success = False

        results = {
            'success': success,
            'status': status,
            'challenge_owner_entries_updated': challenge_owner_entries_updated,
        }
        return results

    @staticmethod
    def update_challenge_supporters_with_organization_change(
            organization_we_vote_id,
            supporter_name,
            we_vote_hosted_profile_image_url_medium,
            we_vote_hosted_profile_image_url_tiny):
        status = ''
        success = True
        challenge_supporter_entries_updated = 0

        try:
            challenge_supporter_entries_updated = ChallengeSupporter.objects \
                .filter(organization_we_vote_id=organization_we_vote_id) \
                .update(supporter_name=supporter_name,
                        we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-CHALLENGE_SUPPORTER_UPDATE_WITH_ORGANIZATION_CHANGE: " + str(e) + " "
            success = False

        results = {
            'success': success,
            'status': status,
            'challenge_supporter_entries_updated': challenge_supporter_entries_updated,
        }
        return results

    def update_challenge_supporters_count(self, challenge_we_vote_id='', politician_we_vote_id=''):
        status = ''
        opposers_count = 0
        supporters_count = 0
        error_results = {
            'challenge_we_vote_id': challenge_we_vote_id,
            'status': status,
            'success': False,
            'supporters_count': supporters_count,
        }
        if positive_value_exists(politician_we_vote_id):
            if not positive_value_exists(challenge_we_vote_id):
                try:
                    queryset = Challenge.objects.using('readonly').all()
                    queryset = queryset.filter(politician_we_vote_id=politician_we_vote_id)
                    temp_list = queryset.values_list('we_vote_id', flat=True).distinct()
                    challenge_we_vote_id = temp_list[0]
                except Exception as e:
                    status += "FAILED_RETRIEVING_CHALLENGE: " + str(e) + ' '
                    error_results['status'] += status
                    return error_results
            try:
                queryset = Organization.objects.using('readonly').all()
                queryset = queryset.filter(politician_we_vote_id=politician_we_vote_id)
                temp_list = queryset.values_list('we_vote_id', flat=True).distinct()
                organization_we_vote_id = temp_list[0]
            except Exception as e:
                status += "FAILED_RETRIEVING_ORGANIZATION: " + str(e) + ' '
                error_results['status'] += status
                return error_results
            try:
                from follow.models import FOLLOWING, FOLLOW_DISLIKE, FollowOrganization
                queryset = FollowOrganization.objects.using('readonly').all()
                queryset = queryset.filter(organization_we_vote_id=organization_we_vote_id)
                following_queryset = queryset.filter(following_status=FOLLOWING)
                supporters_count = following_queryset.count()
                disliking_queryset = queryset.filter(following_status=FOLLOW_DISLIKE)
                opposers_count = disliking_queryset.count()
            except Exception as e:
                status += "FAILED_RETRIEVING_FOLLOW_ORGANIZATION_COUNTS: " + str(e) + ' '
                error_results['status'] += status
                return error_results
        else:
            try:
                count_query = ChallengeSupporter.objects.using('readonly').all()
                count_query = count_query.filter(challenge_we_vote_id=challenge_we_vote_id)
                count_query = count_query.filter(challenge_supported=True)
                supporters_count = count_query.count()
            except Exception as e:
                status += "FAILED_RETRIEVING_CHALLENGE_SUPPORTER_COUNT: " + str(e) + ' '
                error_results['status'] += status
                return error_results

        update_values = {
            'opposers_count': opposers_count,
            'supporters_count': supporters_count,
        }
        update_results = self.update_or_create_challenge(
            challenge_we_vote_id=challenge_we_vote_id,
            update_values=update_values,
        )
        status = update_results['status']
        success = update_results['success']

        results = {
            'challenge_we_vote_id': challenge_we_vote_id,
            'status':               status,
            'success':              success,
            'supporters_count':     supporters_count,
        }
        return results

    @staticmethod
    def update_or_create_challenge(
            challenge_we_vote_id='',
            voter_we_vote_id='',
            organization_we_vote_id='',
            politician_we_vote_id='',
            update_values={}):
        status = ""
        success = True
        challenge = None
        challenge_changed = False
        challenge_created = False
        challenge_manager = ChallengeManager()

        create_variables_exist = \
            (positive_value_exists(voter_we_vote_id) and positive_value_exists(organization_we_vote_id)) \
            or positive_value_exists(politician_we_vote_id)
        update_variables_exist = challenge_we_vote_id
        if not create_variables_exist and not update_variables_exist:
            if not create_variables_exist:
                status += "CREATE_CHALLENGE_VARIABLES_MISSING "
            if not update_variables_exist:
                status += "UPDATE_CHALLENGE_VARIABLES_MISSING "
            status += "COULD_NOT_UPDATE_OR_CREATE: "
            results = {
                'success':             False,
                'status':              status,
                'challenge':           None,
                'challenge_changed':   False,
                'challenge_created':   False,
                'challenge_found':     False,
                'challenge_we_vote_id': '',
            }
            return results

        if positive_value_exists(challenge_we_vote_id):
            results = challenge_manager.retrieve_challenge_as_owner(
                challenge_we_vote_id=challenge_we_vote_id,
                read_only=False)
            challenge_found = results['challenge_found']
            if challenge_found:
                challenge = results['challenge']
                challenge_we_vote_id = challenge.we_vote_id
            success = results['success']
            status += results['status']
        elif positive_value_exists(politician_we_vote_id):
            results = challenge_manager.retrieve_challenge(
                politician_we_vote_id=politician_we_vote_id,
                read_only=False)
            challenge_found = results['challenge_found']
            if challenge_found:
                challenge = results['challenge']
                challenge_we_vote_id = challenge.we_vote_id
            success = results['success']
            status += results['status']
        else:
            results = challenge_manager.retrieve_challenge_as_owner(
                voter_we_vote_id=voter_we_vote_id,
                read_only=False)
            challenge_found = results['challenge_found']
            if challenge_found:
                challenge = results['challenge']
                challenge_we_vote_id = challenge.we_vote_id
            success = results['success']
            status += results['status']

        if not positive_value_exists(success):
            results = {
                'success':              success,
                'status':               status,
                'challenge':            challenge,
                'challenge_changed':    challenge_changed,
                'challenge_created':    challenge_created,
                'challenge_found':      challenge_found,
                'challenge_we_vote_id': challenge_we_vote_id,
            }
            return results

        if not challenge_found:
            try:
                challenge_description = update_values.get('challenge_description', '')
                challenge_title = update_values.get('challenge_title', '')
                in_draft_mode = update_values.get('in_draft_mode', True)
                challenge = Challenge.objects.create(
                    challenge_description=challenge_description,
                    challenge_title=challenge_title,
                    in_draft_mode=in_draft_mode,
                    started_by_voter_we_vote_id=voter_we_vote_id,
                    supporters_count=0,
                )
                challenge_we_vote_id = challenge.we_vote_id
                challenge_found = True
            except Exception as e:
                challenge_created = False
                challenge = Challenge()
                success = False
                status += "CHALLENGE_NOT_CREATED: " + str(e) + " "

        if success and challenge_found:
            # Update existing challenge
            try:
                challenge_changed = False
                if 'challenge_description_changed' in update_values \
                        and positive_value_exists(update_values['challenge_description_changed']):
                    challenge.challenge_description = update_values['challenge_description']
                    challenge_changed = True
                # This is for the actual Challenge photo (profile image copied from Politician below)
                if 'challenge_photo_changed' in update_values \
                        and positive_value_exists(update_values['challenge_photo_changed']):
                    if 'we_vote_hosted_challenge_photo_original_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_challenge_photo_original_url']):
                        challenge.we_vote_hosted_challenge_photo_original_url = \
                            update_values['we_vote_hosted_challenge_photo_original_url']
                        challenge_changed = True
                    if 'we_vote_hosted_challenge_photo_large_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_challenge_photo_large_url']):
                        challenge.we_vote_hosted_challenge_photo_large_url = \
                            update_values['we_vote_hosted_challenge_photo_large_url']
                        challenge_changed = True
                    if 'we_vote_hosted_challenge_photo_medium_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_challenge_photo_medium_url']):
                        challenge.we_vote_hosted_challenge_photo_medium_url = \
                            update_values['we_vote_hosted_challenge_photo_medium_url']
                        challenge_changed = True
                    if 'we_vote_hosted_challenge_photo_small_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_challenge_photo_small_url']):
                        challenge.we_vote_hosted_challenge_photo_small_url = \
                            update_values['we_vote_hosted_challenge_photo_small_url']
                        challenge_changed = True
                elif 'challenge_photo_delete_changed' in update_values \
                        and positive_value_exists(update_values['challenge_photo_delete_changed']) \
                        and 'challenge_photo_delete' in update_values \
                        and positive_value_exists(update_values['challenge_photo_delete']):
                    # Only delete if another photo was not provided
                    challenge.we_vote_hosted_challenge_photo_original_url = None
                    challenge.we_vote_hosted_challenge_photo_large_url = None
                    challenge.we_vote_hosted_challenge_photo_medium_url = None
                    challenge.we_vote_hosted_challenge_photo_small_url = None
                    challenge_changed = True
                if 'challenge_title_changed' in update_values \
                        and positive_value_exists(update_values['challenge_title_changed']):
                    challenge.challenge_title = update_values['challenge_title']
                    challenge_changed = True
                if 'in_draft_mode_changed' in update_values \
                        and positive_value_exists(update_values['in_draft_mode_changed']):
                    in_draft_mode_may_be_updated = True
                    if positive_value_exists(challenge.challenge_title):
                        # An SEO friendly path is not created when we first create the challenge in draft mode
                        if not positive_value_exists(update_values['in_draft_mode']):
                            # If changing from in_draft_mode to published...
                            path_results = challenge_manager.generate_seo_friendly_path(
                                challenge_we_vote_id=challenge.we_vote_id,
                                challenge_title=challenge.challenge_title)
                            if path_results['seo_friendly_path_found']:
                                challenge.seo_friendly_path = path_results['seo_friendly_path']
                            else:
                                status += path_results['status']
                                # We don't want to prevent a challenge from leaving draft mode here
                                # in_draft_mode_may_be_updated = False
                    if in_draft_mode_may_be_updated:
                        challenge.in_draft_mode = positive_value_exists(update_values['in_draft_mode'])
                        challenge_changed = True
                if 'politician_we_vote_id' in update_values \
                        and positive_value_exists(update_values['politician_we_vote_id']):
                    challenge.politician_we_vote_id = update_values['politician_we_vote_id']
                    challenge_changed = True
                if 'opposers_count' in update_values \
                        and positive_value_exists(update_values['opposers_count']):
                    challenge.opposers_count = update_values['opposers_count']
                    challenge_changed = True
                if 'politician_delete_list_serialized' in update_values \
                        and positive_value_exists(update_values['politician_delete_list_serialized']):
                    # Delete from politician_delete_list
                    if update_values['politician_delete_list_serialized']:
                        politician_delete_list = \
                            json.loads(update_values['politician_delete_list_serialized'])
                    else:
                        politician_delete_list = []
                    results = challenge_manager.remove_challenge_politicians_from_delete_list(
                        challenge_we_vote_id=challenge.we_vote_id,
                        politician_delete_list=politician_delete_list,
                    )
                    status += results['status']
                # This is for the profile image copied from Politician (actual Challenge photo above)
                if 'politician_photo_changed' in update_values \
                        and positive_value_exists(update_values['politician_photo_changed']):
                    if 'we_vote_hosted_profile_image_url_large' in update_values:
                        challenge.we_vote_hosted_profile_image_url_large = \
                            update_values['we_vote_hosted_profile_image_url_large']
                        challenge_changed = True
                    if 'we_vote_hosted_profile_image_url_medium' in update_values:
                        challenge.we_vote_hosted_profile_image_url_medium = \
                            update_values['we_vote_hosted_profile_image_url_medium']
                        challenge_changed = True
                    if 'we_vote_hosted_profile_image_url_tiny' in update_values:
                        challenge.we_vote_hosted_profile_image_url_tiny = \
                            update_values['we_vote_hosted_profile_image_url_tiny']
                        challenge_changed = True
                elif 'politician_photo_delete_changed' in update_values \
                        and positive_value_exists(update_values['politician_photo_delete_changed']) \
                        and 'politician_photo_delete' in update_values \
                        and positive_value_exists(update_values['politician_photo_delete']):
                    # Only delete if another photo was not provided
                    challenge.we_vote_hosted_profile_image_url_large = None
                    challenge.we_vote_hosted_profile_image_url_medium = None
                    challenge.we_vote_hosted_profile_image_url_tiny = None
                    challenge_changed = True
                if 'politician_starter_list_changed' in update_values \
                        and positive_value_exists(update_values['politician_starter_list_changed']):
                    # Save to politician list
                    if update_values['politician_starter_list_serialized']:
                        challenge_politician_starter_list = \
                            json.loads(update_values['politician_starter_list_serialized'])
                    else:
                        challenge_politician_starter_list = []
                    results = challenge_manager.update_or_create_challenge_politicians_from_starter(
                        challenge_we_vote_id=challenge.we_vote_id,
                        politician_starter_list=challenge_politician_starter_list,
                    )
                    if results['success']:
                        challenge.politician_starter_list_serialized = None
                        challenge_changed = True
                    else:
                        # If save to politician list fails, save starter_list
                        challenge.politician_starter_list_serialized = \
                            update_values['politician_starter_list_serialized']
                        challenge_changed = True
                if 'supporters_count' in update_values \
                        and positive_value_exists(update_values['supporters_count']):
                    challenge.supporters_count = update_values['supporters_count']
                    challenge_changed = True
                if challenge_changed:
                    challenge.save()
                    status += "CHALLENGE_UPDATED "
                else:
                    status += "CHALLENGE_NOT_UPDATED-NO_CHANGES_FOUND "
                success = True
            except Exception as e:
                challenge = None
                success = False
                status += "CHALLENGE_NOT_UPDATED: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'challenge':            challenge,
            'challenge_changed':    challenge_changed,
            'challenge_created':    challenge_created,
            'challenge_found':      challenge_found,
            'challenge_we_vote_id': challenge_we_vote_id,
        }
        return results

    @staticmethod
    def update_or_create_challenges_are_not_duplicates(challenge1_we_vote_id, challenge2_we_vote_id):
        """
        Either update or create a ChallengesAreNotDuplicates entry.
        """
        exception_multiple_object_returned = False
        success = False
        new_challenges_are_not_duplicates_created = False
        challenges_are_not_duplicates = ChallengesAreNotDuplicates()
        status = ""

        if positive_value_exists(challenge1_we_vote_id) and positive_value_exists(challenge2_we_vote_id):
            try:
                updated_values = {
                    'challenge1_we_vote_id':    challenge1_we_vote_id,
                    'challenge2_we_vote_id':    challenge2_we_vote_id,
                }
                challenges_are_not_duplicates, new_challenges_are_not_duplicates_created = \
                    ChallengesAreNotDuplicates.objects.update_or_create(
                        challenge1_we_vote_id=challenge1_we_vote_id,
                        challenge2_we_vote_id=challenge2_we_vote_id,
                        defaults=updated_values)
                success = True
                status += "CHALLENGES_ARE_NOT_DUPLICATES_UPDATED_OR_CREATED "
            except ChallengesAreNotDuplicates.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_CHALLENGES_ARE_NOT_DUPLICATES_FOUND_BY_CANDIDATE_WE_VOTE_ID '
                exception_multiple_object_returned = True
            except Exception as e:
                status += 'EXCEPTION_UPDATE_OR_CREATE_CHALLENGES_ARE_NOT_DUPLICATES ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                                          success,
            'status':                                           status,
            'MultipleObjectsReturned':                          exception_multiple_object_returned,
            'new_challenges_are_not_duplicates_created': new_challenges_are_not_duplicates_created,
            'challenges_are_not_duplicates':             challenges_are_not_duplicates,
        }
        return results

    @staticmethod
    def update_or_create_challenge_news_item(
            challenge_news_item_we_vote_id='',
            challenge_we_vote_id='',
            organization_we_vote_id='',
            voter_we_vote_id='',
            update_values={}):
        status = ""
        success = True
        challenge_news_item = None
        challenge_news_item_changed = False
        challenge_news_item_created = False
        challenge_news_item_found = False
        challenge_manager = ChallengeManager()

        create_variables_exist = positive_value_exists(challenge_we_vote_id) \
            and positive_value_exists(voter_we_vote_id) \
            and positive_value_exists(organization_we_vote_id)
        update_variables_exist = positive_value_exists(challenge_we_vote_id) \
            and positive_value_exists(challenge_news_item_we_vote_id) \
            and positive_value_exists(voter_we_vote_id)
        if not create_variables_exist and not update_variables_exist:
            status += "COULD_NOT_UPDATE_OR_CREATE: "
            if not create_variables_exist:
                status += "CREATE_CHALLENGE_NEWS_ITEM_VARIABLES_MISSING "
            if not update_variables_exist:
                status += "UPDATE_CHALLENGE_NEWS_ITEM_VARIABLES_MISSING "
            results = {
                'success':                      False,
                'status':                       status,
                'challenge_news_item':          None,
                'challenge_news_item_changed':  False,
                'challenge_news_item_created':  False,
                'challenge_news_item_found':    False,
                'challenge_news_item_we_vote_id': challenge_news_item_we_vote_id,
                'challenge_we_vote_id':         '',
                'voter_we_vote_id':             '',
            }
            return results

        if not positive_value_exists(organization_we_vote_id):
            status += "UPDATE_CHALLENGE_NEWS_ITEM_MISSING_ORGANIZATION_WE_VOTE_ID "
            results = {
                'success':                      False,
                'status':                       status,
                'challenge_news_item':          None,
                'challenge_news_item_changed':  False,
                'challenge_news_item_created':  False,
                'challenge_news_item_found':    False,
                'challenge_news_item_we_vote_id': challenge_news_item_we_vote_id,
                'challenge_we_vote_id':         '',
                'voter_we_vote_id':             '',
            }
            return results

        if positive_value_exists(challenge_news_item_we_vote_id):
            results = challenge_manager.retrieve_challenge_news_item(
                challenge_news_item_we_vote_id=challenge_news_item_we_vote_id,
                read_only=False)
            challenge_news_item_found = results['challenge_news_item_found']
            if challenge_news_item_found:
                challenge_news_item = results['challenge_news_item']
            success = results['success']
            status += results['status']
        else:
            try:
                challenge_news_item = ChallengeNewsItem.objects.create(
                    challenge_news_subject=update_values['challenge_news_subject'],
                    challenge_news_text=update_values['challenge_news_text'],
                    challenge_we_vote_id=challenge_we_vote_id,
                    organization_we_vote_id=organization_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
                challenge_news_item_found = True
                status += "CHALLENGE_NEWS_ITEM_CREATED "
            except Exception as e:
                status += "CHALLENGE_NEWS_ITEM_NOT_CREATED: " + str(e) + " "
                success = False

        if not positive_value_exists(success) or not positive_value_exists(challenge_news_item_found):
            results = {
                'success':                      success,
                'status':                       status,
                'challenge_news_item':          challenge_news_item,
                'challenge_news_item_changed':  challenge_news_item_changed,
                'challenge_news_item_created':  challenge_news_item_created,
                'challenge_news_item_found':    challenge_news_item_found,
                'challenge_news_item_we_vote_id': challenge_news_item_we_vote_id,
                'challenge_we_vote_id':         challenge_we_vote_id,
                'voter_we_vote_id':             voter_we_vote_id,
            }
            return results

        organization_manager = OrganizationManager()
        # Update existing challenge_news_item with changes
        try:
            # Retrieve the speaker_name and we_vote_hosted_profile_image_url_tiny from the organization entry
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                if positive_value_exists(organization.organization_name):
                    challenge_news_item.speaker_name = organization.organization_name
                    challenge_news_item_changed = True
                if positive_value_exists(organization.we_vote_hosted_profile_image_url_medium):
                    challenge_news_item.we_vote_hosted_profile_image_url_medium = \
                        organization.we_vote_hosted_profile_image_url_medium
                    challenge_news_item_changed = True
                if positive_value_exists(organization.we_vote_hosted_profile_image_url_tiny):
                    challenge_news_item.we_vote_hosted_profile_image_url_tiny = \
                        organization.we_vote_hosted_profile_image_url_tiny
                    challenge_news_item_changed = True

            if 'challenge_news_subject_changed' in update_values \
                    and positive_value_exists(update_values['challenge_news_subject_changed']):
                challenge_news_item.challenge_news_subject = update_values['challenge_news_subject']
                challenge_news_item_changed = True
            if 'challenge_news_text_changed' in update_values \
                    and positive_value_exists(update_values['challenge_news_text_changed']):
                challenge_news_item.challenge_news_text = update_values['challenge_news_text']
                challenge_news_item_changed = True
            if 'in_draft_mode_changed' in update_values \
                    and positive_value_exists(update_values['in_draft_mode_changed']):
                challenge_news_item.in_draft_mode = update_values['in_draft_mode']
                challenge_news_item_changed = True
            if 'visible_to_public_changed' in update_values \
                    and positive_value_exists(update_values['visible_to_public_changed']):
                challenge_news_item.visible_to_public = update_values['visible_to_public']
                challenge_news_item_changed = True
            if challenge_news_item_changed:
                challenge_news_item.save()
                status += "CHALLENGE_NEWS_ITEM_UPDATED "
            else:
                status += "CHALLENGE_NEWS_ITEM_NOT_UPDATED-NO_CHANGES_FOUND "
            success = True
        except Exception as e:
            challenge_news_item = None
            challenge_news_item_changed = False
            success = False
            status += "CHALLENGE_NEWS_ITEM_NOT_UPDATED: " + str(e) + " "

        results = {
            'success':                          success,
            'status':                           status,
            'challenge_news_item':              challenge_news_item,
            'challenge_news_item_changed':      challenge_news_item_changed,
            'challenge_news_item_created':      challenge_news_item_created,
            'challenge_news_item_found':        challenge_news_item_found,
            'challenge_news_item_we_vote_id':   challenge_news_item_we_vote_id,
            'challenge_we_vote_id':             challenge_we_vote_id,
        }
        return results

    @staticmethod
    def update_or_create_challenge_owner(
            challenge_we_vote_id='',
            voter_we_vote_id='',
            organization_we_vote_id=None,
            organization_name=None,
            visible_to_public=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        status = ""
        if not positive_value_exists(challenge_we_vote_id) or not positive_value_exists(voter_we_vote_id):
            status += "MISSING_REQUIRED_VALUE_FOR_CHALLENGE_OWNER "
            results = {
                'success':                  False,
                'status':                   status,
                'challenge_owner_created':  False,
                'challenge_owner_found':    False,
                'challenge_owner_updated':  False,
                'challenge_owner':          None,
            }
            return results

        challenge_manager = ChallengeManager()
        challenge_owner_created = False
        challenge_owner_updated = False

        results = challenge_manager.retrieve_challenge_owner(
            challenge_we_vote_id=challenge_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=False)
        challenge_owner_found = results['challenge_owner_found']
        challenge_owner = results['challenge_owner']
        success = results['success']
        status += results['status']

        if positive_value_exists(organization_we_vote_id):
            organization_manager = OrganizationManager()
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                if organization_name is None:
                    organization_name = organization.organization_name
                if we_vote_hosted_profile_image_url_medium is None:
                    we_vote_hosted_profile_image_url_medium = organization.we_vote_hosted_profile_image_url_medium
                if we_vote_hosted_profile_image_url_tiny is None:
                    we_vote_hosted_profile_image_url_tiny = organization.we_vote_hosted_profile_image_url_tiny

        if challenge_owner_found:
            if organization_name is not None \
                    or organization_we_vote_id is not None \
                    or visible_to_public is not None \
                    or we_vote_hosted_profile_image_url_medium is not None \
                    or we_vote_hosted_profile_image_url_tiny is not None:
                try:
                    if organization_name is not None:
                        challenge_owner.organization_name = organization_name
                    if organization_we_vote_id is not None:
                        challenge_owner.organization_we_vote_id = organization_we_vote_id
                    if visible_to_public is not None:
                        challenge_owner.visible_to_public = positive_value_exists(visible_to_public)
                    if we_vote_hosted_profile_image_url_medium is not None:
                        challenge_owner.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                    if we_vote_hosted_profile_image_url_tiny is not None:
                        challenge_owner.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                    challenge_owner.save()
                    challenge_owner_updated = True
                    success = True
                    status += "CHALLENGE_OWNER_UPDATED "
                except Exception as e:
                    challenge_owner = ChallengeOwner()
                    success = False
                    status += "CHALLENGE_OWNER_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                challenge_owner = ChallengeOwner.objects.create(
                    challenge_we_vote_id=challenge_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                    visible_to_public=True,
                )
                if organization_name is not None:
                    challenge_owner.organization_name = organization_name
                if organization_we_vote_id is not None:
                    challenge_owner.organization_we_vote_id = organization_we_vote_id
                if visible_to_public is not None:
                    challenge_owner.visible_to_public = positive_value_exists(visible_to_public)
                if we_vote_hosted_profile_image_url_medium is not None:
                    challenge_owner.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                if we_vote_hosted_profile_image_url_tiny is not None:
                    challenge_owner.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                challenge_owner.save()
                challenge_owner_created = True
                success = True
                status += "CHALLENGE_OWNER_CREATED "
            except Exception as e:
                challenge_owner = None
                success = False
                status += "CHALLENGE_OWNER_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'challenge_owner_created':  challenge_owner_created,
            'challenge_owner_found':    challenge_owner_found,
            'challenge_owner_updated':  challenge_owner_updated,
            'challenge_owner':          challenge_owner,
        }
        return results

    @staticmethod
    def update_or_create_challenge_politician(
            challenge_we_vote_id='',
            politician_name=None,
            politician_we_vote_id=None,
            state_code='',
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        status = ""
        if not positive_value_exists(challenge_we_vote_id) or not positive_value_exists(politician_name):
            status += "MISSING_REQUIRED_VALUE_FOR_CHALLENGE_POLITICIAN "
            results = {
                'success':                      False,
                'status':                       status,
                'challenge_politician_created': False,
                'challenge_politician_found':   False,
                'challenge_politician_updated': False,
                'challenge_politician':         None,
            }
            return results

        challenge_manager = ChallengeManager()
        challenge_politician_created = False
        challenge_politician_updated = False

        results = challenge_manager.retrieve_challenge_politician(
            challenge_we_vote_id=challenge_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            politician_name=politician_name,
            read_only=False)
        challenge_politician_found = results['challenge_politician_found']
        challenge_politician = results['challenge_politician']
        success = results['success']
        status += results['status']

        if challenge_politician_found:
            if politician_name is not None \
                    or politician_we_vote_id is not None \
                    or state_code is not None \
                    or we_vote_hosted_profile_image_url_large is not None \
                    or we_vote_hosted_profile_image_url_medium is not None \
                    or we_vote_hosted_profile_image_url_tiny is not None:
                try:
                    if politician_name is not None:
                        challenge_politician.politician_name = politician_name
                    if politician_we_vote_id is not None:
                        challenge_politician.politician_we_vote_id = politician_we_vote_id
                    if state_code is not None:
                        challenge_politician.state_code = state_code
                    if we_vote_hosted_profile_image_url_large is not None:
                        challenge_politician.we_vote_hosted_profile_image_url_large = \
                            we_vote_hosted_profile_image_url_large
                    if we_vote_hosted_profile_image_url_medium is not None:
                        challenge_politician.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                    if we_vote_hosted_profile_image_url_tiny is not None:
                        challenge_politician.we_vote_hosted_profile_image_url_tiny = \
                            we_vote_hosted_profile_image_url_tiny
                    challenge_politician.save()
                    challenge_politician_updated = True
                    success = True
                    status += "CHALLENGE_POLITICIAN_UPDATED "
                except Exception as e:
                    challenge_politician = None
                    success = False
                    status += "CHALLENGE_POLITICIAN_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                challenge_politician = ChallengePolitician.objects.create(
                    challenge_we_vote_id=challenge_we_vote_id,
                    politician_name=politician_name,
                )
                if politician_we_vote_id is not None:
                    challenge_politician.politician_we_vote_id = politician_we_vote_id
                if state_code is not None:
                    challenge_politician.state_code = state_code
                if we_vote_hosted_profile_image_url_large is not None:
                    challenge_politician.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                if we_vote_hosted_profile_image_url_medium is not None:
                    challenge_politician.we_vote_hosted_profile_image_url_medium = \
                        we_vote_hosted_profile_image_url_medium
                if we_vote_hosted_profile_image_url_tiny is not None:
                    challenge_politician.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                challenge_politician.save()
                challenge_politician_created = True
                success = True
                status += "CHALLENGE_POLITICIAN_CREATED "
            except Exception as e:
                challenge_politician = None
                success = False
                status += "CHALLENGE_POLITICIAN_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'challenge_politician_created': challenge_politician_created,
            'challenge_politician_found':   challenge_politician_found,
            'challenge_politician_updated': challenge_politician_updated,
            'challenge_politician':         challenge_politician,
        }
        return results

    @staticmethod
    def update_or_create_challenge_politicians_from_starter(
            challenge_we_vote_id='',
            politician_starter_list=[]):
        success = True
        status = ''

        challenge_politician_existing_name_list = []
        challenge_politician_existing_we_vote_id_list = []
        challenge_politician_list_created = False
        challenge_politician_list_found = False
        challenge_politician_list_updated = False
        politician_starter_we_vote_id_list = []
        politician_starter_names_without_we_vote_id_list = []
        for politician_starter in politician_starter_list:
            # When politician_starter['value'] and politician_starter['label'] match, it means there isn't we_vote_id
            if positive_value_exists(politician_starter['value']) and \
                    politician_starter['value'] != politician_starter['label']:
                politician_starter_we_vote_id_list.append(politician_starter['value'])
            elif positive_value_exists(politician_starter['label']):
                politician_starter_names_without_we_vote_id_list.append(politician_starter['label'])

        challenge_manager = ChallengeManager()
        challenge_politician_list = challenge_manager.retrieve_challenge_politician_list(
            challenge_we_vote_id=challenge_we_vote_id,
            read_only=False,
        )
        for challenge_politician in challenge_politician_list:
            challenge_politician_existing_we_vote_id_list.append(challenge_politician.politician_we_vote_id)
            if not positive_value_exists(challenge_politician.politician_we_vote_id):
                challenge_politician_existing_name_list.append(challenge_politician.politician_name)
            if challenge_politician.politician_we_vote_id not in politician_starter_we_vote_id_list:
                # NOTE: For now we won't delete any names -- only add them
                if len(politician_starter_names_without_we_vote_id_list) == 0:
                    # Delete this challenge_politician
                    pass
                else:
                    # Make sure this politician isn't in the politician_starter_names_without_we_vote_id_list
                    pass

        from politician.models import PoliticianManager
        politician_manager = PoliticianManager()
        for challenge_politician_we_vote_id in politician_starter_we_vote_id_list:
            if challenge_politician_we_vote_id not in challenge_politician_existing_we_vote_id_list:
                results = politician_manager.retrieve_politician(
                    politician_we_vote_id=challenge_politician_we_vote_id,
                    read_only=True)
                if results['politician_found']:
                    # Create challenge_politician
                    create_results = challenge_manager.update_or_create_challenge_politician(
                        challenge_we_vote_id=challenge_we_vote_id,
                        politician_name=results['politician'].politician_name,
                        politician_we_vote_id=challenge_politician_we_vote_id,
                        state_code=results['politician'].state_code,
                        we_vote_hosted_profile_image_url_large=results['politician']
                        .we_vote_hosted_profile_image_url_large,
                        we_vote_hosted_profile_image_url_medium=results['politician']
                        .we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny=results['politician']
                        .we_vote_hosted_profile_image_url_tiny,
                    )
                    if challenge_politician_we_vote_id not in challenge_politician_existing_we_vote_id_list and \
                            create_results['challenge_politician_found'] or \
                            create_results['challenge_politician_created']:
                        challenge_politician_existing_we_vote_id_list.append(challenge_politician_we_vote_id)
        for challenge_politician_name in politician_starter_names_without_we_vote_id_list:
            if challenge_politician_name not in challenge_politician_existing_name_list:
                # Create challenge_politician
                create_results = challenge_manager.update_or_create_challenge_politician(
                    challenge_we_vote_id=challenge_we_vote_id,
                    politician_name=challenge_politician_name,
                    politician_we_vote_id=None,
                )
                if challenge_politician_name not in challenge_politician_existing_name_list and \
                        create_results['challenge_politician_found'] or \
                        create_results['challenge_politician_created']:
                    challenge_politician_existing_name_list.append(challenge_politician_name)

        results = {
            'success': success,
            'status': status,
            'challenge_politician_list_created':    challenge_politician_list_created,
            'challenge_politician_list_found':      challenge_politician_list_found,
            'challenge_politician_list_updated':    challenge_politician_list_updated,
            'challenge_politician_list':            challenge_politician_list,
        }
        return results

    @staticmethod
    def update_or_create_challenge_supporter(
            challenge_we_vote_id='',
            voter_we_vote_id='',
            organization_we_vote_id='',
            update_values={}):
        status = ""
        challenge_supporter = None
        challenge_supporter_changed = False
        challenge_supporter_created = False
        challenge_manager = ChallengeManager()

        create_variables_exist = positive_value_exists(challenge_we_vote_id) \
            and positive_value_exists(voter_we_vote_id) \
            and positive_value_exists(organization_we_vote_id)
        update_variables_exist = positive_value_exists(challenge_we_vote_id) \
            and positive_value_exists(voter_we_vote_id)
        if not create_variables_exist and not update_variables_exist:
            status += "COULD_NOT_UPDATE_OR_CREATE: "
            if not create_variables_exist:
                status += "CREATE_CHALLENGE_SUPPORTER_VARIABLES_MISSING "
            if not update_variables_exist:
                status += "UPDATE_CHALLENGE_SUPPORTER_VARIABLES_MISSING "
            results = {
                'success':                      False,
                'status':                       status,
                'challenge_supporter':          None,
                'challenge_supporter_changed':  False,
                'challenge_supporter_created':  False,
                'challenge_supporter_found':    False,
                'challenge_we_vote_id':         '',
                'voter_we_vote_id':             '',
            }
            return results

        results = challenge_manager.retrieve_challenge_supporter(
            challenge_we_vote_id=challenge_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=False)
        challenge_supporter_found = results['challenge_supporter_found']
        if challenge_supporter_found:
            challenge_supporter = results['challenge_supporter']
        success = results['success']
        status += results['status']

        if not positive_value_exists(success):
            results = {
                'success':                      success,
                'status':                       status,
                'challenge_supporter':          challenge_supporter,
                'challenge_supporter_changed':  challenge_supporter_changed,
                'challenge_supporter_created':  challenge_supporter_created,
                'challenge_supporter_found':    challenge_supporter_found,
                'challenge_we_vote_id':         challenge_we_vote_id,
                'voter_we_vote_id':             voter_we_vote_id,
            }
            return results

        organization_manager = OrganizationManager()
        challenge_supporter_changed = False
        if not challenge_supporter_found:
            try:
                challenge_supporter = ChallengeSupporter.objects.create(
                    challenge_supported=True,
                    challenge_we_vote_id=challenge_we_vote_id,
                    organization_we_vote_id=organization_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
                status += "CHALLENGE_SUPPORTER_CREATED "
                challenge_supporter_created = True
                challenge_supporter_found = True
                success = True
            except Exception as e:
                challenge_supporter_changed = False
                challenge_supporter_created = False
                challenge_supporter = None
                success = False
                status += "CHALLENGE_SUPPORTER_NOT_CREATED: " + str(e) + " "

        if challenge_supporter_found:
            # Update existing challenge_supporter with changes
            try:
                # Retrieve the supporter_name and we_vote_hosted_profile_image_url_tiny from the organization entry
                organization_results = \
                    organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
                if organization_results['organization_found']:
                    organization = organization_results['organization']
                    if positive_value_exists(organization.organization_name):
                        challenge_supporter.supporter_name = organization.organization_name
                        challenge_supporter_changed = True
                    if positive_value_exists(organization.we_vote_hosted_profile_image_url_medium):
                        challenge_supporter.we_vote_hosted_profile_image_url_medium = \
                            organization.we_vote_hosted_profile_image_url_medium
                        challenge_supporter_changed = True
                    if positive_value_exists(organization.we_vote_hosted_profile_image_url_tiny):
                        challenge_supporter.we_vote_hosted_profile_image_url_tiny = \
                            organization.we_vote_hosted_profile_image_url_tiny
                        challenge_supporter_changed = True

                if 'challenge_supported_changed' in update_values \
                        and positive_value_exists(update_values['challenge_supported_changed']):
                    challenge_supporter.challenge_supported = update_values['challenge_supported']
                    challenge_supporter_changed = True
                if 'linked_position_we_vote_id_changed' in update_values \
                        and positive_value_exists(update_values['linked_position_we_vote_id_changed']):
                    challenge_supporter.linked_position_we_vote_id = update_values['linked_position_we_vote_id']
                    challenge_supporter_changed = True
                if 'supporter_endorsement_changed' in update_values \
                        and positive_value_exists(update_values['supporter_endorsement_changed']):
                    challenge_supporter.supporter_endorsement = \
                        update_values['supporter_endorsement']
                    challenge_supporter_changed = True
                if 'visible_to_public_changed' in update_values \
                        and positive_value_exists(update_values['visible_to_public_changed']):
                    challenge_supporter.visible_to_public = update_values['visible_to_public']
                    challenge_supporter_changed = True
                if challenge_supporter_changed:
                    challenge_supporter.save()
                    status += "CHALLENGE_SUPPORTER_UPDATED "
                else:
                    status += "CHALLENGE_SUPPORTER_NOT_UPDATED-NO_CHANGES_FOUND "
                success = True
            except Exception as e:
                challenge_supporter = None
                challenge_supporter_changed = False
                success = False
                status += "CHALLENGE_SUPPORTER_NOT_UPDATED: " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'challenge_supporter':          challenge_supporter,
            'challenge_supporter_changed':  challenge_supporter_changed,
            'challenge_supporter_created':  challenge_supporter_created,
            'challenge_supporter_found':    challenge_supporter_found,
            'challenge_we_vote_id':         challenge_we_vote_id,
        }
        return results


class ChallengeOwner(models.Model):
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None

    def __unicode__(self):
        return "ChallengeOwner"

    challenge_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)
    feature_this_profile_image = models.BooleanField(default=True)
    order_in_list = models.PositiveIntegerField(null=True, unique=False)
    organization_name = models.CharField(max_length=255, null=False, blank=False)
    organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    visible_to_public = models.BooleanField(default=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)


class ChallengePolitician(models.Model):
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None

    def __unicode__(self):
        return "ChallengePolitician"

    challenge_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20240901" for September, 1, 2024)
    next_election_date_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    candidate_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    politician_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    politician_name = models.CharField(max_length=255, null=False, blank=False)
    state_code = models.CharField(verbose_name="politician home state", max_length=2, null=True)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)


class ChallengeSEOFriendlyPath(models.Model):
    objects = None

    def __unicode__(self):
        return "ChallengeSEOFriendlyPath"

    challenge_we_vote_id = models.CharField(max_length=255, null=True)
    challenge_title = models.CharField(max_length=255, null=False)
    base_pathname_string = models.CharField(max_length=255, null=True)
    pathname_modifier = models.CharField(max_length=10, null=True)  # A short random string to make sure path is unique
    final_pathname_string = models.CharField(max_length=255, null=True, unique=True, db_index=True)


class ChallengeSupporter(models.Model):
    objects = None

    def __unicode__(self):
        return "ChallengeSupporter"

    challenge_supported = models.BooleanField(default=True, db_index=True)
    challenge_we_vote_id = models.CharField(max_length=255, db_index=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True, db_index=True)
    date_supported = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    is_subscribed_by_email = models.BooleanField(default=None, null=True)
    linked_position_we_vote_id = models.CharField(max_length=255, null=True)
    organization_we_vote_id = models.CharField(max_length=255, null=True)
    supporter_name = models.CharField(max_length=255, null=True)
    supporter_endorsement = models.TextField(null=True)
    visibility_blocked_by_we_vote = models.BooleanField(default=False)
    visible_to_public = models.BooleanField(default=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(null=True)


class ChallengeNewsItem(models.Model):
    DoesNotExist = None
    objects = None

    def __unicode__(self):
        return "ChallengeNewsItem"

    challenge_we_vote_id = models.CharField(max_length=255, db_index=True)
    voter_we_vote_id = models.CharField(max_length=255, db_index=True)
    organization_we_vote_id = models.CharField(max_length=255, null=True)
    speaker_name = models.CharField(max_length=255, null=True)
    challenge_news_subject = models.TextField(null=True)
    challenge_news_text = models.TextField(null=True)
    in_draft_mode = models.BooleanField(default=True, db_index=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(null=True)
    visibility_blocked_by_we_vote = models.BooleanField(default=False)
    visible_to_public = models.BooleanField(default=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True, db_index=True)
    date_posted = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    date_sent_to_email = models.DateTimeField(null=True, db_index=True)
    we_vote_id = models.CharField(
        max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)

    # We override the save function, so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_challenge_news_item_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "chalnews" = tells us this is a unique id for a ChallengeNewsItem
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}chalnews{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(ChallengeNewsItem, self).save(*args, **kwargs)
