# quick_info/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
# Diagrams here: https://docs.google.com/drawings/d/1fEs_f2-4Du9knJ8FXn6PQ2BcmXL4zSkMYh-cp75EeLE/edit

from django.db import models
from exception.models import handle_exception, handle_record_found_more_than_one_exception,\
    handle_record_not_saved_exception
import wevote_functions.admin
from wevote_functions.models import convert_to_int, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_last_quick_info_integer, \
    fetch_next_we_vote_id_last_quick_info_master_integer, fetch_site_unique_id_prefix

# Language Codes: http://www.mcanerin.com/en/articles/meta-language.asp
# Country Codes: http://www.mcanerin.com/en/articles/ccTLD.asp
SPANISH = 'es'
ENGLISH = 'en'
TAGALOG = 'tl'
VIETNAMESE = 'vi'
CHINESE = 'zh'
LANGUAGE_CHOICES = (
    (ENGLISH,    'English'),
    (SPANISH,    'Spanish'),
    (TAGALOG,    'Tagalog'),
    (VIETNAMESE, 'Vietnamese'),
    (CHINESE,    'Chinese'),
)

OFFICE = 'office'
CANDIDATE = 'candidate'
POLITICIAN = 'politician'
MEASURE = 'measure'
KIND_OF_BALLOT_ITEM_CHOICES = (
    (OFFICE,        'Office'),
    (CANDIDATE,     'Candidate'),
    (POLITICIAN,    'Politician'),
    (MEASURE,       'Measure'),
)

BALLOTPEDIA = 'ballotpedia'
DIRECT_ENTRY = 'direct'
WIKIPEDIA = 'wikipedia'
SOURCE_SITE_CHOICES = (
    (BALLOTPEDIA,   'Ballotpedia'),
    (DIRECT_ENTRY,  'Direct Entry'),
    (WIKIPEDIA,     'Wikipedia'),
)

logger = wevote_functions.admin.get_logger(__name__)


class QuickInfo(models.Model):
    """
    The information that shows when you click an info icon next to a ballot item
    """
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "info", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_quick_info_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)

    # The language that this text is in
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default=ENGLISH)

    info_text = models.TextField(null=True, blank=True)
    info_html = models.TextField(null=True, blank=True)

    ballot_item_label = models.CharField(verbose_name="text name for ballot item for quick display",
                                         max_length=255, null=True, blank=True)

    site_to_credit = models.CharField(max_length=15, choices=SOURCE_SITE_CHOICES, default=BALLOTPEDIA)

    # A link to any location with more information about this quick information
    more_info_url = models.URLField(blank=True, null=True, verbose_name='url with more the full entry for this info')

    last_updated = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)

    # The unique id of the last person who edited this entry.
    last_editor_we_vote_id = models.CharField(
        verbose_name="last editor we vote id", max_length=255, null=True, blank=True, unique=False)

    # This is the office that the quick_info refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_office", max_length=255, null=True, blank=True, unique=False)

    # This is the candidate/politician that the quick_info refers to.
    #  Either candidate_campaign is filled, contest_office OR contest_measure, but not all three
    candidate_campaign_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the candidate_campaign", max_length=255, null=True,
        blank=True, unique=False)

    # Useful for queries based on Politicians
    politician_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for politician", max_length=255, null=True,
        blank=True, unique=False)

    # This is the measure/initiative/proquick_info that the quick_info refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_measure", max_length=255, null=True,
        blank=True, unique=False)

    # There are many ballot items that don't have (or need) a custom quick_info entry, and can reference a general
    # entry. This field is the we_vote_id of the master quick_info entry that has the general text.
    link_to_master_we_vote_id = models.CharField(
        verbose_name="we vote id of other entry which is the master", max_length=255, default=None, null=True,
        blank=True, unique=True)

    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)

    def __unicode__(self):
        return self.we_vote_id

    class Meta:
        ordering = ('last_updated',)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this organization came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_quick_info_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "info" = tells us this is a unique id for a quick_info entry
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}info{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(QuickInfo, self).save(*args, **kwargs)

    def is_english(self):
        if self.language == ENGLISH:
            return True
        return False

    def is_spanish(self):
        if self.language == SPANISH:
            return True
        return False

    def is_vietnamese(self):
        if self.language == VIETNAMESE:
            return True
        return False

    def is_chinese(self):
        if self.language == CHINESE:
            return True
        return False

    def is_tagalog(self):
        if self.language == TAGALOG:
            return True
        return False

    def get_ballot_item_we_vote_id(self):
        if positive_value_exists(self.contest_office_we_vote_id):
            return self.contest_office_we_vote_id
        elif positive_value_exists(self.candidate_campaign_we_vote_id):
            return self.candidate_campaign_we_vote_id
        elif positive_value_exists(self.politician_we_vote_id):
            return self.politician_we_vote_id
        elif positive_value_exists(self.contest_measure_we_vote_id):
            return self.contest_measure_we_vote_id
        return None


class QuickInfoManager(models.Model):

    def __unicode__(self):
        return "QuickInfoManager"

    def fetch_we_vote_id_from_local_id(self, quick_info_id):
        if positive_value_exists(quick_info_id):
            results = self.retrieve_quick_info_from_id(quick_info_id)
            if results['quick_info_found']:
                quick_info = results['quick_info']
                return quick_info.we_vote_id
            else:
                return None
        else:
            return None

    def retrieve_contest_office_quick_info(self, contest_office_we_vote_id):
        quick_info_id = 0
        quick_info_we_vote_id = None
        candidate_campaign_we_vote_id = None
        politician_we_vote_id = None
        contest_measure_we_vote_id = None
        quick_info_manager = QuickInfoManager()
        return quick_info_manager.retrieve_quick_info(
            quick_info_id, quick_info_we_vote_id,
            contest_office_we_vote_id,
            candidate_campaign_we_vote_id,
            politician_we_vote_id,
            contest_measure_we_vote_id
        )

    def retrieve_candidate_campaign_quick_info(self, candidate_campaign_we_vote_id):
        quick_info_id = 0
        quick_info_we_vote_id = None
        politician_we_vote_id = None
        contest_measure_we_vote_id = None
        contest_office_we_vote_id = None
        quick_info_manager = QuickInfoManager()
        return quick_info_manager.retrieve_quick_info(
            quick_info_id, quick_info_we_vote_id,
            contest_office_we_vote_id,
            candidate_campaign_we_vote_id,
            politician_we_vote_id,
            contest_measure_we_vote_id
        )

    def retrieve_contest_measure_quick_info(self, contest_measure_we_vote_id):
        quick_info_id = 0
        quick_info_we_vote_id = None
        candidate_campaign_we_vote_id = None
        politician_we_vote_id = None
        contest_office_we_vote_id = None
        quick_info_manager = QuickInfoManager()
        return quick_info_manager.retrieve_quick_info(
            quick_info_id, quick_info_we_vote_id,
            contest_office_we_vote_id,
            candidate_campaign_we_vote_id,
            politician_we_vote_id,
            contest_measure_we_vote_id
        )

    def retrieve_quick_info_from_id(self, quick_info_id):
        quick_info_we_vote_id = None
        candidate_campaign_we_vote_id = None
        politician_we_vote_id = None
        contest_office_we_vote_id = None
        contest_measure_we_vote_id = None
        quick_info_manager = QuickInfoManager()
        return quick_info_manager.retrieve_quick_info(
            quick_info_id, quick_info_we_vote_id,
            contest_office_we_vote_id,
            candidate_campaign_we_vote_id,
            politician_we_vote_id,
            contest_measure_we_vote_id
        )

    def retrieve_quick_info_from_we_vote_id(self, quick_info_we_vote_id):
        quick_info_id = 0
        candidate_campaign_we_vote_id = None
        politician_we_vote_id = None
        contest_office_we_vote_id = None
        contest_measure_we_vote_id = None
        quick_info_manager = QuickInfoManager()
        return quick_info_manager.retrieve_quick_info(
            quick_info_id, quick_info_we_vote_id,
            contest_office_we_vote_id,
            candidate_campaign_we_vote_id,
            politician_we_vote_id,
            contest_measure_we_vote_id
        )

    def retrieve_quick_info(self, quick_info_id, quick_info_we_vote_id=None,
                            contest_office_we_vote_id=None,
                            candidate_campaign_we_vote_id=None,
                            politician_we_vote_id=None,
                            contest_measure_we_vote_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        quick_info_on_stage = QuickInfo()
        success = False

        try:
            if positive_value_exists(quick_info_id):
                status = "RETRIEVE_QUICK_INFO_FOUND_WITH_QUICK_INFO_ID"
                quick_info_on_stage = QuickInfo.objects.get(id=quick_info_id)
                quick_info_id = quick_info_on_stage.id
                success = True
            elif positive_value_exists(quick_info_we_vote_id):
                status = "RETRIEVE_QUICK_INFO_FOUND_WITH_WE_VOTE_ID"
                quick_info_on_stage = QuickInfo.objects.get(we_vote_id=quick_info_we_vote_id)
                quick_info_id = quick_info_on_stage.id
                success = True
            elif positive_value_exists(contest_office_we_vote_id):
                status = "RETRIEVE_QUICK_INFO_FOUND_WITH_OFFICE_WE_VOTE_ID"
                quick_info_on_stage = QuickInfo.objects.get(
                    contest_office_we_vote_id=contest_office_we_vote_id)
                quick_info_id = quick_info_on_stage.id
                success = True
            elif positive_value_exists(candidate_campaign_we_vote_id):
                status = "RETRIEVE_QUICK_INFO_FOUND_WITH_CANDIDATE_WE_VOTE_ID"
                quick_info_on_stage = QuickInfo.objects.get(
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
                quick_info_id = quick_info_on_stage.id
                success = True
            elif positive_value_exists(politician_we_vote_id):
                status = "RETRIEVE_QUICK_INFO_FOUND_WITH_POLITICIAN_WE_VOTE_ID"
                quick_info_on_stage = QuickInfo.objects.get(
                    politician_we_vote_id=politician_we_vote_id)
                quick_info_id = quick_info_on_stage.id
                success = True
            elif positive_value_exists(contest_measure_we_vote_id):
                status = "RETRIEVE_QUICK_INFO_FOUND_WITH_MEASURE_WE_VOTE_ID"
                quick_info_on_stage = QuickInfo.objects.get(
                    contest_measure_we_vote_id=contest_measure_we_vote_id)
                quick_info_id = quick_info_on_stage.id
                success = True
            else:
                status = "RETRIEVE_QUICK_INFO_INSUFFICIENT_VARIABLES"
        except QuickInfo.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = "RETRIEVE_QUICK_INFO_MULTIPLE_FOUND"
        except QuickInfo.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = "RETRIEVE_QUICK_INFO_NONE_FOUND"

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'quick_info_found':         True if quick_info_id > 0 else False,
            'quick_info_id':            quick_info_id,
            'quick_info':               quick_info_on_stage,
            'is_chinese':               quick_info_on_stage.is_chinese(),
            'is_english':               quick_info_on_stage.is_english(),
            'is_spanish':               quick_info_on_stage.is_spanish(),
            'is_tagalog':               quick_info_on_stage.is_tagalog(),
            'is_vietnamese':            quick_info_on_stage.is_vietnamese(),
        }
        return results

    def update_or_create_quick_info(self, quick_info_id, quick_info_we_vote_id,
                                    ballot_item_label,
                                    contest_office_we_vote_id,
                                    candidate_campaign_we_vote_id,
                                    politician_we_vote_id,
                                    contest_measure_we_vote_id,
                                    info_html,
                                    info_text,
                                    language,
                                    last_editor_we_vote_id,
                                    link_to_master_we_vote_id,
                                    more_info_url,
                                    site_to_credit,
                                    google_civic_election_id
                                    ):
        # Does a quick_info entry already exist?
        quick_info_manager = QuickInfoManager()
        results = quick_info_manager.retrieve_quick_info(quick_info_id, quick_info_we_vote_id,
                                                         contest_office_we_vote_id,
                                                         candidate_campaign_we_vote_id,
                                                         politician_we_vote_id,
                                                         contest_measure_we_vote_id)

        quick_info_on_stage_found = False
        quick_info_on_stage_id = 0
        quick_info_on_stage = QuickInfo()
        if results['quick_info_found']:
            quick_info_on_stage = results['quick_info']

            # Update this quick_info entry with new values - we do not delete because we might be able to use
            # noinspection PyBroadException
            try:
                if ballot_item_label is not False:
                    quick_info_on_stage.ballot_item_label = ballot_item_label
                if info_html is not False:
                    quick_info_on_stage.info_html = info_html
                if info_text is not False:
                    quick_info_on_stage.info_text = info_text
                if language is not False:
                    quick_info_on_stage.language = language
                if last_editor_we_vote_id is not False:
                    quick_info_on_stage.last_editor_we_vote_id = last_editor_we_vote_id
                if link_to_master_we_vote_id is not False:
                    quick_info_on_stage.link_to_master_we_vote_id = link_to_master_we_vote_id
                if more_info_url is not False:
                    quick_info_on_stage.more_info_url = more_info_url
                if site_to_credit is not False:
                    quick_info_on_stage.site_to_credit = site_to_credit
                if google_civic_election_id is not False:
                    quick_info_on_stage.google_civic_election_id = google_civic_election_id
                # We don't need to update date_last_changed here because set set auto_now=True in the field
                quick_info_on_stage.save()
                quick_info_on_stage_id = quick_info_on_stage.id
                quick_info_on_stage_found = True
                status = 'QUICK_INFO_UPDATED'
            except Exception as e:
                status = 'FAILED_TO_UPDATE_QUICK_INFO'
        elif results['MultipleObjectsReturned']:
            status = 'QUICK_INFO MultipleObjectsReturned'
        elif results['DoesNotExist']:
            try:
                # Create new quick_info entry
                # NOTE: For speed purposes, we are not validating the existence of the items being starred
                quick_info_on_stage = QuickInfo(
                    ballot_item_label=ballot_item_label,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                    politician_we_vote_id=politician_we_vote_id,
                    contest_measure_we_vote_id=contest_measure_we_vote_id,
                    info_html=info_html,
                    info_text=info_text,
                    language=language,
                    last_editor_we_vote_id=last_editor_we_vote_id,
                    link_to_master_we_vote_id=link_to_master_we_vote_id,
                    more_info_url=more_info_url,
                    site_to_credit=site_to_credit,
                    google_civic_election_id=google_civic_election_id
                    # We don't need to update last_updated here because set set auto_now=True in the field
                )
                quick_info_on_stage.save()
                quick_info_on_stage_id = quick_info_on_stage.id
                quick_info_on_stage_found = True
                status = 'CREATED_QUICK_INFO'
            except Exception as e:
                status = 'FAILED_TO_UPDATE_QUICK_INFO'
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status = results['status']

        results = {
            'success':            True if quick_info_on_stage_found else False,
            'status':             status,
            'quick_info_found':   quick_info_on_stage_found,
            'quick_info_id':      quick_info_on_stage_id,
            'quick_info':         quick_info_on_stage,
        }
        return results

    def delete_quick_info(self, quick_info_id):
        quick_info_id = convert_to_int(quick_info_id)
        quick_info_deleted = False

        try:
            if quick_info_id:
                results = self.retrieve_quick_info(quick_info_id)
                if results['quick_info_found']:
                    quick_info = results['quick_info']
                    quick_info_id = quick_info.id
                    quick_info.delete()
                    quick_info_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':            quick_info_deleted,
            'quick_info_deleted': quick_info_deleted,
            'quick_info_id':      quick_info_id,
        }
        return results


class QuickInfoMaster(models.Model):
    """
    Master data that can be applied to multiple ballot items
    """
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "infom" (for "info master"), and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_quick_info_master_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)

    # What kind of ballot item is this a master entry for? Mostly used so we can organize these entries
    kind_of_ballot_item = models.CharField(max_length=10, choices=KIND_OF_BALLOT_ITEM_CHOICES, default=OFFICE)

    # The language that this text is in
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default=ENGLISH)

    info_text = models.TextField(null=True, blank=True)
    info_html = models.TextField(null=True, blank=True)

    master_entry_name = models.CharField(verbose_name="text name for quick info master entry",
                                         max_length=255, null=True, blank=True)

    site_to_credit = models.CharField(max_length=15, choices=SOURCE_SITE_CHOICES, default=BALLOTPEDIA)

    # A link to any location with more information about this quick information
    more_info_url = models.URLField(blank=True, null=True, verbose_name='url with more the full entry for this info')

    last_updated = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)

    # The unique id of the last person who edited this entry.
    last_editor_we_vote_id = models.CharField(
        verbose_name="last editor we vote id", max_length=255, null=True, blank=True, unique=False)

    def __unicode__(self):
        return self.we_vote_id

    class Meta:
        ordering = ('last_updated',)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this organization came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_last_quick_info_master_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "infom" = tells us this is a unique id for a quick_info_master entry
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}infom{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(QuickInfoMaster, self).save(*args, **kwargs)

    def is_english(self):
        if self.language == ENGLISH:
            return True
        return False

    def is_spanish(self):
        if self.language == SPANISH:
            return True
        return False

    def is_vietnamese(self):
        if self.language == VIETNAMESE:
            return True
        return False

    def is_chinese(self):
        if self.language == CHINESE:
            return True
        return False

    def is_tagalog(self):
        if self.language == TAGALOG:
            return True
        return False


class QuickInfoMasterManager(models.Model):

    def __unicode__(self):
        return "QuickInfoMasterManager"

    def fetch_we_vote_id_from_local_id(self, quick_info_master_id):
        if positive_value_exists(quick_info_master_id):
            results = self.retrieve_quick_info_master_from_id(quick_info_master_id)
            if results['quick_info_master_found']:
                quick_info_master = results['quick_info_master']
                return quick_info_master.we_vote_id
            else:
                return None
        else:
            return None

    def retrieve_quick_info_master_from_id(self, quick_info_master_id):
        quick_info_master_we_vote_id = None
        quick_info_master_manager = QuickInfoMasterManager()
        return quick_info_master_manager.retrieve_quick_info_master(quick_info_master_id, quick_info_master_we_vote_id)

    def retrieve_quick_info_master_from_we_vote_id(self, quick_info_master_we_vote_id):
        quick_info_master_id = 0
        quick_info_master_manager = QuickInfoMasterManager()
        return quick_info_master_manager.retrieve_quick_info_master(quick_info_master_id, quick_info_master_we_vote_id)

    def retrieve_quick_info_master(self, quick_info_master_id, quick_info_master_we_vote_id=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        quick_info_master = QuickInfoMaster()
        success = False

        try:
            if positive_value_exists(quick_info_master_id):
                status = "RETRIEVE_QUICK_INFO_MASTER_FOUND_WITH_ID"
                quick_info_master = QuickInfoMaster.objects.get(id=quick_info_master_id)
                quick_info_master_id = quick_info_master.id
                success = True
            elif positive_value_exists(quick_info_master_we_vote_id):
                status = "RETRIEVE_QUICK_INFO_MASTER_FOUND_WITH_WE_VOTE_ID"
                quick_info_master = QuickInfoMaster.objects.get(we_vote_id=quick_info_master_we_vote_id)
                quick_info_master_id = quick_info_master.id
                success = True
            else:
                status = "RETRIEVE_QUICK_INFO_MASTER_INSUFFICIENT_VARIABLES"
        except QuickInfoMaster.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            success = False
            status = "RETRIEVE_QUICK_INFO_MASTER_MULTIPLE_FOUND"
        except QuickInfoMaster.DoesNotExist:
            error_result = False
            exception_does_not_exist = True
            success = True
            status = "RETRIEVE_QUICK_INFO_MASTER_NONE_FOUND"

        results = {
            'success':                  success,
            'status':                   status,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'quick_info_master_found':  True if quick_info_master_id > 0 else False,
            'quick_info_master_id':     quick_info_master_id,
            'quick_info_master':        quick_info_master,
            'is_chinese':               quick_info_master.is_chinese(),
            'is_english':               quick_info_master.is_english(),
            'is_spanish':               quick_info_master.is_spanish(),
            'is_tagalog':               quick_info_master.is_tagalog(),
            'is_vietnamese':            quick_info_master.is_vietnamese(),
        }
        return results

    def update_or_create_quick_info_master(self, quick_info_master_id, quick_info_master_we_vote_id,
                                           master_entry_name,
                                           info_html, info_text,
                                           language,
                                           kind_of_ballot_item,
                                           last_editor_we_vote_id,
                                           more_info_url,
                                           site_to_credit,
                                           ):
        # Does a quick_info_master entry already exist?
        quick_info_master_manager = QuickInfoMasterManager()
        results = quick_info_master_manager.retrieve_quick_info_master(quick_info_master_id,
                                                                       quick_info_master_we_vote_id)

        quick_info_master_found = False
        quick_info_master_id = 0
        quick_info_master = QuickInfoMaster()
        if results['quick_info_master_found']:
            quick_info_master = results['quick_info_master']

            # Update this quick_info_master entry with new values - we do not delete because we might be able to use
            # noinspection PyBroadException
            try:
                if master_entry_name is not False:
                    quick_info_master.master_entry_name = master_entry_name
                if info_html is not False:
                    quick_info_master.info_html = info_html
                if info_text is not False:
                    quick_info_master.info_text = info_text
                if language is not False:
                    quick_info_master.language = language
                if kind_of_ballot_item is not False:
                    quick_info_master.kind_of_ballot_item = kind_of_ballot_item
                if last_editor_we_vote_id is not False:
                    quick_info_master.last_editor_we_vote_id = last_editor_we_vote_id
                if more_info_url is not False:
                    quick_info_master.more_info_url = more_info_url
                if site_to_credit is not False:
                    quick_info_master.site_to_credit = site_to_credit
                # We don't need to update date_last_changed here because set set auto_now=True in the field
                quick_info_master.save()
                quick_info_master_id = quick_info_master.id
                quick_info_master_found = True
                status = 'QUICK_INFO_MASTER_UPDATED'
            except Exception as e:
                status = 'FAILED_TO_UPDATE_QUICK_INFO_MASTER'
        elif results['MultipleObjectsReturned']:
            status = 'QUICK_INFO_MASTER MultipleObjectsReturned'
        elif results['DoesNotExist']:
            try:
                # Create new quick_info_master entry
                # NOTE: For speed purposes, we are not validating the existence of the items being starred
                quick_info_master = QuickInfoMaster(
                    master_entry_name=master_entry_name,
                    info_html=info_html,
                    info_text=info_text,
                    language=language,
                    kind_of_ballot_item=kind_of_ballot_item,
                    last_editor_we_vote_id=last_editor_we_vote_id,
                    more_info_url=more_info_url,
                    site_to_credit=site_to_credit,
                    # We don't need to update last_updated here because set set auto_now=True in the field
                )
                quick_info_master.save()
                quick_info_master_id = quick_info_master.id
                quick_info_master_found = True
                status = 'CREATED_QUICK_INFO_MASTER'
            except Exception as e:
                status = 'FAILED_TO_UPDATE_QUICK_INFO_MASTER'
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status = results['status']

        results = {
            'success':                  True if quick_info_master_found else False,
            'status':                   status,
            'quick_info_master_found':  quick_info_master_found,
            'quick_info_master_id':     quick_info_master_id,
            'quick_info_master':        quick_info_master,
        }
        return results

    def delete_quick_info_master(self, quick_info_master_id):
        quick_info_master_id = convert_to_int(quick_info_master_id)
        quick_info_master_deleted = False

        try:
            if quick_info_master_id:
                results = self.retrieve_quick_info_master(quick_info_master_id)
                if results['quick_info_master_found']:
                    quick_info_master = results['quick_info_master']
                    quick_info_master_id = quick_info_master.id
                    quick_info_master.delete()
                    quick_info_master_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':                      quick_info_master_deleted,
            'quick_info_master_deleted':    quick_info_master_deleted,
            'quick_info_master_id':         quick_info_master_id,
        }
        return results
