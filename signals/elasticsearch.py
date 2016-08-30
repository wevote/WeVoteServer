# signals/elasticsearch.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db.models.signals import post_save
from django.db.models.signals import post_delete
from django.core.signals import request_finished
from django.dispatch import receiver
#from voter.models import Voter

# @receiver(post_save, sender=Voter)
# def save_voter(**kwargs):
#     print("#### post save voter!")
#     print(kwargs)
#

@receiver(post_save)
def save_signal(**kwargs):
    print("#### post save!")
    print(kwargs)

@receiver(post_delete)
def delete_signal(sender, instance, **kwargs):
    print("#### post delete!")
    print(instance)
    print(kwargs)

@receiver(request_finished)
def request_signal(sender, **kwargs):
    print("#### post request!")
    print(kwargs)

print("### signals/elasticsearch start")