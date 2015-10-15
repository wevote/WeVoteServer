# politician/admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.contrib import admin

# Register your models here.
from .models import Politician
# from .models import PoliticianTagLink
# from .models import PoliticianTagLinkDisputed


class PoliticianAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['first_name', 'middle_name', 'last_name', 'id_bioguide', 'id_thomas', 'id_lis', 'id_govtrack',
                           'id_opensecrets', 'id_votesmart', 'id_fec', 'id_cspan', 'wikipedia_id',
                           'ballotpedia_id', 'id_house_history', 'maplight_id', 'id_washington_post', 'id_icpsr',
                           'name_official_full', 'gender', 'birth_date']}),
    ]
    list_display = ('id', 'first_name', 'last_name', 'id_bioguide')
    list_filter = ['last_name']
    search_fields = ['first_name', 'last_name']

admin.site.register(Politician, PoliticianAdmin)

# An alternate way of adding database table so admin
# # Found on stackoverflow.com:
# # http://stackoverflow.com/questions/2223375/multiple-modeladmins-views-for-same-model-in-django-admin
# class TagLinkAdmin(admin.ModelAdmin):
#     fieldsets = [
#         (None, {'fields': ['tag_id', 'politician_id']}),
#     ]
#     list_display = ('id', 'tag_id', 'politician_id')
#     list_filter = ['politician_id']
#     search_fields = ['tag_id', 'politician_id']
#
#
# class TagLinkDisputedAdmin(admin.ModelAdmin):
#     fieldsets = [
#         (None, {'fields': ['tag_id', 'politician_id']}),
#     ]
#     list_display = ('id', 'tag_id', 'politician_id')
#     list_filter = ['politician_id']
#     search_fields = ['tag_id', 'politician_id']
#
# def create_modeladmin(modeladmin, model, name=None):
#     class  Meta:
#         proxy = True
#         app_label = model._meta.app_label
#
#     attrs = {'__module__': '', 'Meta': Meta}
#
#     newmodel = type(name, (model,), attrs)
#
#     admin.site.register(newmodel, modeladmin)
#     return modeladmin


# class MyPoliticianAdmin(TagAdmin):
#     def queryset(self, request):
#         return self.model.objects.filter(user=request.user)
#
#
# class MyTagLinkAdmin(TagLinkAdmin):
#     def queryset(self, request):
#         return self.model.objects.filter(user=request.user)
#
#
# class MyTagLinkDisputedAdmin(TagLinkDisputedAdmin):
#     def queryset(self, request):
#         return self.model.objects.filter(user=request.user)

# create_modeladmin(MyTagAdmin, name='My Tag', model=Tag) # NOTE: the "name" of each of these items need to differ from the class name to avoid a naming conflict
# create_modeladmin(MyTagLinkAdmin, name='My Tag Link', model=PoliticianTagLink)
# create_modeladmin(MyTagLinkDisputedAdmin, name='My Tag Link Disputed', model=PoliticianTagLinkDisputed)