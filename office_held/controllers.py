# office_held/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from office_held.models import OfficeHeldManager


def generate_office_held_dict_list_from_office_held_object_list(office_held_list=[]):
    office_held_dict_list = []
    status = ""
    success = True
    for office_held in office_held_list:
        one_office_dict = {
            'district_id':                  office_held.district_id,
            'district_name':                office_held.district_name,
            'ocd_division_id':              office_held.ocd_division_id,
            'office_held_id':               office_held.id,
            'office_held_description':      office_held.office_held_description,
            'office_held_facebook_url':     office_held.office_held_facebook_url,
            'office_held_name':             office_held.office_held_name,
            'office_held_twitter_handle':   office_held.office_held_twitter_handle,
            'office_held_url':              office_held.office_held_url,
            'office_held_we_vote_id':       office_held.we_vote_id,
            'race_office_level':            office_held.race_office_level,
            'state_code':                   office_held.state_code,
        }
        office_held_dict_list.append(one_office_dict)

    results = {
        'office_held_dict_list':    office_held_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results


def generate_office_held_dict_list_from_office_held_we_vote_id_list(
        office_held_we_vote_id_list=[]):
    office_held_dict_list = []
    office_held_manager = OfficeHeldManager()
    status = ""
    success = True
    if len(office_held_we_vote_id_list) > 0:
        results = office_held_manager.retrieve_office_held_list(
            office_held_we_vote_id_list=office_held_we_vote_id_list,
            read_only=True)
        if results['office_held_list_found']:
            office_held_list = results['office_held_list']
            results = generate_office_held_dict_list_from_office_held_object_list(office_held_list=office_held_list)
            status += results['status']
            if results['success']:
                office_held_dict_list = results['office_held_dict_list']

    results = {
        'office_held_dict_list':    office_held_dict_list,
        'status':                   status,
        'success':                  success,
    }
    return results
