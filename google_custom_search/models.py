# google_custom_search/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/models.py for the code that interfaces with twitter (or other) servers
import wevote_functions.admin
from django.db import models

from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists
from re import compile

logger = wevote_functions.admin.get_logger(__name__)
GOOGLE_SEARCH_ENGINE_ID = get_environment_variable("GOOGLE_SEARCH_ENGINE_ID")
GOOGLE_SEARCH_API_KEY = get_environment_variable("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_API_NAME = get_environment_variable("GOOGLE_SEARCH_API_NAME")
GOOGLE_SEARCH_API_VERSION = get_environment_variable("GOOGLE_SEARCH_API_VERSION")
BALLOTPEDIA_LOGO_URL = "ballotpedia-logo-square"
MAXIMUM_GOOGLE_SEARCH_USERS = 10
MAXIMUM_CHARACTERS_LENGTH = 1024

URL_PATTERNS_TO_IGNORE = [
    r"^https?://uk.linkedin.com",
    r"^https?://nz.linkedin.com",
    r"^https?://www.linkedin.com/pub/dir",
    r"^https?://www.facebook.com/events",
    r"^https?://twitter.com/\w+/status"
]

URL_PATTERNS_TO_IGNORE = [compile(pattern) for pattern in URL_PATTERNS_TO_IGNORE]


class GoogleSearchUser(models.Model):
    """
    These are Google search results that might match a candidate or organization
    """
    candidate_campaign_we_vote_id = models.CharField(verbose_name="candidate we vote id", max_length=255, unique=False)

    search_term_used = models.CharField(verbose_name="", max_length=255, unique=False)
    item_title = models.CharField(verbose_name="searched item title", max_length=255, null=True, blank=True)
    item_link = models.URLField(verbose_name="url where searched item pointing", null=True, blank=True)
    item_snippet = models.CharField(verbose_name="searched item snippet", max_length=1024, null=True, blank=True)
    item_image = models.URLField(verbose_name='image url for searched item', blank=True, null=True)
    item_formatted_url = models.URLField(verbose_name="item formatted url", null=True, blank=True)
    item_meta_tags_description = models.CharField(verbose_name="searched item meta tags description", max_length=1000,
                                                  null=True, blank=True)
    search_request_url = models.URLField(verbose_name="search request url", max_length=255, null=True, blank=True)
    from_ballotpedia = models.BooleanField(default=False, verbose_name="searched link from ballotpedia")
    from_facebook = models.BooleanField(default=False, verbose_name="searched link from facebook")
    from_linkedin = models.BooleanField(default=False, verbose_name="searched link from linkedin")
    from_twitter = models.BooleanField(default=False, verbose_name="searched link from twitter")
    from_wikipedia = models.BooleanField (default=False, verbose_name="searched link from wikipedia")
    not_a_match = models.BooleanField(default=False, verbose_name="this candidate does not match")
    likelihood_score = models.IntegerField(verbose_name="score for a match", null=True, unique=False)
    chosen_and_updated = models.BooleanField(default=False,
                                             verbose_name="when search detail updated in candidate table")
    facebook_search_found = models.BooleanField(default=False, verbose_name="user found from facebook search")
    facebook_name = models.CharField(verbose_name="name from facebook search", max_length=255, null=True, blank=True)
    facebook_emails = models.CharField(verbose_name="emails from facebook", max_length=255, null=True, blank=True)
    facebook_about = models.CharField(verbose_name="about from facebook", max_length=255, null=True, blank=True)
    facebook_location = models.CharField(verbose_name="location from facebook", max_length=255, null=True, blank=True)
    facebook_photos = models.CharField(verbose_name="photos from facebook", max_length=1024, null=True, blank=True)
    facebook_bio = models.CharField(verbose_name="bio from facebook", max_length=1024, null=True, blank=True)
    facebook_general_info = models.CharField(verbose_name="general information from facebook", max_length=1024,
                                             null=True, blank=True)
    facebook_description = models.CharField(verbose_name="description from facebook", max_length=1024,
                                            null=True, blank=True)
    facebook_features = models.CharField(verbose_name="features from facebook", max_length=255, null=True, blank=True)
    facebook_contact_address = models.CharField(verbose_name="contact address from facebook", max_length=255,
                                                null=True, blank=True)
    facebook_mission = models.CharField(verbose_name="mission from facebook", max_length=1024, null=True, blank=True)
    facebook_category = models.CharField(verbose_name="category from facebook", max_length=255, null=True, blank=True)
    facebook_website = models.URLField(verbose_name="website from facebook", null=True, blank=True)
    facebook_personal_info = models.CharField(verbose_name="personal information from facebook", max_length=1024,
                                              null=True, blank=True)
    facebook_personal_interests = models.CharField(verbose_name="personal interests from facebook", max_length=255,
                                                   null=True, blank=True)
    facebook_posts = models.CharField(verbose_name="posts from facebook", max_length=1024, null=True, blank=True)


class GoogleSearchUserManager(models.Manager):

    def __unicode__(self):
        return "TwitterUserManager"

    def update_or_create_google_search_user_possibility(self, candidate_campaign_we_vote_id, google_json, search_term,
                                                        likelihood_score, facebook_json=None, from_ballotpedia=False,
                                                        from_facebook=False, from_linkedin=False, from_twitter=False,
                                                        from_wikipedia=False):
        google_search_user_on_stage = None
        google_search_user_created = False
        try:
            google_search_user_on_stage, google_search_user_created = GoogleSearchUser.objects.update_or_create(
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                item_link=google_json['item_link'],
                defaults={
                    'likelihood_score':             likelihood_score,
                    'search_term_used':             search_term,
                    'from_ballotpedia':             from_ballotpedia,
                    'from_facebook':                from_facebook,
                    'from_linkedin':                from_linkedin,
                    'from_twitter':                 from_twitter,
                    'from_wikipedia':               from_wikipedia,
                    'item_title':                   google_json['item_title'],
                    'item_snippet':                 google_json['item_snippet'],
                    'item_image':                   google_json['item_image'],
                    'item_formatted_url':           google_json['item_formatted_url'],
                    'item_meta_tags_description':   google_json['item_meta_tags_description'],
                    'search_request_url':           google_json['search_request_url']
                    }
                )
            if positive_value_exists(facebook_json):
                if facebook_json['facebook_search_found']:
                    google_search_user_on_stage, google_search_user_updated = GoogleSearchUser.objects.update_or_create(
                        candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                        item_link=google_json['item_link'],
                        defaults={
                            'facebook_search_found':        facebook_json['facebook_search_found'],
                            'facebook_name':                facebook_json['name'],
                            'facebook_emails':              facebook_json['emails'],
                            'facebook_about':               facebook_json['about'],
                            'facebook_location':            facebook_json['location'],
                            'facebook_photos':              facebook_json['photos'][:MAXIMUM_CHARACTERS_LENGTH],
                            'facebook_bio':                 facebook_json['bio'][:MAXIMUM_CHARACTERS_LENGTH],
                            'facebook_general_info':        facebook_json['general_info'][:MAXIMUM_CHARACTERS_LENGTH],
                            'facebook_description':         facebook_json['description'][:MAXIMUM_CHARACTERS_LENGTH],
                            'facebook_features':            facebook_json['features'],
                            'facebook_contact_address':     facebook_json['contact_address'],
                            'facebook_mission':             facebook_json['mission'][:MAXIMUM_CHARACTERS_LENGTH],
                            'facebook_category':            facebook_json['category'],
                            'facebook_website':             facebook_json['website'],
                            'facebook_personal_info':       facebook_json['personal_info'][:MAXIMUM_CHARACTERS_LENGTH],
                            'facebook_personal_interests':  facebook_json['personal_interests'],
                            'facebook_posts':               facebook_json['posts'][:MAXIMUM_CHARACTERS_LENGTH]
                        }
                    )

            if google_search_user_created:
                status = "GOOGLE_SEARCH_USER_POSSIBILITY_CREATED"
            else:
                status = "GOOGLE_SEARCH_USER_POSSIBILITY_UPDATED"
            success = True

        except Exception as e:
            status = "GOOGLE_SEARCH_USER_POSSIBILITY_NOT_CREATED"
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'google_search_user':           google_search_user_on_stage,
            'google_search_user_created':   google_search_user_created
        }
        return results

    def retrieve_google_search_user_from_item_link(self, candidate_campaign_we_vote_id, item_link):
        google_search_user = GoogleSearchUser()
        try:
            if positive_value_exists(candidate_campaign_we_vote_id):
                google_search_user = GoogleSearchUser.objects.get(
                    candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                    item_link=item_link)
            success = True
            google_search_user_found = True
            status = "RETRIEVE_GOOGLE_SEARCH_USER_BY_WE_VOTE_ID"
        except GoogleSearchUser.DoesNotExist:
            google_search_user_found = False
            success = True
            status = "RETRIEVE_GOOGLE_SEARCH_USER_NOT_FOUND"
        except Exception as e:
            google_search_user_found = False
            success = False
            status = 'FAILED retrieve_googgle_search_user'

        results = {
            'success':                      success,
            'status':                       status,
            'google_search_user_found':     google_search_user_found,
            'google_search_user':           google_search_user,
        }
        return results

    def retrieve_google_search_users_list(self, candidate_campaign_we_vote_id):
        google_search_users_list = []
        try:
            google_search_users_queryset = GoogleSearchUser.objects.all()
            google_search_users_queryset = google_search_users_queryset.filter(
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id)
            google_search_users_list = google_search_users_queryset

            if len(google_search_users_list):
                status = "GOOGLE_SEARCH_USERS_LIST_FOUND"
                success = True
                google_search_users_found = True
            else:
                status = "GOOGLE_SEARCH_USERS_LIST_NOT_FOUND"
                success = True
                google_search_users_found = False
        except Exception as e:
            status = "FAILED_RETRIEVE_GOOGLE_SEARCH_USERS_LIST"
            success = False
            google_search_users_found = False
        results = {
            'success':                      success,
            'status':                       status,
            'google_search_users_found':    google_search_users_found,
            'google_search_users_list':     google_search_users_list,
        }
        return results

    def delete_google_search_users_possibilities(self, candidate_campaign_we_vote_id):
        try:
            GoogleSearchUser.objects.filter(candidate_campaign_we_vote_id=candidate_campaign_we_vote_id).delete()
            status = "GOOGLE_SEARCH_USERS_POSSIBILITY_DELETED"
            success = True
        except Exception as e:
            status = "GOOGLE_SEARCH_USERS_POSSIBILITY_NOT_DELETED"
            success = False

        results = {
            'success': success,
            'status': status,
        }
        return results

