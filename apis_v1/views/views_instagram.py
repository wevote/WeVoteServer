# apis_v1/views/views_instagram.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

import json
from urllib.parse import quote
from urllib.parse import urlencode
import wevote_functions.admin
#from wevote_functions.functions import get_voter_device_id, positive_value_exists
import requests
from instagrapi import Client


logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def instagram_sign_in_start_view(request): 
    #cl = Client()
    cl = Client(proxy='socks5://207.45.81.228:23863') #proxy due to public database being ip banned
    user = 'aaronforstate' #name of user on instagram
    cl.login('gamingguy2289', 'Rmu.Q/PQLQy%v_6')

    user_id = cl.user_id_from_username(user)
    print('########################################################################')
    #prints out all of users public information on account
    print(cl.user_info_by_username(user))
    #grabs the hd photo used for instagram profile picture
    temp = cl.user_info_by_username(user)
    print('###########################Prints the URL to the HD profile picture############################################')
    print(temp.profile_pic_url_hd)

    stuff = {
    'UserName'  : temp.username,
    'FullName'  : temp.full_name,
    'verified'  : temp.is_verified,
    'posts'     : temp.media_count,
    'followers' : temp.follower_count,
    'following' : temp.following_count,
    'bio'       : temp.biography,
    'profilePic': temp.profile_pic_url_hd,
    }

    #return HttpResponse(cl.user_id_from_username(user))
    return HttpResponse(json.dumps(stuff))

def instagram_sign_in_request_access_token_view(request):

    
    code = request.GET.get('code', '')
    client_id = '599015611785883'
    client_secret = '8c04837a59e6d5f218ca2cb3da3ec6a4'
    grant_type = 'authorization_code'
    redirect_uri = f'{WE_VOTE_SERVER_ROOT_URL}apis/v1/instagramSignInRequestAccessToken/'
  
    
    data = {
        'code'                 : code,
        'client_id'            : client_id,
        'client_secret'        : client_secret,
        'grant_type'           : grant_type,
        'redirect_uri'         : redirect_uri,
    }
    r = requests.post('https://api.instagram.com/oauth/access_token', data = data)
    return HttpResponse(r.text)

