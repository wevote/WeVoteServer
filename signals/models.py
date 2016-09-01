# signals/elasticsearch.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import logging

from django.db.models.signals import post_save
from django.db.models.signals import post_delete
from django.core.signals import request_finished
from django.dispatch import receiver

from elasticsearch import Elasticsearch

from candidate.models import CandidateCampaign
from measure.models import ContestMeasure
from office.models import ContestOffice


@receiver(post_save)
def save_signal(**kwargs):
    print("#### post save!")
    print(kwargs)

@receiver(post_delete)
def delete_signal(sender, instance, **kwargs):
    print("#### post delete!")
    print(instance)
    print(kwargs)

#@receiver(request_finished)
# def request_signal(sender, **kwargs):
#     print("> request!")
#    print(kwargs)


# CandidateCampaign
@receiver(post_save, sender=CandidateCampaign)
def save_CandidateCampaign_signal(sender, instance, **kwargs):
    print("#### CandidateCampaign save!")
    print(instance)
    print(kwargs)

@receiver(post_delete, sender=CandidateCampaign)
def delete_CandidateCampaign_signal(sender, instance, **kwargs):
    print("#### CandidateCampaign delete!")
    print(instance)
    print(kwargs)

# CandidateCampaign
@receiver(post_save, sender=ContestMeasure)
def save_CandidateCampaign_signal(sender, instance, **kwargs):
    print("#### ContestMeasure save!")
    print(instance)
    print(kwargs)

@receiver(post_delete, sender=ContestMeasure)
def delete_CandidateCampaign_signal(sender, instance, **kwargs):
    print("#### ContestMeasure delete!")
    print(instance)
    print(kwargs)

# ContestOffice
@receiver(post_save, sender=ContestOffice)
def save_ContestOffice_signal(sender, instance, **kwargs):
    print("#### ContestOffice save!")
    print(instance)
    print(kwargs)

@receiver(post_delete, sender=ContestOffice)
def delete_ContestOffice_signal(sender, instance, **kwargs):
    print("#### ContestOffice delete!")
    print(instance)
    print(kwargs)
