# candidate/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception
from wevote_settings.models import fetch_next_id_we_vote_last_candidate_campaign_integer, fetch_site_unique_id_prefix
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class CandidateCampaignList(models.Model):
    """
    This is a class to make it easy to retrieve lists of Candidates
    """

    def retrieve_candidate_campaigns_for_this_election_list(self):
        candidates_list_temp = CandidateCampaign.objects.all()
        # Order by candidate_name.
        # To order by last name we will need to make some guesses in some case about what the last name is.
        candidates_list_temp = candidates_list_temp.order_by('candidate_name')
        candidates_list_temp = candidates_list_temp.filter(election_id=1)  # TODO Temp election_id
        return candidates_list_temp


class CandidateCampaign(models.Model):
    # The id_we_vote identifier is unique across all We Vote sites, and allows us to share our data with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "cand", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.id_we_vote_last_candidate_campaign_integer
    id_we_vote = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=True)
    id_maplight = models.CharField(
        verbose_name="maplight candidate id", max_length=255, default=None, null=True, blank=True, unique=True)
    # election link to local We Vote Election entry. During setup we need to allow this to be null.
    election_id = models.IntegerField(verbose_name="election unique identifier", null=True, blank=True)
    # The internal We Vote id for the ContestOffice that this candidate is competing for.
    # During setup we need to allow this to be null.
    contest_office_id = models.CharField(
        verbose_name="contest_office_id id", max_length=254, null=True, blank=True)
    # politician link to local We Vote Politician entry. During setup we need to allow this to be null.
    politician_id = models.IntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    # The candidate's name.
    candidate_name = models.CharField(verbose_name="candidate name", max_length=254, null=False, blank=False)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="party", max_length=254, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=254, null=True, blank=True)
    photo_url_from_maplight = models.URLField(verbose_name='candidate portrait url of candidate', blank=True, null=True)
    # The order the candidate appears on the ballot for this contest.
    order_on_ballot = models.CharField(verbose_name="order on ballot", max_length=254, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=254, null=True, blank=True)
    # The URL for the candidate's campaign web site.
    candidate_url = models.URLField(verbose_name='website url of candidate campaign', blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of candidate campaign', blank=True, null=True)
    twitter_url = models.URLField(verbose_name='twitter url of candidate campaign', blank=True, null=True)
    google_plus_url = models.URLField(verbose_name='google plus url of candidate campaign', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of candidate campaign', blank=True, null=True)
    # The email address for the candidate's campaign.
    email = models.CharField(verbose_name="candidate campaign email", max_length=254, null=True, blank=True)
    # The voice phone number for the candidate's campaign office.
    phone = models.CharField(verbose_name="candidate campaign email", max_length=254, null=True, blank=True)

    def fetch_photo_url(self):
        if self.photo_url_from_maplight:
            return self.photo_url_from_maplight
        elif self.photo_url:
            return self.photo_url
        else:
            return ""
            # "http://votersedge.org/sites/all/modules/map/modules/map_proposition/images/politicians/2662.jpg"
        # else:
        #     politician_manager = PoliticianManager()
        #     return politician_manager.fetch_photo_url(self.politician_id)

    # We override the save function so we can auto-generate id_we_vote
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique id_we_vote
        if self.id_we_vote:
            self.id_we_vote = self.id_we_vote.strip()
        if self.id_we_vote == "" or self.id_we_vote is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_id_we_vote_last_candidate_campaign_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "cand" = tells us this is a unique id for a CandidateCampaign
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.id_we_vote = "wv{site_unique_id_prefix}cand{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        if self.id_maplight == "":  # We want this to be unique IF there is a value, and otherwise "None"
            self.id_maplight = None
        super(CandidateCampaign, self).save(*args, **kwargs)


#
def mimic_google_civic_initials(name):
    modified_name = name.replace(' A ', ' A. ')
    modified_name = modified_name.replace(' B ', ' B. ')
    modified_name = modified_name.replace(' C ', ' C. ')
    modified_name = modified_name.replace(' D ', ' D. ')
    modified_name = modified_name.replace(' E ', ' E. ')
    modified_name = modified_name.replace(' F ', ' F. ')
    modified_name = modified_name.replace(' G ', ' G. ')
    modified_name = modified_name.replace(' H ', ' H. ')
    modified_name = modified_name.replace(' I ', ' I. ')
    modified_name = modified_name.replace(' J ', ' J. ')
    modified_name = modified_name.replace(' K ', ' K. ')
    modified_name = modified_name.replace(' L ', ' L. ')
    modified_name = modified_name.replace(' M ', ' M. ')
    modified_name = modified_name.replace(' N ', ' N. ')
    modified_name = modified_name.replace(' O ', ' O. ')
    modified_name = modified_name.replace(' P ', ' P. ')
    modified_name = modified_name.replace(' Q ', ' Q. ')
    modified_name = modified_name.replace(' R ', ' R. ')
    modified_name = modified_name.replace(' S ', ' S. ')
    modified_name = modified_name.replace(' T ', ' T. ')
    modified_name = modified_name.replace(' U ', ' U. ')
    modified_name = modified_name.replace(' V ', ' V. ')
    modified_name = modified_name.replace(' W ', ' W. ')
    modified_name = modified_name.replace(' X ', ' X. ')
    modified_name = modified_name.replace(' Y ', ' Y. ')
    modified_name = modified_name.replace(' Z ', ' Z. ')
    return modified_name


class CandidateCampaignManager(models.Model):

    def __unicode__(self):
        return "CandidateCampaignManager"

    def retrieve_candidate_campaign_from_id(self, candidate_campaign_id):
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id)

    def retrieve_candidate_campaign_from_id_we_vote(self, id_we_vote):
        candidate_campaign_id = 0
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id, id_we_vote)

    def fetch_candidate_campaign_id_from_id_we_vote(self, id_we_vote):
        candidate_campaign_id = 0
        candidate_campaign_manager = CandidateCampaignManager()
        results = candidate_campaign_manager.retrieve_candidate_campaign(candidate_campaign_id, id_we_vote)
        if results['success']:
            return results['candidate_campaign_id']
        return 0

    def retrieve_candidate_campaign_from_id_maplight(self, candidate_id_maplight):
        candidate_campaign_id = 0
        id_we_vote = ''
        candidate_campaign_manager = CandidateCampaignManager()
        return candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, id_we_vote, candidate_id_maplight)

    def retrieve_candidate_campaign_from_candidate_name(self, candidate_name):
        candidate_campaign_id = 0
        id_we_vote = ''
        candidate_id_maplight = ''
        candidate_campaign_manager = CandidateCampaignManager()

        results = candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, id_we_vote, candidate_id_maplight, candidate_name)
        if results['success']:
            return results

        # Try to modify the candidate name, and search again
        # MapLight for example will pass in "Ronald  Gold" for example
        candidate_name_try2 = candidate_name.replace('  ', ' ')
        results = candidate_campaign_manager.retrieve_candidate_campaign(
            candidate_campaign_id, id_we_vote, candidate_id_maplight, candidate_name_try2)
        if results['success']:
            return results

        # MapLight also passes in "Kamela D Harris" for example, and Google Civic uses "Kamela D. Harris"
        candidate_name_try3 = mimic_google_civic_initials(candidate_name)
        if candidate_name_try3 != candidate_name:
            results = candidate_campaign_manager.retrieve_candidate_campaign(
                candidate_campaign_id, id_we_vote, candidate_id_maplight, candidate_name_try3)
            if results['success']:
                return results

        # Otherwise return failed results
        return results

    # NOTE: searching by all other variables seems to return a list of objects
    def retrieve_candidate_campaign(
            self, candidate_campaign_id, id_we_vote=None, candidate_id_maplight=None, candidate_name=None):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        candidate_campaign_on_stage = CandidateCampaign()

        try:
            if candidate_campaign_id > 0:
                candidate_campaign_on_stage = CandidateCampaign.objects.get(id=candidate_campaign_id)
                candidate_campaign_id = candidate_campaign_on_stage.id
            elif len(id_we_vote) > 0:
                candidate_campaign_on_stage = CandidateCampaign.objects.get(id_we_vote=id_we_vote)
                candidate_campaign_id = candidate_campaign_on_stage.id
            elif candidate_id_maplight > 0 and candidate_id_maplight != "":
                candidate_campaign_on_stage = CandidateCampaign.objects.get(id_maplight=candidate_id_maplight)
                candidate_campaign_id = candidate_campaign_on_stage.id
            elif len(candidate_name) > 0:
                candidate_campaign_on_stage = CandidateCampaign.objects.get(candidate_name=candidate_name)
                candidate_campaign_id = candidate_campaign_on_stage.id
        except CandidateCampaign.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
        except CandidateCampaign.DoesNotExist:
            exception_does_not_exist = True

        results = {
            'success':                  True if candidate_campaign_id > 0 else False,
            'error_result':             error_result,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'candidate_campaign_found': True if candidate_campaign_id > 0 else False,
            'candidate_campaign_id':    candidate_campaign_id,
            'candidate_campaign':       candidate_campaign_on_stage,
        }
        return results
