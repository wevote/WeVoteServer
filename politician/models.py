# politician/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# Politician-related Models
from django.db import models
from exception.models import handle_record_found_more_than_one_exception
from tag.models import Tag
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


class Politician(models.Model):
    # We are relying on built-in Python id field
    # See this url for properties: https://docs.python.org/2/library/functions.html#property
    first_name = models.CharField(verbose_name="first name",
                                  max_length=255, default=None, null=True, blank=True)
    middle_name = models.CharField(verbose_name="middle name",
                                   max_length=255, default=None, null=True, blank=True)
    last_name = models.CharField(verbose_name="last name",
                                 max_length=255, default=None, null=True, blank=True)
    full_name_official = models.CharField(verbose_name="official full name",
                                          max_length=255, default=None, null=True, blank=True)
    # This is the politician's name from GoogleCivicCandidateCampaign
    full_name_google_civic = models.CharField(verbose_name="full name from google civic",
                                              max_length=255, default=None, null=True, blank=True)
    # This is the politician's name assembled from TheUnitedStatesIo first_name + last_name for quick search
    full_name_assembled = models.CharField(verbose_name="full name assembled from first_name + last_name",
                                           max_length=255, default=None, null=True, blank=True)

    FEMALE = 'F'
    GENDER_NEUTRAL = 'N'
    MALE = 'M'
    UNKNOWN = 'U'
    GENDER_CHOICES = (
        (FEMALE, 'Female'),
        (GENDER_NEUTRAL, 'Gender Neutral'),
        (MALE, 'Male'),
        (UNKNOWN, 'Unknown'),
    )

    gender = models.CharField("gender", max_length=1, choices=GENDER_CHOICES, default=UNKNOWN)

    birth_date = models.DateField("birth date", default=None, null=True, blank=True)
    # race = enum?
    # official_image_id = ??

    id_bioguide = models.CharField(verbose_name="bioguide unique identifier",
                                   max_length=200, null=True, unique=True)
    id_thomas = models.CharField(verbose_name="thomas unique identifier",
                                 max_length=200, null=True, unique=True)
    id_lis = models.CharField(verbose_name="lis unique identifier",
                              max_length=200, null=True, blank=True, unique=False)
    id_govtrack = models.CharField(verbose_name="govtrack unique identifier",
                                   max_length=200, null=True, unique=True)
    id_opensecrets = models.CharField(verbose_name="opensecrets unique identifier",
                                      max_length=200, null=True, unique=False)
    id_votesmart = models.CharField(verbose_name="votesmart unique identifier",
                                    max_length=200, null=True, unique=False)
    id_fec = models.CharField(verbose_name="fec unique identifier",
                              max_length=200, null=True, unique=True, blank=True)
    id_cspan = models.CharField(verbose_name="cspan unique identifier",
                                max_length=200, null=True, blank=True, unique=False)
    id_wikipedia = models.CharField(verbose_name="wikipedia url",
                                    max_length=500, default=None, null=True, blank=True)
    id_ballotpedia = models.CharField(verbose_name="ballotpedia url",
                                      max_length=500, default=None, null=True, blank=True)
    id_house_history = models.CharField(verbose_name="house history unique identifier",
                                        max_length=200, null=True, blank=True)
    id_maplight = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=200, null=True, unique=True, blank=True)
    id_washington_post = models.CharField(verbose_name="washington post unique identifier",
                                          max_length=200, null=True, unique=False)
    id_icpsr = models.CharField(verbose_name="icpsr unique identifier",
                                max_length=200, null=True, unique=False)
    tag_link = models.ManyToManyField(Tag, through='PoliticianTagLink')
    # The full name of the party the official belongs to.
    party = models.CharField(verbose_name="politician political party", max_length=254, null=True)
    state_code = models.CharField(verbose_name="politician home state", max_length=2, null=True)

    # id_bioguide, id_thomas, id_lis, id_govtrack, id_opensecrets, id_votesmart, id_fec, id_cspan, id_wikipedia,
    # id_ballotpedia, id_house_history, id_maplight, id_washington_post, id_icpsr, first_name, middle_name,
    # last_name, name_official_full, gender, birth_date

    def __unicode__(self):
        return self.last_name

    class Meta:
        ordering = ('last_name',)

    def display_full_name(self):
        if self.first_name and self.last_name:
            return self.first_name + " " + self.last_name
        elif self.full_name_google_civic:
            return self.full_name_google_civic
        elif self.full_name_official:
            return self.full_name_official
        else:
            return self.first_name + " " + self.last_name

    def fetch_photo_url(self):
        """
        fetch URL of politician's photo from TheUnitedStatesIo repo
        """
        if self.id_bioguide:
            url_str = 'https://theunitedstates.io/images/congress/225x275/{id_bioguide}.jpg'.format(
                id_bioguide=self.id_bioguide)
            return url_str
        else:
            return ""

    def is_female(self):
        return self.gender in self.FEMALE

    def is_gender_neutral(self):
        return self.gender in self.GENDER_NEUTRAL

    def is_male(self):
        return self.gender in self.MALE

    def is_gender_specified(self):
        return self.gender in (self.FEMALE, self.GENDER_NEUTRAL, self.MALE)


class PoliticianManager(models.Model):
    def __init__(self):
        # TODO Recommend by Hy Carrel
        pass

    def fetch_photo_url(self, politician_id):
        politician_manager = PoliticianManager()
        results = politician_manager.retrieve_politician(politician_id)

        if results['success']:
            politician = results['politician']
            return politician.fetch_photo_url()
        return ""

    def retrieve_politician(self, politician_id):  # , id_we_vote=None
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        politician_on_stage = Politician()
        politician_on_stage_id = 0
        try:
            if politician_id > 0:
                politician_on_stage = Politician.objects.get(id=politician_id)
                politician_on_stage_id = politician_on_stage.id
            # elif len(id_we_vote) > 0:
            #     politician_on_stage = Politician.objects.get(id_we_vote=id_we_vote)
            #     politician_on_stage_id = politician_on_stage.id
        except Politician.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
        except Politician.DoesNotExist:
            error_result = True
            exception_does_not_exist = True

        # politician_on_stage_found2 = politician_on_stage_id > 0  # TODO Why not this simpler case?
        politician_on_stage_found = True if politician_on_stage_id > 0 else False
        results = {
            'success':                      True if politician_on_stage_found else False,
            'politician_found':             politician_on_stage_found,
            'politician_id':                politician_on_stage_id,
            'politician':                   politician_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

# def delete_all_politician_data():
#     with open(LEGISLATORS_CURRENT_FILE, 'rU') as politicians_current_data:
#         politicians_current_data.readline()             # Skip the header
#         reader = csv.reader(politicians_current_data)   # Create a regular tuple reader
#         for index, politician_row in enumerate(reader):
#             if index > 3:
#                 break
#             politician_entry = Politician.objects.order_by('last_name')[0]
#             politician_entry.delete()


class PoliticianTagLink(models.Model):
    """
    A confirmed (undisputed) link between tag & item of interest.
    """
    tag = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier')
    politician = models.ForeignKey(Politician, null=False, blank=False, verbose_name='politician unique identifier')
    # measure_id
    # office_id
    # issue_id


class PoliticianTagLinkDisputed(models.Model):
    """
    This is a highly disputed link between tag & item of interest. Generated from 'tag_added', and tag results
    are only shown to people within the cloud of the voter who posted

    We split off how things are tagged to avoid conflict wars between liberals & conservatives
    (Deal with some tags visible in some networks, and not in others - ex/ #ObamaSucks)
    """
    tag = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier')
    politician = models.ForeignKey(Politician, null=False, blank=False, verbose_name='politician unique identifier')
    # measure_id
    # office_id
    # issue_id
