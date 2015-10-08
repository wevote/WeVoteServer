# apis_v1/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
import json

from voter.models import fetch_voter_id_from_voter_device_link, Voter, VoterManager, VoterDeviceLinkManager


def voter_retrieve_list(voter_device_id):

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id > 0:
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter_id = results['voter_id']
    else:
        # If we are here, return an indication that this voter_device_id is not recognized
        data = {
            'status': "VOTER_ID_DOES_NOT_EXIST",
            'voter_device_id': voter_device_id,
        }
        results = {
            'success': False,
            'json_data': data,
        }
        return results

    if voter_id:
        voter_list = Voter.objects.all()
        voter_list = voter_list.filter(id=voter_id)

        if len(voter_list):
            results = {
                'success': True,
                'voter_list': voter_list,
            }
            return results

    # Trying to mimic the Google Civic error codes scheme
    errors_list = [
        {
            'domain':  "TODO global",
            'reason':  "TODO reason",
            'message':  "TODO Error message here",
            'locationType':  "TODO Error message here",
            'location':  "TODO location",
        }
    ]
    error_package = {
        'errors':   errors_list,
        'code':     400,
        'message':  "Error message here",
    }
    data = {
        'error': error_package,
        'status': "VOTER_ID_COULD_NOT_BE_RETRIEVED",
        'voter_device_id': voter_device_id,
    }
    results = {
        'success': False,
        'json_data': data,
    }
    return results


def voter_count():

    voter_list = Voter.objects.all()
    # Add a filter to only show voters who have actually done something
    # voter_list = voter_list.filter(id=voter_id)

    # TODO DALE We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
    # a bottle neck as we have

    if voter_list.count():
        data = {
            'success': True,
            'voter_count': voter_list.count(),
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        data = {
            'success': False,
            'voter_count': 0,
        }
        return HttpResponse(json.dumps(data), content_type='application/json')


def voter_create(voter_device_id):
    if not voter_device_id \
            or len(voter_device_id) <= 70 \
            or len(voter_device_id) >= 90:
        data = {
            'status': "VALID_VOTER_DEVICE_ID_MISSING",
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    voter_id = 0
    # Make sure a voter record hasn't already been created for this
    existing_voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if existing_voter_id:
        data = {
            'status': "VOTER_ALREADY_EXISTS",
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(data), content_type='application/json')

    # Create a new voter and return the id
    voter_manager = VoterManager()
    results = voter_manager.create_voter()

    if results['voter_created']:
        voter = results['voter']

        # Now save the voter_device_link
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.save_new_voter_device_link(voter_device_id, voter.id)

        if results['voter_device_link_created']:
            voter_device_link = results['voter_device_link']
            voter_id_found = True if voter_device_link.voter_id > 0 else False

            if voter_id_found:
                voter_id = voter_device_link.voter_id

    if voter_id:
        data = {
            'status': "VOTER_CREATED",
            'voter_device_id': voter_device_id,
            'voter_id': voter_id,  # We may want to remove this after initial testing
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        data = {
            'status': "VOTER_NOT_CREATED",
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
