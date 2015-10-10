# twitter/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models


class TwitterUser(models.Model):
    """
    We cache the Twitter info for one handle here. NOTE: multiple accounts can be signed into same Twitter account
    """
    handle = models.CharField(max_length=15, unique=True, verbose_name='twitter handle')
    fullname = models.CharField(blank=True, null=True, max_length=80, verbose_name='full name of twitter user')
    is_group = models.BooleanField(default=False, verbose_name='is this a twitter group account')
    user_url = models.URLField(blank=True, null=True, verbose_name='url of user\'s website')
    bio_statement = models.CharField(blank=True, null=True, max_length=255, verbose_name='bio for user')
    icon_url = models.URLField(blank=True, null=True, verbose_name='url of user\'s profile icon')
    # image_id # We Vote image id after we pull in the image at the twitter icon_url


class Tweet(models.Model):
    """
    A tweet referenced somewhere by a We Vote tag. We store it (once - not every time it is referenced by a tag)
    locally so we can publish JSON from for consumption on the We Vote newsfeed.
    """
    # twitter_tweet_id # (unique id from twitter for tweet?)
    author_handle = models.CharField(max_length=15, verbose_name='twitter handle of this tweet\'s author')
    # (stored quickly before we look up voter_id)
    # author_voter_id = models.ForeignKey(Voter, null=True, blank=True, related_name='we vote id of tweet author')
    is_retweet = models.BooleanField(default=False, verbose_name='is this a retweet?')
    # parent_tweet_id # If this is a retweet, what is the id of the originating tweet?
    body = models.CharField(blank=True, null=True, max_length=255, verbose_name='')
    date_published = models.DateTimeField(null=True, verbose_name='date published')


class TweetFavorite(models.Model):
    """
    This table tells us who favorited a tweet
    """
    tweet_id = models.ForeignKey(Tweet, null=True, blank=True, verbose_name='we vote tweet id')
    # twitter_tweet_id # (unique id from twitter for tweet?)
    # TODO Should favorited_by_handle be a ForeignKey link to the Twitter User? I'm concerned this will slow saving,
    #  and it might be better to ForeignKey against voter_id
    favorited_by_handle = models.CharField(
        max_length=15, verbose_name='twitter handle of person who favorited this tweet')
    # (stored quickly before we look up voter_id)
    # favorited_by_voter_id = models.ForeignKey(
    # Voter, null=True, blank=True, related_name='tweet favorited by voter_id')
    date_favorited = models.DateTimeField(null=True, verbose_name='date favorited')


# This should be the master table
class TwitterWhoIFollow(models.Model):
    """
    Other Twitter handles that I follow, from the perspective of handle_of_me
    """
    handle_of_me = models.CharField(max_length=15, verbose_name='from this twitter handle\'s perspective...')
    handle_i_follow = models.CharField(max_length=15, verbose_name='twitter handle being followed')


# This is a we vote copy (for speed) of Twitter handles that follow me. We should have self-healing scripts that set up
#  entries in TwitterWhoIFollow for everyone following someone in the We Vote network, so this table could be flushed
#  and rebuilt at any time
class TwitterWhoFollowMe(models.Model):
    handle_of_me = models.CharField(max_length=15, verbose_name='from this twitter handle\'s perspective...')
    handle_that_follows_me = models.CharField(max_length=15, verbose_name='twitter handle of this tweet\'s author')
