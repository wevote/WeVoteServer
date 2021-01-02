# share/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime, now
from organization.models import ORGANIZATION_TYPE_CHOICES, UNKNOWN
import sys
from wevote_functions.functions import convert_to_int, generate_random_string, positive_value_exists


class SharedItem(models.Model):
    """
    When a voter shares a link to a candidate, measure, office, or a ballot, map
    the
    """
    # The ending destination -- meaning the link that is being shared
    destination_full_url = models.URLField(max_length=255, blank=True, null=True)
    # A short code that is part of the link that is sent out. For example rFx5 as part of https://WeVote.US/-rFx5
    shared_item_code_no_opinions = models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    # Code for include_public_positions - Not implemented yet
    # shared_item_code_public_opinions = \
    #     models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    # Code for include_friends_only_positions
    shared_item_code_all_opinions = models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    # The voter and organization id of the person initiating the share
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_by_organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    shared_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    shared_by_state_code = models.CharField(max_length=2, null=True, db_index=True)
    # The owner of the custom site this share was from
    site_owner_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=False, db_index=True)
    google_civic_election_id = models.PositiveIntegerField(default=0, null=True, blank=True)
    hide_introduction = models.BooleanField(default=False)
    is_ballot_share = models.BooleanField(default=False)
    is_candidate_share = models.BooleanField(default=False)
    is_measure_share = models.BooleanField(default=False)
    is_office_share = models.BooleanField(default=False)
    is_organization_share = models.BooleanField(default=False)
    is_ready_share = models.BooleanField(default=False)
    # What is being shared
    candidate_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    measure_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    office_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    date_first_shared = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    # We store YYYY as an integer for very fast lookup (ex/ "2017" for permissions in the year 2017)
    year_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    deleted = models.BooleanField(default=False)

    # We override the save function to auto-generate date_as_integer
    def save(self, *args, **kwargs):
        if self.year_as_integer:
            self.year_as_integer = convert_to_int(self.year_as_integer)
        if self.year_as_integer == "" or self.year_as_integer is None:  # If there isn't a value...
            self.generate_year_as_integer()
        super(SharedItem, self).save(*args, **kwargs)

    def generate_year_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        year_as_string = "{:d}".format(
            datetime_now.year,
        )
        self.year_as_integer = convert_to_int(year_as_string)
        return


class SharedPermissionsGranted(models.Model):
    """
    Keep track of the permissions a voter has been granted from
    clicking a link that has been shared with them.
    Note: We use SharedPermissionsGranted to keep track of organizations that are on a voter's radar, even if
    include_friends_only_positions is False (which means they can only see PUBLIC_ONLY positions)
    """
    # The voter and organization id of the person initiating the share
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_by_organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    shared_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    # The person being granted the permissions
    shared_to_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_to_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    google_civic_election_id = models.PositiveIntegerField(default=0, null=True, blank=True)
    # We store YYYY as an integer for very fast lookup (ex/ "2017" for permissions in the year 2017)
    year_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    # Having an entry in this table assumes include_public_positions is True
    include_friends_only_positions = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)


class SharedLinkClicked(models.Model):
    """
    Keep track of each time the shared link was clicked
    """
    # The ending destination -- meaning the link that is being shared
    destination_full_url = models.URLField(max_length=255, blank=True, null=True)
    # The voter and organization id of the person initiating the share
    shared_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    shared_by_organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    shared_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    shared_by_state_code = models.CharField(max_length=2, null=True, db_index=True)
    # The person clicking the link
    viewed_by_voter_we_vote_id = models.CharField(max_length=255, null=True, db_index=True)
    viewed_by_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    viewed_by_state_code = models.CharField(max_length=2, null=True, db_index=True)
    # Information about the share item clicked
    shared_item_id = models.PositiveIntegerField(default=0, null=True, blank=True)
    shared_item_code = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    site_owner_organization_we_vote_id = models.CharField(max_length=255, null=True)
    include_public_positions = models.BooleanField(default=False)
    include_friends_only_positions = models.BooleanField(default=False)
    date_clicked = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
    # We store YYYY as an integer for very fast lookup (ex/ "2017" for the year 2017)
    year_as_integer = models.PositiveIntegerField(null=True, unique=False, db_index=True)


class ShareManager(models.Model):
    # Extending models.Models creates a useless empty table, we probably want to extend models.Manager here

    def __unicode__(self):
        return "ShareManager"

    def create_shared_link_clicked(
            self,
            destination_full_url='',
            shared_item_code='',
            shared_item_id=0,
            shared_by_voter_we_vote_id='',
            shared_by_organization_type='',
            shared_by_organization_we_vote_id='',
            site_owner_organization_we_vote_id='',
            viewed_by_voter_we_vote_id='',
            viewed_by_organization_we_vote_id='',
            include_public_positions=False,
            include_friends_only_positions=False):
        status = ""

        try:
            include_public_positions = positive_value_exists(include_public_positions)
            include_friends_only_positions = positive_value_exists(include_friends_only_positions)
            year_as_integer = self.generate_year_as_integer()
            shared_link_clicked = SharedLinkClicked.objects.create(
                destination_full_url=destination_full_url,
                include_public_positions=include_public_positions,
                include_friends_only_positions=include_friends_only_positions,
                shared_item_code=shared_item_code,
                shared_item_id=shared_item_id,
                shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                shared_by_organization_type=shared_by_organization_type,
                shared_by_organization_we_vote_id=shared_by_organization_we_vote_id,
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
                viewed_by_voter_we_vote_id=viewed_by_voter_we_vote_id,
                viewed_by_organization_we_vote_id=viewed_by_organization_we_vote_id,
                year_as_integer=year_as_integer,
            )
            shared_link_clicked_saved = True
            success = True
            status += "SHARED_LINK_CLICKED_CREATED "
        except Exception as e:
            shared_link_clicked_saved = False
            shared_link_clicked = None
            success = False
            status += "SHARED_LINK_CLICKED_NOT_CREATED " + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'shared_link_clicked_saved':    shared_link_clicked_saved,
            'shared_link_clicked':          shared_link_clicked,
        }
        return results

    def create_or_update_shared_item(
            self,
            destination_full_url='',
            shared_by_voter_we_vote_id='',
            google_civic_election_id=None,
            defaults={}):
        create_shared_item_code_no_opinions = True
        create_shared_item_code_all_opinions = True
        shared_item_code_no_opinions = ''
        shared_item_code_all_opinions = ''
        shared_item_created = False
        shared_item_found = False
        status = ""
        success = True
        if positive_value_exists(google_civic_election_id):
            google_civic_election_id = convert_to_int(google_civic_election_id)
        else:
            google_civic_election_id = 0
        if not positive_value_exists(destination_full_url) or not positive_value_exists(shared_by_voter_we_vote_id):
            status += "CREATE_OR_UPDATE_SHARED_ITEM-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':              False,
                'status':               status,
                'shared_item_found':    shared_item_found,
                'shared_item_created':  shared_item_created,
                'shared_item':          None,
            }
            return results

        results = self.retrieve_shared_item(
            destination_full_url=destination_full_url,
            shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
            google_civic_election_id=google_civic_election_id,
            read_only=False)
        shared_item_found = results['shared_item_found']
        shared_item = results['shared_item']
        success = results['success']
        status += results['status']

        if shared_item_found:
            if positive_value_exists(shared_item.shared_item_code_no_opinions):
                create_shared_item_code_no_opinions = False
            if positive_value_exists(shared_item.shared_item_code_all_opinions):
                create_shared_item_code_all_opinions = False
            if not positive_value_exists(defaults['shared_by_organization_we_vote_id']):
                pass

        if create_shared_item_code_no_opinions:
            random_string = generate_random_string(6)
            # TODO: Confirm its not in use
            shared_item_code_no_opinions = random_string

        if create_shared_item_code_all_opinions:
            random_string = generate_random_string(10)
            # TODO: Confirm its not in use
            shared_item_code_all_opinions = random_string

        if shared_item_found:
            if positive_value_exists(shared_item_code_no_opinions) \
                    or positive_value_exists(shared_item_code_all_opinions) \
                    or not positive_value_exists(shared_item.year_as_integer):
                # There is a reason to update
                try:
                    change_to_save = False
                    if positive_value_exists(shared_item_code_no_opinions):
                        shared_item.shared_item_code_no_opinions = shared_item_code_no_opinions
                        change_to_save = True
                    if positive_value_exists(shared_item_code_all_opinions):
                        shared_item.shared_item_code_all_opinions = shared_item_code_all_opinions
                        change_to_save = True
                    if not positive_value_exists(shared_item.year_as_integer):
                        shared_item.generate_year_as_integer()
                        change_to_save = True
                    if change_to_save:
                        shared_item.save()
                        shared_item_created = True
                        success = True
                        status += "SHARED_ITEM_UPDATED "
                except Exception as e:
                    shared_item_created = False
                    shared_item = None
                    success = False
                    status += "SHARED_ITEM_NOT_UPDATED " + str(e) + " "
        else:
            try:
                shared_item = SharedItem.objects.create(
                    candidate_we_vote_id=defaults['candidate_we_vote_id'],
                    destination_full_url=destination_full_url,
                    google_civic_election_id=google_civic_election_id,
                    is_ballot_share=defaults['is_ballot_share'],
                    is_candidate_share=defaults['is_candidate_share'],
                    is_measure_share=defaults['is_measure_share'],
                    is_office_share=defaults['is_office_share'],
                    is_organization_share=defaults['is_organization_share'],
                    is_ready_share=defaults['is_ready_share'],
                    measure_we_vote_id=defaults['measure_we_vote_id'],
                    office_we_vote_id=defaults['office_we_vote_id'],
                    shared_by_organization_type=defaults['shared_by_organization_type'],
                    shared_by_organization_we_vote_id=defaults['shared_by_organization_we_vote_id'],
                    shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                    shared_item_code_no_opinions=shared_item_code_no_opinions,
                    shared_item_code_all_opinions=shared_item_code_all_opinions,
                    site_owner_organization_we_vote_id=defaults['site_owner_organization_we_vote_id'],
                )
                shared_item_created = True
                shared_item_found = True
                status += "SHARED_ITEM_CREATED "
            except Exception as e:
                shared_item_created = False
                shared_item = None
                success = False
                status += "SHARED_ITEM_NOT_CREATED " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'shared_item_found':    shared_item_found,
            'shared_item_created':  shared_item_created,
            'shared_item':          shared_item,
        }
        return results

    def create_or_update_shared_permissions_granted(
            self,
            shared_by_voter_we_vote_id='',
            shared_by_organization_type='',
            shared_by_organization_we_vote_id='',
            shared_to_voter_we_vote_id='',
            shared_to_organization_we_vote_id='',
            google_civic_election_id=None,
            year_as_integer=None,
            include_friends_only_positions=False):
        shared_permissions_granted_created = False
        shared_permissions_granted_found = False
        status = ""
        success = True
        if positive_value_exists(google_civic_election_id):
            google_civic_election_id = convert_to_int(google_civic_election_id)
        else:
            google_civic_election_id = 0

        if not positive_value_exists(shared_by_voter_we_vote_id) \
                or not positive_value_exists(shared_to_voter_we_vote_id) or not positive_value_exists(year_as_integer):
            status += "CREATE_OR_UPDATE_SHARED_PERMISSIONS_GRANTED-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':              False,
                'status':               status,
                'shared_permissions_granted_found':    shared_permissions_granted_found,
                'shared_permissions_granted_created':  shared_permissions_granted_created,
                'shared_permissions_granted':          None,
            }
            return results

        results = self.retrieve_shared_permissions_granted(
            shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
            shared_to_voter_we_vote_id=shared_to_voter_we_vote_id,
            google_civic_election_id=google_civic_election_id,
            year_as_integer=year_as_integer,
            read_only=False)
        shared_permissions_granted_found = results['shared_permissions_granted_found']
        shared_permissions_granted = results['shared_permissions_granted']
        success = results['success']
        status += results['status']

        if shared_permissions_granted_found:
            # Are we going from include_friends_only_positions == False to include_friends_only_positions == True?
            include_friends_only_positions_added = \
                not positive_value_exists(shared_permissions_granted.include_friends_only_positions) \
                and positive_value_exists(include_friends_only_positions)
            if not positive_value_exists(shared_permissions_granted.year_as_integer) \
                    or include_friends_only_positions_added:
                # There is a reason to update
                try:
                    change_to_save = False
                    if not positive_value_exists(shared_permissions_granted.year_as_integer):
                        shared_permissions_granted.year_as_integer = year_as_integer
                        change_to_save = True
                    if include_friends_only_positions_added:
                        shared_permissions_granted.include_friends_only_positions = True
                        change_to_save = True
                    if change_to_save:
                        shared_permissions_granted.save()
                        shared_permissions_granted_created = True
                        success = True
                        status += "SHARED_PERMISSIONS_GRANTED_UPDATED "
                except Exception as e:
                    shared_permissions_granted_created = False
                    shared_permissions_granted = None
                    success = False
                    status += "SHARED_PERMISSIONS_GRANTED_NOT_UPDATED " + str(e) + " "
        else:
            try:
                shared_permissions_granted = SharedPermissionsGranted.objects.create(
                    shared_by_voter_we_vote_id=shared_by_voter_we_vote_id,
                    shared_by_organization_type=shared_by_organization_type,
                    shared_by_organization_we_vote_id=shared_by_organization_we_vote_id,
                    shared_to_voter_we_vote_id=shared_to_voter_we_vote_id,
                    shared_to_organization_we_vote_id=shared_to_organization_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    year_as_integer=year_as_integer,
                    include_friends_only_positions=include_friends_only_positions,
                )
                shared_permissions_granted_created = True
                shared_permissions_granted_found = True
                status += "SHARED_PERMISSIONS_GRANTED_CREATED "
            except Exception as e:
                shared_permissions_granted_created = False
                shared_permissions_granted = None
                success = False
                status += "SHARED_PERMISSIONS_GRANTED_NOT_CREATED " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'shared_permissions_granted_found':    shared_permissions_granted_found,
            'shared_permissions_granted_created':  shared_permissions_granted_created,
            'shared_permissions_granted':          shared_permissions_granted,
        }
        return results

    def fetch_shared_link_clicked_unique_sharer_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='shared_by_voter_we_vote_id')

    def fetch_shared_link_clicked_unique_viewer_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='viewed_by_voter_we_vote_id')

    def fetch_shared_link_clicked_shared_links_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='shared_item_id')

    def fetch_shared_link_clicked_shared_links_click_count(
            self, shared_by_state_code_list=[], viewed_by_state_code_list=[], year_as_integer_list=[]):
        return self.fetch_shared_link_clicked_count(
            shared_by_state_code_list=shared_by_state_code_list,
            viewed_by_state_code_list=viewed_by_state_code_list,
            year_as_integer_list=year_as_integer_list,
            field_for_distinct_filter='id')

    def fetch_shared_link_clicked_count(
            self, shared_by_state_code_list=[],
            viewed_by_state_code_list=[],
            year_as_integer_list=[],
            field_for_distinct_filter=''):
        if 'test' in sys.argv:
            # If coming from a test, we cannot use readonly
            queryset = SharedLinkClicked.objects.all()
        else:
            queryset = SharedLinkClicked.objects.using('readonly').all()

        if positive_value_exists(len(shared_by_state_code_list)):
            queryset = queryset.filter(shared_by_state_code__in=shared_by_state_code_list)
        if positive_value_exists(len(viewed_by_state_code_list)):
            queryset = queryset.filter(viewed_by_state_code__in=viewed_by_state_code_list)
        if positive_value_exists(len(year_as_integer_list)):
            queryset = queryset.filter(year_as_integer__in=year_as_integer_list)
        if positive_value_exists(field_for_distinct_filter):
            queryset = queryset.values(field_for_distinct_filter).distinct()

        shared_link_clicked_count = 0
        try:
            shared_link_clicked_count = queryset.count()
        except Exception as e:
            pass

        return shared_link_clicked_count

    def generate_year_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        datetime_now = localtime(now()).date()  # We Vote uses Pacific Time for TIME_ZONE
        year_as_string = "{:d}".format(
            datetime_now.year,
        )
        return convert_to_int(year_as_string)

    def retrieve_shared_item(
            self, shared_item_id=0,
            shared_item_code='',
            destination_full_url='',
            shared_by_voter_we_vote_id='',
            google_civic_election_id='',
            read_only=False):
        """

        :param shared_item_id:
        :param shared_item_code:
        :param destination_full_url:
        :param shared_by_voter_we_vote_id:
        :param google_civic_election_id:
        :param read_only:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        shared_item_found = False
        shared_item = SharedItem()
        shared_item_list_found = False
        shared_item_list = []
        status = ""

        try:
            if positive_value_exists(shared_item_id):
                if positive_value_exists(read_only):
                    shared_item = SharedItem.objects.using('readonly').get(
                        id=shared_item_id,
                        deleted=False
                    )
                else:
                    shared_item = SharedItem.objects.get(
                        id=shared_item_id,
                        deleted=False
                    )
                shared_item_id = shared_item.id
                shared_item_found = True
                success = True
                status += "RETRIEVE_SHARED_ITEM_FOUND_BY_ID "
            elif positive_value_exists(shared_item_code):
                if positive_value_exists(read_only):
                    shared_item = SharedItem.objects.using('readonly').get(
                        Q(shared_item_code_no_opinions=shared_item_code) |
                        Q(shared_item_code_all_opinions=shared_item_code),
                        deleted=False
                    )
                else:
                    shared_item = SharedItem.objects.get(
                        Q(shared_item_code_no_opinions=shared_item_code) |
                        Q(shared_item_code_all_opinions=shared_item_code),
                        deleted=False
                    )
                shared_item_id = shared_item.id
                shared_item_found = True
                success = True
                status += "RETRIEVE_SHARED_ITEM_FOUND_BY_CODE "
            elif positive_value_exists(destination_full_url) and positive_value_exists(shared_by_voter_we_vote_id):
                if positive_value_exists(read_only):
                    shared_item_queryset = SharedItem.objects.using('readonly').all()
                else:
                    shared_item_queryset = SharedItem.objects.all()
                if positive_value_exists(google_civic_election_id):
                    shared_item_queryset = shared_item_queryset.filter(
                        destination_full_url__iexact=destination_full_url,
                        shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                        google_civic_election_id=google_civic_election_id,
                        deleted=False
                    )
                else:
                    shared_item_queryset = shared_item_queryset.filter(
                        destination_full_url__iexact=destination_full_url,
                        shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                        deleted=False
                    )
                # We need the sms that has been verified sms at top of list
                shared_item_queryset = shared_item_queryset.order_by('-date_first_shared')
                shared_item_list = shared_item_queryset

                if len(shared_item_list):
                    if len(shared_item_list) == 1:
                        # If only one shared_item is found, return the results as a single shared_item
                        shared_item = shared_item_list[0]
                        shared_item_id = shared_item.id
                        shared_item_found = True
                        shared_item_list_found = False
                        success = True
                        status += "RETRIEVE_SHARED_ITEM_FOUND_BY_URL-ONLY_ONE_FOUND "
                    else:
                        success = True
                        shared_item = shared_item_list[0]
                        shared_item_found = True
                        shared_item_list_found = True
                        status += 'RETRIEVE_SHARED_ITEM_FOUND_BY_URL-LIST_RETRIEVED '
                else:
                    success = True
                    shared_item_list_found = False
                    status += 'RETRIEVE_SHARED_ITEM-NO_SHARED_ITEM_LIST_RETRIEVED '
            else:
                shared_item_found = False
                success = False
                status += "RETRIEVE_SHARED_ITEM_VARIABLES_MISSING "
        except SharedItem.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_SHARED_ITEM_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED_RETRIEVE_SHARED_ITEM ' + str(e) + ' '

        results = {
            'success':                 success,
            'status':                  status,
            'DoesNotExist':            exception_does_not_exist,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'shared_item_found':       shared_item_found,
            'shared_item_id':          shared_item_id,
            'shared_item':             shared_item,
            'shared_item_list_found':  shared_item_list_found,
            'shared_item_list':        shared_item_list,
        }
        return results

    def retrieve_shared_permissions_granted(
            self, shared_permissions_granted_id=0,
            shared_by_voter_we_vote_id='',
            shared_to_voter_we_vote_id='',
            google_civic_election_id=0,
            year_as_integer=0,
            current_year_only=True,
            read_only=False):
        """
        This implementation assumes we only ever get single item results
        :param shared_permissions_granted_id:
        :param shared_by_voter_we_vote_id:
        :param shared_to_voter_we_vote_id:
        :param google_civic_election_id:
        :param year_as_integer:
        :param current_year_only:
        :param read_only:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        shared_permissions_granted_found = False
        shared_permissions_granted = None
        status = ""

        if positive_value_exists(current_year_only):
            year_as_integer = self.generate_year_as_integer()

        try:
            if positive_value_exists(shared_permissions_granted_id):
                if positive_value_exists(read_only):
                    shared_permissions_granted = SharedPermissionsGranted.objects.using('readonly').get(
                        id=shared_permissions_granted_id,
                        deleted=False
                    )
                else:
                    shared_permissions_granted = SharedPermissionsGranted.objects.get(
                        id=shared_permissions_granted_id,
                        deleted=False
                    )
                shared_permissions_granted_id = shared_permissions_granted.id
                shared_permissions_granted_found = True
                success = True
                status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND_BY_ID "
            elif positive_value_exists(shared_by_voter_we_vote_id) \
                    and positive_value_exists(shared_to_voter_we_vote_id) and positive_value_exists(year_as_integer):
                if positive_value_exists(read_only):
                    shared_permissions_granted_queryset = SharedPermissionsGranted.objects.using('readonly').all()
                else:
                    shared_permissions_granted_queryset = SharedPermissionsGranted.objects.all()
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                    shared_to_voter_we_vote_id__iexact=shared_to_voter_we_vote_id,
                    deleted=False
                )
                if positive_value_exists(google_civic_election_id):
                    shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                        google_civic_election_id=google_civic_election_id,
                    )
                if positive_value_exists(year_as_integer):
                    shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                        year_as_integer=year_as_integer,
                    )
                # We need the sms that has been verified sms at top of list
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.order_by('-id')
                shared_permissions_granted_list = list(shared_permissions_granted_queryset)

                if len(shared_permissions_granted_list):
                    if len(shared_permissions_granted_list) == 1:
                        # If only one shared_permissions_granted is found,
                        # return the results as a single shared_permissions_granted
                        shared_permissions_granted = shared_permissions_granted_list[0]
                        shared_permissions_granted_id = shared_permissions_granted.id
                        shared_permissions_granted_found = True
                        success = True
                        status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND-ONLY_ONE_FOUND "
                    else:
                        success = True
                        shared_permissions_granted = shared_permissions_granted_list[0]
                        shared_permissions_granted_found = True
                        status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND-LIST_RETRIEVED '
                        if not positive_value_exists(read_only):
                            # Consider marking additional items as deleted
                            number_found = len(shared_permissions_granted_list)
                            for index in range(1, number_found):
                                temp_shared_permissions_granted = shared_permissions_granted_list[index]
                                temp_shared_permissions_granted.deleted = True
                                temp_shared_permissions_granted.save()
                else:
                    success = True
                    status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED-NO_SHARED_PERMISSIONS_GRANTED_LIST_RETRIEVED '
            else:
                shared_permissions_granted_found = False
                success = False
                status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_VARIABLES_MISSING "
        except SharedPermissionsGranted.DoesNotExist:
            exception_does_not_exist = True
            success = True
            status += "RETRIEVE_SHARED_PERMISSIONS_GRANTED_NOT_FOUND "
        except Exception as e:
            success = False
            status += 'FAILED retrieve_shared_permissions_granted SharedPermissionsGranted ' + str(e) + ' '

        results = {
            'success':                 success,
            'status':                  status,
            'DoesNotExist':            exception_does_not_exist,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'shared_permissions_granted_found':       shared_permissions_granted_found,
            'shared_permissions_granted_id':          shared_permissions_granted_id,
            'shared_permissions_granted':             shared_permissions_granted,
        }
        return results

    def retrieve_shared_permissions_granted_list(self,
                                                 shared_by_voter_we_vote_id='',
                                                 shared_to_voter_we_vote_id='',
                                                 google_civic_election_id=0,
                                                 year_as_integer=0,
                                                 current_year_only=True,
                                                 only_include_friends_only_positions=False,
                                                 read_only=False):
        shared_permissions_granted_list_found = False
        shared_permissions_granted_list = []
        status = ""
        if positive_value_exists(current_year_only):
            year_as_integer = self.generate_year_as_integer()

        try:
            if positive_value_exists(read_only):
                shared_permissions_granted_queryset = SharedPermissionsGranted.objects.using('readonly').all()
            else:
                shared_permissions_granted_queryset = SharedPermissionsGranted.objects.all()
            shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                deleted=False
            )
            if positive_value_exists(shared_by_voter_we_vote_id):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    shared_by_voter_we_vote_id__iexact=shared_by_voter_we_vote_id,
                )
            if positive_value_exists(shared_to_voter_we_vote_id):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    shared_to_voter_we_vote_id__iexact=shared_to_voter_we_vote_id,
                )
            if positive_value_exists(google_civic_election_id):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    google_civic_election_id=google_civic_election_id,
                )
            if positive_value_exists(year_as_integer):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    year_as_integer=year_as_integer,
                )
            if positive_value_exists(only_include_friends_only_positions):
                shared_permissions_granted_queryset = shared_permissions_granted_queryset.filter(
                    include_friends_only_positions=True,
                )

            shared_permissions_granted_queryset = shared_permissions_granted_queryset.order_by('-id')
            shared_permissions_granted_list = list(shared_permissions_granted_queryset)

            if len(shared_permissions_granted_list):
                success = True
                shared_permissions_granted_list_found = True
                status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED_FOUND-LIST_RETRIEVED '
            else:
                success = True
                shared_permissions_granted_list_found = False
                status += 'RETRIEVE_SHARED_PERMISSIONS_GRANTED-NO_SHARED_PERMISSIONS_GRANTED_LIST_RETRIEVED '
        except Exception as e:
            success = False
            status += 'FAILED-RETRIEVE_SHARED_PERMISSIONS_GRANTED_LIST ' + str(e) + ' '

        results = {
            'success': success,
            'status': status,
            'shared_permissions_granted_list_found': shared_permissions_granted_list_found,
            'shared_permissions_granted_list': shared_permissions_granted_list,
        }
        return results
