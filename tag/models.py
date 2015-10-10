# tag/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from twitter.models import Tweet


class Tag(models.Model):
    """
    Any way that content is identified, added anywhere. Tags are never deleted, only TagLinks.
    Fields: hashtag_text, twitter_handle, keywords
    """
    hashtag_text = models.CharField(blank=True, null=True, max_length=255, verbose_name='the text for a single hashtag')
    twitter_handle = models.CharField(max_length=15,
                                      null=True, blank=True, verbose_name='twitter handle that we want to link to something')
    keywords = models.CharField(blank=True,
                                null=True, max_length=255, verbose_name='text that might be found in a tweet')

    # def __unicode__(self):
    #     return 'hashtag: %r, twitter_handle: %r, keywords: %r' % (self.hashtag_text, self.twitter_handle, self.keywords)
    #
    # class Meta:
    #     ordering = ('hashtag_text',)


# TODO Implement later
# class TagLinkConfirm(models.Model):
#     tag_link_id = models.ForeignKey(PoliticianTagLink, null=False, blank=False, verbose_name='tag link unique identifier')
#     voter_id = models.ForeignKey(Voter, null=False, blank=False, verbose_name='voter id')
#
#
# class TagLinkFlag(models.Model):
#     tag_link_id = models.ForeignKey(PoliticianTagLink, null=False, blank=False, verbose_name='tag link unique identifier')
#     voter_id = models.ForeignKey(Voter, null=False, blank=False, verbose_name='voter id')
#
#
# class TaggedTweet(models.Model):
#     tag_id = models.ForeignKey(Tag, null=False, blank=False, verbose_name='tag unique identifier')
#     tweet_id = models.ForeignKey(Tweet, null=False, blank=False, verbose_name='we vote unique identifier for tweet')
#
#
# class TaggedTweetConfirm(models.Model):
#     tagged_tweet_id = models.ForeignKey(TaggedTweet,
#                                         null=False, blank=False, verbose_name='tagged tweet unique identifier')
#     voter_id = models.ForeignKey(Voter, null=False, blank=False, verbose_name='voter id')
#
#
# class TaggedTweetFlag(models.Model):
#     tagged_tweet_id = models.ForeignKey(TaggedTweet,
#                                         null=False, blank=False, verbose_name='tagged tweet unique identifier')
#     voter_id = models.ForeignKey(Voter, null=False, blank=False, verbose_name='voter id')

