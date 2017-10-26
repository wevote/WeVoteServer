# google_custom_search/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/models.py for the code that interfaces with twitter (or other) servers
import wevote_functions.admin
from django.db import models

logger = wevote_functions.admin.get_logger(__name__)


class GoogleSearchUser(models.Model):
    """
    These are Google search results that might match a candidate or organization
    """
    candidate_campaign_we_vote_id = models.CharField(verbose_name="candidate we vote id", max_length=255, unique=False)

    search_term_used = models.CharField(verbose_name="", max_length=255, unique=False)
    item_title = models.CharField(verbose_name="searched item title", max_length=255, null=True, blank=True)
    item_link = models.URLField(verbose_name="url where searched item pointing", null=True, blank=True)
    item_snippet = models.CharField(verbose_name="searched item snippet", max_length=1000, null=True, blank=True)
    item_image = models.URLField(verbose_name='image url for searched item', blank=True, null=True)
    item_formatted_url = models.URLField(verbose_name="item formatted url", null=True, blank=True)
    item_meta_tags_description = models.CharField(verbose_name="searched item meta tags description", max_length=1000,
                                                  null=True, blank=True)
    search_request_url = models.URLField(verbose_name="search request url", null=True, blank=True)
    not_a_match = models.BooleanField(default=False, verbose_name="")
    likelihood_score = models.IntegerField(verbose_name="score for a match", null=True, unique=False)


class GoogleSearchUserManager(models.Model):

    def __unicode__(self):
        return "TwitterUserManager"

    def update_or_create_google_search_user_possibility(self, candidate_campaign_we_vote_id, google_json, search_term,
                                                        likelihood_score):
        try:
            GoogleSearchUser.objects.update_or_create(
                candidate_campaign_we_vote_id=candidate_campaign_we_vote_id,
                item_link=google_json['item_link'],
                defaults={
                    'likelihood_score':             likelihood_score,
                    'search_term_used':             search_term,
                    'item_title':                   google_json['item_title'],
                    'item_snippet':                 google_json['item_snippet'],
                    'item_image':                   google_json['item_image'],
                    'item_formatted_url':           google_json['item_formatted_url'],
                    'item_meta_tags_description':   google_json['item_meta_tags_description'],
                    'search_request_url':           google_json['search_request_url']
                    }
                )
            status = "GOOGLE_SEARCH_USER_POSSIBILITY_CREATED"
            success = True

        except Exception as e:
            status = "GOOGLE_SEARCH_USER_POSSIBILITY_NOT_CREATED"
            success = False

        results = {
            'success': success,
            'status': status,
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
