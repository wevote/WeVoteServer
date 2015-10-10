# tag/admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import admin

# Register your models here.
from .models import Tag


class TagAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['hashtag_text', 'twitter_handle', 'keywords']}),
    ]
    list_display = ('id', 'hashtag_text', 'twitter_handle', 'keywords')
    list_filter = ['twitter_handle']
    search_fields = ['hashtag_text', 'twitter_handle', 'keywords']

admin.site.register(Tag, TagAdmin)
